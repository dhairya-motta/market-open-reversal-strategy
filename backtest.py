import pandas as pd
import numpy as np
import time

def run_backtest():
    start_time = time.time()
    print("Loading dataset...")
    df = pd.read_csv(r"C:\Users\kingcuber\Desktop\algoRange\Dataset_NQ_1min_2022_2025.csv")
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df.set_index('timestamp ET', inplace=True)
    df.sort_index(inplace=True)
    
    # We will use Vwap_ETH as the continuous VWAP. If it's 0, use Vwap_RTH
    df['VWAP'] = df['Vwap_ETH']
    df.loc[df['VWAP'] == 0, 'VWAP'] = df['Vwap_RTH']
    
    timeframes = ['1min', '5min', '15min', '30min', '1h']
    target_RRs = [2, 3, 4, 5, 7, 10]
    initial_equity = 100000.0
    risk_pct = 0.0025
    
    # Store results
    results = []
    hourly_stats = {tf: {rr: {hr: {'wins': 0, 'losses': 0} for hr in range(24)} for rr in target_RRs} for tf in timeframes}

    for tf in timeframes:
        print(f"Processing Timeframe: {tf}...")
        
        if tf == '1min':
            tf_df = df.copy()
        else:
            tf_df = df.resample(tf).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'VWAP': 'last'
            }).dropna()
            
        tf_df['prev_close'] = tf_df['close'].shift(1)
        tf_df['prev_vwap'] = tf_df['VWAP'].shift(1)
        
        # Long Signal: Open < VWAP and Close > VWAP
        tf_df['long_signal'] = (tf_df['open'] < tf_df['VWAP']) & (tf_df['close'] > tf_df['VWAP'])
        # Short Signal: Open > VWAP and Close < VWAP
        tf_df['short_signal'] = (tf_df['open'] > tf_df['VWAP']) & (tf_df['close'] < tf_df['VWAP'])
        
        signals = tf_df[tf_df['long_signal'] | tf_df['short_signal']].copy()
        
        if len(signals) == 0:
            continue
            
        print(f"Found {len(signals)} signals for {tf}")
        
        # Optimization: convert to numpy arrays for faster iteration
        df_index = df.index.values
        df_highs = df['high'].values
        df_lows = df['low'].values
        
        for rr in target_RRs:
            equity = initial_equity
            
            for entry_time, row in signals.iterrows():
                is_long = row['long_signal']
                entry_price = row['close']
                
                if is_long:
                    sl = row['low']
                else:
                    sl = row['high']
                    
                risk = abs(entry_price - sl)
                if risk <= 0:
                    continue # Invalid candle
                    
                if is_long:
                    tp = entry_price + risk * rr
                else:
                    tp = entry_price - risk * rr
                    
                # Find start index in 1min data (the candle AFTER the signal candle)
                end_time = entry_time + pd.Timedelta(tf)
                start_idx = np.searchsorted(df_index, end_time.to_numpy())
                
                outcome = None
                # Scan next max 1000 candles to find resolution
                max_scan = min(start_idx + 1000, len(df_index))
                
                for i in range(start_idx, max_scan):
                    high = df_highs[i]
                    low = df_lows[i]
                    
                    if is_long:
                        if low <= sl:
                            outcome = 'loss'
                            break
                        if high >= tp:
                            outcome = 'win'
                            break
                    else:
                        if high >= sl:
                            outcome = 'loss'
                            break
                        if low <= tp:
                            outcome = 'win'
                            break
                            
                entry_hour = entry_time.hour
                
                if outcome == 'win':
                    equity *= (1 + risk_pct * rr)
                    hourly_stats[tf][rr][entry_hour]['wins'] += 1
                elif outcome == 'loss':
                    equity *= (1 - risk_pct)
                    hourly_stats[tf][rr][entry_hour]['losses'] += 1
                    
            results.append({
                'Timeframe': tf,
                'RR': rr,
                'Final Equity': equity
            })
            print(f"  RR {rr}: Final Equity = ${equity:.2f}")

    print("Generating report...")
    with open('report.txt', 'w') as f:
        f.write("VWAP Strategy Backtest Results\n")
        f.write("==============================\n\n")
        for res in results:
            tf = res['Timeframe']
            rr = res['RR']
            eq = res['Final Equity']
            total_wins = sum([hourly_stats[tf][rr][hr]['wins'] for hr in range(24)])
            total_losses = sum([hourly_stats[tf][rr][hr]['losses'] for hr in range(24)])
            total_trades = total_wins + total_losses
            wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
            f.write(f"TF: {tf:5s} | RR: {rr:2d} | Trades: {total_trades:4d} | WR: {wr:5.2f}% | Final Equity: ${eq:,.2f}\n")
            
        f.write("\nHourly Performance (Win Rates)\n")
        f.write("==============================\n")
        for tf in timeframes:
            f.write(f"\nTimeframe: {tf}\n")
            for rr in target_RRs:
                f.write(f"  RR {rr}:\n")
                for hr in range(24):
                    w = hourly_stats[tf][rr][hr]['wins']
                    l = hourly_stats[tf][rr][hr]['losses']
                    t = w + l
                    wr = (w / t * 100) if t > 0 else 0
                    if t > 0:
                        f.write(f"    Hour {hr:02d}: {t:3d} trades, WR: {wr:5.2f}%\n")

    print(f"Done in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    run_backtest()
