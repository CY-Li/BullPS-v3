import requests
import pandas as pd
import matplotlib.pyplot as plt
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
            print("✓ 數據獲取成功")
            return self.data
        except requests.exceptions.HTTPError as e:
            print(f"✗ HTTP錯誤: {e}")
            print("提示: CNN API可能需要從瀏覽器訪問或使用代理")
            return None
        except Exception as e:
            print(f"✗ 數據獲取失敗: {e}")
            return None
    
    def get_current_index(self):
        """獲取當前指數"""
        if not self.data:
            self.fetch_data()
        
        if not self.data:
            print("無法獲取數據，請檢查網絡連接或使用備用方案")
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
    
    def plot_index(self, days=90):
        """繪製恐懼貪婪指數圖表"""
        df = self.get_historical_data()
        
        if df.empty:
            print("無數據可供繪圖")
            return
        
        # 取最近N天的數據
        df_recent = df.tail(days)
        
        # 設置中文字體
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 繪製主線圖
        ax.plot(df_recent['date'], df_recent['score'], 
                linewidth=2, color='#2E86AB', label='恐懼貪婪指數')
        
        # 填充區域顏色
        ax.fill_between(df_recent['date'], 0, df_recent['score'], 
                        alpha=0.3, color='#2E86AB')
        
        # 添加水平線標記區域
        ax.axhline(y=25, color='red', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=45, color='orange', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=55, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=75, color='green', linestyle='--', alpha=0.5, linewidth=1)
        
        # 添加區域標籤
        ax.text(df_recent['date'].iloc[0], 12, '極度恐慌', 
                fontsize=10, alpha=0.6, color='red')
        ax.text(df_recent['date'].iloc[0], 35, '恐慌', 
                fontsize=10, alpha=0.6, color='orange')
        ax.text(df_recent['date'].iloc[0], 50, '中性', 
                fontsize=10, alpha=0.6, color='gray')
        ax.text(df_recent['date'].iloc[0], 65, '貪婪', 
                fontsize=10, alpha=0.6, color='lightgreen')
        ax.text(df_recent['date'].iloc[0], 87, '極度貪婪', 
                fontsize=10, alpha=0.6, color='green')
        
        # 設置標題和標籤
        current = self.get_current_index()
        ax.set_title(f'CNN恐懼貪婪指數 (當前: {current["指數"]:.1f} - {current["狀態"]})', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('指數值', fontsize=12)
        
        # 設置Y軸範圍
        ax.set_ylim(0, 100)
        
        # 網格
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)
        
        # 圖例
        ax.legend(loc='upper right', fontsize=10)
        
        plt.tight_layout()
        plt.show()
    
    def get_statistics(self):
        """獲取統計數據"""
        df = self.get_historical_data()
        
        if df.empty:
            print("無數據可供統計")
            return None
        
        stats = {
            '平均值': df['score'].mean(),
            '中位數': df['score'].median(),
            '標準差': df['score'].std(),
            '最大值': df['score'].max(),
            '最小值': df['score'].min(),
            '當前值': df['score'].iloc[-1]
        }
        
        # 計算各狀態佔比
        rating_counts = df['rating_cn'].value_counts()
        total = len(df)
        
        print("\n" + "="*50)
        print("統計數據")
        print("="*50)
        for key, value in stats.items():
            print(f"{key:8s}: {value:6.2f}")
        
        print("\n各狀態佔比:")
        for rating, count in rating_counts.items():
            percentage = (count / total) * 100
            print(f"{rating:8s}: {percentage:5.1f}% ({count}天)")
        print("="*50)
        
        return stats
    
    def save_to_csv(self, filename='fear_greed_data.csv'):
        """保存數據到CSV"""
        df = self.get_historical_data()
        if df.empty:
            print("無數據可供保存")
            return
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✓ 數據已保存到 {filename}")
    
    def load_from_json(self, json_file):
        """從本地JSON文件加載數據（備用方案）"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✓ 已從 {json_file} 加載數據")
            return self.data
        except Exception as e:
            print(f"✗ 加載JSON失敗: {e}")
            return None


# 使用範例
if __name__ == "__main__":
    # 創建實例
    fgi = FearGreedIndex()
    
    # 獲取當前指數
    print("\n當前恐懼貪婪指數:")
    print("-" * 50)
    current = fgi.get_current_index()
    
    if current:
        for key, value in current.items():
            print(f"{key}: {value}")
        
        # 獲取統計數據
        fgi.get_statistics()
        
        # 繪製圖表（最近90天）
        print("\n正在繪製圖表...")
        fgi.plot_index(days=90)
        
        # 保存數據
        fgi.save_to_csv()
        
        print("\n程式執行完成！")
    else:
        print("\n" + "="*60)
        print("API訪問受限，請使用以下備用方案:")
        print("="*60)
        print("\n方案1: 使用代理或VPN")
        print("方案2: 在瀏覽器中打開以下網址，複製JSON數據保存為 data.json:")
        print("      https://production.dataviz.cnn.io/index/fearandgreed/graphdata")
        print("\n然後使用以下代碼加載:")
        print("      fgi.load_from_json('data.json')")
        print("      current = fgi.get_current_index()")
        print("\n方案3: 使用替代API（如下所示）")
        print("="*60)
