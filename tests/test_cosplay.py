# -*- coding: utf-8 -*-
# @Time    : 2023/5/17 15:15 
# @Author  : xzr
# @File    : test_role.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
from pprint import pprint
from unittest import TestCase
from cosplay import CustomerServiceRole, get_role_prompt
from chat_server import ChatGPT, ChatBotServer, Questions


# @Desc    :
class TestCustomerService(TestCase):
    def test_get_prompt(self):
        text = '朴食技术部规范'
        errmsg, prompt = get_role_prompt('', text)
        errmsg, prompt = get_role_prompt(text, '技术部详细规范')
        print(prompt, len(prompt))
        chat_bot = ChatBotServer(ChatGPT())
        res = chat_bot.talk(Questions(prompt, {}))
        #print(res)
