from graphviz import Digraph
import pandas as pd
from ast import literal_eval
from itertools import permutations
import streamlit as st
from course_path import node_str, has_edge, has_solid_path, add_prereq
import requests, io
from SessionState import get

def remove_unnecessary_edges(graph: Digraph, courses: pd.DataFrame, course_list: list, styles=None):
    for p in permutations(course_list, r=2):
        if has_edge(graph, p[0], p[1], styles):
            for prereq in courses[courses['course_number'] == p[1]].iloc[0]['course_prepare_must']:
                if has_solid_path(graph, courses, p[0], prereq):
                    try:
                        graph.body.remove(graph._edge % (p[0], p[1], ''))
                    except ValueError:
                        for style in styles:
                            try:
                                graph.body.remove(graph._edge % (p[0], p[1], ' [style={}]'.format(style)))
                            except ValueError:
                                continue
                    break

def main():
    st.title('あなたにぴったりなコースをお届け！')

    # TODO 最新のCSVの場所に変える
    token = st.secrets['token'] # aidemy-contentsから読み取りができるトークン
    owner = 'TeamAidemy'
    repo = 'aidemy-contents'
    path = 'contents-automator/all.csv'
    branch = 'abstract_csv/feature'

    # GitHubから最新のCSVをダウンロードしてDataFrameに変換する
    r = requests.get('https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}'.format(
        owner=owner, repo=repo, path=path, branch=branch), headers={
            'accept': 'application/vnd.github.v3.raw',
            'authorization': 'token {}'.format(token)
        }
    )
    courses = pd.read_csv(io.StringIO(r.text), 
        converters={'course_prepare_must': literal_eval, 'course_prepare_suggestion': literal_eval, 'course_suggestion': literal_eval})

    # 可視化に必要な変数を定義
    name = 'custom'
    fontname = 'Noto Sans CJK JP'
    path = Digraph(name=name, strict=True)
    path.attr('graph', fontname=fontname)
    path.attr('node', fontname=fontname)
    path.attr('edge', fontname=fontname)
    aidemy = 'https://aidemy.aidemy.jp/courses/'
    node_colors = ['green', 'yellow', 'orange', 'red']
    styles = ['dashed']

    # コース間関係の全体像を表示する
    if st.checkbox('全体像を表示'):
        # 全体像のグラフを初期化する
        dot = Digraph(name='all', strict=True)
        dot.attr('graph', rankdir='LR')
        dot.attr('graph', fontname=fontname)
        dot.attr('node', fontname=fontname)
        dot.attr('edge', fontname=fontname)
        
        # 全てのコースをグラフに追加する
        for _, row in courses.iterrows():
            dot.node(str(row['course_number']), row['course_title'], color=node_colors[row['course_level'] - 1], 
                href=aidemy+str(row['course_number']))
        edges = st.multiselect('表示したい関係性を選択してください', ['予習必須', 'できればやろう', '次におすすめ'])
        
        # エッジを追加する
        if '予習必須' in edges:
            for _, row in courses.iterrows():
                for prereq in row['course_prepare_must']:
                    dot.edge(str(prereq), str(row['course_number']))
        if 'できればやろう' in edges:
            for _, row in courses.iterrows():
                for prereq in row['course_prepare_suggestion']:
                    dot.edge(str(prereq), str(row['course_number']), style='dashed')
        if '次におすすめ' in edges:
            for _, row in courses.iterrows():
                for next in row['course_suggestion']:
                    if not has_edge(dot, str(row['course_number']), str(next), ['dashed']):
                        dot.edge(str(row['course_number']), str(next), style='dotted', color='purple')
        
        # 余分なエッジを取り除く
        remove_unnecessary_edges(dot, courses, courses['course_number'], styles)

        # グラフを表示
        st.graphviz_chart(dot)
        st.markdown('$\\rightarrow$: 予習必須　$\dashrightarrow$: できればやろう')

    # キーワードで目標となるコースを検索して、ユーザーに提示する
    search_keys = st.text_input('キーワードで目標にしたいコースを検索')
    if not search_keys:
        st.stop()
    search_keys = search_keys.replace('　', ' ').split() # ORで検索
    candidate_ids = set()
    for key in search_keys:
        # コースタイトルと概要とキーワードの中を検索
        candidates = courses[courses['course_title'].str.contains(key, case=False) | courses['course_description'].str.contains(key, case=False) | 
            courses['keywords'].str.contains(key, case=False)]
        candidate_ids.update(set(candidates['course_number']))
    options = []
    name_id_dict = {}
    for candidate in candidate_ids:
        row = courses[courses['course_number'] == candidate].iloc[0]
        options.append(row['course_title'])
        name_id_dict[row['course_title']] = candidate
    selected = st.multiselect('受講したいコースを選んでください', options)
    
    # 選択したコースを記録しつつ選択が終わるまで待機
    target_courses = set()
    target_course_names = set()
    for s in selected:
        target_course_names.add(s)
        target_courses.add(name_id_dict[s])
    st.text('選択済みのコース')
    for c in target_course_names:
        st.markdown('[{}]({})'.format(c, aidemy + str(name_id_dict[c])))
    if not st.button('選択完了'):
        st.stop()

    # 目標としたいコースと、その予習必須・おすすめコースをグラフに追加する
    course_list = [] # グラフ内にある全てのコースのリスト
    for target in target_courses:
        row = courses[courses['course_number'] == target].iloc[0]
        if node_str(str(target), row['course_title'], color=node_colors[row['course_level'] - 1], 
                    href=aidemy+str(target), fontname="Noto Sans CJK JP") not in path.body:
            course_list.append(target)
            path.node(str(target), row['course_title'], color=node_colors[row['course_level'] - 1], 
                href=aidemy+str(target), fontname="Noto Sans CJK JP")
            add_prereq(path, courses, target, node_colors, aidemy, course_list)

    # 余分なエッジを取り除く
    remove_unnecessary_edges(path, courses, course_list, styles)

    required = set()
    encouraged = set()
    for course in course_list:
        if course in target_courses:
            continue
        for target in target_courses:
            if has_solid_path(path, courses, course, target):
                required.add(course)
                break
        if course not in required:
            encouraged.add(course)

    st.subheader('受講必須のコース')
    if len(required) == 0:
        st.text('なし')
    for r in required:
        row = courses[courses['course_number'] == r].iloc[0]
        st.markdown('[{}]({})'.format(row['course_title'], aidemy + str(r)))
    st.subheader('受講おすすめのコース')
    if len(encouraged) == 0:
        st.text('なし')
    for e in encouraged:
        row = courses[courses['course_number'] == e].iloc[0]
        st.markdown('[{}]({})'.format(row['course_title'], aidemy + str(e)))

    st.subheader('おすすめの受講順序')
    st.graphviz_chart(path)
    st.markdown('$\\rightarrow$: 予習必須　$\dashrightarrow$: できればやろう')

if __name__ == "__main__":
    session_state = get(password='')
    authorized = False

    if session_state.password != st.secrets['password']:
        with st.form("パスワードを入力してください"):
            session_state.password = st.text_input("パスワード", type='password')
            submitted = st.form_submit_button("ログイン")
            if submitted:
                if session_state.password == st.secrets['password']:
                    authorized = True
                else:
                    st.error("the password you entered is incorrect")
        if authorized:
            main()
    else:
        main()