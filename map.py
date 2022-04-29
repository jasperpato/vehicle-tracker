import geopandas as gpds # https://geopandas.org/en/stable/
from geopy import distance # https://github.com/geopy/geopy
import matplotlib.pyplot as plt # https://matplotlib.org/
from shapely.geometry import Point # https://github.com/shapely/shapely
import sys


# base coordinates

COORDS = {
  'Cameron': (-31.980937, 115.819665),
  'Reid': (-31.979143,115.818025)
}

DROPPED_RSSI = -999

# for coloring

RSSI_LIMITS = (-120, -50)
PRR_LIMITS = (0.4, 1)

# remove false GPS readings

MAX_DIST = 600
MIN_LAT, MAX_LAT = -31.9828, -31.9776
MIN_LONG, MAX_LONG = 115.816, 115.821

# for tiling

LEFT, TOP, RIGHT, BOTTOM = 115.814, -31.976, 115.822, -31.986 # map bounds
NUM_SQUARES = 40 # number of square lengths along each axis

WIDTH, HEIGHT = (RIGHT-LEFT) / NUM_SQUARES, (TOP - BOTTOM) / NUM_SQUARES

# for concentric binning

BIN_RADIUS = 30


def usage():
    print('python3 map.py [-m: mapping only] [-r: reporting only] [--all: all datasets] *dataset_numbers')
    print('eg. python3 map.py 1 4')


def combine_data(date, location, sf, tx):
    '''
    Takes experiment details as inputs.
    Uses receiver and sender files to create a complete data set.
    Treats both missing and corrupted packets as dropped packets, with RSSI = DROPPED_RSSI.
    Cannot handle resets or any decreased or duplicated seq number in files.
    Skips Python block and line comments in files.
    Assumes transmitter data is uncorrupted.
    Returns packet reception data as list of tuples (seq, RSSI, dist, lat, long).
    '''

    try:
        n = f'data/{date}-{location}-SF{sf}-{tx}dBm-{{}}.csv'
        r = open(n.format('Receiver'), 'r')
        s = open(n.format('Sender'), 'r')
  
    except:
        usage()
        return None

    base = COORDS[location]
    data = []
  
    receiver = r.readlines()
    skip = False

    for l in s.readlines():

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
                if len(r_data) != 14: continue # corrupted if there is not 14 fields
                r_seq, rssi = int(r_data[1]), int(r_data[9]) # corrupted if seq or rssi is not int

            except: pass

            if r_seq == seq:
                found = True
                break

        if not found: rssi = DROPPED_RSSI # never reached receiver
        dist = distance.distance( base, (lat, long) ).m

        if dist > MAX_DIST or lat < MIN_LAT or lat > MAX_LAT or long < MIN_LONG or long > MAX_LONG: continue

        data.append( (seq, rssi, dist, lat, long) )

    return tuple(data)


def grid(data):
    '''
    Groups points into a grid of tiles and calculates PRR for each tile.
    Input: list of points [ (seq, RSSI, dist, long, lat), ... ]
    Output: list of tile data: [ (bottom_lat, left_long, PRR), ... ]
    '''

    # initialise tiles

    tile = []
    for i in range(NUM_SQUARES):
        x = LEFT + WIDTH * i
        for j in range(NUM_SQUARES):
            y = BOTTOM + HEIGHT * j
            tile.append([x, y, []])# left, bottom, list of RSSIs in tile

    # sort data into tiles

    for l in data:
        for i, t in enumerate(tile):
            lat, long = l[3:]
            x, y = t[:2]
            if x <= long and long < x + WIDTH and y <= lat and lat < y + HEIGHT:
                tile[i][2].append(l[1])
                break

    # remove empty tiles

    new_tile = []
    for t in tile:
        if len(t[2]): new_tile.append(t)
    tile = new_tile

    # replace RSSI list with PRR for each tile
    
    for t in tile:
        dropped = 0
        for r in t[2]:
            if r == DROPPED_RSSI: dropped += 1
        t[2] = 1 - dropped / len(t[2])

    return tile


def color(r, lim):
    '''
    Returns hex string of color gradient from green -> yellow -> red,
    based on the value of r compared to the limits (min, max).
    Green means high
    '''
    green = int(255 * max(0, min(1, 2 * (r - lim[0]) / (lim[1] - lim[0]))))
    red = int(255 * max(0, min(1, 2 * (1 - (r - lim[0]) / (lim[1] - lim[0])))))
    return '#{:02X}{:02X}00'.format(red, green)


def map(data, grid_data, base, title):
    '''
    Input: list of points [ (seq, RSSI, dist, long, lat), ... ]
    Plots data points color-coded by signal strength, and aggregated data squares color-coded by PRR.
    '''

    _, ax = plt.subplots(figsize=(6,9))
    plt.title(title)

    # background map

    for name, col in [ ('roads-line', 'darkgrey'), ('buildings-polygon', 'grey') ]:
        shp = gpds.read_file(f'mygeodata/map/{name}.shp')
        shp.plot(ax=ax, color=col, zorder=-1)

    # PRR grid

    for x, y, prr in grid_data:
        c = color(prr, PRR_LIMITS)
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

    b = Point( COORDS[base][1], COORDS[base][0] )
    c = { 'geometry': [ b ] }
    gdf = gpds.GeoDataFrame(c, crs='EPSG:4326')
    gdf.plot(ax=ax, color='blue', markersize=20)


