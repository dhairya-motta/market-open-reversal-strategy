import pandas as pd
import numpy as np

def run_prop_firm_backtest():
    print("Loading dataset...")
    df = pd.read_csv(r"C:\Users\kingcuber\Desktop\algoRange\Dataset_NQ_1min_2022_2025.csv")
    df['timestamp ET'] = pd.to_datetime(df['timestamp ET'])
    df.set_index('timestamp ET', inplace=True)
    df.sort_index(inplace=True)
    
    df['VWAP'] = df['Vwap_ETH']
    df.loc[df['VWAP'] == 0, 'VWAP'] = df['Vwap_RTH']
    
    print("Resampling to 15min...")
    tf = '15min'
    tf_df = df.resample(tf).agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'VWAP': 'last'
    }).dropna()
    
    # Calculate 200 EMA
    tf_df['EMA_200'] = tf_df['close'].ewm(span=200, adjust=False).mean()
    
    # Generate Signals
    # Long: Open < VWAP, Close > VWAP, Close > 200 EMA
    tf_df['long_signal'] = (tf_df['open'] < tf_df['VWAP']) & (tf_df['close'] > tf_df['VWAP']) & (tf_df['close'] > tf_df['EMA_200'])
    # Short: Open > VWAP, Close < VWAP, Close < 200 EMA
    tf_df['short_signal'] = (tf_df['open'] > tf_df['VWAP']) & (tf_df['close'] < tf_df['VWAP']) & (tf_df['close'] < tf_df['EMA_200'])
    
    signals = tf_df[tf_df['long_signal'] | tf_df['short_signal']].copy()
    print(f"Found {len(signals)} signals.")
    
    target_RRs = [2, 3]
    penalty_points = 0.75 # 3 ticks total for slippage & commission
    
    df_index = df.index.values
    df_highs = df['high'].values
    df_lows = df['low'].values
    
    # Prop Firm Rules
    START_EQUITY = 50000.0
    RISK_AMT = 250.0 # 0.5% of 50k
    MAX_DD_LIMIT = 2500.0
    PROFIT_TARGET = 3000.0
    
    results_md = "# Prop Firm Evaluation Backtest Results\n\n"
    results_md += "**Strategy:** 15m VWAP Cross + 200 EMA Trend Filter\n"
    results_md += f"**Prop Firm Rules:** $50k Account, ${PROFIT_TARGET} Target, ${MAX_DD_LIMIT} Trailing DD\n"
    results_md += f"**Risk Per Trade:** ${RISK_AMT}\n\n"

    for rr in target_RRs:
        print(f"Simulating RR {rr}...")
        
        # We will split into "Evaluations" - whenever an account passes or fails, we start a new one to see the success rate.
        evals_taken = 0
        evals_passed = 0
        evals_failed = 0
        
        current_equity = START_EQUITY
        current_peak = START_EQUITY
        
        # PnL tracking for overall stats
        total_trades = 0
        total_wins = 0
        total_losses = 0
        total_net_profit = 0
        
        for entry_time, row in signals.iterrows():
            is_long = row['long_signal']
            entry_price = row['close']
            sl = row['low'] if is_long else row['high']
            risk_pts = abs(entry_price - sl)
            
            if risk_pts < 0.25: continue
            
            # Position sizing
            pt_value = 20.0
            # How many contracts to risk $250?
            contracts = RISK_AMT / (risk_pts * pt_value)
            
            tp = entry_price + risk_pts * rr if is_long else entry_price - risk_pts * rr
            
            end_time = entry_time + pd.Timedelta(tf)
            start_idx = np.searchsorted(df_index, end_time.to_numpy())
            max_scan = min(start_idx + 1500, len(df_index)) # roughly 24 hours max holding
            
            future_highs = df_highs[start_idx:max_scan]
            future_lows = df_lows[start_idx:max_scan]
            
            res_pts = 0
            for h, l in zip(future_highs, future_lows):
                if is_long:
                    if l <= sl: res_pts = sl - entry_price; break
                    if h >= tp: res_pts = tp - entry_price; break
                else:
                    if h >= sl: res_pts = entry_price - sl; break
                    if l <= tp: res_pts = entry_price - tp; break
            
            if res_pts == 0:
                res_pts = (sl - entry_price) if is_long else (entry_price - sl)
                
            # Deduct fees
            net_pts = res_pts - penalty_points
            trade_pnl = net_pts * pt_value * contracts
            
            # Update Eval Account
            if current_equity == START_EQUITY:
                evals_taken += 1
                
            current_equity += trade_pnl
            
            # Trailing Drawdown calculation (high watermark)
            if current_equity > current_peak:
                current_peak = current_equity
            
            trailing_dd_threshold = current_peak - MAX_DD_LIMIT
            # Some prop firms trail from high watermark but lock it at starting balance. Let's assume standard trailing.
            # If trailing threshold reaches START_EQUITY, it stops trailing.
            if trailing_dd_threshold > START_EQUITY:
                trailing_dd_threshold = START_EQUITY
                
            is_blown = current_equity <= trailing_dd_threshold
            is_passed = current_equity >= (START_EQUITY + PROFIT_TARGET)
            
            if is_blown:
                evals_failed += 1
                # Reset for next eval
                current_equity = START_EQUITY
                current_peak = START_EQUITY
            elif is_passed:
                evals_passed += 1
                # Reset for next eval
                current_equity = START_EQUITY
                current_peak = START_EQUITY
                
            # Overall Stats
            total_trades += 1
            total_net_profit += trade_pnl
            if trade_pnl > 0:
                total_wins += 1
            else:
                total_losses += 1
                
        win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        pass_rate = (evals_passed / evals_taken) * 100 if evals_taken > 0 else 0
        
        results_md += f"### Target: {rr}R (Fixed, No Trailing Stop)\n"
        results_md += f"- **Total Trades (3 Years):** {total_trades:,}\n"
        results_md += f"- **Win Rate:** {win_rate:.2f}%\n"
        results_md += f"- **Total Gross PnL:** ${total_net_profit:,.2f}\n"
        results_md += f"- **Evaluations Taken:** {evals_taken}\n"
        results_md += f"- **Evaluations Passed:** {evals_passed}\n"
        results_md += f"- **Evaluations Failed:** {evals_failed}\n"
        results_md += f"- **Prop Firm Pass Rate:** {pass_rate:.2f}%\n\n"

    with open(r"C:\Users\kingcuber\.gemini\antigravity-ide\brain\8370803b-9474-4100-8b6b-158135823a70\scratch\prop_firm_results.md", 'w', encoding='utf-8') as f:
        f.write(results_md)
        
    print("Done")

if __name__ == "__main__":
    run_prop_firm_backtest()
