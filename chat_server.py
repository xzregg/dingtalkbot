# -*- coding: utf-8 -*-
# @Time    : 2023/5/15 14:34 
# @Author  : xzr
# @File    : chat_server.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
import json
import signal
from collections import OrderedDict
from dataclasses import dataclass, field
import queue
import threading
import traceback

import httpx
import vthread as vthread
from decouple import config
from pandora.bots.legacy import State as _State, ChatPrompt
from pandora.bots.server import ChatBot

from pandora.openai.api import ChatGPT as _ChatGPT
from pandora.openai.utils import Console
import typing

from model import ConversationsModel, KnowledgeModel


class ChatGPT(_ChatGPT):
    def __init__(self, access_tokens=config('ACCESS_TOKEN', ''), proxy=None):
        if not isinstance(access_tokens, dict):
            access_tokens = {'default': access_tokens}
        super().__init__(access_tokens, proxy=proxy)

    def update_token(self, access_token):
        self.__init__(access_token)

    def _talk(self, prompt, model, message_id, parent_message_id, conversation_id=None, stream=True, token=None):
        data = {
                'action'           : 'next',
                'messages'         : [
                        {
                                'id'     : message_id,
                                'role'   : 'user',
                                'author' : {
                                        'role': 'user',
                                },
                                'content': {
                                        'content_type': 'text',
                                        'parts'       : [prompt],
                                },
                        }
                ],
                'model'            : model,
                'parent_message_id': parent_message_id,
        }

        if conversation_id:
            data['conversation_id'] = conversation_id

        return self.__request_conversation(data, token)

    async def _do_request_sse_(self, url, headers, data, queue, event):
        async with httpx.AsyncClient(verify=self.ca_bundle, proxies=self.proxy) as client:
            async with client.stream('POST', url, json=data, headers=headers, timeout=600) as resp:
                try:
                    async for line in self.__process_sse(resp):
                        queue.put(line)

                        if event.is_set():
                            await client.aclose()
                            break
                except Exception as e:
                    traceback.print_exc()
                    yield await self.__process_sse_except(resp)
                if event.is_set():
                    await client.aclose()
                queue.put(None)


class ChatBotServerException(Exception):
    def __init__(self, errmsg=''):
        self.errmsg = errmsg

    def __str__(self):
        return self.errmsg


class State(_State):
    def __init__(self, title=None, conversation_id=None, model_slug=None, user_prompt=ChatPrompt(),
                 chatgpt_prompt=ChatPrompt()):
        super().__init__(title, conversation_id, model_slug, user_prompt, chatgpt_prompt)
        self.prompt_map = OrderedDict()


@dataclass
class Questions:
    text: str
    data: dict
    callback: typing.Callable[[str, typing.Dict, str], None] = lambda q, r: r
    message_id: str = field(default_factory=ChatPrompt.gen_message_id)
    parent_id: str = ''
    hint: str = ''
    session_id: str = ''


