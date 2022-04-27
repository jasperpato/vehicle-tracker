import geopandas as gpds
from geopy import distance
import matplotlib.pyplot as plt
from matplotlib import patches
from shapely.geometry import Point
import sys


DROPPED_RSSI = -999

RSSI_LIMITS = (-120, -50)
PRR_LIMITS = (0.4, 1)

MAX_DIST = 300
MIN_LAT = -31.9828 # this chops off losts of dropped packets in 24-04 Cameron 8 20

LEFT, TOP, RIGHT, BOTTOM = 115.814, -31.976, 115.822, -31.986 # map bounds
NUM_SQUARES = 40 # number of square lengths along each axis

WIDTH, HEIGHT = (RIGHT-LEFT) / NUM_SQUARES, (TOP - BOTTOM) / NUM_SQUARES

BIN_RADIUS = 30

BASE = ''
COORDS = {
  'Cameron': (-31.980937, 115.819665),
  'Reid': (-31.979143,115.818025)
}


def usage():
    print('Usage: python3 map.py [-m] [-r] *experiment_number(s)')
    print('eg. python3 map.py 1 4')


def combine_data(date, location, sf, tx):
    '''
    Takes experiment details as inputs.
    Uses receiver and sender files to create a complete data set.
    Treats both missing and corrupted packets as dropped packets, with RSSI = DROPPED_RSSI.
    Cannot handle resets or any decreased or duplicated seq number in files.
    Skips Python block and line comments in files.
    Returns packet reception data as list of tuples (seq, RSSI, dist, lat, long).
    '''

    try:
        n = f'results/{date}-{location.capitalize()}-SF{sf}-{tx}dBm-{{}}.csv'
        r = open(n.format('Receiver'), 'r')
        s = open(n.format('Sender'), 'r')
  
    except:
        usage()
        return None

    base = COORDS[location.capitalize()]
    data = []
  
    receiver = r.readlines()
    skip = False

    for i, l in enumerate(s.readlines()):

        # skip over comments in csv file (''' and #)
        if l == "'''\n" and not skip:
            skip = True
            continue
        if l == "'''\n" and skip:
            skip = False
            continue
        if not l or skip or l[0] == '#': continue
    
        s_data = l.split(',')

        seq = int(s_data[0])
        lat, long = float(s_data[1]), float(s_data[2])

        r_seq, rssi = -1, -1
        r_skip = False
        found = False

        # find matching receiver data
        for rl in receiver:

            # skip over comments in csv file (''' and #)
            if l.strip() == "'''\n" and not r_skip:
                r_skip = True
                continue
            if l.strip() == "'''\n" and r_skip:
                r_skip = False
                continue
            if not l or r_skip or l[0] == '#': continue

            try:
                r_data = rl.split(',')
                if len(r_data) != 14: continue
                r_seq, rssi = int(r_data[1]), int(r_data[9])

            except: pass

            if r_seq == seq:
                found = True
                break

        if not found: rssi = DROPPED_RSSI
        dist = distance.distance( base, (lat, long) ).m

        if dist > MAX_DIST or lat < MIN_LAT: continue

        data.append( (seq, rssi, dist, lat, long) )

    return data


def display(data):
    '''
    Prints data
    '''
    for l in data:
        print(f'seq: {l[0]}, RSSI: {l[1]}, dist: {round(l[2], 4)}, loc: {(l[3], l[4])}')


def grid(data):
    '''
    Groups points into a grid of bins and calculates aggregate data for each bin.
    Input: list of points [ (seq, RSSI, dist, long, lat), ... ]
    Output: dict of bins { (bottom, left): (meanDist, PRR) }
    '''
    bins = {}
    for i in range(NUM_SQUARES):
        x = LEFT + WIDTH * i
        for j in range(NUM_SQUARES):
            y = BOTTOM + HEIGHT * j
            bins[(x,y)] = []

    # sort data into bins
    for l in data:
        for (x, y) in bins.keys():

            lat, long = l[3:]

            if x <= long and long < x + WIDTH and y <= lat and lat < y + HEIGHT:
                bins[(x,y)].append((l[1], l[2]))
                break

    # remove empty bins

    remove = []
    for (x, y), bin_data in bins.items():
        if len(bin_data) == 0:
            remove.append((x,y))
    for r in remove: bins.pop(r) 

    # aggregate bin data
    
    for (x, y), bin_data in bins.items():
        RSSIsum, distSum, dropped = 0, 0, 0

        for d in bin_data:

            if d[0] == DROPPED_RSSI: dropped += 1
            else: RSSIsum += d[0]
            
            distSum += d[1]

        l = len(bin_data)

        if l - dropped == 0: meanRSSI = DROPPED_RSSI
        else: meanRSSI = RSSIsum / (l - dropped)

        bins[(x,y)] = (distSum / l, 1 - dropped / l)

    return bins


