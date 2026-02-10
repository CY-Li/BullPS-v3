import yfinance as yf
print("Starting download...")
df = yf.download("2330.TW", period="1mo", interval="1d", progress=False)
print(f"Downloaded: {len(df)} rows")
print(df.head())
