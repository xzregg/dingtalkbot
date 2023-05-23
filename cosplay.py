# -*- coding: utf-8 -*-
# @Time    : 2023/5/17 14:35 
# @Author  : xzr
# @File    : role.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
from typing import List

from decouple import config

from model import KnowledgeModel


class BaseRole(object):
    keyword = []
    base_cue_word_tpl = ''

    def check_active_prompt(self, keyword, prompt):
        return False

    def get_prompt_tpl(self, prompt):
        return '', '%s'


class CustomerServiceRole(BaseRole):
    active_keyword_list = ['客服', '支援', 'Faq', '朴食']
    base_cue_word_tpl = '''
我会给你一些知识文档内容,格式为"Title:"是标题,"Link:"是访问链接,"Content:"是内容,你根据知识文档回复我的问题。
请注意,1.回复风格必须专业简练. 2.不需要客套和礼貌,更不需要在最后加上额外解释 3.如果回复内容包含密码等敏感信息,使用"***"替换. 
4.如果从内容中找不到答案或理解不清楚则直接回复在"Content:"后面的那段内容.
5.最后加上所有与问题相关"Link:"的访问链接
以下是知识内容:
------------
{qa_text}
------------
内容结束,我的提问是: 
%s
'''

    def check_active_prompt(self, keyword, prompt):
        for k in self.active_keyword_list:
            if keyword.find(k) >= 0:
                return prompt
            ki = prompt.find(k)
            if ki >= 0:
                prompt = prompt[ki + len(k):]
                return prompt

    def to_str(self, s_list):
        return ''.join(s_list)

    def get_prompt_tpl(self, prompt):
        """
        标题高亮则用 选取所有内容
        如果内容高亮则只选高亮内容
        :param prompt:
        :return:
        """
        res = KnowledgeModel.search(prompt, size=3)
        qa_list = []
        token_size = 0
        for item in res.get('hits', []):
            q = self.to_str(item['highlight'].get('title', ''))
            a = self.to_str(item['highlight'].get('content', ''))
            q_s = self.to_str(item['_source'].get('title', ''))
            a_s = self.to_str(item['_source'].get('content', ''))
            if q:
                a = a or a_s
            else:
                q = q_s
            if len(a) < 500:
                a = a_s

            text = f'''
Title: {q.strip()}
Link:
Content: {a.strip()} 
            '''
            token_size += len(text)
            qa_list.append(text)
            if token_size >= 4000:
                break
        qa_text = self.to_str(qa_list)[:4000]
        cue_prompt = self.base_cue_word_tpl.format(qa_text=qa_text).strip() if qa_list else ''
        if cue_prompt:
            return '', cue_prompt
        return f'很抱歉，我们的知识库中没有与 {prompt} 相关的内容，请添加相关信息后再尝试搜索。', ''


class SensitiveRole(BaseRole):
    SENSITIVE_WORDS = config('SENSITIVE_WORDS', '').split(',')

    def check_active_prompt(self, keyword, prompt):
        return prompt

    def get_prompt_tpl(self, prompt):
        for k in self.SENSITIVE_WORDS:
            if prompt.find(k) >= 0:
                return '请不要使用包含敏感词汇的词语，这些词汇可能会引起不必要的冲突或误解。', ''
        return '', '%s'


role_list: List[BaseRole] = [
        SensitiveRole(),
        CustomerServiceRole()
]


def get_role_prompt(active_text: str, prompt: str) -> (str, str):
    errmsg = ''
    hint_prompt = '%s'
    for role in role_list:
        active_prompt = role.check_active_prompt(active_text, prompt)
        if active_prompt:
            prompt = active_prompt
            errmsg, hint_prompt = role.get_prompt_tpl(prompt)
            if errmsg:
                break
    return errmsg, hint_prompt, prompt
