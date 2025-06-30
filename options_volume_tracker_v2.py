#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
選擇權交易量追蹤器 v2.0
動態抓取當前市場選擇權交易量前50大的美股代號
自動更新 stock_watchlist.json 監控清單
"""

import yfinance as yf
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
import time
import warnings
from pathlib import Path
import logging
from typing import List, Dict, Optional

# 導入配置
try:
    from options_volume_config import *
except ImportError:
    # 如果配置文件不存在，使用預設值
    TOP_N = 50
    UPDATE_INTERVAL = 300
    CUSTOM_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC']
    USE_CUSTOM_SYMBOLS = False
    PRINT_TO_CONSOLE = True
    REQUEST_DELAY = 0.1
    MAX_RETRIES = 3
    INCLUDE_MARKET_DATA = True
    INCLUDE_EXPIRY_INFO = True

warnings.filterwarnings('ignore')

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('options_tracker.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class OptionsVolumeTrackerV2:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # stock_watchlist.json 文件路徑
        self.watchlist_file = Path("stock_watchlist.json")
        
        logging.info("選擇權交易量追蹤器已初始化")
    
    def load_watchlist(self) -> Dict:
        """載入現有的 stock_watchlist.json"""
        try:
            if self.watchlist_file.exists():
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logging.info(f"成功載入現有監控清單，包含 {len(data.get('stocks', []))} 支股票")
                return data
            else:
                logging.warning("stock_watchlist.json 不存在，將創建新文件")
                return {"stocks": [], "settings": {}}
        except Exception as e:
            logging.error(f"載入 stock_watchlist.json 失敗: {e}")
            return {"stocks": [], "settings": {}}
    
    def update_watchlist(self, top_symbols: List[str], max_stocks: int = 50) -> bool:
        """更新 stock_watchlist.json 文件"""
        try:
            # 載入現有數據
            watchlist_data = self.load_watchlist()
            
            # 獲取現有設定
            settings = watchlist_data.get('settings', {})
            
            # 保留現有設定中的分析參數
            if not settings:
                settings = {
                    "analysis_period": 60,
                    "rsi_oversold": 30,
                    "rsi_overbought": 70
                }
            
            # 更新股票列表
            # 保留前 max_stocks 支股票
            updated_stocks = top_symbols[:max_stocks]
            
            # 創建新的監控清單數據
            new_watchlist_data = {
                "stocks": updated_stocks,
                "settings": settings
            }
            
            # 備份原文件
            if self.watchlist_file.exists():
                backup_file = self.watchlist_file.with_suffix('.json.backup')
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
                logging.info(f"已備份原文件到: {backup_file}")
            
            # 寫入新數據
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(new_watchlist_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"成功更新 stock_watchlist.json，包含 {len(updated_stocks)} 支股票")
            
            # 顯示更新摘要
            print(f"\n📋 監控清單更新摘要:")
            print(f"   更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   股票數量: {len(updated_stocks)}")
            print(f"   前5支股票: {', '.join(updated_stocks[:5])}")
            print(f"   文件位置: {self.watchlist_file.absolute()}")
            
            return True
            
        except Exception as e:
            logging.error(f"更新 stock_watchlist.json 失敗: {e}")
            return False
    
    def get_stock_symbols(self) -> List[str]:
        """獲取股票代號列表"""
        if USE_CUSTOM_SYMBOLS:
            logging.info(f"使用自定義股票列表，共 {len(CUSTOM_SYMBOLS)} 支股票")
            return CUSTOM_SYMBOLS
        else:
            try:
                logging.info("正在獲取S&P 500股票列表...")
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                tables = pd.read_html(url)
                sp500_table = tables[0]
                symbols = sp500_table['Symbol'].tolist()
                logging.info(f"成功獲取 {len(symbols)} 支S&P 500股票")
                return symbols
            except Exception as e:
                logging.error(f"獲取S&P 500列表失敗: {e}")
                logging.info("使用備用股票列表")
                return CUSTOM_SYMBOLS
    
    def get_options_volume(self, symbol: str) -> Dict:
        """獲取單一股票的選擇權交易量"""
        for attempt in range(MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                
                # 獲取選擇權到期日
                options = ticker.options
                
                if not options:
                    return {
                        'symbol': symbol,
                        'total_volume': 0,
                        'call_volume': 0,
                        'put_volume': 0,
                        'put_call_ratio': 0,
                        'expiry': None,
                        'timestamp': datetime.now().isoformat()
                    }
                
                # 使用最近的到期日
                latest_expiry = options[0]
                
                # 獲取看漲和看跌選擇權
                option_chain = ticker.option_chain(latest_expiry)
                calls = option_chain.calls
                puts = option_chain.puts
                
                # 計算交易量
                call_volume = calls['volume'].sum() if not calls.empty else 0
                put_volume = puts['volume'].sum() if not puts.empty else 0
                total_volume = call_volume + put_volume
                
                # 計算看跌/看漲比率
                put_call_ratio = put_volume / call_volume if call_volume > 0 else 0
                
                return {
                    'symbol': symbol,
                    'total_volume': total_volume,
                    'call_volume': call_volume,
                    'put_volume': put_volume,
                    'put_call_ratio': put_call_ratio,
                    'expiry': latest_expiry,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logging.warning(f"獲取 {symbol} 選擇權數據失敗 (嘗試 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                else:
                    return {
                        'symbol': symbol,
                        'total_volume': 0,
                        'call_volume': 0,
                        'put_volume': 0,
                        'put_call_ratio': 0,
                        'expiry': None,
                        'timestamp': datetime.now().isoformat()
                    }
    
    def get_market_data(self, symbols: List[str]) -> pd.DataFrame:
        """獲取股票的市場數據"""
        try:
            logging.info("正在獲取市場數據...")
            
            market_data = []
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    # 獲取歷史數據來計算當前價格
                    hist = ticker.history(period="1d")
                    current_price = hist['Close'].iloc[-1] if not hist.empty else 0
                    
                    market_data.append({
                        'symbol': symbol,
                        'name': info.get('longName', 'N/A'),
                        'price': current_price,
                        'market_cap': info.get('marketCap', 0),
                        'volume': info.get('volume', 0),
                        'pe_ratio': info.get('trailingPE', 0),
                        'beta': info.get('beta', 0)
                    })
                    
                    time.sleep(0.05)  # 避免API限制
                    
                except Exception as e:
                    logging.warning(f"獲取 {symbol} 市場數據失敗: {e}")
                    continue
            
            return pd.DataFrame(market_data)
            
        except Exception as e:
            logging.error(f"獲取市場數據失敗: {e}")
            return pd.DataFrame()
    
    def get_top_options_volume(self, top_n: int = TOP_N) -> pd.DataFrame:
        """獲取選擇權交易量前N大的股票"""
        symbols = self.get_stock_symbols()
        
        logging.info(f"正在分析 {len(symbols)} 支股票的選擇權交易量...")
        
        results = []
        for i, symbol in enumerate(symbols):
            logging.info(f"進度: {i+1}/{len(symbols)} - 分析 {symbol}")
            volume_data = self.get_options_volume(symbol)
            results.append(volume_data)
            
            # 避免API限制
            time.sleep(REQUEST_DELAY)
        
        # 轉換為DataFrame並排序
        df = pd.DataFrame(results)
        df = df[df['total_volume'] > 0]  # 過濾掉交易量為0的股票
        df = df.sort_values('total_volume', ascending=False)
        
        return df.head(top_n)
    
    def generate_report(self, top_options_df: pd.DataFrame, market_data_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """生成報告"""
        if PRINT_TO_CONSOLE:
            print("\n" + "="*100)
            print("選擇權交易量前50大美股報告")
            print("="*100)
            print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*100)
        
        if market_data_df is not None and not market_data_df.empty:
            # 合併選擇權數據和市場數據
            merged_df = top_options_df.merge(market_data_df, on='symbol', how='left')
            
            if PRINT_TO_CONSOLE:
                for idx, row in merged_df.iterrows():
                    print(f"{idx+1:2d}. {row['symbol']:6s} - {row.get('name', 'N/A')[:35]:35s}")
                    print(f"    選擇權總交易量: {row['total_volume']:,}")
                    print(f"    看漲選擇權: {row['call_volume']:,} | 看跌選擇權: {row['put_volume']:,}")
                    print(f"    看跌/看漲比率: {row['put_call_ratio']:.2f}")
                    if 'price' in row and pd.notna(row['price']):
                        print(f"    當前價格: ${row['price']:.2f}")
                    if 'market_cap' in row and pd.notna(row['market_cap']):
                        print(f"    市值: ${row['market_cap']/1e9:.1f}B")
                    print()
        else:
            merged_df = top_options_df
            if PRINT_TO_CONSOLE:
                for idx, row in merged_df.iterrows():
                    print(f"{idx+1:2d}. {row['symbol']:6s}")
                    print(f"    選擇權總交易量: {row['total_volume']:,}")
                    print(f"    看漲選擇權: {row['call_volume']:,} | 看跌選擇權: {row['put_volume']:,}")
                    print(f"    看跌/看漲比率: {row['put_call_ratio']:.2f}")
                    if 'expiry' in row and row['expiry']:
                        print(f"    到期日: {row['expiry']}")
                    print()
        
        return merged_df
    
    def run_single_scan(self, update_watchlist: bool = True, max_watchlist_stocks: int = 50):
        """執行單次掃描"""
        logging.info("開始執行選擇權交易量掃描...")
        
        # 獲取選擇權交易量前N大的股票
        top_options = self.get_top_options_volume(TOP_N)
        
        if top_options.empty:
            logging.warning("沒有找到選擇權交易量數據")
            return
        
        # 獲取市場數據
        symbols = top_options['symbol'].tolist()
        market_data = self.get_market_data(symbols)
        
        # 生成報告
        final_df = self.generate_report(top_options, market_data)
        
        # 更新監控清單
        if update_watchlist:
            top_symbols = final_df['symbol'].tolist()
            success = self.update_watchlist(top_symbols, max_watchlist_stocks)
            if success:
                logging.info("監控清單更新成功")
            else:
                logging.error("監控清單更新失敗")
        
        logging.info("掃描完成！")
        return final_df

def main():
    """主函數"""
    tracker = OptionsVolumeTrackerV2()
    
    print("選擇權交易量追蹤器 v2.0")
    print("="*50)
    print("開始執行選擇權交易量掃描...")
    
    try:
        result = tracker.run_single_scan(update_watchlist=True, max_watchlist_stocks=50)
        if result is not None:
            print(f"\n成功獲取 {len(result)} 支股票的選擇權數據")
            print("✅ stock_watchlist.json 已自動更新")
        else:
            print("掃描完成，但沒有獲取到有效數據")
    except Exception as e:
        logging.error(f"程式執行錯誤: {e}")
        print(f"程式執行失敗: {e}")

if __name__ == "__main__":
    main() 