import pandas as pd
import numpy as np
import time
import os

RISK_PER_TRADE = 0.01
EVAL_COST = 499.0

# Prop Firm Constants ($100k Account)
START_BAL = 100000.0
STATIC_MAX_LOSS = 88000.0
DAILY_DRAWDOWN_PCT = 0.04
PAYOUT_TARGET_PCT = 0.05
PHASE_1_TARGET = 110000.0
PHASE_2_TARGET = 106000.0

class PropAccount:
    def __init__(self):
        self.evals_blown = 0
        self.evals_passed = 0
        self.payouts_count = 0
        self.total_payouts_usd = 0.0
        self.total_fees = 0.0
        self.has_taken_1r_payout = False
        self.reset_account()
        
    def reset_account(self):
        self.phase = 1
        self.equity = START_BAL
        self.start_of_day_equity = START_BAL
        self.daily_loss_limit = START_BAL * DAILY_DRAWDOWN_PCT
        self.daily_loss = 0.0
        self.total_fees += EVAL_COST
        self.has_taken_1r_payout = False
        
    def next_day(self):
        self.start_of_day_equity = self.equity
        self.daily_loss_limit = self.start_of_day_equity * DAILY_DRAWDOWN_PCT
        self.daily_loss = 0.0

    def process_pnl(self, pnl, current_date):
        self.equity += pnl
        if pnl < 0:
            self.daily_loss += abs(pnl)
            
        if self.equity <= STATIC_MAX_LOSS or self.daily_loss >= self.daily_loss_limit:
            self.evals_blown += 1
            self.reset_account()
            return 'blown'
            
        if self.phase == 1 and self.equity >= PHASE_1_TARGET:
            self.phase = 2
            self.equity = START_BAL
            self.start_of_day_equity = START_BAL
            self.daily_loss = 0.0
            return 'passed_phase1'
            
        elif self.phase == 2 and self.equity >= PHASE_2_TARGET:
            self.phase = 'FUNDED'
            self.equity = START_BAL
            self.start_of_day_equity = START_BAL
            self.daily_loss = 0.0
            self.evals_passed += 1
            return 'passed_phase2'
            
        elif self.phase == 'FUNDED':
            if not self.has_taken_1r_payout and self.equity >= START_BAL + 1000.0:
                payout_amt = 1000.0
                self.payouts_count += 1
                self.total_payouts_usd += payout_amt
                self.equity -= payout_amt
                self.start_of_day_equity -= payout_amt
                self.has_taken_1r_payout = True
                return 'payout_1r'
                
            elif self.equity >= START_BAL * (1 + PAYOUT_TARGET_PCT):
                payout_amt = self.equity - START_BAL
                self.payouts_count += 1
                self.total_payouts_usd += payout_amt
                self.equity = START_BAL
                self.start_of_day_equity = START_BAL
                self.daily_loss = 0.0
                return 'payout'
                
        return 'active'

