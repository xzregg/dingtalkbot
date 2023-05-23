import asyncio
import base64
import hashlib
import hmac
import html
import json
import signal
import time
import urllib
from typing import Any

import addict
import uvicorn
import xmltodict
from fastapi import Body, Request
from fastapi import FastAPI, Response
from fastapi import Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from wechatpy.utils import to_text

from chat_server import ChatBotServer, Questions
from cosplay import SensitiveRole
from dingtalk import DingtalkChatbot, MsgMakerDingtalkChatbot
from model import ConversationsModel
from sdk.wxbot.WXBizMsgCrypt import WXBizMsgCrypt

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

gpt_bot = ChatBotServer()
ding_msg_maker = MsgMakerDingtalkChatbot('')


@app.post('/qywx')
async def qywx_post(body: dict = Body(...), request: Request = None) -> Any:
    return ''


@app.get('/qywx')
async def qywx(msg_signature: str = '', timestamp: str = 0, nonce: str = "", echostr: str = "", request: Request = None) -> Any:
    token = '1aDGY0Oo198F'
    aeskey = 'g9FabMlWDXbBHYUHabj1pAdgu39oeyB53hXXQzEfLGs'
    sCorpID = 'ww518bb40fac29ee08'
    wxcpt = WXBizMsgCrypt(token, aeskey, sCorpID)
    ret, sEchoStr = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
    message = sEchoStr
    return Response(message)


@app.post('/wxbot')
async def wxbot(body: dict = Body(...), request: Request = None) -> Any:
    """
    https://developers.weixin.qq.com/doc/aispeech/confapi/thirdkefu/recivemsg.html#%E5%AF%B9%E8%AF%9D%E6%9D%A5%E6%BA%90-from
    :param body:
    :param request:
    :return:
    """

    APPID = 'oaOlEBSG41q5X2v'
    Token = 'i1b1JNJTL3w56t5vQdSh87r7n4YZoP'
    AESKey = 'LOzU5mgPDnUSUrqOjZBpP8yNAsRj5MGSw6OH6K7YFuU'
    encrypted_b64 = body.get('encrypted')
    wx_bot = WXBizMsgCrypt(Token, AESKey, APPID)
    ret, decryp_xml = wx_bot.Decrypt(encrypted_b64)
    if ret == 0:
        # {'userid': '5m5WQGyzDqj', 'appid': 'i1b1JNJTL3w56t5vQdSh87r7n4YZoP', 'content': {'msg': 'asd'}, 'from': '0', 'status': '0', 'kfstate': '0', 'channel': '7', 'msgtype': 'text', 'assessment': None, 'waiterid': 'i1b1JNJTL3w56t5vQdSh87r7n4YZoP', 'waitername': None, 'waiteravatar': None, 'createtime': '1684742325250'}
        data = xmltodict.parse(to_text(decryp_xml))['xml']
        userid = data['userid']
        channel = data['channel']
        text = data['content'].get('msg', '')
        event = data.get('event')
        if data['from'] == '0' and isinstance(text, str) and text:
            def send_msg(q: Questions, reply):
                wx_bot.send_msg(reply, userid, channel)

            msg = gpt_bot.check_talk(text.strip(), data, userid, '', send_msg)
            ret = wx_bot.send_msg(msg, userid, channel)
    return ret


@app.get('/')
async def dinkbot_get(request: Request = None):
    timestamp = str(round(time.time() * 1000))
    secret = 'fmmYochm6pkpvRs_PwGAH6tsTko3RvWXaSeRcSKPX_z8huWCertFbnQwOEfIDJTu'
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    print(timestamp)
    print(sign)
    return Response(sign)


@app.post('/dinkbot')
async def dinkbot(body: dict = Body(...), request: Request = None) -> Any:
    """
    {
    "conversationId": "xxx",
    "atUsers": [
        {
            "dingtalkId": "xxx",
            "staffId":"xxx"
        }
    ],
    "chatbotCorpId": "dinge8a565xxxx",
    "chatbotUserId": "$:LWCP_v1:$Cxxxxx",
    "msgId": "msg0xxxxx",
    "senderNick": "杨xx",
    "isAdmin": true,
    "senderStaffId": "user123",
    "sessionWebhookExpiredTime": 1613635652738,
    "createAt": 1613630252678,
    "senderCorpId": "dinge8a565xxxx",
    "conversationType": "2",
    "senderId": "$:LWCP_v1:$Ff09GIxxxxx",
    "conversationTitle": "机器人测试-TEST",
    "isInAtList": true,
    "sessionWebhook": "https://oapi.dingtalk.com/robot/sendBySession?session=xxxxx",
    "text": {
        "content": " 你好"
    },
    "msgtype": "text"
}
    """

    data = addict.Addict(body)
    msgtype = data.msgtype
    is_group_chat = data.conversationTitle
    msg = '请问有什么可能帮助您,请@我!'
    if msgtype == 'text':
        text = data.text.content
    elif msgtype == 'richText':
        text = data.content.richText[0].text
    else:
        text = ''
        msg = '不支持的消息类型'

    senderStaffId = data.senderStaffId
    at_dingtalk_ids = [senderStaffId] if senderStaffId else []
    at_text = ('@' + ('@'.join(at_dingtalk_ids)) if at_dingtalk_ids and is_group_chat else '')
    is_at_all = not at_dingtalk_ids
    text = text.strip()

    conversationTitle = data.conversationTitle
    if text:
        def send_ding(q: Questions, reply):
            prompt = q.text
            data = q.data
            _is_at_all = is_at_all
            _at_text = at_text
            _at_dingtalk_ids = at_dingtalk_ids
            if (prompt.find('@all') >= 0 or prompt.find('@所有人') >= 0) and is_group_chat:
                _at_dingtalk_ids = []
                _at_text = ''
                _is_at_all = True
            prompt = prompt.strip().split('\n')[-1][-50:]
            # reply = html.escape(reply)
            prompt_link = gpt_bot.generate_prompt_link(q.message_id)
            DingtalkChatbot(data['sessionWebhook']).send_markdown(f'{prompt}', f'>{_at_text} [{prompt}]({prompt_link}):\n\n{reply}', at_dingtalk_ids=_at_dingtalk_ids, is_at_all=_is_at_all)

        msg = gpt_bot.check_talk(text, data, senderStaffId, conversationTitle, send_ding)

    return ding_msg_maker.send_markdown(msg, f'{at_text} {msg}', at_dingtalk_ids=at_dingtalk_ids, is_at_all=is_at_all)


