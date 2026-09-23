"""
專案名稱：AIot_L3_CWA_HW1 - Taiwan Weather Forecast
模組說明：中央氣象署 CWA API 抓取與資料清洗模組 (get_weather.py)
步驟對應：步驟 3 ~ 7 (API 資料取得、JSON 解析、提取 MinT / MaxT、資料整理與預覽)
"""

import os
import sys
import json
from collections import defaultdict
from typing import List, Dict, Optional
import requests
import urllib3
import pandas as pd

import sys

# 確保在 Windows 終端機能正常印出 Unicode
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 匯入資料庫存取函式
from database import save_forecasts, init_db

# 關閉 SSL 驗證警告 (因應 Python 3.14 / Windows 憑證相容性)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 讀取本地 .env 檔案中的敏感設定 (已由 .gitignore 排除)
def load_env_file(filepath: str = ".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env_file()

# 支援 Streamlit Cloud (share.streamlit.io) 的 Secrets 環境變數
try:
    import streamlit as st
    if hasattr(st, "secrets") and "CWA_API_KEY" in st.secrets:
        os.environ["CWA_API_KEY"] = st.secrets["CWA_API_KEY"]
except Exception:
    pass

# 中央氣象署 API 授權金鑰 (優先由 Streamlit Cloud Secrets / .env / 系統環境變數讀取)
DEFAULT_API_KEY = os.getenv("CWA_API_KEY", "")

# 台灣分區對應縣市 (對應作業 6 大預報區域)
REGION_MAPPING = {
    "北部地區": ["基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣"],
    "中部地區": ["臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣"],
    "南部地區": ["臺南市", "高雄市", "屏東縣"],
    "東北部地區": ["宜蘭縣"],
    "東部地區": ["花蓮縣"],
    "東南部地區": ["臺東縣"],
}

# 各分區地理代表中心座標 (用於 Folium 地圖視覺化: 步驟 17, 18)
REGION_COORDINATES = {
    "北部地區": {"lat": 24.95, "lon": 121.40},
    "中部地區": {"lat": 23.95, "lon": 120.70},
    "南部地區": {"lat": 22.75, "lon": 120.45},
    "東北部地區": {"lat": 24.70, "lon": 121.75},
    "東部地區": {"lat": 23.80, "lon": 121.45},
    "東南部地區": {"lat": 22.85, "lon": 121.05},
}


def fetch_cwa_forecast(api_key: str = DEFAULT_API_KEY) -> Optional[dict]:
    """
    從中央氣象署 CWA API 取得全臺一週預報資料 (F-D0047-091) (步驟 4)
    """
    if not api_key:
        print("[Error] 未設定 CWA_API_KEY！請在 .env 檔案中設定 CWA_API_KEY=您的授權碼")
        return None

    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={api_key}"
    print(f"正在連線中央氣象署 CWA API (F-D0047-091)...")

    try:
        response = requests.get(url, verify=False, timeout=20)
        response.raise_for_status()
        data = response.json()

        if data.get("success") == "true" or data.get("success") is True:
            print("[OK] 成功取得氣象署 API JSON 資料！")
            return data
        else:
            print(f"API 回傳失敗訊息: {data.get('message')}")
            return None
    except Exception as e:
        print(f"連線或擷取 API 資料時發生錯誤: {e}")
        return None


def parse_and_process_weather(raw_json: dict) -> pd.DataFrame:
    """
    解析 JSON 結構並計算各分區每日最低與最高溫 (步驟 5、6、7)
    回傳 Pandas DataFrame (欄位: regionName, dataDate, mint, maxt)
    """
    locations = raw_json.get("records", {}).get("Locations", [{}])[0].get("Location", [])
    if not locations:
        print("未在 JSON 中找到 Location 資料！")
        return pd.DataFrame()

    county_data = {}
    for loc in locations:
        county_name = loc.get("LocationName")
        county_data[county_name] = {
            "MinT": defaultdict(list),
            "MaxT": defaultdict(list),
        }

        for elem in loc.get("WeatherElement", []):
            elem_name = elem.get("ElementName")
            # 抓取最高溫
            if elem_name == "最高溫度":
                for t in elem.get("Time", []):
                    date_str = t["StartTime"][:10]
                    val = float(t["ElementValue"][0]["MaxTemperature"])
                    county_data[county_name]["MaxT"][date_str].append(val)
            # 抓取最低溫
            elif elem_name == "最低溫度":
                for t in elem.get("Time", []):
                    date_str = t["StartTime"][:10]
                    val = float(t["ElementValue"][0]["MinTemperature"])
                    county_data[county_name]["MinT"][date_str].append(val)

    # 依分區彙整各縣市一週高低溫
    records = []
    for region, counties in REGION_MAPPING.items():
        all_dates = set()
        for c in counties:
            if c in county_data:
                all_dates.update(county_data[c]["MinT"].keys())

        for date_str in sorted(list(all_dates)):
            mins = [
                min(county_data[c]["MinT"][date_str])
                for c in counties
                if c in county_data and date_str in county_data[c]["MinT"]
            ]
            maxs = [
                max(county_data[c]["MaxT"][date_str])
                for c in counties
                if c in county_data and date_str in county_data[c]["MaxT"]
            ]

            if mins and maxs:
                avg_min = round(sum(mins) / len(mins), 1)
                avg_max = round(sum(maxs) / len(maxs), 1)
                records.append({
                    "regionName": region,
                    "dataDate": date_str,
                    "mint": avg_min,
                    "maxt": avg_max
                })

    df = pd.DataFrame(records)
    return df


def update_weather_pipeline(api_key: str = DEFAULT_API_KEY) -> pd.DataFrame:
    """
    完整的 ETL 流程：擷取 ➔ 清洗 ➔ 寫入 SQLite (步驟 8)
    """
    raw_data = fetch_cwa_forecast(api_key)
    if not raw_data:
        print("無法取得 API 資料，取消更新。")
        return pd.DataFrame()

    df = parse_and_process_weather(raw_data)
    if df.empty:
        print("解析後無有效氣象資料！")
        return df

    print("\n【資料整理與預覽 (步驟 7)】")
    print(df.head(10))

    # 寫入 SQLite
    records = df.to_dict(orient="records")
    save_forecasts(records)
    print("[OK] 氣象預報資料更新完成！")
    return df


if __name__ == "__main__":
    df = update_weather_pipeline()
