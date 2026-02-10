import yfinance as yf
import json

def test():
    symbols = ["AMZN", "DIS", "IWM"]
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        t = yf.Ticker(symbol)
        try:
            # 獲取過期日
            expirations = t.options
            print(f"Expirations: {expirations[:5]}")
            
            # 獲取指定日期的選擇權
            if expirations:
                # 尋找最接近 2026-03-20 (AMZN) 或 2026-03-06 (DIS) 或 2026-03-13 (IWM) 的日期
                # 這裡簡單測試第一個
                opt = t.option_chain(expirations[0])
                print(f"Puts count: {len(opt.puts)}")
                print(opt.puts.head(2))
            else:
                print("No options found.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    test()
