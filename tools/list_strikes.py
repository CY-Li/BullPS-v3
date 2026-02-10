import yfinance as yf

def list_dis_strikes():
    t = yf.Ticker("DIS")
    expiry = "2026-03-06"
    try:
        options = t.option_chain(expiry)
        puts = options.puts
        print(f"DIS {expiry} Put Strikes:")
        print(puts['strike'].tolist())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    list_dis_strikes()
