from config import *


def make_tree(node_string, href, vercode):
    root ={}
    rnode = node_string.split('/')[0]
    cnode = '/'.join(node_string.split('/')[1:])
    root['text'] = rnode
    href = href + '/' + rnode
    if len(cnode) > 0:
        root['nodes'] = make_tree(cnode, href, vercode)
    else:
        root['href'] = host + 'filediff?fname=' + href + '&vercode=' + vercode
    return [root]


def append_node(root, current_node):
    for child_node in root:
        if child_node['text'] == current_node['text']:
            root = append_node(child_node['nodes'],current_node['nodes'][0])
            break
    else:
        root.append(current_node)
    return root


def map_tree(root, node):
    if len(root) == 0:
        return [node]
    append_node(root, node)
    return root


def make_diff_tree(treedata, appname, vercode):

    keys = treedata.keys()
    keys.sort()
    out = []

    for node_string in keys:
        tree_node = make_tree(node_string[1:], appname,vercode)
        out = map_tree(out, tree_node[0])
    # out = [
    #     {"text": "Parent 1",
    #      "nodes": [
    #          {"text": "Children",
    #           "nodes": [
    #               {"text": "Parent 1", "href": "http://www.google.com"},
    #               {"text": "Parent 5000"}
    #           ]},
    #          {"text": "Child 2"}
    #      ]},
    #     {"text": "Parent 2"},
    #     {"text": "Parent 1"}
    # ]
    return out


def simple_tree(tree_data,appname,vercode):
    ret = []
    for data in tree_data:
        ret.append({'text':data,'href':host + 'filediff?fname='+ appname+'/'+ data + '&vercode=' + vercode })
    return ret
