import pandas as pd
import numpy as np

PENALTY_PTS = 0.75
TARGET_R = 1.0

def load_data():
    print("Loading NSX dataset...")
    df = pd.read_csv(r"C:\Users\kingcuber\.gemini\antigravity-ide\scratch\nsx_cleaned_2010_2024.csv")
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
    df.set_index('timestamp', inplace=True)
    df = df.between_time('09:30', '16:00')
    df['date'] = df.index.date
    return df

def extract_and_simulate(df):
    days = df['date'].unique()
    print(f"Loaded {len(days)} days of NSX data. Extracting and simulating...")

    results = []

    for d in days:
        day_df = df[df['date'] == d]
        
        # --- AM SESSION ---
        liq_start = pd.Timestamp(f"{d} 09:30:00").tz_localize('US/Eastern')
        liq_end   = pd.Timestamp(f"{d} 09:59:00").tz_localize('US/Eastern')
        sb_start = pd.Timestamp(f"{d} 10:00:00").tz_localize('US/Eastern')
        sb_end   = pd.Timestamp(f"{d} 11:00:00").tz_localize('US/Eastern')
        
        if liq_end in day_df.index:
            liq_data = day_df.loc[liq_start:liq_end]
            if len(liq_data) > 0:
                liq_high, liq_low = liq_data['high'].max(), liq_data['low'].min()
                sb_window = day_df.loc[sb_start:sb_end]
                
                if len(sb_window) >= 3:
                    state = 'WAITING'; sweep_extreme = 0
                    for ts, row in sb_window.iterrows():
                        h, l, c = row['high'], row['low'], row['close']
                        if state == 'WAITING':
                            if l < liq_low:   state = 'SWEEPING_LOW';  sweep_extreme = l
                            elif h > liq_high: state = 'SWEEPING_HIGH'; sweep_extreme = h
                        elif state == 'SWEEPING_LOW':
                            if l < sweep_extreme: sweep_extreme = l
                            if c > liq_low:
                                results.append({'date': d, 'month': f"{d.year}-{d.month:02d}", 'year': d.year, 'is_long': True, 'entry': c, 'sweep': sweep_extreme, 'ts': ts, 'session': 'AM'})
                                break
                        elif state == 'SWEEPING_HIGH':
                            if h > sweep_extreme: sweep_extreme = h
                            if c < liq_high:
                                results.append({'date': d, 'month': f"{d.year}-{d.month:02d}", 'year': d.year, 'is_long': False, 'entry': c, 'sweep': sweep_extreme, 'ts': ts, 'session': 'AM'})
                                break

        # --- PM SESSION ---
        liq_start = pd.Timestamp(f"{d} 13:30:00").tz_localize('US/Eastern')
        liq_end   = pd.Timestamp(f"{d} 13:59:00").tz_localize('US/Eastern')
        sb_start = pd.Timestamp(f"{d} 14:00:00").tz_localize('US/Eastern')
        sb_end   = pd.Timestamp(f"{d} 15:00:00").tz_localize('US/Eastern')
        
        if liq_end in day_df.index:
            liq_data = day_df.loc[liq_start:liq_end]
            if len(liq_data) > 0:
                liq_high, liq_low = liq_data['high'].max(), liq_data['low'].min()
                sb_window = day_df.loc[sb_start:sb_end]
                
                if len(sb_window) >= 3:
                    state = 'WAITING'; sweep_extreme = 0
                    for ts, row in sb_window.iterrows():
                        h, l, c = row['high'], row['low'], row['close']
                        if state == 'WAITING':
                            if l < liq_low:   state = 'SWEEPING_LOW';  sweep_extreme = l
                            elif h > liq_high: state = 'SWEEPING_HIGH'; sweep_extreme = h
                        elif state == 'SWEEPING_LOW':
                            if l < sweep_extreme: sweep_extreme = l
                            if c > liq_low:
                                results.append({'date': d, 'month': f"{d.year}-{d.month:02d}", 'year': d.year, 'is_long': True, 'entry': c, 'sweep': sweep_extreme, 'ts': ts, 'session': 'PM'})
                                break
                        elif state == 'SWEEPING_HIGH':
                            if h > sweep_extreme: sweep_extreme = h
                            if c < liq_high:
                                results.append({'date': d, 'month': f"{d.year}-{d.month:02d}", 'year': d.year, 'is_long': False, 'entry': c, 'sweep': sweep_extreme, 'ts': ts, 'session': 'PM'})
                                break

    print(f"Extracted {len(results)} trades. Simulating...")
    df_index = df.index.values

    final_results = []
    for t in results:
        entry = t['entry']
        is_long = t['is_long']
        sweep = t['sweep']
        
        if is_long:
            sl = sweep - 1.0
            if sl >= entry: sl = entry - 0.25 # Failsafe
            risk_pts = abs(entry - sl)
            tp = entry + (risk_pts * TARGET_R)
        else:
            sl = sweep + 1.0
            if sl <= entry: sl = entry + 0.25 # Failsafe
            risk_pts = abs(entry - sl)
            tp = entry - (risk_pts * TARGET_R)

        start_ts = t['ts'].to_numpy()
        start_idx = np.searchsorted(df_index, start_ts)
        end_ts = pd.Timestamp(f"{t['date']} 15:59:00").tz_localize('US/Eastern').to_numpy()
        end_idx = np.searchsorted(df_index, end_ts)

        if start_idx >= len(df) or start_idx >= end_idx: continue
        eval_window = df.iloc[start_idx+1:end_idx+1]
        
        res_pts = 0
        filled = False
        
        for idx, row in eval_window.iterrows():
            h, l = row['high'], row['low']
            if not filled:
                if is_long:
                    if l <= entry:
                        filled = True
                        if l <= sl: res_pts = sl - entry; break
                        if h >= tp: res_pts = tp - entry; break
                else:
                    if h >= entry:
                        filled = True
                        if h >= sl: res_pts = entry - sl; break
                        if l <= tp: res_pts = entry - tp; break
            else:
                if is_long:
                    if l <= sl: res_pts = sl - entry; break
                    if h >= tp: res_pts = tp - entry; break
                else:
                    if h >= sl: res_pts = entry - sl; break
                    if l <= tp: res_pts = entry - tp; break

        if not filled: continue
        if res_pts == 0:
            c = eval_window.iloc[-1]['close']
            res_pts = (c - entry) if is_long else (entry - c)
            
        net_pts = res_pts - PENALTY_PTS
        net_r = net_pts / risk_pts
        
        final_results.append({
            'date': t['date'],
            'month': t['month'],
            'year': t['year'],
            'session': t['session'],
            'net_r': net_r,
            'is_win': 1 if net_r > 0 else 0
        })

    return pd.DataFrame(final_results)

