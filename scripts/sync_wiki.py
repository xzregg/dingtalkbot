# -*- coding: utf-8 -*-
# @Time    : 2023/5/18 17:28 
# @Author  : xzr
# @File    : sync_wiki.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :
import json
import sqlite3

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


def sync_wiki():
    # 连接Elasticsearch
    # es = Elasticsearch(['https://elastic.packertec.com:443'], verify_certs=False)
    es = Elasticsearch(['http://es01:9200', 'http://es02:9200', 'http://es03:9200'], verify_certs=False)

    # SQLite数据库连接
    conn = sqlite3.connect('showdoc.db.php')
    cursor = conn.cursor()

    # 判断索引是否存在，不存在则创建索引
    index_name = 'knowledge_graph'
    try:
        with open('position_data.json', 'r') as fp:
            position_data = json.load(fp)
    except:
        position_data = [0, 0]

    last_id, history_id = position_data
    where_text = ""
    if history_id:
        where_text = f'LEFT JOIN page_history ph ON p.page_id = ph.page_id WHERE ph.page_history_id > {history_id}'
    cur_last_id = cursor.execute('SELECT page_id FROM page order by page_id desc limit 1').fetchone()[0]
    if cur_last_id > last_id:
        where_text = F'WHERE page_id>={last_id}'

    # 读取SQLite数据库中的page表数据
    cursor.execute(f'''
SELECT  p.page_id, p.page_title, p.page_content, p.page_comments, p.is_del,c.cat_name,p.author_username ,p.item_id
FROM page p
LEFT JOIN catalog c ON p.item_id = c.item_id
{where_text}
GROUP BY p.page_id''')
    rows = cursor.fetchall()

    # 构建批量操作列表
    actions = []
    batch_size = 100  # 每批处理的数据量
    for i, row in enumerate(rows):
        page_id, page_title, page_content, page_comments, is_del, cat_name, author_username, item_id = row
        document = {
                'page_id'      : page_id,
                'doc_type'     : 'wiki',
                'title'        : page_title,
                'content'      : page_content,
                'catalog'      : cat_name,
                'author'       : author_username,
                'page_comments': page_comments,
                'link'         : f'https://wiki.packertec.com/web/#/{item_id}?page_id={page_id}',
        }
        # 查询是否存在以page_id为条件
        query = {'term': {'page_id': page_id}}
        search_results = es.search(index=index_name, body={'query': query}, _source=False)
        if search_results['hits']['total']['value'] > 0:
            index_id = search_results['hits']['hits'][0]['_id']
            if is_del == 1:
                # 如果is_del字段为1表示删除数据
                actions.append({'_op_type': 'delete', '_index': index_name, '_id': index_id})
            else:
                # 数据存在则执行更新操作
                actions.append({'_op_type': 'update', '_index': index_name, '_id': index_id, '_source': {'doc': document}})
        else:
            # 数据不存在则执行插入操作
            actions.append({'_index': index_name, '_source': document})
        if (i + 1) % batch_size == 0:
            # 达到批量处理的数量，执行批量操作
            bulk(es, actions)
            actions = []  # 清空操作列表
    # 处理剩余的数据
    if actions:
        bulk(es, actions)
    history_id = cursor.execute('SELECT page_history_id FROM page_history order by page_history_id desc limit 1').fetchone()[0]
    with open('position_data.json', 'w') as fp:
        json.dump([cur_last_id, history_id], fp)
    # 关闭数据库连接
    cursor.close()
    conn.close()


if __name__ == '__main__':
    sync_wiki()
