"""
專案名稱：AIot_L3_CWA_HW1 - Taiwan Weather Forecast
模組說明：SQLite 資料庫管理模組 (database.py)
功能包含：建立資料庫、創建 TemperatureForecasts 資料表、防重複寫入、查詢檢索。
"""

import os
import sqlite3
import pandas as pd
from typing import List, Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "data.db")


def get_connection(db_name: str = DB_NAME) -> sqlite3.Connection:
    """取得 SQLite 資料庫連線"""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_name: str = DB_NAME) -> None:
    """
    初始化資料庫與資料表設計 (步驟 8、9、20)
    建立 TemperatureForecasts 資料表，並設置 (regionName, dataDate) 唯一約束以防重複插入
    """
    conn = get_connection(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataDate TEXT NOT NULL,
            mint REAL NOT NULL,
            maxt REAL NOT NULL,
            UNIQUE(regionName, dataDate)
        );
    """)
    conn.commit()
    conn.close()
    print(f"[{db_name}] 資料表 TemperatureForecasts 初始化完成！")


def save_forecasts(data_list: List[Dict], db_name: str = DB_NAME) -> int:
    """
    將氣象資料寫入資料庫 (防重複寫入機制: INSERT OR REPLACE) (步驟 8、20)
    data_list 元素格式：{'regionName': str, 'dataDate': str, 'mint': float, 'maxt': float}
    """
    if not data_list:
        return 0

    init_db(db_name)
    conn = get_connection(db_name)
    cursor = conn.cursor()

    sql = """
        INSERT INTO TemperatureForecasts (regionName, dataDate, mint, maxt)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(regionName, dataDate) DO UPDATE SET
            mint = excluded.mint,
            maxt = excluded.maxt;
    """

    rows = [
        (item["regionName"], item["dataDate"], float(item["mint"]), float(item["maxt"]))
        for item in data_list
    ]

    cursor.executemany(sql, rows)
    conn.commit()
    affected = len(rows)
    conn.close()
    print(f"成功儲存/更新 {affected} 筆氣溫資料至 {db_name}")
    return affected


def get_distinct_regions(db_name: str = DB_NAME) -> List[str]:
    """查詢所有不重複的地區名稱 (步驟 10)"""
    conn = get_connection(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName;")
    regions = [row["regionName"] for row in cursor.fetchall()]
    conn.close()
    return regions


def get_forecast_by_region(region_name: str, db_name: str = DB_NAME) -> pd.DataFrame:
    """依地區查詢一週氣溫預報 (步驟 10、12)"""
    conn = get_connection(db_name)
    query = """
        SELECT id, regionName, dataDate, mint, maxt
        FROM TemperatureForecasts
        WHERE regionName = ?
        ORDER BY dataDate ASC;
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df


def get_forecast_by_date(data_date: str, db_name: str = DB_NAME) -> pd.DataFrame:
    """依日期查詢各地區氣溫預報 (步驟 18: 地圖日期過濾)"""
    conn = get_connection(db_name)
    query = """
        SELECT regionName, dataDate, mint, maxt
        FROM TemperatureForecasts
        WHERE dataDate = ?
        ORDER BY regionName ASC;
    """
    df = pd.read_sql_query(query, conn, params=(data_date,))
    conn.close()
    return df


def get_all_dates(db_name: str = DB_NAME) -> List[str]:
    """取得資料庫中所有預報日期清單"""
    conn = get_connection(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dataDate FROM TemperatureForecasts ORDER BY dataDate ASC;")
    dates = [row["dataDate"] for row in cursor.fetchall()]
    conn.close()
    return dates


if __name__ == "__main__":
    init_db()
    print("Distinct regions:", get_distinct_regions())
