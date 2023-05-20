# -*- coding: utf-8 -*-
# @Time    : 2023/5/16 17:24 
# @Author  : xzr
# @File    : faq.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
import json

from decouple import config
from objectdict import ObjectDict
from addict import Addict
from elasticsearch import Elasticsearch


class BaseEsModel(ObjectDict):
    _es = Elasticsearch(config('ES_HOST').split(','),
                        verify_certs=False,
                        )
    _es_index_name = 'knowledge_graph'
    doc_type = ''  # es 7 开始已经去掉 _type 概念,只能自定个 doc_type 类型吧

    @classmethod
    def create_index(cls):
        pass
        mapping = {
                "properties": {
                        "doc_type": {"type": "keyword"},
                }
        }
        cls._es.indices.create(index=cls._es_index_name, body={"mappings": mapping}, ignore=400)

    @classmethod
    def search(cls, query, size=5):
        query = Addict(query)
        query.size = size
        res = cls._es.search(index=cls._es_index_name, body=query)
        return res['hits']

    @classmethod
    def get_index(cls, index_id):
        res = cls._es.get(index=cls._es_index_name, id=index_id)
        return res['_source']

    @classmethod
    def create(cls, data):
        return cls._es.index(index=cls._es_index_name, body=data)

    @classmethod
    def modify(cls, index_id, data):
        return cls._es.update(index=cls._es_index_name, id=index_id, body=data)

    @classmethod
    def delete(cls, index_id):
        # 删除文档
        return cls._es.delete(index=cls._es_index_name, id=index_id)

    @classmethod
    def drop(cls):
        cls._es.indices.delete(index=cls._es_index_name, ignore=[400, 404])


class KnowledgeModel(BaseEsModel):
    _es = Elasticsearch(['https://elastic.packertec.com:443'],
                        verify_certs=False,
                        )
    _es_index_name = 'knowledge_graph'
    doc_type: str = 'wiki'
    title: str = ''
    content: str = ''
    catalog: str = ''
    page_id: str = ''
    author: str = ''

    @classmethod
    def create_index(cls):
        mapping = {
                "properties": {
                        "doc_type": {"type": "keyword"},
                        "title"   : {"type": "text", "analyzer": "ik_max_word"},
                        "content" : {"type": "text", "analyzer": "ik_max_word"},
                        "catalog" : {"type": "keyword"},
                        "author"  : {"type": "keyword"}
                }
        }
        cls._es.indices.create(index=cls._es_index_name, body={"mappings": mapping}, ignore=400)

    @classmethod
    def index_from_text(cls, text: str, author: str = '', doc_type='faq'):
        title_split = text.strip().split('\n', 1)
        title = title_split[0].strip()
        content = title_split[-1].strip()
        if len(title) <= 3:
            return '标题必须大于3个字'
        if not content:
            return '内容不完整'
        data = cls()
        data.doc_type = doc_type
        data.title = title
        data.content = content
        data.author = author
        data.catalog = 'faq'
        index_id = None
        query = Addict()
        query.query.bool.must = [
                {"match": {
                        "title": {
                                "query"   : data.title,
                                "operator": "and"
                        }
                }},
                {'term': {'doc_type': data.doc_type}}
        ]
        query.size = 1
        search_results = cls._es.search(index=cls._es_index_name, body=query, _source=False)
        if search_results['hits']['total']['value'] > 0:
            index_id = search_results['hits']['hits'][0]['_id']
        result = cls._es.index(index=cls._es_index_name, id=index_id, body=data)
        # cls._es.commit()
        return f'[{title}] 更新成功!'

    @classmethod
    def delete_from_title(cls, title):
        title = title.split('\n')[0]
        query = {"query": {"match": {"title": title}}}
        result = cls._es.delete_by_query(index=cls._es_index_name, body=query)
        return f'[{title}] 删除成功!'

    @classmethod
    def search(cls, text, doc_type='', size=5, **kwargs):
        # 搜索文档
        query = Addict()
        query.size = size
        query.highlight.fields = {
                "title"  : {},
                "content": {}
        }
        query.query.bool.must = [
                {
                        "multi_match": {
                                "query" : text,
                                "fields": ["title", "content"]
                        }
                },
        ]
        if doc_type:
            query.query.bool.must.append({
                    "term": {
                            "doc_type": doc_type,
                    },
            })
        res = cls._es.search(index=cls._es_index_name, body=query, **kwargs)
        return res['hits']


class ConversationsModel(BaseEsModel):
    _es = Elasticsearch(['https://elastic.packertec.com:443'],
                        verify_certs=False,
                        )
    _es_index_name = 'chat_conversations'

    @classmethod
    def create(cls, data):
        return cls._es.index(index=cls._es_index_name, id=data['id'], body=data)


ConversationsModel.create_index()
KnowledgeModel.create_index()
