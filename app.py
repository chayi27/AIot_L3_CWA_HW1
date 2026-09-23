"""
專案名稱：Taiwan Weather Forecast - AIot_L3_CWA_HW1
模組說明：Streamlit 互動式天氣預報 Web 應用程式 (app.py)
步驟對應：步驟 11 ~ 19 (Web 介面、SQL 讀取、地區選單、折線圖、表格、Folium 地圖、Dashboard 整合)
"""

import sys
import datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

# 確保輸出支援 UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 匯入專案自訂模組
import database
from get_weather import update_weather_pipeline, REGION_COORDINATES

# 設定頁面配置 (步驟 11)
st.set_page_config(
    page_title="Taiwan Weather Forecast - AIot_L3_CWA_HW1",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 套用現代化自訂樣式 (CSS)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .badge-author {
        display: inline-block;
        background-color: #2563EB;
        color: white;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .legend-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 10px;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)


def get_temp_color(avg_temp: float) -> str:
    """依平均溫度區間著色 (步驟 17: <20°C 藍, 20-25°C 綠, 25-30°C 橘黃, >30°C 紅)"""
    if avg_temp < 20.0:
        return "#2563EB"  # 藍色 (<20°C)
    elif 20.0 <= avg_temp < 25.0:
        return "#10B981"  # 綠色 (20-25°C)
    elif 25.0 <= avg_temp <= 30.0:
        return "#F59E0B"  # 黃色/橘色 (25-30°C)
    else:
        return "#EF4444"  # 紅色 (>30°C)


def main():
    # 初始化資料庫檢查
    database.init_db()

    # 側邊欄控制面板
    with st.sidebar:
        st.markdown("### ⚙️ 控制面板")
        st.markdown('<span class="badge-author">作者：AIot_L3_CWA_HW1</span>', unsafe_allow_html=True)
        st.markdown("---")

        # 手動更新氣象資料按鈕
        if st.button("🔄 立即從 CWA API 更新資料", use_container_width=True):
            with st.spinner("正在連線中央氣象署抓取最新預報..."):
                update_weather_pipeline()
                st.success("氣象資料已更新完畢！")
                st.rerun()

        # 取得所有可用分區 (步驟 10、13)
        available_regions = database.get_distinct_regions()

        # 若無資料則先自動抓一次
        if not available_regions:
            with st.spinner("偵測到資料庫為空，正在進行首次資料同步..."):
                update_weather_pipeline()
                available_regions = database.get_distinct_regions()

        # 地區下拉選單 (步驟 13)
        default_index = available_regions.index("中部地區") if "中部地區" in available_regions else 0
        selected_region = st.selectbox(
            "📍 選擇預報地區 (Select Region):",
            available_regions,
            index=default_index
        )

        # 日期清單 (步驟 18)
        available_dates = database.get_all_dates()
        selected_date = st.selectbox(
            "📅 選擇地圖日期 (Select Date):",
            available_dates,
            index=0 if available_dates else None
        )

        st.markdown("---")
        st.markdown("#### 📌 HW10 核心規範")
        st.caption("1. 介接 CWA API 六大分區一週氣溫")
        st.caption("2. 解析提取 MinT 與 MaxT")
        st.caption("3. 存入 SQLite data.db (防重複寫入)")
        st.caption("4. Streamlit 透過 SQL 查詢顯示折線圖與表格")
        st.caption("5. 進階：Folium 台灣互動地圖依溫度變色")

    # 主畫面標題 (步驟 16、19)
    st.markdown('<div class="main-title">🌤️ 台灣天氣預報 Taiwan Weather Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">從氣象資料到互動式天氣預報應用 | 開發者：<b>AIot_L3_CWA_HW1</b></div>', unsafe_allow_html=True)

    # 讀取所選地區之一週資料 (步驟 12: 使用 SQL 從 SQLite 讀取)
    df_region = database.get_forecast_by_region(selected_region)

    if df_region.empty:
        st.warning(f"目前查無「{selected_region}」的氣候資料，請點擊左側「🔄 立即從 CWA API 更新資料」。")
        return

    # 摘要指標卡片 (KPI Metrics)
    col1, col2, col3, col4 = st.columns(4)
    first_day = df_region.iloc[0]
    avg_t = round((first_day['mint'] + first_day['maxt']) / 2, 1)
    temp_diff = round(first_day['maxt'] - first_day['mint'], 1)

    with col1:
        st.metric("目前預報地區", f"{selected_region}")
    with col2:
        st.metric("🔥 今日最高溫", f"{first_day['maxt']} °C")
    with col3:
        st.metric("❄️ 今日最低溫", f"{first_day['mint']} °C")
    with col4:
        st.metric("🌡️ 預估日溫差", f"{temp_diff} °C", delta=f"均溫 {avg_t} °C")

    st.markdown("---")

    # 雙欄並列版面配置：左邊台灣互動地圖，右邊氣溫折線圖與數據表 (對應作業成果展現完整 Dashboard)
    col_left, col_right = st.columns([1, 1], gap="medium")

    # ==================== 左欄：台灣互動天氣地圖 (步驟 17, 18) ====================
    with col_left:
        st.subheader(f"🗺️ 台灣互動天氣地圖 (步驟 17, 18)")
        st.caption(f"📅 預報日期：**{selected_date}**（可在左側側邊欄切換不同日期）")

        # 讀取該日期所有分區資料
        df_date = database.get_forecast_by_date(selected_date)

        # 建立 Folium 地圖，採用穩定的 OpenStreetMap 免金鑰圖層，中心設在台灣
        m = folium.Map(
            location=[23.75, 120.95],
            zoom_start=7,
            tiles="OpenStreetMap"
        )

        # 將 6 大分區氣候點標註在地圖上
        for _, row in df_date.iterrows():
            r_name = row['regionName']
            if r_name in REGION_COORDINATES:
                coord = REGION_COORDINATES[r_name]
                avg_temp_val = round((row['mint'] + row['maxt']) / 2, 1)
                color = get_temp_color(avg_temp_val)

                popup_html = f"""
                <div style="font-family:sans-serif; min-width:130px; font-size:13px;">
                    <b style="font-size:15px; color:#1E3A8A;">{r_name}</b><br/>
                    <span style="color:#6B7280;">日期：{row['dataDate']}</span>
                    <hr style="margin:4px 0;"/>
                    最高溫：<span style="color:#EF4444; font-weight:bold;">{row['maxt']}°C</span><br/>
                    最低溫：<span style="color:#2563EB; font-weight:bold;">{row['mint']}°C</span><br/>
                    平均溫：<b>{avg_temp_val}°C</b>
                </div>
                """

                # 著色氣泡標記
                folium.CircleMarker(
                    location=[coord['lat'], coord['lon']],
                    radius=20,
                    popup=folium.Popup(popup_html, max_width=240),
                    tooltip=f"{r_name}：平均 {avg_temp_val}°C (最低 {row['mint']}° / 最高 {row['maxt']}°)",
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.8,
                    weight=2
                ).add_to(m)

                # 在氣泡中央顯示平均溫度文字標籤
                folium.Marker(
                    location=[coord['lat'], coord['lon']],
                    icon=folium.DivIcon(
                        html=f"""<div style="font-weight:bold; color:white; text-shadow: 1px 1px 2px #000; font-size:11px; text-align:center; transform: translate(-50%, -50%);">{avg_temp_val}°</div>"""
                    )
                ).add_to(m)

        # 渲染 Folium 地圖 (自適應寬度)
        st_folium(m, width=540, height=450)

        # 溫度色階圖例 (步驟 17 評分標準)
        st.markdown("""
        <div class="legend-box">
            <b>🎨 平均溫度分級著色圖例 (步驟 17)：</b><br/>
            <span style="color:#2563EB; font-weight:bold;">● &lt; 20°C (藍色: 寒冷/偏涼)</span> &nbsp;|&nbsp; 
            <span style="color:#10B981; font-weight:bold;">● 20°C ~ 25°C (綠色: 舒適)</span><br/>
            <span style="color:#F59E0B; font-weight:bold;">● 25°C ~ 30°C (黃色: 溫暖)</span> &nbsp;|&nbsp; 
            <span style="color:#EF4444; font-weight:bold;">● &gt; 30°C (紅色: 炎熱)</span>
        </div>
        """, unsafe_allow_html=True)

    # ==================== 右欄：折線圖與資料表 (步驟 14, 15) ====================
    with col_right:
        st.subheader(f"📈 {selected_region} - 一週氣溫走勢圖 (步驟 14)")

        # 繪製折線圖 (步驟 14: 最高溫紅線 MaxT, 最低溫藍線 MinT)
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=120)

        dates = df_region['dataDate'].apply(lambda x: x[5:]).tolist()  # MM-DD
        maxts = df_region['maxt'].tolist()
        mints = df_region['mint'].tolist()

        # 畫線與端點標記
        ax.plot(dates, maxts, marker='o', color='#EF4444', linewidth=2.5, label='最高氣溫 (MaxT)')
        ax.plot(dates, mints, marker='o', color='#2563EB', linewidth=2.5, label='最低氣溫 (MinT)')

        # 在每個折點上方標記數值
        for i, (d, mx, mn) in enumerate(zip(dates, maxts, mints)):
            ax.text(i, mx + 0.4, f"{mx}°", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#B91C1C')
            ax.text(i, mn - 0.7, f"{mn}°", ha='center', va='top', fontsize=9, fontweight='bold', color='#1D4ED8')

        # 圖表修飾
        y_min = min(mints) - 3
        y_max = max(maxts) + 3
        ax.set_ylim(y_min, y_max)
        ax.set_ylabel("氣溫 (°C)", fontsize=11)
        ax.set_title(f"{selected_region} 一週高低氣溫預報", fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='upper right', frameon=True)

        # 解決中文顯示支援
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        st.pyplot(fig)

        st.markdown("#### 📋 清楚呈現一週資料 (步驟 15)")
        # 整理呈現表格
        display_df = df_region[['dataDate', 'mint', 'maxt']].copy()
        display_df.columns = ['預報日期', '最低溫 (°C)', '最高溫 (°C)']
        display_df['平均溫 (°C)'] = ((display_df['最低溫 (°C)'] + display_df['最高溫 (°C)']) / 2).round(1)
        display_df['日溫差 (°C)'] = (display_df['最高溫 (°C)'] - display_df['最低溫 (°C)']).round(1)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 頁面下方：當日全台分區總覽表格
    st.markdown("---")
    st.subheader(f"📊 {selected_date} 全台六大分區氣溫對照表")
    summary_all = df_date[['regionName', 'mint', 'maxt']].copy()
    summary_all.columns = ['分區名稱', '最低氣溫 (°C)', '最高氣溫 (°C)']
    summary_all['平均氣溫 (°C)'] = ((summary_all['最低氣溫 (°C)'] + summary_all['最高氣溫 (°C)']) / 2).round(1)
    st.dataframe(summary_all, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
