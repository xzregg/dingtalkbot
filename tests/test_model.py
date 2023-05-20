# -*- coding: utf-8 -*-
# @Time    : 2023/5/16 17:40 
# @Author  : xzr
# @File    : test_faq.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com

from pprint import pprint
from unittest import TestCase
from model import KnowledgeModel

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from faker import Faker
import random

fake = Faker('zh_CN')  # 指定语言为中文


class TestModel(TestCase):

    def test_create(self):
        KnowledgeModel._es.indices.delete(index=KnowledgeModel._es_index_name, ignore=[400, 404])
        KnowledgeModel.create_index()
        data_list = []
        for x in range(100):
            title = fake.sentence(nb_words=5)
            author = fake.name()
            publish_date = fake.date_this_century(before_today=True, after_today=False)
            content = fake.paragraphs(nb=random.randint(3, 5))

            data = KnowledgeModel()
            data.catalog = 'test'
            data.title = title
            data.content = ''.join(content)
            data.page_id = ''
            data.author = 'test'
            data_list.append(data)
        actions = [
                {
                        "_index" : KnowledgeModel._es_index_name,
                        "_source": d,
                }
                for d in data_list
        ]
        res = bulk(KnowledgeModel._es, actions)
        print(res)

    def test_drop(self):
        KnowledgeModel.drop()
        KnowledgeModel.create_index()

    def test_search(self):
        res = KnowledgeModel.search('维系')
        pprint(res, indent=4)

    def test_get(self):
        res = KnowledgeModel.get_index('oyeGM4gBAX9araRtwfvb')
        pprint(res, indent=4)
