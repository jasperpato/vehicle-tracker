
DROPPED_RSSI = -999

COORDS = {
  "Cameron": (-31.980937, 115.819665),
  "Reid": (-31.979143,115.818025)
}

def usage():
  print('Usage: python3 analysis.py date location sf tx')
  print("eg. python3 analysis.py 24-04 Cameron 7 13")


def get_data(date, location, sf, tx):
  '''
  Takes experiment details as inputs.
  Uses receiver and sender files to create a complete data set.
  Handles both missing and corrupted packets as dropped packets, with
  RSSI = DROPPED_RSSI.
  Cannot handles resets (decreased seq number) in files.
  Returns packet reception data as list of tuples (seq, RSSI, dist, lat, long).
  '''
  import geopy.distance as gpd
  
  try:
    n = f"results/{date}-{location.capitalize()}-SF{sf}-{tx}dBm-{{}}.csv"
    print(n.format("Receiver"))
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
      RSSI = int(d[10])

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
        
        if int(s) <= prev_seq: continue
        if int(s) == seq: break

        dist = gpd.geodesic(base, (float(la), float(lo))).m
        data.append((int(s), DROPPED_RSSI, dist, float(la), float(lo)))

    dist = gpd.geodesic(base, (lat, long)).m
    data.append((seq, RSSI, dist, lat, long))

    prev_seq = seq

  return data


def display(data):
  for l in data:
    print(f"seq: {l[0]}, RSSI: {l[1]}, dist: {round(l[2], 4)}, loc: {(l[3], l[4])}")


if __name__ == "__main__":
  import sys
  
  if len(sys.argv) != 5:
    usage()
    exit(1)

  data = get_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
  display(data)
  
  exit(0)