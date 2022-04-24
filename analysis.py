
def report_dropped(filename):
  '''
  Reports dropped packets in a data file.
  Usage: python3 analysis.py fileno
  '''

  f = None
  try: f = open(filename, 'r')
  except:
    print("Usage: python3 analysis.py fileno")
    exit(1)

  prev_coords = ()
  prev_seq = -1
  dropped = []
  seq_resets = 0

  for i, l in enumerate(f.readlines()):
    
    d = l.split(',')
    if len(d) != 14: continue
    
    coords = ()
    seq = -1

    try:
      coords = (float(d[2]), float(d[3]))
      seq = int(d[1])
    except: continue

    if seq < prev_seq: # assume reset
      seq_resets += prev_seq - seq

    seq += seq_resets

    if i > 0 and seq > prev_seq + 1:
      # print(f"Dropped {seq - prev_seq - 1} packet(s) between {prev_seq} and {seq}, {prev_coords} and {coords}.\n")
      dropped.append(((prev_seq, prev_coords), (seq, coords)))

    prev_seq = seq
    prev_coords = coords

  return dropped

if __name__ == "__main__":
  import sys
  
  dropped = report_dropped(f"./results/lora-CSSE-mobile-exp{sys.argv[1]}-22-04.csv")
  
  for i in dropped:
    print(f"Dropped {i[1][0] - i[0][0] - 1} packet(s) between {i[0][0]} and {i[1][0]}, {i[0][1]} and {i[1][1]}.\n")