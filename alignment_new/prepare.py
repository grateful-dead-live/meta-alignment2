import os, json, re
import networkx as nx
from networkx.drawing.nx_agraph import read_dot
from copy import copy
from collections import Counter
from subprocess import Popen, DEVNULL, PIPE
from pprint import pprint


#DATE = '90-03-14'
FOLDER = '/Volumes/gspeed1/thomasw/grateful_dead/2020/GD-DTW/results_15s_linregress/'#90-03-14/'  #116030_116746'
#FOLDER = './'


def etreeNumber(e):
        for j in e.split('.'):
            try: return int(j)
            except: pass


# dct to find folders of recordings to get lengths of unmatched files
def getDirsDict():
    if os.path.exists('dirdict.json'):
        return json.load(open('dirdict.json'))
    DIR1 = '/Volumes/gspeed1/thomasw/grateful_dead/lma'
    DIR2 = '/Volumes/gspeed1/thomasw/grateful_dead/lma_soundboards/sbd' 
    
    folders1 = [os.path.join(DIR1, f) for f in os.listdir(DIR1) if os.path.isdir(os.path.join(DIR1, f))]
    folders2 = [os.path.join(DIR2, f) for f in os.listdir(DIR2) if os.path.isdir(os.path.join(DIR2, f))]
    dirs = folders1 + folders2
    dirDict = {}
    for d in dirs:
        dirDict[etreeNumber(d.split('/')[-1])] = d
    json.dump(dirDict, open('dirdict.json', 'w'))
    return dirDict


def loadJson(date):
    print('loading json files')
    jsons = {}
    folder = os.path.join(FOLDER, date)
    for d in [f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]:
        #print(d)
        j = None
        for f in [i for i in os.listdir(os.path.join(folder, d)) if i.endswith('.json') and not i.endswith('full.json') and not i.startswith('unmatched')]:
            jsons[d+'__'+f[:-5]] = json.load(open(os.path.join(folder, d, f))) 
    jsons['unmatched'] = json.load(open(os.path.join(folder, 'unmatched.json')))['unmatched']
    return jsons


# find all in_edges including indirectly connected
def find_connected(g, node):
    def find_connected_r(g, nodes, connected):
        new_connections = []
        for n in nodes:
            for i in g.in_edges(n[0]):
                new_connections.append(i)
        if new_connections:
            connected += list(new_connections)
            return find_connected_r(g, new_connections, connected)
        else:
            return connected
    def chain_connected(cn):
        c = 0
        to_del = []
        result = copy(cn)
        for i, n in enumerate(cn):
            for j, m in enumerate(cn):
                if n[-1] == m[0]:
                    c += 1
                    result[i] = tuple(list(n) + list(m)[1:])
        if c == 0:
            return result
        else:
            return chain_connected(result)
    cn = list(g.in_edges(node))
    cn = find_connected_r(g, cn, cn)
    cn = chain_connected(cn)
    cn = [list(n[:-1]) for n in cn]
    return cn

# get connected graphs of individual tracks
def sub_graphs(g):
    in_nodes = [n for n in g.nodes() if len(g.in_edges(n)) > 0 and len(g.out_edges(n)) == 0]
    return [{n: find_connected(g,n)} for n in in_nodes]


def get_all_ids(g):
    res = []
    for n in g.nodes():
        if n.split('_')[0] not in res:
            res.append(n.split('_')[0])
    return res


# sort recording by number of matched files
def rank_ids_amount(s):
    ids = [list(i.keys())[0].split('_')[0] for i in s]
    ids_sorted = [i[0] for i in Counter(ids).most_common()]
    return ids_sorted


# sort recording by length
def rank_ids_length(lengths):
    l = []
    for k, v in lengths.items():
        l.append((sum([i[1] for i in v]), k))
    return [i[1] for i in sorted(l, reverse=True)]
    

def get_lengths(jsons, id, dirsdict):
    lengths = []
    for k in jsons.keys():
        key_ids = k.split('__')[0].split('_')
        if id in key_ids:
            filename = jsons[k]['filenames'][key_ids.index(id)].split('/')[-1]
            length = jsons[k]['lengths'][key_ids.index(id)]
            if (filename, length) not in lengths:
                lengths.append((filename, length))
    unmatched = [f for f in jsons['unmatched'] if f.startswith(id)]
    if unmatched:
        #print('unmatched:', unmatched)
        for f in unmatched:
            fs = f.split('_')
            p = os.path.join(dirsdict[fs[0]], fs[1])
            if f.lower().endswith('shn'):
                cmd = 'shntool len ' + p
                p = Popen(cmd, shell=True,stdout=PIPE).communicate()
                s = str(p).split()[10].replace('.',':').split(':')
                l = int(s[0])*60 + int(s[1]) + int(s[2])*0.01
            else:
                cmd = 'soxi -D ' + p
                p = Popen(cmd, shell=True,stdout=PIPE).communicate()
                l = float(str(p[0])[2:-3])
            lengths.append((fs[1], l))
    #print(lengths)
    return sorted(lengths)


def prepare_data(date):
    print('analysing graph')
    g = read_dot(os.path.join(FOLDER+date, date+'.dot'))
    subs = sub_graphs(g)


    ids_by_number_of_matched_files = rank_ids_amount(subs)
    dirsdict = getDirsDict()
    jsons = loadJson(date)
    #json.dump(jsons, open('jsons.json', 'w'))
    #jsons = json.load(open('jsons.json'))
    lengths = {}
    for i in get_all_ids(g):
        lengths[i] = get_lengths(jsons, i, dirsdict)
    ids_by_length = rank_ids_length(lengths)

    # add unmatched to subgraph:
    for n in nx.isolates(g):
        subs.append({n:[]})    
    
    return subs, ids_by_length, ids_by_number_of_matched_files, lengths, jsons

def track_tuple_to_json_id(n):
    id1 = n[0].split('_')[0]
    fn1 = ('_').join(n[0].split('_')[1:])    
    id2 = n[1].split('_')[0]
    fn2 = ('_').join(n[1].split('_')[1:])     
    return id1+'_'+id2+'__'+fn1+'__'+fn2


def main():
    pass
    #subgraphs, ids_by_length, lengths, jsons = prepare_data(DATE)

if __name__ == "__main__":
    main()