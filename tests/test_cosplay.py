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
        text = '傻逼'

        role_prompt = get_role_prompt('', text)
        text = role_prompt.get_text()
        print(role_prompt.errmsg,text)
        chat_bot = ChatBotServer()
        res = chat_bot.talk(Questions(text, {}))
        # print(res)