def radius_intervals(point_data):
    '''
    Input: point_data [ (seq, RSSI, dist, lat, long), ... ],
    Output: list of radius interval data [ (min_radius, max_radius, num_points, meanRSSI, PRR), ... ]
    '''

    # make bins

    bins = []
    for i in range(MAX_DIST // BIN_RADIUS):
        bins.append( [i * BIN_RADIUS, (i+1) * BIN_RADIUS, 0, 0, 0] )
   
    # find num_datapoints, RSSI and PRR for each interval
    
    for i in range(len(bins)):
        num, RSSIsum, dropped = 0, 0, 0
        for p in point_data:
            if i * BIN_RADIUS <= p[2] and p[2] < (i+1) * BIN_RADIUS:
                num += 1
                if p[1] == DROPPED_RSSI: dropped += 1
                else: RSSIsum += p[1]
        if num:
            bins[i][2] = num
            bins[i][3] = RSSIsum / (num - dropped) if (num - dropped) else DROPPED_RSSI
            bins[i][4] = 1 - dropped / num

    # cast data to tuple

    for i, b in enumerate(bins): bins[i] = tuple(b)

    return tuple(bins)


if __name__ == '__main__':
    '''
    python3 map.py [-m: mapping only] [-r: reporting only] [--all: all datasets] *dataset_numbers
    '''

    exp = [
        ('24-04', 'Reid', 7, 13),
        ('24-04', 'Reid', 7, 18),
        ('24-04', 'Reid', 8, 20),
        ('24-04', 'Cameron', 7, 13),
        ('24-04', 'Cameron', 7, 18),
        ('24-04', 'Cameron', 8, 20)
    ]

    # parse command line options

    m = sys.argv[1] == '-m'
    r = sys.argv[1] == '-r'
    if sys.argv[1] == '-m' or sys.argv[1] == '-r':
        sys.argv.pop(1)

    all = False
    if len(sys.argv) > 1: all = sys.argv[1] == '--all'

    # store radial data for comparison

    param_data = [[], [], [], [], [], []]
    
    #loop through datasets

    for a in (sys.argv[1:] if m else range(6)):

        date, base, sf, tx = exp[int(a)]
        title = f'{date} {base} SF{sf} TX{tx}'

        point_data = combine_data(date, base, sf, tx)
        grid_data = grid(point_data)

        radius_data = radius_intervals(point_data)

        # store radial data for comparison

        if not m:
            for d in radius_data: param_data[int(a)].append(d)

        if not r and (all or str(a) in sys.argv[1:]): map(point_data, grid_data, base, title)

    # group data with same params from each experiment and compare parameter sets

    if not m:
        param_results = [[], [], []]

        # for each parameter set

        for i in range(3):
            
            # for each radius interval

            for j in range(MAX_DIST // BIN_RADIUS):
                r1, r2, num1, rssi1, prr1 = param_data[i][j]
                num2, rssi2, prr2 = param_data[i+3][j][2:]

                # consider radius intervals coontaining no data points

                if not num1:
                    if not num2:
                        param_results[i].append(())
                        continue
                    param_results[i].append(param_data[i+3][j])
                    continue
                if not num2:
                    param_results[i].append(param_data[i][j])
                    continue

                # combine data with the same parameters from both experiments

                meanRSSI = (rssi1 * num1 + rssi2 * num2) / (num1 + num2)
                meanPRR = 1 - ((1 - prr1) * num1 + (1 - prr2) * num2) / (num1 + num2)
                param_results[i].append((r1, r2, num1+num2, meanRSSI, meanPRR))

        # compare parameter sets at each radius

        print('\n' + 15 * ' ', end='')
        print("     SF7 TX13          SF7 TX18          SF8 TX20     ")

        # for storing average PRR percentage increase

        meanParams = [[0, 0, 0], [0, 0, 0]]

        for j in range(MAX_DIST // BIN_RADIUS):

            # continue if no data points in interval

            if not param_results[0][j] and not param_results[1][j] and not param_results[2][j]: continue

            print()
            print(f'{j * BIN_RADIUS:3} <= r < {(j+1) * BIN_RADIUS:3}:', end = '')
            rssi1, prr1 = param_results[0][j][3:]

            for i in range(3):
                rssi, prr = param_results[i][j][3:]
                if param_results[i][j]:
                    if i > 0:
                        print(f'  {rssi:7.02f} ', end = '')
                        percent = (rssi - rssi1) / -rssi1 * 100
                        print(f'({percent:5.02f}%) ', end='')

                        # store percentage increase

                        meanParams[i-1][0] += 1
                        meanParams[i-1][1] += percent

                    else: print(f'     {rssi:7.02f}     ', end = '')
                else: print(' ' * 10)
            print('\n' + 15 * ' ', end='')
            for i in range(3):
                rssi, prr = param_results[i][j][3:]
                if param_results[i][j]:
                    if i > 0:
                        print(f'  {prr:7.04f} ', end='')
                        percent = (prr - prr1) / prr1
                        print(f'({percent:5.02f}%) ', end='')

                        # store percentage increase

                        meanParams[i-1][2] += percent

                    else: print(f'     {prr:7.04f}     ', end='')
                else: print(' ' * 10)
            print()
        print()

        # report mean PRR percentage increase

        print('Mean PRR percentage increases:\n')
        for t, p in zip(('SF7 TX18', 'SF8 TX20'), meanParams):
            print(f'{t}: {p[2] / 12:5.04f}')
        print()

    plt.show(block=True)