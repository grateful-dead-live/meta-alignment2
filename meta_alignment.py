import os, json, copy
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt
import matplotlib.patches as patches

MIN_R = 0.9999

ref_lengths = 'data/gd1982-10-10.nak700.anon-poris.LMPP.95682.flac16_lenghts.json'

base_dir = 'data/ref_gd1982-10-10.nak700.anon-poris.LMPP.95682.flac16_cens_smoothing_21/'
rec_dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if d != '.DS_Store']
permutation = [4, 9, 3, 1, 8, 2, 0, 5, 7, 6]
rec_dirs = [rec_dirs[i] for i in permutation]

#rec_dirs = rec_dirs[:3]
match_files = [[os.path.join(r, m) for m in os.listdir(r) if m.endswith('.json')] for r in rec_dirs]
matches = [[json.load(open(m)) for m in ms] for ms in match_files]

flatten = lambda l: [item for sublist in l for item in sublist]
split = lambda l, locs: [l[i:j] for i, j in zip([0]+locs, locs+[None])]

#splits into 10s segments based on thomas's backwards sorting
def split_segments(points):
    locs = [i for i, p in enumerate(points) if i > 0 and p[0] > points[i-1][0]]
    return split(points, locs)

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
def partition_match(match):
    points = match['dtw']
    if (len(points) > 0 and stats.linregress(points)[2] < MIN_R):
        parts = partition(split_segments2(points))
        print(match['file'], 'split into', [len(p) for p in parts])
        return parts
    return [[sorted(points)]] #all one partition

def plot_timelines(timelines, names, outfile):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    max_time = max([s[1] for t in timelines for part in t for s in part])
    min_time = min([s[0] for t in timelines for part in t for s in part])
    norm = lambda t: t-min_time#(t-min_time)/(max_time-min_time)
    print(min_time, max_time)
    height = 1.0/(len(timelines))
    for i, tl in enumerate(timelines):
        for j, part in enumerate(tl):
            [ax.add_patch(patches.Rectangle((norm(s[0]), 1-((i+1)*height)), norm(s[1])-norm(s[0]),
                height, alpha=0.3, color='r' if j % 2 is 0 else 'b', linewidth=0)) for s in part]
        ax.text(200, 1-((i+0.5)*height), names[i], fontsize=4)
    ax.set_xlim(0, max_time-min_time)
    ax.set_xlabel('reference time in seconds')
    ax.set_yticklabels([])
    ax.set_yticks([])
    ax.set_ylabel('recording')
    fig.patch.set_facecolor('white')
    plt.savefig(outfile, facecolor='white', edgecolor='none')

def fill_gaps(tracks, lengths):
    gapless = copy.deepcopy(tracks)
    for i, partitions in enumerate(gapless):
        length = lengths[i]
        first_seg = partitions[0][0]
        if len(first_seg) > 0:
            #add audio before first matched segment
            first_point = first_seg[0]
            if first_point[0] > 0:
                first_seg.insert(0, [0, first_point[1]-first_point[0]])
            #add audio after last matched segment
            last_seg = partitions[-1][-1]
            last_point = last_seg[-1]
            if last_point[0] < length:
                last_seg.append([length, last_point[1]+(length-last_point[0])])
            #fill gaps between all other matched segments
            for j, p in enumerate(partitions):
                if j < len(partitions)-1:
                    current_last = p[-1][-1]
                    next_first = partitions[j+1][0][0]
                    xdiff = next_first[0] - current_last[0]
                    if xdiff > 0:# >0 sec gap
                        p[-1].append([next_first[0], current_last[1] + xdiff])
        else: #track has no match -> stick before or after matched track
            if i < len(gapless)-1:
                first_of_next_part = gapless[i+1][0][0][0]
                partitions[0][0] = [[0, first_of_next_part[1]-length], [length, first_of_next_part[1]]]
            else:
                last_of_previous_part = gapless[i-1][0][0][0]
                partitions[0][0] = [[0, last_of_previous_part[1]], [length, last_of_previous_part[1]+length]]
    return gapless



