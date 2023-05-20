# -*- coding: utf-8 -*-
# @Time    : 2023/2/10 10:36 
# @Author  : xzr
# @File    : test_gitlab.py
# @Software: PyCharm
# @Contact : xzregg@gmail.com
# @Desc    :

import gitlab


def get_git_track_msg_author_info(git_url, private_token, project_name_with_namespace, filename, lineno, branch='master'):
    try:
        gl = gitlab.Gitlab(url=git_url, private_token=private_token)
        project = gl.projects.get(project_name_with_namespace)
        blames = project.files.blame(filename, branch)
        tlc = 0
        for item in blames:
            commit, lines = item.get('commit', {}), item.get('lines', [])
            tlc += len(lines)
            if tlc >= lineno:
                return commit
        return {}
    except gitlab.exceptions.GitlabListError as e:
        return {}
    except Exception as e:
        return {}


if __name__ == '__main__':
    # gl = gitlab.Gitlab(url='https://gitlab.base.packertec.com/', private_token='2X5Qjc2AdcPMcg4XBv6M')
    gl = gitlab.Gitlab(url='http://112.74.91.93:880', private_token='glpat-uGfjHj9AzATTrHTevx1H')
    project_name_with_namespace = "shixiang-sass/backend/cashier_v4"
    for project in gl.projects.list():
        print(project.id)
        print(project.name_with_namespace)
        print(project.name_with_namespace)

    commit = get_git_track_msg_author_info('http://112.74.91.93:880', 'glpat-uGfjHj9AzATTrHTevx1H', project_name_with_namespace, 'apps/background/apps.py', 2, branch='master')
    print(commit)
