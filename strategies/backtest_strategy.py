import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import sys

def backtest(ticker):
    print(f"Fetching data for {ticker}...")
    try:
        # Fetch 2y data
        df = yf.download(ticker, period="2y", progress=False)
    except Exception as e:
        return {"error": str(e)}
    
    if len(df) < 50:
        return {"error": "Not enough data fetched"}
    
    # Calculate HV (30-day rolling std dev of daily returns, annualized)
    # Using 'Close' or 'Adj Close'. 'Close' matches daily price action better for strike selection in real-time?
    # Usually Adjusted Close is better for returns, but Strikes are based on raw price.
    # However, yfinance 'Close' is split-adjusted. 'Adj Close' is split and dividend adjusted.
    # We will use 'Close' for price levels and 'Adj Close' for Returns calculation if possible, 
    # but yfinance often returns just one or the other depending on version.
    # Let's check columns. Recent yfinance returns MultiIndex if not flattened, or just columns.
    
    # Reset index to make Date a column for easier handling if needed, or keep as index.
    # df.index is DatetimeIndex.
    
    # Handle yfinance structure (sometimes MultiIndex columns)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(ticker, axis=1, level=1)
        except:
            # Maybe just level 0 if only one ticker
            pass
            
    # Calculate Returns
    df['Returns'] = df['Close'].pct_change()
    
    # Annualized HV
    df['HV'] = df['Returns'].rolling(window=30).std() * np.sqrt(252)
    
    # 30-day Low
    df['Low_30'] = df['Low'].rolling(window=30).min()
    
    trades = []
    
    # Step approx 30 calendar days -> 21 trading days
    step = 21 
    
    # Start index: 30 (for window)
    current_idx = 30
    
    print("Simulating trades...")
    while current_idx + step < len(df):
        # Entry
        entry_date = df.index[current_idx]
        entry_price = float(df['Close'].iloc[current_idx])
        hv = float(df['HV'].iloc[current_idx])
        low_30 = float(df['Low_30'].iloc[current_idx])
        
        if pd.isna(hv) or pd.isna(low_30):
            current_idx += 1
            continue

        # Calculate Strikes
        # 1SD move (for 30 days)
        # Using 30/365 for time decay in volatility model approximation
        # Sigma move = Price * HV * sqrt(T)
        t_years = 30 / 365.0
        one_sd_move = entry_price * hv * np.sqrt(t_years)
        strike_1sd = entry_price - one_sd_move
        
        # Strategy Rule: Short Put Strike = 30-day Low OR 1SD below price
        # We take the MINIMUM (lower price) to be conservative/safer
        short_strike = min(low_30, strike_1sd)
        
        # Long Strike
        long_strike = short_strike - 5.0
        
        # Credit: 20% of spread width (5.0) = 1.0
        credit = 1.0
        
        # Expiration
        exit_idx = current_idx + step
        exit_date = df.index[exit_idx]
        exit_price = float(df['Close'].iloc[exit_idx])
        
        # P&L Calculation
        pnl = 0.0
        outcome = ""
        
        # Max Profit = Credit (if price > short_strike)
        if exit_price >= short_strike:
            pnl = credit
            outcome = "Win"
        # Max Loss = Credit - SpreadWidth (if price < long_strike)
        elif exit_price <= long_strike:
            pnl = credit - 5.0
            outcome = "Max Loss"
        # Partial Loss
        else:
            loss_amt = short_strike - exit_price
            pnl = credit - loss_amt
            outcome = "Partial Loss"
            
        trades.append({
            "entry_date": str(entry_date.date()),
            "exit_date": str(exit_date.date()),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "hv_30": round(hv, 4),
            "low_30": round(low_30, 2),
            "short_strike": round(short_strike, 2),
            "long_strike": round(long_strike, 2),
            "pnl": round(pnl, 2),
            "outcome": outcome
        })
        
        # Move to next trade (next month)
        current_idx += step

    # Metrics
    if not trades:
        return {"error": "No trades generated"}
        
    df_trades = pd.DataFrame(trades)
    
    # Win Rate
    win_count = len(df_trades[df_trades['pnl'] > 0])
    win_rate = win_count / len(df_trades)
    
    # Total P&L (x100 for contract value)
    total_pnl = df_trades['pnl'].sum() * 100
    
    # Max Drawdown
    # Calculate cumulative P&L
    df_trades['cum_pnl'] = df_trades['pnl'].cumsum() * 100
    df_trades['peak'] = df_trades['cum_pnl'].cummax()
    df_trades['drawdown'] = df_trades['cum_pnl'] - df_trades['peak']
    max_drawdown = df_trades['drawdown'].min()
    
    results = {
        "ticker": ticker,
        "metrics": {
            "win_rate": round(win_rate, 4),
            "total_pnl": round(total_pnl, 2),
            "max_drawdown": round(max_drawdown, 2),
            "trade_count": len(trades)
        },
        "trades": trades
    }
    
    return results

if __name__ == "__main__":
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        
    print(f"Running backtest for {ticker}...")
    res = backtest(ticker)
    
    # Output to file
    out_file = "BullPS-v3/results.json"
    with open(out_file, "w") as f:
        json.dump(res, f, indent=2)
        
    print(json.dumps(res, indent=2))
