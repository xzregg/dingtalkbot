# -*- coding: utf-8 -*-
# @Time    : 2023/5/17 14:35 
# @Author  : xzr
# @File    : role.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
from decouple import config
from typing import List

from model import KnowledgeModel


class BaseRole(object):
    keyword = []
    base_cue_word_tpl = ''

    def check_active_prompt(self, keyword, prompt):
        return False

    def get_prompt(self, prompt):
        return '', self.base_cue_word_tpl.format(prompt=prompt)


class CustomerServiceRole(BaseRole):
    active_keyword_list = ['客服', '支援', 'Faq', '朴食']
    base_cue_word_tpl = '''
你是技术顾问,我会给你几段文档内容,"Title:"是标题,"Link:"是访问链接,"Content:"是内容,你根据文档内容回复我的问题。请注意,回复风格必须专业简练,不需要客套和礼貌,如果对内容逻辑理解不清晰则直接复制"Content:"后面那段内容,而且不需要额外解释,如果回复内容包含密码等敏感信息,使用"***"替换,以下是内容:
------------
{qa_text}
------------
内容结束,我的提问是: 
{prompt} ?
'''

    def check_active_prompt(self, keyword, prompt):
        for k in self.active_keyword_list:
            if keyword.find(k) >= 0:
                return prompt
            ki = prompt.find(k)
            if ki >= 0:
                prompt = prompt[ki + len(k):]
                return prompt

    def get_prompt(self, prompt):
        """
        标题高亮则用 选取所有内容
        如果内容高亮则只选高亮内容
        :param prompt:
        :return:
        """
        res = KnowledgeModel.search(prompt)
        qa_list = []
        token_size = 0
        for item in res.get('hits', []):
            q = item['highlight'].get('title', '')
            a = item['highlight'].get('content', '')
            if q:
                a = item['_source'].get('content')
            q = '\n'.join(q) if isinstance(q, list) else q
            a = '\n'.join(a) if isinstance(q, list) else a
            token_size += len(q) + len(a)
            if token_size >= 4000:
                break
            if q and a:
                qa_list.append(f'''
    Title: {q.strip()}
    Link:
    Content: {a.strip()} 
    ''')
        cue_prompt = self.base_cue_word_tpl.format(qa_text=''.join(qa_list), prompt=prompt).strip() if qa_list else ''
        if not cue_prompt:
            return f'很抱歉，我们的知识库中没有与 {prompt} 相关的内容，请添加相关信息后再尝试搜索。',prompt
        else:
            return '', self.base_cue_word_tpl.format(qa_text=''.join(qa_list), prompt=prompt).strip() if qa_list else prompt


class SensitiveRole(BaseRole):
    SENSITIVE_WORDS = config('SENSITIVE_WORDS', '').split(',')

    def check_active_prompt(self, keyword, prompt):
        return prompt

    def get_prompt(self, prompt):
        for k in self.SENSITIVE_WORDS:
            if prompt.find(k) >= 0:
                return '请不要使用包含敏感词汇的词语，这些词汇可能会引起不必要的冲突或误解。', prompt
        return '', prompt


role_list: List[BaseRole] = [
        SensitiveRole(),
        CustomerServiceRole()
]


def get_role_prompt(active_text: str, prompt: str) -> (str, str):
    errmsg = ''
    for role in role_list:
        active_prompt = role.check_active_prompt(active_text, prompt)
        if active_prompt:
            prompt = active_prompt
            errmsg, prompt = role.get_prompt(prompt)
            if errmsg:
                break
    return errmsg, prompt.strip()
