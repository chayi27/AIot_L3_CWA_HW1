"""
專案名稱：台灣即時氣象地圖 (Taiwan Weather Map) - AIot_L3_CWA_HW1
支援雙平台：
1. 本機 / Streamlit Cloud：執行 streamlit run app.py
2. Vercel 雲端部署：匯出符合 Vercel Python Runtime 規範之頂層 "app" / "handler" WSGI 應用程式
   (參考規範：https://vercel.com/docs/functions/runtimes/python#python-entrypoints)
"""

import os
import sys
import json
import sqlite3
import pandas as pd
from typing import Dict, List

# 確保輸出支援 UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 匯入資料庫模組
import database
from get_weather import update_weather_pipeline, REGION_COORDINATES


def get_windy_temp_color(temp: float) -> str:
    """溫度色彩分級 (Windy 漸層色階)"""
    if temp < 15.0:
        return "#2c7bb6"
    elif 15.0 <= temp < 20.0:
        return "#5aa2cf"
    elif 20.0 <= temp < 25.0:
        return "#7fcdbb"
    elif 25.0 <= temp < 28.0:
        return "#fee08b"
    elif 28.0 <= temp < 32.0:
        return "#fdae61"
    else:
        return "#d73027"


# ==============================================================================
# 1. Vercel Serverless WSGI Entrypoint ("app" / "handler")
# ==============================================================================

def get_all_db_data_json():
    """取得資料庫所有預報資料並轉為 JSON 供 Vercel 前端使用"""
    database.init_db()
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT regionName, dataDate, mint, maxt FROM TemperatureForecasts ORDER BY dataDate ASC, regionName ASC;")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # 若資料庫為空，嘗試初次抓取
    if not rows:
        try:
            update_weather_pipeline()
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT regionName, dataDate, mint, maxt FROM TemperatureForecasts ORDER BY dataDate ASC, regionName ASC;")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
        except Exception:
            pass
            
    return rows


