# Market Open Reversal Strategy

This repository contains the simulation engine, logic, and comprehensive multi-year backtest data for a **Market Open Reversal Strategy** (formerly referred to as the "Fibo 50-pt Strategy") optimized for NQ (Nasdaq 100) futures.

## The Strategy

The strategy targets the immediate market open volatility (NY Session at 9:30 AM EST and London Session Variant B at 3:00 AM EST) looking for a specific structural sweep.

- **Instrument:** NQ
- **Risk:** 1% per trade

### Strategy Setup & Rules

1. **Trading Windows:** 
   - **NY Session:** 09:30 AM – 10:10 AM EST
   - **London Session (Variant B):** 03:00 AM – 04:00 AM EST
2. **The Setup (Impulse & Retracement):**
   - The engine monitors the market open to establish an initial impulse wave. It tracks the extreme high and extreme low from the session open to define a Fibonacci range (0 to 1).
   - We wait for price to retrace into the "Golden Pocket"—specifically between the **23.6% and 40.0%** Fibonacci retracement levels.
3. **Execution Logic:**
   - **Market Entry:** If price enters the 23.6% - 40% zone, execute a market order in the direction of the initial impulse.
   - **Limit Entry:** If price moves too fast and violently breaks past the 40% level before an entry can trigger, a limit order is dynamically placed at the **33.0%** retracement level to catch the wick.
4. **Trade Management:**
   - **Stop Loss:** Hard stop placed exactly at the 0% Fibonacci level (the absolute extreme of the impulse wave).
   - **Take Profit:** Fixed 50 points from the entry price.
   - **Frequency:** Maximum of one trade per session window.

- **Account Mechanics:** The system leverages Prop Firm evaluation mechanics. Accounts are automatically discarded upon hitting a static drawdown limit, allowing the strategy to hedge against long consecutive losing streaks while maximizing outsized win streaks.


## Prop Firm Payout Mechanics (The "2% Rinse")

Through extensive multi-year backtesting across thousands of trades, we discovered that waiting for large payouts (e.g. 4%) on funded accounts resulted in a high frequency of accounts blowing up before cashing out. 

Instead, this strategy utilizes a **2% Continuous Rinsing** mechanic. Once an account passes its evaluations (Phase 1 & Phase 2) and gets funded:
1. The first payout targets a 1% profit to immediately recoup the Evaluation Fee.
2. Every subsequent payout triggers as soon as the account equity reaches +2% ($2,000 buffer on a 100k account).
3. The account is aggressively milked for small, continuous cash flow. 

---

## 10-Year Backtest Results (2015 - 2025)

These metrics represent a brutal 10-year simulation of trading this strategy exclusively on $100k Prop Firm accounts, accounting for all evaluation fees, account blow-ups, and actual physical dollars extracted.

### London Session Variant B
Because the London session strings together wins more aggressively and chops less than NY, it massively outperforms in actual dollars extracted.

- **Total Trades Taken:** 4,168
- **Total Evaluations Started:** 217
- **Evaluations Passed:** 44
- **Total Fees Paid:** $98,735.00
- **Total Refunds Earned:** $13,195.00
- **Net Fee Burn:** $85,540.00
- **Total Payouts Received:** $307,000.00
- **Net Profit (Payouts - Net Burn):** **$221,460.00**
- **Return on Spend (ROI):** **358.9%**

**Account Lifecycle:**
- Avg Days to Pass Eval (P1+P2): 20.2 days
- Avg Days to First 2% Payout (from funded): 5.2 days
- Avg 2% Payouts per passed account: 3.16

### NY Session
- **Total Trades Taken:** 3,634
- **Total Evaluations Started:** 145
- **Evaluations Passed:** 23
- **Total Fees Paid:** $65,975.00
- **Net Fee Burn:** $59,605.00
- **Total Payouts Received:** $156,000.00
- **Net Profit (Payouts - Net Burn):** **$96,395.00**
- **Return on Spend (ROI):** **261.7%**

**Account Lifecycle:**
- Avg Days to Pass Eval (P1+P2): 27.0 days
- Avg Days to First 2% Payout (from funded): 12.5 days
- Avg 2% Payouts per passed account: 3.09

---

## 5-Year Backtest Results (2020 - 2025)

The most recent 5 years of price action (which includes higher NQ volatility post-pandemic) showed even more lucrative returns for the 2% rinsing logic.

### London Session Variant B (5-Year)
- **Net Profit:** $188,610.00
- **Return on Spend (ROI):** 814.7%
- **Total Payouts Received:** $215,000.00
- **Avg 2% Payouts per passed account:** 4.76 *(Accounts survive much longer in this regime)*

### NY Session (5-Year)
- **Net Profit:** $77,260.00
- **Return on Spend (ROI):** 706.4%
- **Total Payouts Received:** $90,000.00
- **Avg 2% Payouts per passed account:** 3.42

## Conclusion
The **Market Open Reversal Strategy** paired with a strict **2% Payout Rinsing Framework** generates exceptional yield when executed on the London session. By frequently resetting the drawdown clock via Prop Firm evaluations and relentlessly stripping profits off the top, the strategy acts as an anti-fragile system against sudden structural shifts in NQ volatility.
