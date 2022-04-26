import geopandas as gpds
from geopy import distance
import matplotlib.pyplot as plt
from shapely.geometry import Point
import sys


DROPPED_RSSI = -999
MAX_DIST = 300
RSSI_LIMITS = (-120, -50)
COORDS = {
  "Cameron": (-31.980937, 115.819665),
  "Reid": (-31.979143,115.818025)
}


def usage():
    print('Usage: python3 analysis.py date location sf tx')
    print("eg. python3 analysis.py 24-04 Cameron 7 13")


def combine_data(date, location, sf, tx):
    '''
    Takes experiment details as inputs.
    Uses receiver and sender files to create a complete data set.
    Handles both missing and corrupted packets as dropped packets, with
    RSSI = DROPPED_RSSI.
    Cannot handles resets (decreased seq number) in files.
    Skips Python block and line comments in files.
    Returns packet reception data as list of tuples (seq, RSSI, dist, lat, long).
    '''

    try:
        n = f"results/{date}-{location.capitalize()}-SF{sf}-{tx}dBm-{{}}.csv"
        r = open(n.format("Receiver"), 'r')
        s = open(n.format("Sender"), 'r')
  
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
            if l == "'''\n" and not r_skip:
                r_skip = True
                print("'''")
                continue
            if l == "'''\n" and r_skip: r_skip = False
            if not l or r_skip or l[0] == '#':
                print('#')
                continue

            try:
                r_data = rl.split(',')
                if len(r_data) != 14: continue
                r_seq, rssi = int(r_data[1]), int(r_data[9])
                # print(r_seq, rssi)

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
        print(f"seq: {l[0]}, RSSI: {l[1]}, dist: {round(l[2], 4)}, loc: {(l[3], l[4])}")


def RSSI_limits(data):
    '''
    Returns (min, max) of RSSI values
    '''
    min, max = -DROPPED_RSSI, DROPPED_RSSI
    for d in data:
        if d[1] == DROPPED_RSSI: continue
        if d[1] < min: min = d[1]
        if d[1] > max: max = d[1]

    print(min, max)
    return (min, max)


def RSSI_color(r):
    '''
    Takes r: RSSI, lim: (min, max) RSSI in data
    Returns hex string of RSSI color gradient from green -> yellow -> red
    '''
    lim = RSSI_LIMITS
    green = int(255 * min(1, 2 * (r - lim[0]) / (lim[1] - lim[0])))
    red = int(255 * min(1, 2 * (1 - (r - lim[0]) / (lim[1] - lim[0]))))
    return "#{:02X}{:02X}00".format(red, green)


def map(data, location):

    _, ax = plt.subplots(figsize=(6,8))

    # background map

    for name, col in [
        ("roads-line", "darkgrey"),
        ("buildings-polygon", "grey"),
    ]:
        shp = gpds.read_file(f"mygeodata/map/{name}.shp")
        shp.plot(ax=ax, color=col)

    # data points

    d = { "color": [], "geometry": [] }

    # lim = RSSI_limits(data)
    # print(lim)

    for p in data:
        d["color"].append("#000000" if p[1] == DROPPED_RSSI else RSSI_color(p[1]))
        d["geometry"].append(Point( (p[-1], p[-2]) ))

    gdf = gpds.GeoDataFrame(d, crs="EPSG:4326")
    gdf.plot(ax=ax, color=gdf["color"], markersize=1)

    # base station coordinate

    base = Point( COORDS[location.capitalize()][1], COORDS[location.capitalize()][0] )
    c = { "geometry": [ base ] }
    gdf = gpds.GeoDataFrame(c, crs="EPSG:4326")
    gdf.plot(ax=ax, color="blue", markersize=20)

    plt.show(block=True)

if __name__ == "__main__":

    if len(sys.argv) != 5:
        usage()
        exit(1)

    data = combine_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    
    # display(data)

    map(data, sys.argv[2])
  

  