seglimits = lambda parts: [[s[0][1], s[-1][1]] for p in parts for s in p if len(s) > 0]
partlimits = lambda parts: [[p[0][0][1], p[-1][-1][1]] for p in parts]

#TIMELINE WITH PLACES WHERE EVERY REF SEGMENT IS FROM
def construct_timeline(matches):
    pairs = [[(partition_match(m), m['length']) for m in ms] for ms in matches]
    partitions = [[p[0] for p in ps] for ps in pairs]
    gapless = [[fill_gaps(p[0], p[1]) for p in ps] for ps in pairs]
    plot_timelines([[seglimits(p) for p in ps] for ps in partitions], 'seglines.pdf')
    plot_timelines([[partlimits(p) for p in ps] for ps in partitions], 'partlines.pdf')
    plot_timelines([[partlimits(p) for p in ps] for ps in gapless], 'timelines.pdf')

def get_ref_tracks():
    lengths = list(json.load(open(ref_lengths)).values())
    ref_starts = [sum(lengths[:i]) for i in range(len(lengths))]
    return [[[ref_starts[i], ref_starts[i]+lengths[i]]] for i in range(len(lengths))]

def split_at_loc(tracks, location, insert):
    #print(location, insert)
    for i, t in enumerate(tracks):
        tracks[i] = flatten([[[p[0], location], [location+insert, p[1]+insert]]
            if p[0] < location and location < p[1] else [p] for p in t])
    #UPDATE!!!!!
    #i, j = next(((i, j) for i, t in enumerate(tracks) for j, p in enumerate(t) if p[0] < location and location < p[1]), None)
    #part_to_split = tracks[i][j]
    # tracks[i] = flatten([[[p[0], location], [location+insert, p[1]+insert]]
    #     if p is part_to_split else [p] for p in tracks[i]])

def push_back(track, delta):
    track[0] += delta
    track[1] += delta

def plot_seglines(matches):
    ref_tracks = get_ref_tracks()
    partitions = [[partition_match(m) for m in ms] for ms in matches]
    limits = [[seglimits(p) for p in ps] for ps in partitions]
    limits.insert(0, ref_tracks)
    names = ['gd1982-10-10.nak700.anon-poris.LMPP.95682.flac16']+[d.replace(base_dir, '') for d in rec_dirs]
    plot_timelines(limits, names, 'seglines5.pdf')

def construct_timeline_forreal(matches):
    ref_tracks = get_ref_tracks()
    #print(ref_tracks)
    partitions = [[partition_match(m) for m in ms] for ms in matches]
    
    lengths = [[m['length'] for m in ms] for ms in matches]
    gapless = [fill_gaps(partitions[i], lengths[i]) for i in range(len(matches))]
    
    limits = [[partlimits(p) for p in ps] for ps in gapless]
    limits.insert(0, ref_tracks)
    
    print([p for r in limits for t in r for p in t if p[0] <= 100])
    
    for i, rec in enumerate(limits):
        parts = [p for track in rec for p in track]
        for j, p in enumerate(parts):
            if j > 0 and p[0] < parts[j-1][1]:
                start = p[0]
                end = parts[j-1][1]
                duration = end - start
                print('overlap!', i, j, duration, end)
                #push back all later tracks of all shows including reference   if p[0] <= start and p[1] >= end
                [push_back(p, duration) for r in limits for t in r for p in t if (p[0] >= start or (p[0] < start and p[1] > end)) and r is not rec]
                #push back later tracks of this recording
                [push_back(p, duration) for t in rec for p in t if p[0] >= start]
                #split the reference at location
                #split_at_loc(ref_tracks, end, duration)
                #[split_at_loc(r, end, duration) for r in limits if r is not rec]
    
    print([p for r in limits for t in r for p in t if p[0] <= 100])
    
    names = ['gd1982-10-10.nak700.anon-poris.LMPP.95682.flac16']+[d.replace(base_dir, '') for d in rec_dirs]
    plot_timelines(limits, names, 'timelines5.pdf')
    #print([[p[0][0][0] for p in ps] for ps in gapless])
    #[[add_track_to_timeline(p) for p in ps] for ps in gapless]

construct_timeline_forreal(matches)