def run_simulation(data_path, stop_after_3_losses):
    print(f"\n=============================================")
    variant_name = f"Combined London 2.0R & NY 50pt | Stop after 3 losses: {stop_after_3_losses}"
    print(variant_name)
    start_load = time.time()
    
    df = pd.read_csv(data_path)
    df['time ET'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
    df.set_index('time ET', inplace=True)
    df.sort_index(inplace=True)
    
    max_date = df.index.max()
    start_date = max_date - pd.DateOffset(years=5)
    df = df[df.index >= start_date]

    print(f"Loaded {len(df)} rows in {time.time() - start_load:.2f} seconds.")

    account = PropAccount()
    events = []
    current_date = None

    # Daily variables
    daily_sl_count = 0

    # Session variables
    in_trade = False
    trade_entry = 0.0
    trade_sl = 0.0
    trade_tp = 0.0
    bias = None
    extreme_price = None
    fib_0 = None
    fib_1 = None
    session_sl_count = 0
    limit_order_active = False
    limit_order_price = 0.0
    limit_order_tp = 0.0
    limit_order_sl = 0.0
    range_high = None
    range_low = None
    stop_trading_session = False
    
    # Session Timings
    r_lon_start = pd.Timestamp('01:10').time()
    r_lon_end = pd.Timestamp('02:22').time()
    e_lon_start = pd.Timestamp('02:30').time()
    e_lon_end = pd.Timestamp('05:00').time()

    r_ny_start = pd.Timestamp('08:12').time()
    r_ny_end = pd.Timestamp('09:22').time()
    e_ny_start = pd.Timestamp('09:30').time()
    e_ny_end = pd.Timestamp('11:00').time()
    
    current_session = None

    sim_start = time.time()

    for row in df.itertuples():
        current_time = row.Index
        time_only = current_time.time()
        day_of_week = current_time.weekday()
        date_only = current_time.date()
        
        if current_date != date_only:
            current_date = date_only
            account.next_day()
            daily_sl_count = 0
            
            in_trade = False
            bias = None
            range_high = None
            range_low = None
            limit_order_active = False
            stop_trading_session = False
            current_session = None
            session_sl_count = 0

        r_high = row.high
        r_low = row.low
        r_close = row.close
        
        if day_of_week == 4 and time_only >= pd.Timestamp('15:50').time() and in_trade:
            r_return = (r_close - trade_entry) / (trade_entry - trade_sl) if bias == 'LONG' else (trade_entry - r_close) / (trade_sl - trade_entry)
            pnl = START_BAL * RISK_PER_TRADE * r_return
            res = account.process_pnl(pnl, current_date)
            events.append({'date': date_only, 'type': 'FRIDAY_EXIT', 'pnl': pnl})
            in_trade = False
            stop_trading_session = True

        if in_trade:
            if bias == 'LONG':
                if r_low <= trade_sl:
                    session_sl_count += 1
                    daily_sl_count += 1
                    loss = START_BAL * RISK_PER_TRADE
                    res = account.process_pnl(-loss, current_date)
                    events.append({'date': date_only, 'type': 'LONG_SL', 'pnl': -loss})
                    in_trade = False
                    extreme_price = min(extreme_price, r_low)
                    fib_0 = extreme_price
                elif r_high >= trade_tp:
                    actual_rr = (trade_tp - trade_entry) / (trade_entry - trade_sl)
                    profit = START_BAL * RISK_PER_TRADE * actual_rr
                    res = account.process_pnl(profit, current_date)
                    events.append({'date': date_only, 'type': 'LONG_TP', 'pnl': profit})
                    in_trade = False
                    bias = None
                    stop_trading_session = True
            elif bias == 'SHORT':
                if r_high >= trade_sl:
                    session_sl_count += 1
                    daily_sl_count += 1
                    loss = START_BAL * RISK_PER_TRADE
                    res = account.process_pnl(-loss, current_date)
                    events.append({'date': date_only, 'type': 'SHORT_SL', 'pnl': -loss})
                    in_trade = False
                    extreme_price = max(extreme_price, r_high)
                    fib_0 = extreme_price
                elif r_low <= trade_tp:
                    actual_rr = (trade_entry - trade_tp) / (trade_sl - trade_entry)
                    profit = START_BAL * RISK_PER_TRADE * actual_rr
                    res = account.process_pnl(profit, current_date)
                    events.append({'date': date_only, 'type': 'SHORT_TP', 'pnl': profit})
                    in_trade = False
                    bias = None
                    stop_trading_session = True
            if in_trade:
                continue

        if time_only == r_lon_start and not in_trade:
            current_session = 'LONDON'
            session_sl_count = 0
            bias = None
            range_high = None
            range_low = None
            limit_order_active = False
            stop_trading_session = False
            
        elif time_only == r_ny_start and not in_trade:
            current_session = 'NY'
            session_sl_count = 0
            bias = None
            range_high = None
            range_low = None
            limit_order_active = False
            stop_trading_session = False

        if stop_trading_session or in_trade or current_session is None:
            continue

        if session_sl_count >= 2:
            continue
            
        if stop_after_3_losses and daily_sl_count >= 3:
            continue

        if current_session == 'LONDON':
            r_start, r_end, e_start, e_end = r_lon_start, r_lon_end, e_lon_start, e_lon_end
        else:
            r_start, r_end, e_start, e_end = r_ny_start, r_ny_end, e_ny_start, e_ny_end

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
                        daily_sl_count += 1
                        loss = START_BAL * RISK_PER_TRADE
                        res = account.process_pnl(-loss, current_date)
                        events.append({'date': date_only, 'type': 'LONG_SL', 'pnl': -loss})
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
                        daily_sl_count += 1
                        loss = START_BAL * RISK_PER_TRADE
                        res = account.process_pnl(-loss, current_date)
                        events.append({'date': date_only, 'type': 'SHORT_SL', 'pnl': -loss})
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
                        risk = abs(trade_entry - trade_sl)
                        trade_tp = trade_entry + (risk * 2.0) if current_session == 'LONDON' else trade_entry + 50
                    else:
                        limit_order_active = True
                        limit_order_price = f330
                        limit_order_sl = trade_sl
                        if limit_order_price == limit_order_sl: limit_order_sl -= 1
                        risk = abs(limit_order_price - limit_order_sl)
                        limit_order_tp = limit_order_price + (risk * 2.0) if current_session == 'LONDON' else limit_order_price + 50
                        
            elif bias == 'SHORT':
                if c < f236:
                    trade_sl = fib_0
                    if c >= f400:
                        in_trade = True
                        trade_entry = c
                        if trade_entry == trade_sl: trade_sl += 1
                        risk = abs(trade_entry - trade_sl)
                        trade_tp = trade_entry - (risk * 2.0) if current_session == 'LONDON' else trade_entry - 50
                    else:
                        limit_order_active = True
                        limit_order_price = f330
                        limit_order_sl = trade_sl
                        if limit_order_price == limit_order_sl: limit_order_sl += 1
                        risk = abs(limit_order_price - limit_order_sl)
                        limit_order_tp = limit_order_price - (risk * 2.0) if current_session == 'LONDON' else limit_order_price - 50

    print(f"Simulation completed in {time.time() - sim_start:.2f} seconds.")
    print("--- Summary ---")

    df_events = pd.DataFrame(events)
    if not df_events.empty:
        print(f"Total Trades Taken: {len(df_events)}")
        print(f"Evaluations Blown: {account.evals_blown}")
        print(f"Evaluations Passed (Fully Funded): {account.evals_passed}")
        print(f"Total Evaluation Fees Paid: ${account.total_fees:,.2f}")
        print(f"Total Payouts Received: {account.payouts_count} (${account.total_payouts_usd:,.2f})")
        print(f"Net Profit: ${account.total_payouts_usd - account.total_fees:,.2f}")
    else:
        print("No trades taken.")
    print("=============================================\n")

if __name__ == "__main__":
    nq_data = r'C:\Users\kingcuber\.gemini\antigravity-ide\scratch\nsx_cleaned_2010_2024.csv'
    run_simulation(nq_data, stop_after_3_losses=True)
    run_simulation(nq_data, stop_after_3_losses=False)