def generate_vercel_html() -> str:
    """產生符合 taiwan-weather-map 風格的高科技深色視覺化網頁"""
    data_rows = get_all_db_data_json()
    data_json_str = json.dumps(data_rows, ensure_ascii=False)
    coords_json_str = json.dumps(REGION_COORDINATES, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>台灣即時氣象地圖 - AIot_L3_CWA_HW1</title>
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0b0f19;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow-x: hidden;
            padding: 16px 20px;
        }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px 24px;
            margin-bottom: 14px;
            backdrop-filter: blur(12px);
        }}
        .topbar h1 {{ font-size: 1.45rem; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
        .badge {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .main-container {{
            display: grid;
            grid-template-columns: 72% 28%;
            gap: 16px;
        }}
        @media (max-width: 1024px) {{
            .main-container {{ grid-template-columns: 1fr; }}
        }}
        #map {{
            height: 680px;
            width: 100%;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            z-index: 1;
        }}
        .card {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
            backdrop-filter: blur(12px);
        }}
        .card-header {{
            font-size: 0.92rem;
            font-weight: 700;
            color: #e2e8f0;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
        .metric-cell {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 8px 10px;
            text-align: center;
        }}
        .metric-label {{ font-size: 0.75rem; color: #94a3b8; }}
        .metric-val {{ font-size: 1.25rem; font-weight: 800; color: #f8fafc; }}
        select {{
            width: 100%;
            background: #1e293b;
            color: #f8fafc;
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }}
        .gradient-bar {{
            height: 10px;
            width: 100%;
            border-radius: 9999px;
            background: linear-gradient(to right, #2c7bb6, #5aa2cf, #abd9e9, #7fcdbb, #d9ef8b, #fee08b, #fdae61, #f46d43, #d73027);
            margin-top: 6px;
        }}
        .scale-ticks {{ display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; text-align: center; }}
        th, td {{ padding: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); }}
        th {{ color: #94a3b8; }}
        .bottom-bar {{
            margin-top: 14px;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
        }}
        .btn {{
            text-decoration: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 600;
            color: white;
            background: #2563eb;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <h1><span>🌀 台灣即時氣象地圖</span> <span style="font-size:0.85rem; color:#94a3b8; font-weight:normal;">中央氣象署開放資料 (Vercel 部署版)</span></h1>
        <div class="badge">開發者：AIot_L3_CWA_HW1</div>
    </div>

    <div class="main-container">
        <!-- 左側主視圖：台灣氣象地圖 -->
        <div>
            <div id="map"></div>
            <div class="card" style="margin-top: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:0.82rem;">🎨 Windy 氣溫色階圖例 (Temperature Scale)</b>
                    <span style="font-size:0.75rem; color:#94a3b8;">單位: °C</span>
                </div>
                <div class="gradient-bar"></div>
                <div class="scale-ticks">
                    <span>5°</span><span>10°</span><span>15°</span><span>20°</span><span>24°</span><span>28°</span><span>32°</span><span>36°+</span>
                </div>
            </div>
        </div>

        <!-- 右側控制面板 -->
        <div>
            <div class="card">
                <div class="card-header">🎛️ 圖層與控制</div>
                <label style="font-size:0.78rem; color:#94a3b8;">📅 選擇預報日期：</label>
                <select id="dateSelect" onchange="onDateChange()"></select>
                <label style="font-size:0.78rem; color:#94a3b8;">📍 選擇預報分區：</label>
                <select id="regionSelect" onchange="onRegionChange()"></select>
            </div>

            <div class="card">
                <div class="card-header" id="kpiTitle">📊 即時氣候指標</div>
                <div class="metric-grid">
                    <div class="metric-cell">
                        <div class="metric-label">今日最高溫</div>
                        <div class="metric-val" id="maxTempVal" style="color:#f87171;">--°C</div>
                    </div>
                    <div class="metric-cell">
                        <div class="metric-label">今日最低溫</div>
                        <div class="metric-val" id="minTempVal" style="color:#60a5fa;">--°C</div>
                    </div>
                    <div class="metric-cell">
                        <div class="metric-label">預估平均溫</div>
                        <div class="metric-val" id="avgTempVal" style="color:#38bdf8;">--°C</div>
                    </div>
                    <div class="metric-cell">
                        <div class="metric-label">預估日溫差</div>
                        <div class="metric-val" id="diffTempVal" style="color:#fbbf24;">--°C</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">📈 7日氣溫走勢 (HW10)</div>
                <canvas id="tempChart" height="150"></canvas>
            </div>

            <div class="card">
                <div class="card-header">📋 一週數據表格</div>
                <div style="max-height:160px; overflow-y:auto;">
                    <table>
                        <thead><tr><th>日期</th><th>最低</th><th>最高</th><th>均溫</th></tr></thead>
                        <tbody id="tableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="bottom-bar">
        <div>🚀 <b>Vercel 部署已就緒</b> ｜ GitHub 儲存庫：<code>chayi27/AIot_L3_CWA_HW1</code></div>
        <a href="https://github.com/chayi27/AIot_L3_CWA_HW1" target="_blank" class="btn">📂 開啟 GitHub 倉庫</a>
    </div>

    <script>
        const allData = {data_json_str};
        const regionCoords = {coords_json_str};

        // 初始化底圖 (Esri Dark Canvas)
        const map = L.map('map').setView([23.72, 120.95], 7);
        L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Esri World Dark Gray',
            maxZoom: 16
        }}).addTo(map);

        let markersLayer = L.layerGroup().addTo(map);
        let chartInstance = null;

        // 提取所有不重複日期與地區
        const dates = [...new Set(allData.map(d => d.dataDate))].sort();
        const regions = [...new Set(allData.map(d => d.regionName))].sort();

        // 填充選單
        const dateSelect = document.getElementById('dateSelect');
        dates.forEach(d => {{
            const opt = document.createElement('option');
            opt.value = d; opt.innerText = d;
            dateSelect.appendChild(opt);
        }});

        const regionSelect = document.getElementById('regionSelect');
        regions.forEach(r => {{
            const opt = document.createElement('option');
            opt.value = r; opt.innerText = r;
            if (r === '中部地區') opt.selected = true;
            regionSelect.appendChild(opt);
        }});

        function getColor(temp) {{
            if (temp < 15) return '#2c7bb6';
            if (temp < 20) return '#5aa2cf';
            if (temp < 25) return '#7fcdbb';
            if (temp < 28) return '#fee08b';
            if (temp < 32) return '#fdae61';
            return '#d73027';
        }}

        function updateMap() {{
            markersLayer.clearLayers();
            const curDate = dateSelect.value;
            const dateRows = allData.filter(d => d.dataDate === curDate);

            dateRows.forEach(row => {{
                const coord = regionCoords[row.regionName];
                if (!coord) return;
                const avgT = ((row.mint + row.maxt) / 2).toFixed(1);
                const color = getColor(avgT);

                const circle = L.circleMarker([coord.lat, coord.lon], {{
                    radius: 25,
                    fillColor: color,
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.9
                }}).addTo(markersLayer);

                circle.bindPopup(`
                    <div style="font-family:sans-serif; min-width:130px; color:#0f172a;">
                        <h3 style="margin:0 0 4px 0; color:#1e3a8a;">${{row.regionName}}</h3>
                        <b>日期：</b>${{row.dataDate}}<br/>
                        <b>最高溫：</b><span style="color:#ef4444; font-weight:bold;">${{row.maxt}}°C</span><br/>
                        <b>最低溫：</b><span style="color:#2563eb; font-weight:bold;">${{row.mint}}°C</span><br/>
                        <b>平均溫：</b><b>${{avgT}}°C</b>
                    </div>
                `);

                const label = L.marker([coord.lat, coord.lon], {{
                    icon: L.divIcon({{
                        html: `<div style="font-weight:900; color:#ffffff; text-shadow:0 1px 3px #000; font-size:13px; text-align:center; transform:translate(-50%, -50%);">${{Math.round(avgT)}}°</div>`,
                        className: ''
                    }})
                }}).addTo(markersLayer);
            }});
        }}

        function updateSidePanel() {{
            const curRegion = regionSelect.value;
            const regionRows = allData.filter(d => d.regionName === curRegion).sort((a,b) => a.dataDate.localeCompare(b.dataDate));
            if (regionRows.length === 0) return;

            document.getElementById('kpiTitle').innerText = `📊 ${{curRegion}} - 即時指標`;
            const first = regionRows[0];
            const avg = ((first.mint + first.maxt) / 2).toFixed(1);
            const diff = (first.maxt - first.mint).toFixed(1);

            document.getElementById('maxTempVal').innerText = `${{first.maxt}}°C`;
            document.getElementById('minTempVal').innerText = `${{first.mint}}°C`;
            document.getElementById('avgTempVal').innerText = `${{avg}}°C`;
            document.getElementById('diffTempVal').innerText = `${{diff}}°C`;

            // 更新表格
            const tb = document.getElementById('tableBody');
            tb.innerHTML = '';
            regionRows.forEach(r => {{
                const rAvg = ((r.mint + r.maxt) / 2).toFixed(1);
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${{r.dataDate.slice(5)}}</td><td style="color:#60a5fa;">${{r.mint}}°</td><td style="color:#f87171;">${{r.maxt}}°</td><td>${{rAvg}}°</td>`;
                tb.appendChild(tr);
            }});

            // 更新折線圖
            const ctx = document.getElementById('tempChart').getContext('2d');
            const labels = regionRows.map(r => r.dataDate.slice(5));
            const maxts = regionRows.map(r => r.maxt);
            const mints = regionRows.map(r => r.mint);

            if (chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{ label: '最高溫', data: maxts, borderColor: '#f87171', backgroundColor: 'rgba(248,113,113,0.1)', tension: 0.3, pointRadius: 4 }},
                        {{ label: '最低溫', data: mints, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', tension: 0.3, pointRadius: 4 }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }} }},
                    scales: {{
                        x: {{ ticks: {{ color: '#94a3b8', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                        y: {{ ticks: {{ color: '#94a3b8', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
                    }}
                }}
            }});
        }}

        function onDateChange() {{ updateMap(); }}
        function onRegionChange() {{ updateSidePanel(); }}

        updateMap();
        updateSidePanel();
    </script>
</body>
</html>"""
    return html


# ==============================================================================
# Vercel Entrypoint Handler (符合 WSGI 標準)
# ==============================================================================

def app(environ, start_response):
    """Vercel Python Runtime 入口點 (導出頂級 "app" 與 "handler" 變數)"""
    status = '200 OK'
    headers = [
        ('Content-type', 'text/html; charset=utf-8'),
        ('Cache-Control', 'public, max-age=60')
    ]
    start_response(status, headers)
    body = generate_vercel_html()
    return [body.encode('utf-8')]

# Vercel 所要求的頂級入口點別名
handler = app
application = app


# ==============================================================================
# 2. 本機 / Streamlit Cloud 執行函式
# ==============================================================================

def run_streamlit_app():
    import streamlit as st
    import matplotlib.pyplot as plt
    import folium
    from streamlit_folium import st_folium

    database.init_db()

    st.set_page_config(
        page_title="台灣即時氣象地圖 - AIot_L3_CWA_HW1",
        page_icon="🌀",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
    <style>
        .stApp { background-color: #0b0f19; color: #f1f5f9; }
        header[data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        .block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; max-width: 98% !important; }
        .windy-topbar {
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px; padding: 12px 20px; margin-bottom: 14px; backdrop-filter: blur(12px);
        }
        .topbar-title { font-size: 1.45rem; font-weight: 800; color: #38bdf8; display: flex; align-items: center; gap: 10px; }
        .topbar-badge {
            background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 4px 12px; border-radius: 9999px; font-size: 0.82rem; font-weight: 600;
        }
        .glass-card {
            background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px; padding: 14px; margin-bottom: 12px; backdrop-filter: blur(14px);
        }
        .card-header {
            font-size: 0.92rem; font-weight: 700; color: #e2e8f0; margin-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 6px;
        }
        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .metric-cell {
            background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px; padding: 8px 10px; text-align: center;
        }
        .metric-label { font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px; }
        .metric-val { font-size: 1.25rem; font-weight: 800; color: #f8fafc; }
        .windy-gradient-bar {
            height: 10px; width: 100%; border-radius: 9999px;
            background: linear-gradient(to right, #2c7bb6, #5aa2cf, #abd9e9, #7fcdbb, #d9ef8b, #fee08b, #fdae61, #f46d43, #d73027);
        }
        .scale-ticks { display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; font-family: monospace; margin-top: 4px; }
        .bottom-deploy-bar {
            margin-top: 14px; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; font-size: 0.86rem;
        }
        .deploy-link-btn {
            text-decoration: none; padding: 6px 14px; border-radius: 6px; font-weight: 600; font-size: 0.82rem;
            border: 1px solid rgba(255, 255, 255, 0.15); color: #e2e8f0; background: rgba(255, 255, 255, 0.05);
        }
    </style>
    """, unsafe_allow_html=True)

    available_regions = database.get_distinct_regions()
    if not available_regions:
        update_weather_pipeline()
        available_regions = database.get_distinct_regions()

    available_dates = database.get_all_dates()

    st.markdown("""
    <div class="windy-topbar">
        <div class="topbar-title">
            <span>🌀 台灣即時氣象地圖</span>
            <span style="font-size:0.85rem; color:#94a3b8; font-weight:normal;">中央氣象署開放資料即時視覺化 (HW10 類 Windy 風格)</span>
        </div>
        <div class="topbar-badge">開發者：AIot_L3_CWA_HW1</div>
    </div>
    """, unsafe_allow_html=True)

    col_map, col_side = st.columns([7.2, 2.8], gap="small")

    with col_side:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">🎛️ 圖層與底圖控制</div>', unsafe_allow_html=True)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            basemap_mode = st.radio("地圖風格：", ["深色 (Windy)", "街道圖 (OSM)"], index=0, label_visibility="collapsed")
        with col_b2:
            show_labels = st.checkbox("顯示數字標籤", value=True)
            if st.button("🔄 刷新 API", use_container_width=True):
                update_weather_pipeline()
                st.rerun()

        selected_date = st.selectbox("📅 預報日期：", available_dates, index=0 if available_dates else None)
        default_idx = available_regions.index("中部地區") if "中部地區" in available_regions else 0
        selected_region = st.selectbox("📍 預報地區：", available_regions, index=default_idx)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_map:
        df_date = database.get_forecast_by_date(selected_date)
        if "深色" in basemap_mode:
            tiles_url = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
            attr = "Esri Dark Canvas"
        else:
            tiles_url = "OpenStreetMap"
            attr = "OpenStreetMap"

        m = folium.Map(location=[23.72, 120.95], zoom_start=7, tiles=tiles_url, attr=attr)

        for _, row in df_date.iterrows():
            r_name = row['regionName']
            if r_name in REGION_COORDINATES:
                coord = REGION_COORDINATES[r_name]
                avg_t = round((row['mint'] + row['maxt']) / 2, 1)
                color = get_windy_temp_color(avg_t)

                folium.CircleMarker(
                    location=[coord['lat'], coord['lon']],
                    radius=25,
                    popup=f"{r_name}: {avg_t}°C (Min: {row['mint']}° / Max: {row['maxt']}°)",
                    tooltip=f"{r_name}: 平均 {avg_t}°C",
                    color="#ffffff",
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    weight=2
                ).add_to(m)

                if show_labels:
                    folium.Marker(
                        location=[coord['lat'], coord['lon']],
                        icon=folium.DivIcon(
                            html=f"""<div style="font-weight:900; color:#fff; text-shadow: 0 1px 3px #000; font-size:13px; text-align:center; transform: translate(-50%, -50%); pointer-events:none;">{int(round(avg_t))}°</div>"""
                        )
                    ).add_to(m)

        st_folium(m, width=None, height=690, use_container_width=True)

        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 18px; margin-top:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.82rem; font-weight:700; color:#e2e8f0;">🎨 溫度色階 (Windy Color Scale)</span>
                <span style="font-size:0.75rem; color:#94a3b8;">單位: °C</span>
            </div>
            <div class="windy-gradient-bar"></div>
            <div class="scale-ticks">
                <span>5°</span><span>10°</span><span>15°</span><span>20°</span><span>24°</span><span>28°</span><span>32°</span><span>36°+</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_side:
        df_region = database.get_forecast_by_region(selected_region)
        first_day = df_region.iloc[0] if not df_region.empty else None

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📊 {selected_region} - 即時數值</div>', unsafe_allow_html=True)
        if first_day is not None:
            avg_t = round((first_day['mint'] + first_day['maxt']) / 2, 1)
            diff_t = round(first_day['maxt'] - first_day['mint'], 1)
            st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-cell"><div class="metric-label">最高溫</div><div class="metric-val" style="color:#f87171;">{first_day['maxt']}°C</div></div>
                <div class="metric-cell"><div class="metric-label">最低溫</div><div class="metric-val" style="color:#60a5fa;">{first_day['mint']}°C</div></div>
                <div class="metric-cell"><div class="metric-label">平均溫</div><div class="metric-val" style="color:#38bdf8;">{avg_t}°C</div></div>
                <div class="metric-cell"><div class="metric-label">溫差</div><div class="metric-val" style="color:#fbbf24;">{diff_t}°C</div></div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📈 {selected_region} - 7日走勢 (HW10)</div>', unsafe_allow_html=True)
        if not df_region.empty:
            fig, ax = plt.subplots(figsize=(4.8, 2.4), dpi=130)
            fig.patch.set_facecolor('#0f172a')
            ax.set_facecolor('#1e293b')
            dates = df_region['dataDate'].apply(lambda x: x[5:]).tolist()
            ax.plot(dates, df_region['maxt'].tolist(), marker='o', markersize=4, color='#f87171', linewidth=1.8, label='最高溫')
            ax.plot(dates, df_region['mint'].tolist(), marker='o', markersize=4, color='#38bdf8', linewidth=1.8, label='最低溫')
            ax.tick_params(colors='#94a3b8', labelsize=7.5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, linestyle=':', alpha=0.25, color='#cbd5e1')
            ax.legend(loc='upper right', fontsize=7, facecolor='#0f172a', labelcolor='#e2e8f0')
            plt.tight_layout()
            st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📋 {selected_region} - 一週數據表</div>', unsafe_allow_html=True)
        if not df_region.empty:
            simple_df = df_region[['dataDate', 'mint', 'maxt']].copy()
            simple_df.columns = ['日期', '最低', '最高']
            simple_df['均溫'] = ((simple_df['最低'] + simple_df['最高']) / 2).round(1)
            st.dataframe(simple_df, height=170, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="bottom-deploy-bar">
        <div>🚀 <b>專案部署 (Deploy Center)</b> ｜ GitHub: <code>chayi27/AIot_L3_CWA_HW1</code></div>
        <a href="https://github.com/chayi27/AIot_L3_CWA_HW1" target="_blank" class="deploy-link-btn">📂 開啟 GitHub 倉庫</a>
    </div>
    """, unsafe_allow_html=True)


# 判斷是否由 Streamlit 執行
if __name__ == "__main__":
    run_streamlit_app()
else:
    # 檢查是否在 Streamlit 執行緒中
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            run_streamlit_app()
    except Exception:
        pass
