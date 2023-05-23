# -*- coding: utf-8 -*-
# @Time    : 2023/5/17 15:15 
# @Author  : xzr
# @File    : test_role.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
from unittest import TestCase

from chat_server import Questions, ChatBotServer
from cosplay import get_role_prompt


# @Desc    :
class TestCustomerService(TestCase):
    def test_get_prompt(self):
        text = '朴食 用户注册'
        # errmsg,hint_prompt, prompt = get_role_prompt('', text)
        # errmsg, hint_prompt,prompt = get_role_prompt(text, '用户注册')
        # print(errmsg, len(prompt), prompt)
        errmsg, hint_prompt, prompt = get_role_prompt('', text)
        print(errmsg, len(prompt), hint_prompt.replace("%s", prompt))
        chat_bot = ChatBotServer()
        res = chat_bot.talk(Questions(prompt, {}))
        # print(res)
