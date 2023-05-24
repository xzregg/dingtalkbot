# -*- coding: utf-8 -*-
# @Time    : 2023/5/16 17:24 
# @Author  : xzr
# @File    : faq.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
import json
import time
import traceback

import redis
from addict import Addict
from decouple import config
from elasticsearch import Elasticsearch
from objectdict import ObjectDict

redis_client = redis.Redis.from_url(config('REDIS_URL'))
REDIS_LOCK_TIMEOUT = 60


def get_cache(name):
    try:
        content = redis_client.get(name)
        return json.loads(content.decode())
    except Exception:
        return ''


def set_cache(key, value, **kwargs):
    try:
        return redis_client.set(key, json.dumps(value, ensure_ascii=False), **kwargs)
    except Exception:
        return ''


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
    def search(cls, query, size=5, sort=None):
        body = Addict()
        body.query = query
        body.size = size
        if sort:
            body.sort = sort
        res = cls._es.search(index=cls._es_index_name, body=body)
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

    @classmethod
    def delete_from_query(cls, field: dict = None):
        query = {"query": {"match": field}}
        result = cls._es.delete_by_query(index=cls._es_index_name, body=query)
        return result


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
                        "title"   : {"type": "text", "analyzer": "ik_smart"},
                        "content" : {"type": "text", "analyzer": "ik_smart"},  # ik_max_word
                        "catalog" : {"type": "keyword"},
                        "author"  : {"type": "keyword"},
                        "link"    : {"type": "keyword"}
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
        for i in range(3):
            try:
                with redis_client.lock(f"KnowledgeModel:INDEX:{data.title}", timeout=REDIS_LOCK_TIMEOUT):
                    search_results = cls._es.search(index=cls._es_index_name, body=query, _source=False)
                    if search_results['hits']['total']['value'] > 0:
                        index_id = search_results['hits']['hits'][0]['_id']
                    result = cls._es.index(index=cls._es_index_name, id=index_id, body=data)
                    return f'[{title}] 更新成功!'
            except Exception as e:
                traceback.print_exc()
                time.sleep(0.5)
        return f'[{title}] 更新失败!'

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
        query.highlight.pre_tags = ['`']
        query.highlight.post_tags = ['`']
        query.highlight.fragment_size = 300
        query.highlight.number_of_fragments = 3
        query.query.bool.must = [
                {
                        "bool": {
                                "should": [
                                        {"match": {"title": text}},
                                        {"match": {"content": text}}
                                ]
                        }
                },
                # {
                #         "multi_match": {
                #                 "query" : text,
                #                 "fields": ["title", "content"]
                #         }
                # },
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
    def create_index(cls):
        pass
        mapping = {
                "properties": {
                        "doc_type"  : {"type": "keyword"},
                        "id"        : {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "parent_id" : {"type": "keyword"},
                }
        }
        cls._es.indices.create(index=cls._es_index_name, body={"mappings": mapping}, ignore=400)

    @classmethod
    def create(cls, data):
        return cls._es.index(index=cls._es_index_name, id=data['id'], body=data)


ConversationsModel.create_index()
KnowledgeModel.create_index()
