import re
from collections import defaultdict

with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\scratch\report.txt") as f:
    lines = f.readlines()

best_hours = []

current_tf = None
current_rr = None

# To find overall best hour, we could aggregate trades and wins per hour
agg = defaultdict(lambda: {'wins': 0, 'trades': 0})

for line in lines:
    line = line.strip()
    if line.startswith("Timeframe:"):
        current_tf = line.split(":")[-1].strip()
    elif line.startswith("RR"):
        current_rr = line.split(":")[0].strip()
    elif line.startswith("Hour"):
        # Hour 00: 1004 trades, WR: 30.88%
        match = re.search(r"Hour (\d+): (\d+) trades, WR: ([\d.]+)%", line)
        if match:
            hr, trades, wr = match.groups()
            hr = int(hr)
            trades = int(trades)
            wr = float(wr)
            wins = round((wr / 100) * trades)
            agg[hr]['trades'] += trades
            agg[hr]['wins'] += wins
            if trades > 100:  # Minimum sample size
                best_hours.append({
                    'tf': current_tf,
                    'rr': current_rr,
                    'hour': hr,
                    'trades': trades,
                    'wr': wr
                })

print("Top 10 Hours across all setups (min 100 trades):")
best_hours.sort(key=lambda x: x['wr'], reverse=True)
for i in range(10):
    b = best_hours[i]
    print(f"TF: {b['tf']:5s} | {b['rr']} | Hour {b['hour']:02d} | WR: {b['wr']:5.2f}% | Trades: {b['trades']}")

print("\nAggregate Best Hours (Total across all TFs and RRs):")
agg_list = []
for hr, data in agg.items():
    if data['trades'] > 0:
        wr = (data['wins'] / data['trades']) * 100
        agg_list.append((hr, wr, data['trades']))

agg_list.sort(key=lambda x: x[1], reverse=True)
for hr, wr, trades in agg_list[:10]:
    print(f"Hour {hr:02d} | Overall WR: {wr:5.2f}% | Total Trades: {trades}")
