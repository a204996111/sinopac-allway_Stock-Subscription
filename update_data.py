import json
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import requests
import os # 🌟 新增：用來處理路徑

def get_current_price(stock_code, market):
    suffix = ".TW" if "上市" in str(market) else ".TWO"
    ticker1 = f"{stock_code}{suffix}"
    ticker2 = f"{stock_code}.TWO" if suffix == ".TW" else f"{stock_code}.TW"
    
    for t in [ticker1, ticker2]:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1d")
            if not hist.empty:
                return round(float(hist['Close'].iloc[-1]), 2)
        except:
            continue
    return 0.0

try:
    print("開始抓取證交所資料...")
    # 設定台灣時間 (UTC+8)
    tw_time = datetime.utcnow() + timedelta(hours=8)
    tw_year = tw_time.year - 1911
    today_str = f"{tw_year}/{tw_time.strftime('%m/%d')}"

    url = "https://www.twse.com.tw/rwd/zh/announcement/publicForm?response=json"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    res = requests.get(url, headers=headers, timeout=10)
    
    if res.status_code == 200:
        json_data = res.json()
        df = pd.DataFrame(json_data['data'], columns=json_data['fields'])
        
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['發行市場', '證券名稱'])
        df = df[~df['發行市場'].astype(str).str.contains('債')]
        df = df[df['申購結束日'] >= today_str]
        
        result = []
        for index, row in df.iterrows():
            shares_str = str(row['申購股數']).replace(',', '').strip()
            shares = int(shares_str) if shares_str.isdigit() else 1000
            
            sub_price_str = str(row['承銷價(元)']).replace(',', '').strip()
            if not sub_price_str.replace('.', '', 1).isdigit():
                continue
                
            code = str(row['證券代號']).strip()
            market = str(row['發行市場']).strip()
            is_emerging = "初" in market
            
            print(f"正在抓取 {code} {row['證券名稱']} 最新股價...")
            current_price = get_current_price(code, market)

            result.append({
                "name": str(row['證券名稱']).strip(),
                "code": code,
                "market": market,
                "startDate": str(row['申購開始日']).strip(),
                "endDate": str(row['申購結束日']).strip(),
                "lotteryDate": str(row['抽籤日期']).strip(), 
                "disburseDate": str(row['撥券日期(上市、上櫃日期)']).strip(),
                "subPrice": float(sub_price_str),
                "shares": shares,
                "currentPrice": current_price,
                "isEmerging": is_emerging
            })

        final_data = {
            "status": "success",
            "data": {
                "source": "github_actions",
                "update_time": tw_time.strftime("%Y-%m-%d %H:%M"),
                "list": result
            }
        }

        # 🌟 絕對路徑防護：確保存檔位置跟 update_data.py 在同一個資料夾
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'data.json')

        # 寫入 data.json
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 更新成功！資料已精準寫入: {json_path}")

except Exception as e:
    print(f"❌ 更新失敗: {e} (放棄本次更新，保留舊資料)")