@app.post('/api/prompt')
async def gpt_prompt(body: dict = Body(...), request: Request = None):
    prompt_id = body.get('id', '')
    result = gpt_bot.state.prompt_map.get(prompt_id)
    if not result:
        result = ConversationsModel.get_index(prompt_id)
        if result:
            gpt_bot.state.prompt_map[prompt_id] = result
    return JSONResponse(result)


@app.post('/api/session_list')
async def get_session_list(body: dict = Body(...), request: Request = None):
    sid = body.get('sid', '')
    result = ConversationsModel.search({'term': {'session_id': sid}}, size=20)['hits']
    result = [item['_source'] for item in result]
    return JSONResponse(result)


@app.post("/api/chat-process")
async def chat_process(body: dict = Body(...), request: Request = None):
    """ 额外的对话
    data: {"id":"chatcmpl-6r3B875xFqmzK9lMm8sousVO3iBN4","object":"chat.completion.chunk","created":1678101622,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}
    :param request:
    :return:
    """
    prompt_id = request.query_params.get('id', '') or body.get('id')
    prompt = body.get('prompt', '').strip()
    conversationId = body.get('options', {}).get('conversationId', '')
    parentMessageId = body.get('options', {}).get('parentMessageId', '')
    session_id = body.get('options', {}).get('sid', '')

    data = {}
    data['end'] = False
    data['id'] = prompt_id
    if not prompt_id and prompt:
        errmsg, hint_prompt = SensitiveRole().get_prompt_tpl(prompt)
        if errmsg:
            data['text'] = errmsg
            data['end'] = True
        else:
            text = hint_prompt % prompt
            prompt_id = gpt_bot.add_async_talk(text, body, lambda d, s: '', parentMessageId, hint=hint_prompt, session_id=session_id)
            if not prompt_id:
                data['text'] = '机器人提交失败,请稍后再提问!'
                data['end'] = True

    delay = 0.1

    async def generate():
        index = 0
        while 1:
            index += 1
            data['conversationId'] = gpt_bot.state.conversation_id
            result = gpt_bot.state.prompt_map.get(prompt_id)
            # 暂时不清楚有什么用
            data['detail'] = {"choices": [{"delta": {"content": ""}, "index": index, "finish_reason": None}]}
            if result:
                reply = result.get('reply')
                if reply:
                    content = reply['content']['parts'][0]
                    data['id'] = reply['id']
                    data['text'] = content
                    if reply['status'] == 'finished_successfully':
                        data['end'] = True
            else:
                if index * delay > 60 * 2:
                    data['text'] = '超过2分钟还没处理,请重重试'
                    data['end'] = True
            rsp = json.dumps(data, ensure_ascii=False)
            yield f'{rsp}\n'
            if data['end']:
                break
            data['end'] = False
            await asyncio.sleep(delay)

    headers = {
            "Content-Type": "application/octet-stream",
            # "Transfer-Encoding": "chunked",
    }

    return StreamingResponse(generate(), headers=headers)


@app.get('/prompt')
async def gpt_prompt(content_type: str = Header(None), request: Request = None):
    prompt_id = request.query_params.get('id', '')
    result = gpt_bot.state.prompt_map.get(prompt_id)

    if content_type and content_type.find('json') >= 0:
        return Response(json.dumps(result))

    meta = '<meta http-equiv="refresh" content="1">'
    prompt_text = title = content = '回答中...'

    if result:
        prompt_text = result['content']['parts'][0].strip().split('\n')[-1][-50:]
        reply = result.get('reply')
        if reply:
            content = reply['content']['parts'][0]
            content = html.escape(content)
            if reply['status'] == 'finished_successfully':
                meta = ''
                title = '完成'
    rsp = f'''
    <!DOCTYPE html>
<html>
<style>
p {{margin:0px}}
pre {{margin:0px}}
</style>
<head>
	<meta charset="UTF-8">
	<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
	<link href="https://cdn.bootcss.com/highlight.js/9.18.1/styles/monokai-sublime.min.css" rel="stylesheet">
    <script src="https://cdn.bootcss.com/highlight.js/9.18.1/highlight.min.js"></script>
	<title>{title}</title>
	{meta}
</head>
<body>
<pre>
{prompt_text} :
</pre>
<hr>
<pre id="markdown">
{content}
</pre>
</body>
<script>
let markdown = document.getElementById('markdown');
//markdown.innerHTML = marked.parse(markdown.innerText);
//hljs.initHighlightingOnLoad();
</script>
</html>
    '''
    return Response(rsp)


def signal_handler(signum, frame):
    gpt_bot.stop()
    print('Signal handler called with signal', signum)


if __name__ == "__main__":
    # 注册信号处理程序
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    uvicorn.run(app, reload=False, host="0.0.0.0", port=5001)
