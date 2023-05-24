# -*- coding: utf-8 -*-
# @Time    : 2023/5/19 16:50 
# @Author  : xzr
# @File    : test_chat_server.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
import time
from unittest import TestCase
from pprint import pprint
from unittest import TestCase
from cosplay import CustomerServiceRolePrompt, get_role_prompt
from chat_server import ChatGPT, ChatBotServer, Questions


# @Desc    :
class TestChatBotServer(TestCase):
    def test_process_command(self):
        """
    /q 列出当前队列
    /c 当前问题
    /add 按标题增加知识点,标题存在则覆盖更新 用法: /update 标题\n内容
    /del 删除知识点 用法: /del 标题
        :return:
        """
        chat_bot = ChatBotServer()
        cmd = '/q'
        res = chat_bot.process_command(cmd)
        print(res)
        cmd = '/c'
        res = chat_bot.process_command(cmd)
        print(res)

        cmd = '/add 这个是标题1 \n测试一下增加Faq文档 爱仕达低调低调撒打'
        res = chat_bot.process_command(cmd)
        print(res)
        time.sleep(1)
        cmd = '/add 这个是标题1 \n测试一下增加Faq文档,更改的内容'
        res = chat_bot.process_command(cmd)
        print(res)

    def test_delete_command(self):
        chat_bot = ChatBotServer()

        cmd = '/del 这个是标题1 \n测试一下增加Faq文档,更改的内容'
        res = chat_bot.process_command(cmd)
        print(res)
