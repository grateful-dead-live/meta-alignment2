from prepare import prepare_data, track_tuple_to_json_id
from scipy import stats
import numpy as np
from pprint import pprint
from copy import copy, deepcopy
from itertools import combinations
import json

DATE = '90-03-14'
MIN_R = 0.9999

split = lambda l, locs: [l[i:j] for i, j in zip([0]+locs, locs+[None])]
flatten = lambda l: [item for sublist in l for item in sublist]

#splits into continuous line segments
def split_segments2(points, delta=2):
    points = sorted(points)
    leap = lambda p, q: abs(p[0] - q[0]) > delta or abs(p[1] - q[1]) > delta
    locs = [i for i, p in enumerate(points) if i > 0 and leap(p, points[i-1])]
    return split(points, locs)


def find_best_break(segs):
    if stats.linregress(flatten(segs))[2] < MIN_R:
        rs = []
        for i in range(len(segs)):
            splits = [flatten(segs[:i]), flatten(segs[i:])]
            rs.append(max([stats.linregress(s)[2] for s in splits if len(s) > 0]))
        best_break = np.argmax(rs)
        if 0 < best_break and best_break < len(segs):
            return best_break


def get_ref_tracks(id, ls):
    lengths = [i[1] for i in ls[id]]
    ref_starts = [sum(lengths[:i]) for i in range(len(lengths))]
    return [[ref_starts[i], ref_starts[i]+lengths[i]] for i in range(len(lengths))]


def partition(segs):
    partitions = [segs]
    breaks = [find_best_break(p) for p in partitions]
    while len([b for b in breaks if b is not None]) > 0:
        partitions = [[p[:breaks[i]], p[breaks[i]:]] if breaks[i] is not None else [p] for i, p in enumerate(partitions)]
        partitions = flatten(partitions)
        breaks = [find_best_break(p) for p in partitions]
        #print([len(p) for p in partitions])
    return partitions


#split into reasonably well aligned partitions
def partition_match(jsons, jkey):
    #print(jkey)
    points = jsons[jkey]['dtw']
    if (len(points) > 0 and stats.linregress(points)[2] < MIN_R):
        parts = partition(split_segments2(points))
        print(jsons[jkey]['filenames'][0], 'split into', [len(p) for p in parts])
        return parts
    return [[sorted(points)]] #all one partition
    
def get_combination_matches(jsons, pair):
    return [k for k in list(jsons.keys()) if k.startswith(pair[1]+'_'+pair[0])]


def multi_index(item, arr):
    a = [x for x in arr if item in x][0]
    return (arr.index(a), a.index(item))


def sort_subgraphs(subs, ids_by_length, lengths):
    getkeyid = lambda l: list(l.keys())[0].split('_')[0]
    flatsub = lambda l: list(set([list(l.keys())[0]] + [x for sublist in list(l.values())[0] for x in sublist]))

    # sort subgraphs by lengths of recording
    subs = sorted(subs, key=lambda l: ids_by_length.index(getkeyid(l)))

    file_list = []
    for i in ids_by_length:
        file_list.append([i+'_'+t[0] for t in lengths[i]])

    ssubs = deepcopy(subs)
    change_idx = []

    # TODO: this needs to be recursive
    for i, s in enumerate(subs[1:]):
        if getkeyid(s) != getkeyid(subs[i]):
            found_idx = None
            flat_s = flatsub(s)
            for f in flat_s:
                prv_file = None
                nxt_file = None
                idx = multi_index(f, file_list)
                if idx[1] > 0:
                    prv_file = file_list[idx[0]][idx[1]-1]
                if idx[1] < len(file_list[idx[0]])-1:
                    nxt_file = file_list[idx[0]][idx[1]+1]
                for j in subs:
                    if j != s:
                        flat_j = flatsub(j)
                        for fs in flat_s:
                            if prv_file:
                                if prv_file in flat_j:
                                    try:
                                        found_idx = subs.index(j) + 1
                                        print('prev', found_idx)
                                    except: pass
                            if nxt_file and not found_idx:
                                if nxt_file in flat_j:
                                    try:
                                        found_idx = subs.index(j)
                                        print('next', found_idx)
                                    except: pass
                            if found_idx:
                                break   
                if found_idx:
                    change_idx.append((found_idx, i))
                    break
                    
            if not found_idx:
                print('no index found for subgraph')
    if change_idx:
        change_idx.sort()
        print(change_idx)
                    
def main():
    subgraphs, ids_by_length, ids_by_number_of_matched_files, lengths, jsons = prepare_data(DATE)
    #pprint(subgraphs)
    sort_subgraphs(subgraphs, ids_by_length, lengths)

    #file_lists = get_file_lists(ids_by_length, lengths)
    #pprint(lengths)
    unmatched = jsons['unmatched']
    #print(unmatched)
    ref_id = ids_by_length[0]
    #comb = list(combinations(ids_by_length, 2))
    
    #first
    jkeys = list(jsons.keys())
    #partitions = [partition_match(jsons, k) for k in jkeys if k != 'unmatched']

    #[print(c, len(p)) for c, p in zip(comb, partitions)]
    #json.dump(partitions, open('partitions.json', 'w'))

main()