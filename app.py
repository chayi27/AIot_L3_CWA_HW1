"""
專案名稱：台灣即時氣象地圖 (Taiwan Weather Map) - AIot_L3_CWA_HW1
參考設計：taiwan-weather-map.vercel.app (類 Windy 風格極致深色互動視覺化)
功能架構：CWA OpenData API × SQLite (data.db) × Streamlit × Folium
版面設計：以大幅台灣氣候地圖為全屏視覺核心 (佔比 ~70%)，右側以毛玻璃小模組 (Glassmorphic Blocks) 呈現圖層控制、折線圖與數據表。
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

# 設定頁面配置 (預設收起側邊欄，讓全域主視覺面積最大化)
st.set_page_config(
    page_title="台灣即時氣象地圖 - AIot_L3_CWA_HW1",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 套用深色系類 Windy / Next.js 毛玻璃科技感 CSS
st.markdown("""
<style>
    /* 深色背景全域配置 */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    
    /* 隱藏 Streamlit 頂部預設會遮擋畫面的 Deploy 按鈕與原生 Header */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
    
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
        max-width: 98% !important;
    }
    
    /* 頂部全寬導覽條 */
    .windy-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 20px;
        margin-bottom: 14px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .topbar-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 10px;
        letter-spacing: -0.02em;
    }
    .topbar-subtitle {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-left: 6px;
    }
    .topbar-badge {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* 右側懸浮小模組卡片 (Glassmorphism Blocks) */
    .glass-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        backdrop-filter: blur(14px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    .card-header {
        font-size: 0.92rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 6px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        padding-bottom: 6px;
    }
    
    /* 指標小數字格子 */
    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }
    .metric-cell {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 8px 10px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 2px;
    }
    .metric-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #f8fafc;
    }

    /* 類 Windy / taiwan-weather-map 漸層彩虹溫度色階尺 */
    .windy-gradient-bar {
        height: 10px;
        width: 100%;
        border-radius: 9999px;
        background: linear-gradient(to right, #2c7bb6, #5aa2cf, #abd9e9, #7fcdbb, #d9ef8b, #fee08b, #fdae61, #f46d43, #d73027);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .scale-ticks {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #94a3b8;
        font-family: monospace;
        margin-top: 4px;
    }

    /* 移至畫面下方的 Deploy 部署資訊列 */
    .bottom-deploy-bar {
        margin-top: 14px;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 10px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.86rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    .deploy-link-btn {
        text-decoration: none;
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #e2e8f0;
        background: rgba(255, 255, 255, 0.05);
        transition: all 0.2s ease;
    }
    .deploy-link-btn:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #38bdf8;
    }
    .deploy-action-btn {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white !important;
        border: 1px solid #3b82f6;
    }
</style>
""", unsafe_allow_html=True)


def get_windy_temp_color(temp: float) -> str:
    """
    符合 taiwan-weather-map 與 CWA 標準之平滑氣溫色階
    <15 藍 / 15-20 水藍 / 20-25 綠青 / 25-28 溫暖黃 / 28-32 橘紅 / >32 鮮紅
    """
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


def main():
    database.init_db()

    # 確保資料存在
    available_regions = database.get_distinct_regions()
    if not available_regions:
        with st.spinner("首次啟動，正在載入中央氣象署資料..."):
            update_weather_pipeline()
            available_regions = database.get_distinct_regions()

    available_dates = database.get_all_dates()

    # ==================== 頂部導航橫條 (Windy-like Top Bar) ====================
    st.markdown("""
    <div class="windy-topbar">
        <div class="topbar-title">
            <span>🌀 台灣即時氣象地圖</span>
            <span class="topbar-subtitle">中央氣象署開放資料即時視覺化 (HW10 類 Windy 風格)</span>
        </div>
        <div class="topbar-badge">開發者：AIot_L3_CWA_HW1</div>
    </div>
    """, unsafe_allow_html=True)

    # ==================== 核心大版面排版 ====================
    # 左側：大幅台灣地圖 (佔比 ~72%) ｜ 右側：小模組面板 (佔比 ~28%)
    col_map, col_side = st.columns([7.2, 2.8], gap="small")

    # ------------------ 右側小模組的互動控制 (先宣告以供地圖讀取) ------------------
    with col_side:
        # [小 Block 1]：圖層與底圖控制
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">🎛️ 圖層與底圖控制</div>', unsafe_allow_html=True)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            basemap_mode = st.radio(
                "地圖底圖風格：",
                ["深色 (Windy)", "街道圖 (OSM)"],
                index=0,
                horizontal=False,
                label_visibility="collapsed"
            )
        with col_b2:
            show_labels = st.checkbox("顯示氣溫數字標籤", value=True)
            if st.button("🔄 刷新 API", use_container_width=True):
                with st.spinner("連線氣象署..."):
                    update_weather_pipeline()
                    st.rerun()

        selected_date = st.selectbox(
            "📅 選擇預報日期：",
            available_dates,
            index=0 if available_dates else None
        )

        default_reg_idx = available_regions.index("中部地區") if "中部地區" in available_regions else 0
        selected_region = st.selectbox(
            "📍 選擇預報地區：",
            available_regions,
            index=default_reg_idx
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== 【左側核心大區塊】：超大幅台灣氣象地圖 ====================
    with col_map:
        df_date = database.get_forecast_by_date(selected_date)

        # 依選擇切換底圖 (深色高科技 vs 標準街道圖)
        if "深色" in basemap_mode:
            # 採用全球最高品質無須 API Key 之 Esri World Dark Gray 高清圖資
            tiles_url = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
            attribution = "Esri Dark Canvas"
        else:
            tiles_url = "OpenStreetMap"
            attribution = "OpenStreetMap"

        # 建立大視角地圖，中心設定在台灣本島中央
        m = folium.Map(
            location=[23.72, 120.95],
            zoom_start=7,
            tiles=tiles_url,
            attr=attribution,
            zoom_control=True
        )

        # 標註六大分區氣溫彩球
        for _, row in df_date.iterrows():
            r_name = row['regionName']
            if r_name in REGION_COORDINATES:
                coord = REGION_COORDINATES[r_name]
                avg_t = round((row['mint'] + row['maxt']) / 2, 1)
                color = get_windy_temp_color(avg_t)

                popup_html = f"""
                <div style="font-family:system-ui, sans-serif; background:#0f172a; color:#f8fafc; padding:10px 14px; border-radius:10px; min-width:145px; box-shadow:0 4px 12px rgba(0,0,0,0.5);">
                    <div style="font-size:16px; font-weight:800; color:#38bdf8; margin-bottom:2px;">{r_name}</div>
                    <div style="font-size:11px; color:#94a3b8; margin-bottom:8px;">預報日期：{row['dataDate']}</div>
                    <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:6px; font-size:13px;">
                        <div style="margin-bottom:3px;">🔥 最高氣溫：<b style="color:#f87171;">{row['maxt']}°C</b></div>
                        <div style="margin-bottom:3px;">❄️ 最低氣溫：<b style="color:#60a5fa;">{row['mint']}°C</b></div>
                        <div style="border-top:1px dashed rgba(255,255,255,0.15); margin-top:4px; padding-top:4px;">
                            🌡️ 平均溫度：<b style="color:#38bdf8; font-size:14px;">{avg_t}°C</b>
                        </div>
                    </div>
                </div>
                """

                # 著色氣泡標記 (發光圓點效果)
                folium.CircleMarker(
                    location=[coord['lat'], coord['lon']],
                    radius=25,
                    popup=folium.Popup(popup_html, max_width=260),
                    tooltip=f"{r_name}: 平均 {avg_t}°C (最高 {row['maxt']}° / 最低 {row['mint']}°)",
                    color="#ffffff",
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    weight=2
                ).add_to(m)

                # 氣溫數字標籤 (可透過控制項開關)
                if show_labels:
                    folium.Marker(
                        location=[coord['lat'], coord['lon']],
                        icon=folium.DivIcon(
                            html=f"""<div style="font-weight:900; color:#ffffff; text-shadow: 0 1px 4px #000, 0 0 2px #000; font-size:13px; text-align:center; transform: translate(-50%, -50%); pointer-events:none;">{int(round(avg_t))}°</div>"""
                        )
                    ).add_to(m)

        # 輸出 700px 高度、氣勢恢弘的全景地圖
        st_folium(m, width=None, height=690, use_container_width=True)

        # 類 Windy / taiwan-weather-map 正宗漸層溫度色階尺 (下方掛載)
        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 18px; margin-top:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.82rem; font-weight:700; color:#e2e8f0;">🎨 溫度色階 (Windy Color Scale)</span>
                <span style="font-size:0.75rem; color:#94a3b8;">單位: °C</span>
            </div>
            <div class="windy-gradient-bar"></div>
            <div class="scale-ticks">
                <span>5°</span>
                <span>10°</span>
                <span>15°</span>
                <span>20°</span>
                <span>24°</span>
                <span>28°</span>
                <span>32°</span>
                <span>36°+</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==================== 【右側小模組區塊 (續)】 ====================
    with col_side:
        df_region = database.get_forecast_by_region(selected_region)
        first_day = df_region.iloc[0] if not df_region.empty else None

        # [小 Block 2]：4宮格氣候指標
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📊 {selected_region} - 即時數值</div>', unsafe_allow_html=True)
        if first_day is not None:
            avg_t = round((first_day['mint'] + first_day['maxt']) / 2, 1)
            diff_t = round(first_day['maxt'] - first_day['mint'], 1)

            st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-cell">
                    <div class="metric-label">今日最高溫</div>
                    <div class="metric-val" style="color:#f87171;">{first_day['maxt']}°C</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">今日最低溫</div>
                    <div class="metric-val" style="color:#60a5fa;">{first_day['mint']}°C</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">平均氣溫</div>
                    <div class="metric-val" style="color:#38bdf8;">{avg_t}°C</div>
                </div>
                <div class="metric-cell">
                    <div class="metric-label">預估溫差</div>
                    <div class="metric-val" style="color:#fbbf24;">{diff_t}°C</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # [小 Block 3]：一週氣溫折線圖 (高質感深色風格)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📈 {selected_region} - 7日走勢 (HW10)</div>', unsafe_allow_html=True)
        if not df_region.empty:
            fig, ax = plt.subplots(figsize=(4.8, 2.4), dpi=130)
            fig.patch.set_facecolor('#0f172a')
            ax.set_facecolor('#1e293b')

            dates = df_region['dataDate'].apply(lambda x: x[5:]).tolist()
            maxts = df_region['maxt'].tolist()
            mints = df_region['mint'].tolist()

            ax.plot(dates, maxts, marker='o', markersize=4, color='#f87171', linewidth=1.8, label='最高溫')
            ax.plot(dates, mints, marker='o', markersize=4, color='#38bdf8', linewidth=1.8, label='最低溫')

            for i, (d, mx, mn) in enumerate(zip(dates, maxts, mints)):
                ax.text(i, mx + 0.5, f"{int(round(mx))}°", ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#fca5a5')
                ax.text(i, mn - 0.9, f"{int(round(mn))}°", ha='center', va='top', fontsize=7.5, fontweight='bold', color='#93c5fd')

            ax.set_ylim(min(mints) - 3, max(maxts) + 3)
            ax.tick_params(colors='#94a3b8', labelsize=7.5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#334155')
            ax.spines['bottom'].set_color('#334155')
            ax.grid(True, linestyle=':', alpha=0.25, color='#cbd5e1')
            ax.legend(loc='upper right', fontsize=7, facecolor='#0f172a', edgecolor='#334155', labelcolor='#e2e8f0')
            plt.tight_layout()

            st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)

        # [小 Block 4]：一週預報精簡數據表
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">📋 {selected_region} - 一週數據表</div>', unsafe_allow_html=True)
        if not df_region.empty:
            simple_df = df_region[['dataDate', 'mint', 'maxt']].copy()
            simple_df.columns = ['日期', '最低', '最高']
            simple_df['均溫'] = ((simple_df['最低'] + simple_df['最高']) / 2).round(1)
            st.dataframe(simple_df, height=170, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== 【畫面下方】：專案部署 (Deploy) 與儲存庫工具列 ====================
    st.markdown("""
    <div class="bottom-deploy-bar">
        <div style="display:flex; align-items:center; gap:14px;">
            <span style="font-size:1rem;">🚀</span>
            <div>
                <b>專案部署 (Deploy Center)</b>
                <span style="color:#94a3b8; margin-left:8px; font-size:0.8rem;">已同步至 GitHub 遠端儲存庫: <code>chayi27/AIot_L3_CWA_HW1</code> (分支: <code>main</code>)</span>
            </div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <a href="https://github.com/chayi27/AIot_L3_CWA_HW1" target="_blank" class="deploy-link-btn">
                📂 開啟 GitHub 倉庫
            </a>
            <a href="https://share.streamlit.io" target="_blank" class="deploy-link-btn deploy-action-btn">
                ☁️ 一鍵部署至 Streamlit Cloud
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