def color(r, lim):
    '''
    Returns hex string of color gradient from green -> yellow -> red,
    based on the value of r compared to the limits (min, max).
    Green means high
    '''
    green = int(255 * max(0, min(1, 2 * (r - lim[0]) / (lim[1] - lim[0]))))
    red = int(255 * max(0, min(1, 2 * (1 - (r - lim[0]) / (lim[1] - lim[0])))))
    return '#{:02X}{:02X}00'.format(red, green)


def map(data, grid_data):
    '''
    Input: list of points [ (seq, RSSI, dist, long, lat), ... ]
    Plots data points color-coded by signal strength, and aggregated data squares color-coded by PRR.
    '''

    _, ax = plt.subplots(figsize=(5,7))

    # background map

    for name, col in [
        ('roads-line', 'darkgrey'),
        ('buildings-polygon', 'grey'),
    ]:
        shp = gpds.read_file(f'mygeodata/map/{name}.shp')
        shp.plot(ax=ax, color=col, zorder=-1)

    # grid

    for (x,y), d in grid_data.items():
        c = color(d[1], PRR_LIMITS)
        p = plt.Rectangle((x,y), WIDTH, HEIGHT, color=c, alpha = 0.5)
        ax.add_patch(p)

    # data points

    d = { 'color': [], 'geometry': [] }

    for p in data:
        d['color'].append('#000000' if p[1] == DROPPED_RSSI else color(p[1], RSSI_LIMITS))
        d['geometry'].append(Point( (p[-1], p[-2]) ))

    gdf = gpds.GeoDataFrame(d, crs='EPSG:4326')
    gdf.plot(ax=ax, color=gdf['color'], markersize=1)

    # base station coordinate

    base = Point( COORDS[BASE][1], COORDS[BASE][0] )
    c = { 'geometry': [ base ] }
    gdf = gpds.GeoDataFrame(c, crs='EPSG:4326')
    gdf.plot(ax=ax, color='blue', markersize=20)


def report(point_data, bin_data):
    '''
    Inputs: point_data [ (seq, RSSI, dist, lat, long), ... ],
    bin_data { (x,y): (dist, PRR), ... }
    Reports concentric bin data
    '''

    # make bins

    RSSIs, PRRs = [], []
    for i in range(0, MAX_DIST, BIN_RADIUS):
        RSSIs.append([])
        PRRs.append([])
   
    # put RSSI and PRR in concentric bins 
    #    
    for i in range(len(RSSIs)):

        for p in point_data:
            if i * BIN_RADIUS <= p[2] and p[2] < (i+1) * BIN_RADIUS and p[1] != DROPPED_RSSI:
                RSSIs[i].append(p[1])
        
        for d in bin_data.values():
            if i * BIN_RADIUS <= d[0] and d[0] < (i+1) * BIN_RADIUS:
                PRRs[i].append(d[1])

    # print report

    for i in range(len(RSSIs)):
        if len(RSSIs[i]) == 0 or len(PRRs) == 0: continue
        print(f'{i * BIN_RADIUS} <= Radius < {(i+1) * BIN_RADIUS}')
        print(f'Mean RSSI: {sum(RSSIs[i]) / len(RSSIs[i])}')
        print(f'Mean PRR: {sum(PRRs[i]) / len(PRRs[i])}\n')


if __name__ == '__main__':
    '''
    Usage: python3 map.py [-m] [-r] *experiment_number(s)
    [-m] for only mapping
    [-r] for only reporting
    Default is mapping and reporting.
    '''

    exp = {
        1: ('24-04', 'Reid', 7, 13),
        2: ('24-04', 'Reid', 7, 18),
        3: ('24-04', 'Reid', 8, 20),
        4: ('24-04', 'Cameron', 7, 13),
        5: ('24-04', 'Cameron', 7, 18),
        6: ('24-04', 'Cameron', 8, 20),
    }

    m = sys.argv[1] == '-m'
    r = sys.argv[1] == '-r'
    if sys.argv[1] == '-m' or sys.argv[1] == '-r':
        sys.argv.pop(1)

    for a in sys.argv[1:]:

        BASE = exp[int(a)][1]

        d = combine_data(*exp[int(a)])
        g = grid(d)

        if not m:
            print(f'\n{exp[int(a)]}\n')
            report(d, g)

        if not r: map(d, g)

    plt.show(block=True)
  

  
