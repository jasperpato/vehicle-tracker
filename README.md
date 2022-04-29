# Data

The collected data can be found in /data.

Receiver data is in csv form with header:
Time, Number, S_Lat, S_Long, Bandwidth, CodingRate, Frequency, SpreadingFactor, TxPower, PacketRSSI, RSSI, SNR, R_Lat, R_Long

Sender data is in csv format with header:
Number, S_Lat, S_Long

# Analysis

map.py cleans and analyses each dataset. It maps the RSSI of each data point and the PRR of each tile in a grid around the receiver node. It also reports the mean RSSI and PRR in distance intervals from the receiver node.

# Usage

```
> git clone https://github.com/jasperpato/vehicle-tracker
> cd vehicle-tracker
> python3 -m venv venv
> source venv/bin/activate
> pip install -r req.txt
> python3 map.py [-m: mapping only] [-r: reporting only] [--all: all datasets] *dataset_numbers
```
