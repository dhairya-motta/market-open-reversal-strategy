import pandas as pd
import numpy as np
import time
import os
import matplotlib.pyplot as plt

RISK_PER_TRADE = 0.01

def run_personal_capital(data_path, years_to_run, range_start_str, range_end_str, entry_start_str, entry_end_str, session_name):
    print(f"\n=============================================")
    print(f"Loading NQ dataset for {years_to_run}-Year Personal Capital Backtest...")
    print(f"Variant: {session_name} | Flat 50 Points | 1% Risk")
    start_load = time.time()
    
    df = pd.read_csv(data_path)
    df['time ET'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
    df.set_index('time ET', inplace=True)
    df.sort_index(inplace=True)
    
    max_date = df.index.max()
    start_date = max_date - pd.DateOffset(years=years_to_run)
    df = df[df.index >= start_date]

    print(f"Loaded {len(df)} rows in {time.time() - start_load:.2f} seconds.")

    equity = 100000.0
    equity_curve = [equity]
    dates = [df.index.min()]
    trade_outcomes = []
    win_amts = []
    loss_amts = []
    
    current_date = None
    
    r_start = pd.Timestamp(range_start_str).time()
    r_end = pd.Timestamp(range_end_str).time()
    e_start = pd.Timestamp(entry_start_str).time()
    e_end = pd.Timestamp(entry_end_str).time()

    in_trade = False
    trade_entry = 0.0
    trade_sl = 0.0
    trade_tp = 0.0
    bias = None
    extreme_price = None
    fib_0 = None
    fib_1 = None
    limit_order_active = False
    limit_order_price = 0.0
    limit_order_tp = 0.0
    limit_order_sl = 0.0
    range_high = None
    range_low = None
    stop_trading_session = False
    session_sl_count = 0

    sim_start = time.time()

    for row in df.itertuples():
        current_time = row.Index
        time_only = current_time.time()
        day_of_week = current_time.weekday()
        date_only = current_time.date()
        
        if current_date != date_only:
            current_date = date_only
            
            in_trade = False
            bias = None
            range_high = None
            range_low = None
            limit_order_active = False
            stop_trading_session = False
            session_sl_count = 0

        r_high = row.high
        r_low = row.low
        r_close = row.close
        
        if day_of_week == 4 and time_only >= pd.Timestamp('15:50').time() and in_trade:
            r_return = (r_close - trade_entry) / (trade_entry - trade_sl) if bias == 'LONG' else (trade_entry - r_close) / (trade_sl - trade_entry)
            pnl = equity * RISK_PER_TRADE * r_return
            equity += pnl
            equity_curve.append(equity)
            dates.append(current_time)
            trade_outcomes.append(1 if pnl > 0 else -1)
            if pnl > 0: win_amts.append(pnl)
            else: loss_amts.append(abs(pnl))
            in_trade = False
            stop_trading_session = True

        if in_trade:
            if bias == 'LONG':
                if r_low <= trade_sl:
                    session_sl_count += 1
                    loss = equity * RISK_PER_TRADE
                    equity -= loss
                    equity_curve.append(equity)
                    dates.append(current_time)
                    trade_outcomes.append(-1)
                    loss_amts.append(loss)
                    in_trade = False
                    extreme_price = min(extreme_price, r_low)
                    fib_0 = extreme_price
                elif r_high >= trade_tp:
                    actual_rr = (trade_tp - trade_entry) / (trade_entry - trade_sl)
                    profit = equity * RISK_PER_TRADE * actual_rr
                    equity += profit
                    equity_curve.append(equity)
                    dates.append(current_time)
                    trade_outcomes.append(1)
                    win_amts.append(profit)
                    in_trade = False
                    bias = None
                    stop_trading_session = True
            elif bias == 'SHORT':
                if r_high >= trade_sl:
                    session_sl_count += 1
                    loss = equity * RISK_PER_TRADE
                    equity -= loss
                    equity_curve.append(equity)
                    dates.append(current_time)
                    trade_outcomes.append(-1)
                    loss_amts.append(loss)
                    in_trade = False
                    extreme_price = max(extreme_price, r_high)
                    fib_0 = extreme_price
                elif r_low <= trade_tp:
                    actual_rr = (trade_entry - trade_tp) / (trade_sl - trade_entry)
                    profit = equity * RISK_PER_TRADE * actual_rr
                    equity += profit
                    equity_curve.append(equity)
                    dates.append(current_time)
                    trade_outcomes.append(1)
                    win_amts.append(profit)
                    in_trade = False
                    bias = None
                    stop_trading_session = True
            if in_trade:
                continue

        if stop_trading_session or session_sl_count >= 2:
            continue
            
        if time_only >= r_start and time_only <= r_end:
            if range_high is None:
                range_high, range_low = r_high, r_low
            else:
                range_high = max(range_high, r_high)
                range_low = min(range_low, r_low)
            continue

        if range_high is None or range_low is None:
            continue

        if bias is None:
            if r_low < range_low:
                bias = 'LONG'
                extreme_price = r_low
                fib_1 = range_high
                fib_0 = extreme_price
            elif r_high > range_high:
                bias = 'SHORT'
                extreme_price = r_high
                fib_1 = range_low
                fib_0 = extreme_price
            if bias is None:
                continue

        if bias == 'LONG' and r_high >= fib_1:
            stop_trading_session = True
            limit_order_active = False
            continue
        elif bias == 'SHORT' and r_low <= fib_1:
            stop_trading_session = True
            limit_order_active = False
            continue

        if bias == 'LONG':
            extreme_price = min(extreme_price, r_low)
            fib_0 = extreme_price
        elif bias == 'SHORT':
            extreme_price = max(extreme_price, r_high)
            fib_0 = extreme_price

        if limit_order_active:
            if bias == 'LONG':
                if r_high >= limit_order_tp:
                    limit_order_active = False
                    continue
                if r_low <= limit_order_price:
                    trade_entry, trade_sl, trade_tp = limit_order_price, limit_order_sl, limit_order_tp
                    if r_low <= trade_sl:
                        session_sl_count += 1
                        loss = equity * RISK_PER_TRADE
                        equity -= loss
                        equity_curve.append(equity)
                        dates.append(current_time)
                        trade_outcomes.append(-1)
                        loss_amts.append(loss)
                        limit_order_active = False
                        extreme_price = min(extreme_price, r_low)
                        fib_0 = extreme_price
                    else:
                        in_trade = True
                        limit_order_active = False
            elif bias == 'SHORT':
                if r_low <= limit_order_tp:
                    limit_order_active = False
                    continue
                if r_high >= limit_order_price:
                    trade_entry, trade_sl, trade_tp = limit_order_price, limit_order_sl, limit_order_tp
                    if r_high >= trade_sl:
                        session_sl_count += 1
                        loss = equity * RISK_PER_TRADE
                        equity -= loss
                        equity_curve.append(equity)
                        dates.append(current_time)
                        trade_outcomes.append(-1)
                        loss_amts.append(loss)
                        limit_order_active = False
                        extreme_price = max(extreme_price, r_high)
                        fib_0 = extreme_price
                    else:
                        in_trade = True
                        limit_order_active = False
            continue

        if time_only >= e_start and time_only <= e_end:
            fib_range = fib_1 - fib_0
            c = r_close
            
            f236 = fib_0 + fib_range * 0.236
            f400 = fib_0 + fib_range * 0.400
            f330 = fib_0 + fib_range * 0.330
            
            if bias == 'LONG':
                if c > f236:
                    trade_sl = fib_0
                    if c <= f400:
                        in_trade = True
                        trade_entry = c
                        if trade_entry == trade_sl: trade_sl -= 1
                        trade_tp = trade_entry + 50
                    else:
                        limit_order_active = True
                        limit_order_price = f330
                        limit_order_sl = trade_sl
                        if limit_order_price == limit_order_sl: limit_order_sl -= 1
                        limit_order_tp = limit_order_price + 50
                        
            elif bias == 'SHORT':
                if c < f236:
                    trade_sl = fib_0
                    if c >= f400:
                        in_trade = True
                        trade_entry = c
                        if trade_entry == trade_sl: trade_sl += 1
                        trade_tp = trade_entry - 50
                    else:
                        limit_order_active = True
                        limit_order_price = f330
                        limit_order_sl = trade_sl
                        if limit_order_price == limit_order_sl: limit_order_sl += 1
                        limit_order_tp = limit_order_price - 50

    # Calculate metrics
    wins = sum(1 for o in trade_outcomes if o > 0)
    losses = sum(1 for o in trade_outcomes if o < 0)
    win_rate = wins / len(trade_outcomes) if trade_outcomes else 0
    profit_factor = sum(win_amts) / sum(loss_amts) if sum(loss_amts) > 0 else 0
    
    # Max Drawdown calculation
    eq_series = pd.Series(equity_curve)
    rolling_max = eq_series.cummax()
    drawdowns = (eq_series - rolling_max) / rolling_max
    max_dd = drawdowns.min() * 100

    print(f"Simulation completed in {time.time() - sim_start:.2f} seconds.")
    print("--- Detailed Summary ---")
    print(f"Total Trades Taken: {len(trade_outcomes)}")
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Final Balance: ${equity:,.2f}")
    print(f"Net Profit: ${equity - 100000.0:,.2f}")
    print(f"Total Return: {((equity - 100000.0)/100000.0)*100:.1f}%")
    print("=============================================\n")
    
    # Save equity curve plot
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10,5))
    plt.plot(dates, equity_curve, color='blue', linewidth=1)
    plt.title(f"Personal Capital Equity Curve: {session_name} ({years_to_run} Years)")
    plt.ylabel("Account Balance ($)")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_name = f"personal_capital_{session_name.replace(' ', '_').lower()}.png"
    plt.savefig(plot_name)
    print(f"Saved plot to {plot_name}")


if __name__ == "__main__":
    nq_data = r'C:\Users\kingcuber\.gemini\antigravity-ide\scratch\nsx_cleaned_2010_2024.csv'
    
    # 5-Year
    run_personal_capital(nq_data, 5, '08:12', '09:22', '09:30', '11:00', "NY Session")
    run_personal_capital(nq_data, 5, '01:10', '02:22', '02:30', '05:00', "London Variant B")
    
    # 10-Year
    run_personal_capital(nq_data, 10, '08:12', '09:22', '09:30', '11:00', "NY Session")
    run_personal_capital(nq_data, 10, '01:10', '02:22', '02:30', '05:00', "London Variant B")