def get_nfp_dates(df):
    first_fridays = df.groupby([df.index.year, df.index.month]).apply(
        lambda x: x[x.index.dayofweek == 4].index.min()
    ).dropna()
    return set(first_fridays.dt.date)

def generate_report(res_df, session_name):
    grouped = res_df.groupby(['year', 'month']).agg(
        trades=('net_r', 'count'),
        wins=('is_win', 'sum'),
        total_r=('net_r', 'sum')
    ).reset_index()
    
    grouped['win_rate'] = (grouped['wins'] / grouped['trades'] * 100).round(1)
    # 1R = 0.5% return on $100k account risking $500
    grouped['return_pct'] = (grouped['total_r'] * 0.5).round(2)
    
    report = f"## {session_name} Session Breakdown (No NFP)\n\n"
    report += "| Month | Trades | Win Rate | Total R | Return % |\n"
    report += "|---|---|---|---|---|\n"
    
    for _, row in grouped.iterrows():
        report += f"| {row['month']} | {row['trades']} | {row['win_rate']}% | {row['total_r']:.2f}R | {row['return_pct']}% |\n"
        
    return report

if __name__ == "__main__":
    df = load_data()
    nfp_dates = get_nfp_dates(df)
    
    res_df = extract_and_simulate(df)
    
    # Filter NFP
    res_df = res_df[~res_df['date'].isin(nfp_dates)]
    
    am_res = res_df[res_df['session'] == 'AM']
    pm_res = res_df[res_df['session'] == 'PM']
    
    with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\monthly_breakdown.md", "w") as f:
        f.write("# Silver Bullet Monthly Breakdown (2010-2024)\n")
        f.write("True limit order execution. Assuming $500 risk (0.5%) per trade on a $100k Account.\n\n")
        f.write(generate_report(am_res, "AM"))
        f.write("\n\n")
        f.write(generate_report(pm_res, "PM"))
    
    print("Report generated successfully.")
