import requests
import pandas as pd
from datetime import datetime
import json

class FearGreedIndex:
    """CNN恐懼貪婪指數分析工具"""
    
    def __init__(self):
        self.api_url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        self.data = None
        
    def fetch_data(self):
        """從CNN API獲取恐懼貪婪指數數據"""
        try:
            # 添加請求標頭，模擬瀏覽器訪問
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.cnn.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site'
            }
            
            response = requests.get(self.api_url, headers=headers, timeout=10)
            response.raise_for_status()
            self.data = response.json()
            # In a server environment, prefer logging over printing
            # print("✓ 數據獲取成功")
            return self.data
        except requests.exceptions.HTTPError as e:
            # print(f"✗ HTTP錯誤: {e}")
            # print("提示: CNN API可能需要從瀏覽器訪問或使用代理")
            return None
        except Exception as e:
            # print(f"✗ 數據獲取失敗: {e}")
            return None
    
    def get_current_index(self):
        """獲取當前指數"""
        if not self.data:
            self.fetch_data()
        
        if not self.data:
            # print("無法獲取數據，請檢查網絡連接或使用備用方案")
            return None
            
        current = self.data['fear_and_greed']
        return {
            '指數': current['score'],
            '狀態': self.translate_rating(current['rating']),
            '更新時間': current['timestamp'],
            '前一日收盤': current['previous_close'],
            '一週前': current['previous_1_week'],
            '一月前': current['previous_1_month'],
            '一年前': current['previous_1_year']
        }
    
    def translate_rating(self, rating):
        """翻譯評級"""
        ratings = {
            'extreme fear': '極度恐慌',
            'fear': '恐慌',
            'neutral': '中性',
            'greed': '貪婪',
            'extreme greed': '極度貪婪'
        }
        return ratings.get(rating, rating)
    
    def get_historical_data(self):
        """獲取歷史數據並轉換為DataFrame"""
        if not self.data:
            self.fetch_data()
        
        if not self.data:
            return pd.DataFrame()
            
        hist_data = self.data['fear_and_greed_historical']['data']
        df = pd.DataFrame(hist_data)
        
        # 轉換時間戳為日期
        df['date'] = pd.to_datetime(df['x'], unit='ms')
        df['score'] = df['y']
        df['rating_cn'] = df['rating'].apply(self.translate_rating)
        
        return df[['date', 'score', 'rating', 'rating_cn']]

    def load_from_json(self, json_file):
        """從本地JSON文件加載數據（備用方案）"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            # print(f"✓ 已從 {json_file} 加載數據")
            return self.data
        except Exception as e:
            # print(f"✗ 加載JSON失敗: {e}")
            return None
