import yfinance as yf
import json
import sys
from datetime import datetime
import pytz

def get_data(symbols):
    results = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        results[symbol] = {
            "price": info.get("regularMarketPrice"),
            "pre_price": info.get("preMarketPrice"),
            "pre_vol": info.get("preMarketVolume"),
            "prev_close": info.get("previousClose")
        }
    return results

def analyze_bps():
    symbols = ["AAPL", "AMZN", "MSFT"]
    data = get_data(symbols + ["^VIX"])
    
    # Monitored positions
    positions = [
        {"symbol": "AAPL", "short_strike": 255.0},
        {"symbol": "AMZN", "short_strike": 235.0},
        {"symbol": "MSFT", "short_strike": 475.0} # This seems odd but I'll use it
    ]
    
    vix = data["^VIX"]["price"]
    
    report = "📈 【美股盤前快訊 - 21:00 Snapshot】\n\n"
    report += f"📊 市場波動率 (VIX): {vix:.2f}\n"
    report += "(註: Fear & Greed 指數目前無法獲取)\n\n"
    
    report += "🔍 核心持倉盤前動態:\n"
    
    for pos in positions:
        sym = pos["symbol"]
        d = data[sym]
        curr = d["pre_price"] if d["pre_price"] else d["price"]
        prev = d["prev_close"]
        change = (curr - prev) / prev * 100
        vol = d["pre_vol"] if d["pre_vol"] else 0
        
        strike = pos["short_strike"]
        dist = (curr - strike) / strike * 100
        
        report += f"🔹 {sym}: ${curr:.2f} ({change:+.2f}%)\n"
        report += f"   - 盤前成交量: {vol:,}\n"
        report += f"   - 距離 Short Strike ({strike}): {dist:+.2f}%\n"
        if dist < 3 and dist > 0:
            report += "   ⚠️ 警語: 距離履約價過近，留意開盤波動！\n"
        elif dist <= 0:
            report += "   🚨 警語: 已進入價內 (ITM)！請評估轉倉或止損。\n"
        report += "\n"
        
    report += "💡 策略建議:\n"
    if vix > 20:
        report += "- VIX 高於 20，市場情緒不穩，建議暫緩新開 BPS 倉位。\n"
    else:
        report += "- VIX 平穩，維持現有 BPS 策略，監控開盤後 30 分鐘走勢。\n"
        
    if any(( (data[s]["pre_price"] if data[s]["pre_price"] else data[s]["price"]) - p["short_strike"]) / p["short_strike"] < 0.03 for s, p in zip(["AAPL", "AMZN", "MSFT"], positions)):
         report += "- 部分個股接近或突破 Short Strike，建議檢查保證金與風險控制。\n"

    return report

if __name__ == "__main__":
    try:
        print(analyze_bps())
    except Exception as e:
        print(f"Error: {e}")
