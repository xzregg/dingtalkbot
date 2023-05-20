# -*- coding: utf-8 -*-
# @Time    : 2023/5/18 13:28 
# @Author  : xzr
# @File    : dingtalk.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
from dingtalkchatbot.chatbot import DingtalkChatbot as _DingtalkChatbot


class DingtalkChatbot(_DingtalkChatbot):
    def msg_open_type(self, url):
        return url


class MsgMakerDingtalkChatbot(DingtalkChatbot):
    """
    重写 post 方法直接返回消息结构
    """

    def post(self, data):
        return data
