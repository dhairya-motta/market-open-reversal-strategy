import re
from collections import defaultdict

with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\scratch\report.txt") as f:
    lines = f.readlines()

# Structure: rr_data[rr][hour] = {'wins': 0, 'trades': 0}
rr_data = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'trades': 0}))

current_rr = None

for line in lines:
    line = line.strip()
    if line.startswith("RR"):
        current_rr = line.split(":")[0].strip().replace("RR ", "")
    elif line.startswith("Hour"):
        match = re.search(r"Hour (\d+): (\d+) trades, WR: ([\d.]+)%", line)
        if match:
            hr, trades, wr = match.groups()
            hr = int(hr)
            trades = int(trades)
            wr = float(wr)
            wins = round((wr / 100) * trades)
            rr_data[current_rr][hr]['trades'] += trades
            rr_data[current_rr][hr]['wins'] += wins

# Generate markdown
md_content = "# Best Hours by Risk-Reward (RR)\n\n"
md_content += "This breakdown shows the most optimal trading hours for each specific Risk-Reward target, aggregated across all timeframes.\n\n"

for rr in sorted([int(x) for x in rr_data.keys()]):
    rr_str = str(rr)
    md_content += f"### Target: {rr}R\n\n"
    md_content += "| Rank | Hour (ET) | Win Rate | Total Trades |\n"
    md_content += "|:---:|:---|:---:|:---|\n"
    
    hour_stats = []
    for hr, data in rr_data[rr_str].items():
        if data['trades'] > 50: # Ensure some minimum sample size
            wr = (data['wins'] / data['trades']) * 100
            hour_stats.append((hr, wr, data['trades']))
            
    hour_stats.sort(key=lambda x: x[1], reverse=True)
    
    medals = ["🥇", "🥈", "🥉", "4", "5"]
    for i, (hr, wr, trades) in enumerate(hour_stats[:5]):
        medal = medals[i]
        md_content += f"| {medal} | **{hr:02d}:00** | **{wr:.2f}%** | {trades:,} |\n"
    
    md_content += "\n"

with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\scratch\best_hours_by_rr.md", "w", encoding="utf-8") as f:
    f.write(md_content)
print("Done writing markdown.")
