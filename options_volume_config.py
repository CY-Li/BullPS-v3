# 選擇權交易量追蹤器配置文件

# 基本設定
TOP_N = 50  # 要追蹤的前N大選擇權交易量股票
UPDATE_INTERVAL = 300  # 更新間隔（秒），預設5分鐘

# 股票代號列表（可以自定義要追蹤的股票）
CUSTOM_SYMBOLS = [
    # 科技股
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC',
    'CRM', 'ADBE', 'ORCL', 'CSCO', 'IBM', 'QCOM', 'AVGO', 'TXN', 'MU', 'KLAC',
    
    # 金融股
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'TFC', 'COF',
    
    # 醫療保健
    'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN',
    
    # 消費品
    'PG', 'KO', 'PEP', 'WMT', 'HD', 'MCD', 'DIS', 'NKE', 'SBUX', 'COST',
    
    # 能源
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'OXY', 'HAL',
    
    # 其他熱門股票
    'SPY', 'QQQ', 'IWM', 'VIX', 'UVXY', 'TQQQ', 'SQQQ', 'SOXL', 'SOXS'
]

# 是否使用自定義股票列表（True）或自動獲取S&P 500列表（False）
USE_CUSTOM_SYMBOLS = False

# 輸出設定
PRINT_TO_CONSOLE = True  # 是否在控制台顯示結果

# API設定
REQUEST_DELAY = 0.1  # 請求間隔（秒），避免API限制
MAX_RETRIES = 3  # 最大重試次數

# 選擇權設定
OPTIONS_EXPIRY_DAYS = 30  # 只考慮30天內到期的選擇權
MIN_VOLUME_THRESHOLD = 100  # 最小交易量閾值

# 報告設定
INCLUDE_MARKET_DATA = True  # 是否包含市場數據（價格、市值等）
INCLUDE_EXPIRY_INFO = True  # 是否包含到期日信息 