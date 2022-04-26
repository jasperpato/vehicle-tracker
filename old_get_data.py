from map import COORDS, MAX_DIST, usage, distance


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


def get_data(date, location, sf, tx):

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
        # print(n.format("Receiver"))
        r = open(n.format("Receiver"), 'r')
        s = open(n.format("Sender"), 'r')
  
    except:
        usage()
        return None

    sender = s.readlines()
    base = COORDS[location.capitalize()]
    data = []
  
    prev_seq = -1
    skip = False

    for i, l in enumerate(r.readlines()):

        # skip over comments in csv file (''' and #)
        if l == "'''\n" and not skip:
            skip = True
            continue
        if l == "'''\n" and skip: skip = False
        if not l or skip or l[0] == '#': continue
    
        d = l.split(',')
        if len(d) != 14: continue

        try:
            seq = int(d[1])
            lat, long = float(d[2]), float(d[3])
            RSSI = int(d[9])

        except: continue
    
        if i > 0 and seq - prev_seq > 1: # find dropped packets in sender file
      
            for ll in sender:

                # skip over comments in csv file (''' and #)
                if ll == "'''\n" and not skip:
                    skip = True
                    continue
                if ll == "'''\n" and skip: skip = False
                if not ll or skip or ll[0] == '#': continue

                s, la, lo = ll.split(',')
                s, la, lo = int(s), float(la), float(lo)
        
                if s <= prev_seq: continue
                if s == seq: break

                dist = distance.distance( base, (la, lo) ).m
                data.append((s, DROPPED_RSSI, dist, la, lo))

        dist = distance.distance( base, (lat, long) ).m
        data.append((seq, RSSI, dist, lat, long))

        prev_seq = seq

    # find and delete outliers

    for i, d in enumerate(data):
        if d[2] > MAX_DIST: data.pop(i)

    return data