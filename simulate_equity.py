import pandas as pd
import numpy as np

def run_simulation():
    print("Loading dataset...")
    df = pd.read_csv(r"C:\Users\kingcuber\Desktop\algoRange\Dataset_NQ_1min_2022_2025.csv")
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df.set_index('timestamp ET', inplace=True)
    df.sort_index(inplace=True)
    
    df['VWAP'] = df['Vwap_ETH']
    df.loc[df['VWAP'] == 0, 'VWAP'] = df['Vwap_RTH']
    
    timeframes = ['1min', '5min']
    target_RRs = [2, 5, 10]
    best_hours = [18, 19, 20]
    risk_levels = [0.001, 0.0025, 0.005, 0.01]
    
    df_index = df.index.values
    df_highs = df['high'].values
    df_lows = df['low'].values

    md_content = "# Drawdown and Compounding Stats\n\n"
    md_content += f"Trading ONLY during the best hours: **{best_hours} ET**.\n\n"

    for tf in timeframes:
        md_content += f"## Timeframe: {tf}\n"
        print(f"Processing {tf}...")
        
        if tf == '1min':
            tf_df = df.copy()
        else:
            tf_df = df.resample(tf).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'VWAP': 'last'
            }).dropna()
            
        tf_df['long_signal'] = (tf_df['open'] < tf_df['VWAP']) & (tf_df['close'] > tf_df['VWAP'])
        tf_df['short_signal'] = (tf_df['open'] > tf_df['VWAP']) & (tf_df['close'] < tf_df['VWAP'])
        signals = tf_df[tf_df['long_signal'] | tf_df['short_signal']].copy()
        
        # Filter for best hours
        signals = signals[signals.index.hour.isin(best_hours)]
        
        if len(signals) == 0: continue
        
        for rr in target_RRs:
            # We will collect the sequence of outcomes
            c1_outcomes = []
            c2_outcomes = []
            
            for entry_time, row in signals.iterrows():
                is_long = row['long_signal']
                entry_price = row['close']
                sl = row['low'] if is_long else row['high']
                risk = abs(entry_price - sl)
                if risk <= 0: continue
                
                tp = entry_price + risk * rr if is_long else entry_price - risk * rr
                one_r = entry_price + risk if is_long else entry_price - risk
                two_r = entry_price + risk * 2 if is_long else entry_price - risk * 2
                
                end_time = entry_time + pd.Timedelta(tf)
                start_idx = np.searchsorted(df_index, end_time.to_numpy())
                max_scan = min(start_idx + 1500, len(df_index))
                
                future_highs = df_highs[start_idx:max_scan]
                future_lows = df_lows[start_idx:max_scan]
                
                c1_sl, c2_sl = sl, sl
                c1_res, c2_res = -1, -1
                
                for h, l in zip(future_highs, future_lows):
                    if is_long:
                        if l <= c1_sl and c1_res == -1: c1_res = (c1_sl - entry_price) / risk
                        if l <= c2_sl and c2_res == -1: c2_res = (c2_sl - entry_price) / risk
                        if h >= tp:
                            if c1_res == -1: c1_res = rr
                            if c2_res == -1: c2_res = rr
                        if h >= one_r:
                            if c1_sl < entry_price: c1_sl = entry_price
                            if c2_sl < entry_price: c2_sl = entry_price
                        if h >= two_r:
                            if c2_sl < one_r: c2_sl = one_r
                    else:
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
                    if c1_res != -1 and c2_res != -1: break
                        
                if c1_res == -1: c1_res = (c1_sl - entry_price)/risk if is_long else (entry_price - c1_sl)/risk
                if c2_res == -1: c2_res = (c2_sl - entry_price)/risk if is_long else (entry_price - c2_sl)/risk
                
                c1_outcomes.append(round(c1_res))
                c2_outcomes.append(round(c2_res))

            # Helper to process outcomes
            def process_equity(outcomes, case_name):
                net_r = sum(outcomes)
                cum_r = 0
                max_dd_r = 0
                peak_r = 0
                for r in outcomes:
                    cum_r += r
                    if cum_r > peak_r: peak_r = cum_r
                    dd = peak_r - cum_r
                    if dd > max_dd_r: max_dd_r = dd
                
                res_str = f"### {case_name} | Target: {rr}R\n"
                res_str += f"- **Total Trades:** {len(outcomes):,}\n"
                res_str += f"- **Net R:** +{net_r} R\n"
                res_str += f"- **Max DD (in R):** -{max_dd_r} R\n\n"
                
                res_str += "| Risk % | Final Equity ($100k Start) | Max Portfolio DD % |\n"
                res_str += "|---|---|---|\n"
                
                for risk in risk_levels:
                    equity = 100000.0
                    peak_eq = 100000.0
                    max_eq_dd = 0.0
                    
                    for r in outcomes:
                        # PnL = equity * risk * r
                        equity *= (1 + (risk * r))
                        if equity > peak_eq: peak_eq = equity
                        dd_pct = (peak_eq - equity) / peak_eq * 100
                        if dd_pct > max_eq_dd: max_eq_dd = dd_pct
                        
                    # Format equity to avoid massive scientific notation, cap at 999 Trillion
                    if equity > 999_000_000_000:
                        eq_str = f"${equity/1_000_000_000_000:.2f} Trillion+"
                    elif equity > 999_000_000:
                        eq_str = f"${equity/1_000_000_000:.2f} Billion"
                    elif equity > 999_000:
                        eq_str = f"${equity/1_000_000:.2f} Million"
                    else:
                        eq_str = f"${equity:,.2f}"
                        
                    res_str += f"| {risk*100}% | {eq_str} | {max_eq_dd:.1f}% |\n"
                res_str += "\n"
                return res_str
                
            md_content += process_equity(c1_outcomes, "Case 1 (BE at 1R)")
            md_content += process_equity(c2_outcomes, "Case 2 (BE at 1R, Lock +1R at 2R)")

    with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\scratch\equity_simulation.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    print("Done")

if __name__ == "__main__":
    run_simulation()