class ChatBotServer(ChatBot):
    def __init__(self, chatgpt: ChatGPT = None):
        self.chatgpt = chatgpt
        self.token_key = self.chatgpt.default_token_key
        self.conversation_base = None
        self.state: State = None
        self.max_answer_num = 3
        self.questions_queue = queue.Queue(self.max_answer_num)
        self.current_question = None
        self.t = None
        self.is_stop = False

        self.model_slug = ''
        # 不生效
        # self.model_slug = 'gpt-3.5-turbo-0301'
        self.init_conversation()
        self.run()

    def is_full(self):
        return self.questions_queue.qsize() >= self.max_answer_num

    def get_size(self):
        return self.questions_queue.qsize()

    @vthread.thread()
    def _run(self):
        while 1:
            try:
                if self.is_stop:
                    break
                q: Questions = self.questions_queue.get()
                self.current_question = q.text
                if q.text and q.callback:
                    try:
                        result = self.talk(q)
                        q.callback(q, result)
                    except:
                        traceback.print_exc()
                self.current_question = None
            except Exception as e:
                traceback.print_exc()
                self.current_question = None

    def stop(self):
        self.is_stop = True

    def run(self):
        t = threading.Thread(target=self._run, args=())
        t.daemon = True
        t.start()
        self.t = t

    def set_state_prompt_map(self, q: Questions):
        self.state.prompt_map.setdefault(q.message_id, {'id': q.message_id, 'conversation_id': self.state.conversation_id, 'content': {'parts': [q.text]}, 'parent_id': q.parent_id})

    def add_async_talk(self, text, data: dict, callback: Questions.callback, parent_id=''):
        if not self.is_full():
            message_id = ChatPrompt.gen_message_id()
            q = Questions(text, data, callback, message_id, parent_id)
            self.questions_queue.put(q)
            self.set_state_prompt_map(q)
            return message_id
        else:
            return None
            # raise ChatBotServerException('回答队列已满')

    def init_conversation(self, title='钉钉'):
        """根据title初始化对话"""
        try:
            with open('conversations.json', 'rb') as fp:
                conversations = json.load(fp)
        except Exception as e:
            conversations = self.chatgpt.list_conversations(1, 10, token=self.token_key)
            with open('conversations.json', 'wb') as fp:
                json.dump(conversations, fp, ensure_ascii=False)
        if not conversations['total']:
            return None
        choices = ['c', 'r', 'dd']
        items = conversations['items']
        first_page = 0 == conversations['offset']
        last_page = (conversations['offset'] + conversations['limit']) >= conversations['total']
        conversation_id = ''
        for item in items:
            conversation_id = item['id']
            if item['title'].find(title) >= 0:
                self.conversation_base = item
                break
        if conversation_id:
            self.state = State(conversation_id=conversation_id)
            self.__load_conversation(conversation_id)

        else:
            self.__new_conversation()

    def __new_conversation(self):
        models = self.chatgpt.list_models(token=self.token_key)[0]
        self.state = State(model_slug=models['slug'])
        self.state.title = 'New Chat'

    def __load_conversation(self, conversation_id):
        try:
            with open(f'{conversation_id}.json', 'rb') as fp:
                result = json.load(fp)
        except Exception as e:
            result = self.chatgpt.get_conversation(conversation_id, token=self.token_key)
            with open(f'{conversation_id}.json', 'wb') as fp:
                json.dump(result, fp, ensure_ascii=False)
        current_node_id = result['current_node']
        nodes = []
        while True:
            node = result['mapping'][current_node_id]
            if not node.get('parent'):
                break
            nodes.insert(0, node)
            current_node_id = node['parent']
        self.state.title = result['title']
        merge = False
        for node in nodes:
            message = node['message']
            if 'model_slug' in message['metadata']:
                self.state.model_slug = self.model_slug or message['metadata']['model_slug']
            self.state.prompt_map[node['id']] = message
            role = message['author']['role'] if 'author' in message else message['role']
            self.state.prompt_map[node['id']] = message
            if 'user' == role:
                prompt = self.state.user_prompt
                self.state.user_prompts.append(ChatPrompt(message['content']['parts'][0], parent_id=node['parent'], message_id=node['id']))
            elif 'assistant' == role:
                prompt = self.state.chatgpt_prompt
                merge = 'end_turn' in message and message['end_turn'] is None
                self.state.prompt_map[node['parent']]['reply'] = message
            else:
                continue

            prompt.prompt = message['content']['parts'][0]
            prompt.parent_id = node['parent']
            prompt.message_id = node['id']
        pass

    def get_current_qsize_text(self):
        return '当前队列 %s/%s' % (self.questions_queue.qsize(), self.max_answer_num)

    def process_command(self, command, data: dict = None, callback: typing.Callable[[typing.Dict, str], None] = Questions.callback):
        cmd_split = command.strip().lower().split(maxsplit=1)

        command = cmd_split[0].strip()
        text = cmd_split[-1].strip()

        if '/q' == command:
            return self.get_current_qsize_text()
        elif '/c' == command:
            return '当前回答问题: %s' % self.current_question or '无'
        elif '/add' == command:
            return KnowledgeModel.index_from_text(text)
        elif '/del' == command:
            return KnowledgeModel.delete_from_title(text)
        elif '/send_id' == command:
            return f'你的发送id:{(data or {}).get("senderStaffid", "无")}'
        elif '/token' == command:
            token = text
            self.chatgpt.update_token(token)
            return '已更新Token'
        else:
            return self.get_print_usage()

    @staticmethod
    def get_print_usage():
        return '''
```
命令:
    /q 列出当前队列
    /c 当前问题
    /add 按标题增加知识点,标题存在则覆盖更新 用法: /add 标题\n内容
```
        '''

    def talk(self, q: Questions):
        prompt = q.text
        message_id = q.message_id
        parent_id = q.parent_id or self.state.chatgpt_prompt.message_id # 获取最后一次的 msg ID
        first_prompt = not self.state.conversation_id
        if self.state.edit_index:
            idx = self.state.edit_index - 1
            user_prompt = self.state.user_prompts[idx]
            self.state.user_prompt = ChatPrompt(prompt, parent_id=user_prompt.parent_id)
            self.state.user_prompts = self.state.user_prompts[0:idx]

            self.state.edit_index = None
        else:
            self.state.user_prompt = ChatPrompt(prompt, parent_id=parent_id, message_id=message_id)
        self.set_state_prompt_map(q)
        status, _, generator = self.chatgpt.talk(prompt, self.state.model_slug, self.state.user_prompt.message_id,
                                                 self.state.user_prompt.parent_id, self.state.conversation_id,
                                                 token=self.token_key)

        text = prompt.strip().split('\n')[-1][:16]
        Console.info_bh('==================== {} ===================='.format(text))
        content = self.__print_reply(status, generator, message_id)
        Console.info_bh('====================={}====================='.format("=" * len(text)))
        self.state.user_prompts.append(self.state.user_prompt)

        if first_prompt:
            new_title = self.chatgpt.gen_conversation_title(self.state.conversation_id, self.state.model_slug,
                                                            self.state.chatgpt_prompt.message_id, token=self.token_key)
            self.state.title = new_title
        ConversationsModel.create(self.state.prompt_map[message_id])
        return content

    def __print_reply(self, status, generator, message_id):
        if 200 != status:
            next(generator)
            return '网络发送错误 ,请稍后再试或联系管理员! %s' % status
            # raise Exception(status, next(generator))
        p = 0
        for result in generator:
            if result['error']:
                # raise Exception(result['error'])
                return result['error']

            if not result['message']:
                # raise Exception('miss message property.')
                return 'miss message property.'

            text = None
            message = result['message']
            if 'assistant' == message['author']['role']:
                text = message['content']['parts'][0][p:]
                p += len(text)
                content = message['content']['parts'][0]
            self.state.conversation_id = result['conversation_id']
            self.state.chatgpt_prompt.prompt = message['content']['parts'][0]
            self.state.chatgpt_prompt.parent_id = self.state.user_prompt.message_id
            self.state.chatgpt_prompt.message_id = message['id']
            message['conversation_id'] = result['conversation_id']
            message['parent_id'] = message_id
            if 'system' == message['author']['role']:
                self.state.user_prompt.parent_id = message['id']
            if text:
                Console.success(text, end='')
            self.state.prompt_map[message['id']] = message
            self.state.prompt_map[message_id]['reply'] = message
        print('\n')
        return content
