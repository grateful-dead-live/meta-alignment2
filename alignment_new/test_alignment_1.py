from prepare import prepare_data, track_tuple_to_json_id
from scipy import stats
import numpy as np
from pprint import pprint
from copy import copy, deepcopy
from itertools import combinations
import json, sys

DATE = '90-07-19'
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


def move_item(arr, item, new_index):
    try:
        arr.remove(item)
        arr.insert(new_index, item)
    except ValueError:
        print(f'Moving item to {new_index} failed')
    return arr


def sort_subgraphs(subs, lengths, ids_by_length):
    # file_lists sorted by list length
    file_list = []
    for i in ids_by_length:
        file_list.append([i+'_'+t[0] for t in lengths[i]])
    
    flatsub = lambda l: list(set([list(l.keys())[0]] + [x for sublist in list(l.values())[0] for x in sublist]))
    sorted_subs_all = []
    for i, rec in enumerate(file_list):
        sorted_subs = []
        for track in rec:
            for j, s in enumerate(subs):
                sflat = flatsub(s)
                if track in sflat:
                    found = True
                    sorted_subs.append(j)
                    break
        sorted_subs_all.append(list(dict.fromkeys(sorted_subs)))
    sorted_subs_all = sorted(sorted_subs_all, key=len)#, reverse=True)

    ordered = sorted_subs_all[0]
    #print('srt', ordered)
    #print()
    for rec in sorted_subs_all[1:]:
        #print('rec', rec)
        for i, n in enumerate(rec):
            if n not in ordered:
                prevs = [m for m in rec[:i]]
                prevs.reverse()
                nexts = [m for m in rec[i+1:]]
                pos = None
                for p in range(max([len(prevs), len(nexts)])):
                    if p < len(prevs)-1:
                        try:
                            pos = ordered.index(prevs[p]) + 1
                            break
                        except:
                            pass
                    if p < len(nexts)-1:
                        try:
                            pos = ordered.index(nexts[p])
                            break
                        except:
                            pass
                if pos != None:
                    ordered.insert(pos, n)
                else:
                    pass#print('cannot reorder item', rec, n)
        #print('srt', ordered)
        #print()
    print(ordered)
    res = [subs[i] for i in ordered]
    #json.dump(res, open('res.json', 'w'))
    return res

def main():
    subgraphs, ids_by_length, ids_by_number_of_matched_files, lengths, jsons = prepare_data(DATE)
    subgraphs = sort_subgraphs(subgraphs, lengths, ids_by_length)
    #pprint(subgraphs)
    #unmatched = jsons['unmatched']
    #jkeys = list(jsons.keys())
    #partitions = [partition_match(jsons, k) for k in jkeys if k != 'unmatched']

    #[print(c, len(p)) for c, p in zip(comb, partitions)]
    #json.dump(partitions, open('partitions.json', 'w'))

main()