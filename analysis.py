'''
Reports dropped packets in a data file.
Usage: python3 analysis.py fileno
'''
import sys

f = None
try: f = open(f"./results/lora-CSSE-mobile-exp{sys.argv[1]}-22-04.csv", 'r')
except:
  print("Usage: python3 analysis.py fileno")
  exit(1)

prev_coords = ()
prev_seq = -1

print()
for i, l in enumerate(f.readlines()):
  
  d = l.split(',')
  if len(d) != 14: continue
  
  coords = ()
  seq = -1
  
  try:
    coords = (float(d[2]), float(d[3]))
    seq = int(d[1])
  except: continue

  if i > 0 and seq > prev_seq + 1:
    print(f"Dropped {seq - prev_seq - 1} packet(s) between {prev_seq} and {seq}, {prev_coords} and {coords}.\n")
  
  prev_seq = seq
  prev_coords = coords
