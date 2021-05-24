from graphviz import Digraph
import pandas as pd
from graphviz import lang

def node_str(name, label=None, _attributes=None, **attrs) -> str:
    """
    指定されたパラメータを持つノードのgraphviz上でのstringを返す。
    """
    _node  = '\t%s%s'
    name = lang.quote(name)
    attr_list = lang.attr_list(label, attrs, _attributes)
    line = _node % (name, attr_list)
    return line

def has_edge(graph: Digraph, tail_name, head_name, styles=None) -> bool:
    """
    `graph`に`tail_name`から`head_name`へのエッジがあるかどうか調べる。
    """
    edge = (graph._edge % (tail_name, head_name, '')) in graph.body
    if not styles is None:
        for style in styles:
            edge = edge or ((graph._edge % (tail_name, head_name, ' [style={}]'.format(style))) in graph.body)
    return edge

def has_solid_path(graph: Digraph, courses: pd.DataFrame, tail_name, head_name) -> bool:
    """
    `graph`に`tail_name`から`head_name`へ予習必須のみのパスがあるかどうか調べる。
    """
    if (graph._edge % (tail_name, head_name, '')) in graph.body:
        return True
    for prereq in courses[courses['course_number'] == head_name].iloc[0]['course_prepare_must']:
        if has_solid_path(graph, courses, tail_name, prereq):
            return True
    return False

def add_prereq(graph: Digraph, courses: pd.DataFrame, course_id: int, node_colors: list, url: str, course_list: list):
    """
    `course_id`の予習必須・おすすめのコースを`graph`と`course_list`に追加する。
    """
    row = courses[courses['course_number'] == course_id].iloc[0]
    for prereq in row['course_prepare_must']:
        prereq_row = courses[courses['course_number'] == prereq].iloc[0]
        if node_str(str(prereq), prereq_row['course_title'], color=node_colors[prereq_row['course_level'] - 1], 
            href=url+str(prereq), fontname="Noto Sans CJK JP") not in graph.body:
            course_list.append(prereq)
            graph.node(str(prereq), prereq_row['course_title'], color=node_colors[prereq_row['course_level'] - 1], 
                href=url+str(prereq), fontname="Noto Sans CJK JP")
            add_prereq(graph, courses, prereq, node_colors, url, course_list)
        graph.edge(str(prereq), str(course_id))
    for prereq in row['course_prepare_suggestion']:
        prereq_row = courses[courses['course_number'] == prereq].iloc[0]
        if node_str(str(prereq), prereq_row['course_title'], color=node_colors[prereq_row['course_level'] - 1], 
                href=url+str(prereq), fontname="Noto Sans CJK JP") not in graph.body:
            course_list.append(prereq)
            graph.node(str(prereq), prereq_row['course_title'], color=node_colors[prereq_row['course_level'] - 1], 
                href=url+str(prereq), fontname="Noto Sans CJK JP")
            add_prereq(graph, courses, prereq, node_colors, url, course_list)
        graph.edge(str(prereq), str(course_id), style='dashed')
