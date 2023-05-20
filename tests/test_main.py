# -*- coding: utf-8 -*-
# @Time    : 2023/5/15 14:06 
# @Author  : xzr
# @File    : test_main.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
from unittest import TestCase
from dingtalk import DingtalkChatbot


# @Desc    :
class Test(TestCase):
    def test_dinkbot(self):
        wh = 'https://oapi.dingtalk.com/robot/send?access_token=ecf5539490396fb709bb2454f7fcf32dbecc9a408f9840ea814ed6b1597d3022'
        ding = DingtalkChatbot(wh, pc_slide=False)
        msg = '''
> @15975623354 发送消息测试:内容

以下是一个将 Markdown 格式的文本转换为 HTML 显示的示例代码：

```html
&lt;!DOCTYPE html&gt;
&lt;html&gt;
&lt;head&gt;
    &lt;title&gt;Markdown to HTML&lt;/title&gt;
    &lt;style&gt;
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            padding: 20px;
        }
        h1, h2, h3, h4, h5, h6 {
            font-weight: bold;
        }
        p {
            margin-bottom: 10px;
        }
        code {
            background-color: #f4f4f4;
            padding: 4px;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            overflow-x: auto;
        }
    &lt;/style&gt;
&lt;/head&gt;
&lt;body&gt;
    &lt;div id=&quot;markdown-content&quot;&gt;&lt;/div&gt;
    
    &lt;script src=&quot;https://cdn.jsdelivr.net/npm/marked/marked.min.js&quot;&gt;&lt;/script&gt;
    &lt;script&gt;
        // Markdown 文本
        var markdownText = &quot;# Hello, Markdown!\n\nThis is **bold** text and this is *italic* text.&quot;;
        
        // 将 Markdown 转换为 HTML
        var htmlContent = marked(markdownText);
        
        // 显示 HTML 内容
        var markdownContentElement = document.getElementById(&quot;markdown-content&quot;);
        markdownContentElement.innerHTML = htmlContent;
    &lt;/script&gt;
&lt;/body&gt;
&lt;/html&gt;
```

将上述代码保存为一个 `.html` 文件并在浏览器中打开，就可以看到 Markdown 格式的文本以 HTML 的形式进行显示。
        '''
        msg = '(http://www.baidu.com) \n\n [百度](http://www.baidu.com)\n'
        # msg = '#### {title} \n > {message} [sentry](http://www.baidu.com) {git_msg}'
        ding.send_markdown("发送消息", msg, at_mobiles=['15975623354'], is_auto_at=True)
