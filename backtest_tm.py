import pandas as pd
import numpy as np
import time

def run_scenarios():
    print("Loading dataset...")
    df = pd.read_csv(r"C:\Users\kingcuber\Desktop\algoRange\Dataset_NQ_1min_2022_2025.csv")
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df.set_index('timestamp ET', inplace=True)
    df.sort_index(inplace=True)
    
    df['VWAP'] = df['Vwap_ETH']
    df.loc[df['VWAP'] == 0, 'VWAP'] = df['Vwap_RTH']
    
    timeframes = ['1min', '5min', '15min', '30min', '1h']
    target_RRs = [2, 3, 4, 5, 7, 10]
    
    # Store results
    # results[scenario][tf][rr][hr] = {'trades':0, 'net_r': 0, 'wins':0, 'be':0, 'loss':0}
    scenarios = ['Case 1 (BE at 1R)', 'Case 2 (BE at 1R, Lock 1R at 2R)']
    results = {sc: {tf: {rr: {hr: {'trades':0, 'net_r':0, 'wins':0, 'be':0, 'lock1':0, 'loss':0} for hr in range(24)} for rr in target_RRs} for tf in timeframes} for sc in scenarios}

    df_index = df.index.values
    df_highs = df['high'].values
    df_lows = df['low'].values
    
    start_time = time.time()

    for tf in timeframes:
        print(f"Processing TF {tf}...")
        if tf == '1min':
            tf_df = df.copy()
        else:
            tf_df = df.resample(tf).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'VWAP': 'last'
            }).dropna()
            
        tf_df['long_signal'] = (tf_df['open'] < tf_df['VWAP']) & (tf_df['close'] > tf_df['VWAP'])
        tf_df['short_signal'] = (tf_df['open'] > tf_df['VWAP']) & (tf_df['close'] < tf_df['VWAP'])
        
        signals = tf_df[tf_df['long_signal'] | tf_df['short_signal']].copy()
        if len(signals) == 0: continue
        
        for entry_time, row in signals.iterrows():
            hr = entry_time.hour
            is_long = row['long_signal']
            entry_price = row['close']
            sl = row['low'] if is_long else row['high']
            risk = abs(entry_price - sl)
            if risk <= 0: continue
            
            end_time = entry_time + pd.Timedelta(tf)
            start_idx = np.searchsorted(df_index, end_time.to_numpy())
            max_scan = min(start_idx + 1500, len(df_index))
            
            future_highs = df_highs[start_idx:max_scan]
            future_lows = df_lows[start_idx:max_scan]
            
            for rr in target_RRs:
                tp = entry_price + risk * rr if is_long else entry_price - risk * rr
                one_r = entry_price + risk if is_long else entry_price - risk
                two_r = entry_price + risk * 2 if is_long else entry_price - risk * 2
                
                # State tracking
                c1_sl = sl
                c2_sl = sl
                
                c1_res = -1
                c2_res = -1
                
                for h, l in zip(future_highs, future_lows):
                    if is_long:
                        # Check stop outs first (conservative)
                        if l <= c1_sl and c1_res == -1: c1_res = (c1_sl - entry_price) / risk
                        if l <= c2_sl and c2_res == -1: c2_res = (c2_sl - entry_price) / risk
                        
                        # Check TP
                        if h >= tp:
                            if c1_res == -1: c1_res = rr
                            if c2_res == -1: c2_res = rr
                        
                        # Update trailing stops for future candles
                        if h >= one_r:
                            if c1_sl < entry_price: c1_sl = entry_price
                            if c2_sl < entry_price: c2_sl = entry_price
                        if h >= two_r:
                            if c2_sl < one_r: c2_sl = one_r
                            
                    else: # short
                        if h >= c1_sl and c1_res == -1: c1_res = (entry_price - c1_sl) / risk
                        if h >= c2_sl and c2_res == -1: c2_res = (entry_price - c2_sl) / risk
                        
                        if l <= tp:
                            if c1_res == -1: c1_res = rr
                            if c2_res == -1: c2_res = rr
                            
                        if l <= one_r:
                            if c1_sl > entry_price: c1_sl = entry_price
                            if c2_sl > entry_price: c2_sl = entry_price
                        if l <= two_r:
                            if c2_sl > one_r: c2_sl = one_r

                    if c1_res != -1 and c2_res != -1:
                        break
                        
                # Default to whatever SL was if neither hit (ran out of data)
                if c1_res == -1: c1_res = (c1_sl - entry_price)/risk if is_long else (entry_price - c1_sl)/risk
                if c2_res == -1: c2_res = (c2_sl - entry_price)/risk if is_long else (entry_price - c2_sl)/risk
                
                # Record Case 1
                c1_res = round(c1_res)
                results['Case 1 (BE at 1R)'][tf][rr][hr]['trades'] += 1
                results['Case 1 (BE at 1R)'][tf][rr][hr]['net_r'] += c1_res
                if c1_res == rr: results['Case 1 (BE at 1R)'][tf][rr][hr]['wins'] += 1
                elif c1_res == 0: results['Case 1 (BE at 1R)'][tf][rr][hr]['be'] += 1
                else: results['Case 1 (BE at 1R)'][tf][rr][hr]['loss'] += 1
                
                # Record Case 2
                c2_res = round(c2_res)
                results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['trades'] += 1
                results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['net_r'] += c2_res
                if c2_res == rr: results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['wins'] += 1
                elif c2_res == 1: results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['lock1'] += 1
                elif c2_res == 0: results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['be'] += 1
                else: results['Case 2 (BE at 1R, Lock 1R at 2R)'][tf][rr][hr]['loss'] += 1

    print(f"Simulation done in {time.time() - start_time:.2f}s. Generating report...")
    
    with open('trade_management_report.md', 'w', encoding='utf-8') as f:
        f.write("# Trade Management Scenarios Results\n\n")
        
        for sc in scenarios:
            f.write(f"## {sc}\n\n")
            
            # Overall Net R by Timeframe and RR
            f.write("### Net R Overview\n")
            f.write("| Timeframe | 2R | 3R | 4R | 5R | 7R | 10R |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            
            for tf in timeframes:
                row_str = f"| **{tf}** |"
                for rr in target_RRs:
                    net = sum(results[sc][tf][rr][hr]['net_r'] for hr in range(24))
                    row_str += f" {net:+.1f} R |"
                f.write(row_str + "\n")
            f.write("\n")
            
            # Top 3 Hours per RR (Aggregated across TFs)
            f.write("### Top 3 Hours by RR (Aggregated TFs)\n")
            for rr in target_RRs:
                hr_agg = []
                for hr in range(24):
                    net = sum(results[sc][tf][rr][hr]['net_r'] for tf in timeframes)
                    tr = sum(results[sc][tf][rr][hr]['trades'] for tf in timeframes)
                    if tr > 50:
                        hr_agg.append((hr, net, tr))
                hr_agg.sort(key=lambda x: x[1], reverse=True)
                
                f.write(f"#### Target: {rr}R\n")
                f.write("| Rank | Hour (ET) | Net R | Total Trades |\n")
                f.write("|:---:|:---:|:---:|:---:|\n")
                medals = ["🥇", "🥈", "🥉"]
                for i, (hr, net, tr) in enumerate(hr_agg[:3]):
                    f.write(f"| {medals[i]} | {hr:02d}:00 | {net:+.1f} R | {tr:,} |\n")
                f.write("\n")

if __name__ == "__main__":
    run_scenarios()
