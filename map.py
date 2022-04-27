import geopandas as gpds
from geopy import distance
import matplotlib.pyplot as plt
from shapely.geometry import Point
import sys


DROPPED_RSSI = -999
RSSI_LIMITS = (-120, -50)
PRR_LIMITS = (0.4, 1)

MAX_DIST = 400

LEFT, TOP, RIGHT, BOTTOM = 115.814, -31.976, 115.822, -31.986 # map bounds
NUM_SQUARES = 30 # number of square lengths along each axis
WIDTH, HEIGHT = (RIGHT-LEFT) / NUM_SQUARES, (TOP - BOTTOM) / NUM_SQUARES

BASE = ''
COORDS = {
  'Cameron': (-31.980937, 115.819665),
  'Reid': (-31.979143,115.818025)
}


def usage():
    print('Usage: python3 map.py *experiment_number(s)')
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
        data.append( (seq, rssi, dist, lat, long) )

    # find and delete outliers

    for i, d in enumerate(data):
        if d[2] > MAX_DIST: data.pop(i)

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
    Output: dict of bins { (bottom, left): (meanRSSI, meanDist, PRR) }
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

    # aggregate bin data
    remove = []
    for (x, y), bin_data in bins.items():
        
        if len(bin_data) == 0:
            remove.append((x,y))
            continue

        RSSIsum, distSum, dropped = 0, 0, 0

        for d in bin_data:

            if d[0] == DROPPED_RSSI: dropped += 1
            else: RSSIsum += d[0]
            
            distSum += d[1]

        l = len(bin_data)

        if l - dropped == 0: meanRSSI = -999
        else: meanRSSI = RSSIsum / (l - dropped)

        bins[(x,y)] = (meanRSSI, distSum / l, 1 - dropped / l)

    for r in remove: bins.pop(r) 

    return bins


def color(r, lim):
    '''
    Returns hex string of color gradient from green -> yellow -> red
    '''
    green = int(255 * max(0, min(1, 2 * (r - lim[0]) / (lim[1] - lim[0]))))
    red = int(255 * max(0, min(1, 2 * (1 - (r - lim[0]) / (lim[1] - lim[0])))))
    return '#{:02X}{:02X}00'.format(red, green)


def map(data, grid_data):
    '''
    Input: list of points [ (seq, RSSI, dist, long, lat), ... ], experiment location string
    Plots points on map, color-coded by signal strength.
    Plots bins color-coded by PRR.
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
        c = color(d[2], PRR_LIMITS)
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

    # plt.show(block=True)


if __name__ == '__main__':
    '''
    Usage: python3 map.py *experiment_number(s)
    '''

    exp = {
        1: ('24-04', 'Reid', 7, 13),
        2: ('24-04', 'Reid', 7, 18),
        3: ('24-04', 'Reid', 8, 20),
        4: ('24-04', 'Cameron', 7, 13),
        5: ('24-04', 'Cameron', 7, 18),
        6: ('24-04', 'Cameron', 8, 20),
    }

    for a in sys.argv[1:]:
        BASE = exp[int(a)][1]
        data = combine_data(*exp[int(a)])
        grid_data = grid(data)
        map(data, grid_data)
    
    plt.show(block=True)
  

  
