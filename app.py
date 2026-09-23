"""
專案名稱：Taiwan Weather Forecast - AIot_L3_CWA_HW1
模組說明：Streamlit 互動式天氣預報 Web 應用程式 (app.py)
版面特色：以台灣地圖為視覺核心大區域 (Hero Map)，右側搭配緊湊精緻的卡片型小區塊 (Data Blocks)
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

# 設定頁面配置 (寬螢幕、側邊欄預設收合以放大地圖可視範圍)
st.set_page_config(
    page_title="Taiwan Weather Forecast - AIot_L3_CWA_HW1",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 套用現代化儀表板卡片樣式
st.markdown("""
<style>
    /* 全域字體與間距微調 */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
        color: white;
        padding: 14px 24px;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }
    .header-badge {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.88rem;
        font-weight: 600;
    }
    /* 卡片容器樣式 */
    .ui-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    }
    .ui-card-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    /* 溫度圖例橫條 */
    .legend-bar {
        display: flex;
        justify-content: space-around;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 8px 10px;
        margin-top: 8px;
        font-size: 0.8rem;
        font-weight: 600;
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
        return "#F59E0B"  # 黃橘色 (25-30°C)
    else:
        return "#EF4444"  # 紅色 (>30°C)


def main():
    database.init_db()

    # 側邊欄控制面板
    with st.sidebar:
        st.markdown("### ⚙️ 系統設定")
        st.markdown("**作者：`AIot_L3_CWA_HW1`**")
        st.markdown("---")

        if st.button("🔄 立即從 CWA API 更新資料", use_container_width=True):
            with st.spinner("連線中央氣象署抓取最新預報中..."):
                update_weather_pipeline()
                st.success("氣象資料已更新完畢！")
                st.rerun()

        available_regions = database.get_distinct_regions()
        if not available_regions:
            with st.spinner("正在進行初次資料載入..."):
                update_weather_pipeline()
                available_regions = database.get_distinct_regions()

        available_dates = database.get_all_dates()

        st.markdown("#### 🎯 地圖與數據過濾")
        selected_date = st.selectbox(
            "📅 選擇地圖日期 (Select Date):",
            available_dates,
            index=0 if available_dates else None
        )

        default_region_idx = available_regions.index("中部地區") if "中部地區" in available_regions else 0
        selected_region = st.selectbox(
            "📍 選擇右側預報地區 (Select Region):",
            available_regions,
            index=default_region_idx
        )

        st.markdown("---")
        st.caption("• 採用 OpenStreetMap 高清免金鑰圖資")
        st.caption("• 地圖大面積展示六大分區氣候氣泡")
        st.caption("• 點擊地圖氣泡可查看當日各區溫度詳情")

    # 頂部全寬橫幅 (Top Banner)
    st.markdown(f"""
    <div class="top-header">
        <div class="header-title">🌤️ 台灣天氣預報儀表板 (Taiwan Weather Forecast)</div>
        <div class="header-badge">開發者：AIot_L3_CWA_HW1 ｜ 預報日期：{selected_date}</div>
    </div>
    """, unsafe_allow_html=True)

    # 核心排版：左側【大幅地圖核心區 (7.5)】 vs 右側【緊湊資訊小模組 (4.5)】
    col_map, col_side = st.columns([7.5, 4.5], gap="large")

    # ==================== 【左側主區塊】：大幅台灣地圖 ====================
    with col_map:
        st.markdown("##### 🗺️ 台灣分區氣候互動地圖 (主視野)")

        # 讀取該日期所有地區氣溫
        df_date = database.get_forecast_by_date(selected_date)

        # 建立大視角 Folium 地圖，縮放級別調整為最適合台灣全島展開的大小
        m = folium.Map(
            location=[23.70, 120.95],
            zoom_start=7,
            tiles="OpenStreetMap"
        )

        # 繪製各分區標記 (大尺寸彩球 + 數值)
        for _, row in df_date.iterrows():
            r_name = row['regionName']
            if r_name in REGION_COORDINATES:
                coord = REGION_COORDINATES[r_name]
                avg_t = round((row['mint'] + row['maxt']) / 2, 1)
                color = get_temp_color(avg_t)

                popup_content = f"""
                <div style="font-family:sans-serif; min-width:140px; padding:4px;">
                    <b style="font-size:16px; color:#1E3A8A;">{r_name}</b><br/>
                    <span style="color:#64748B; font-size:12px;">日期：{row['dataDate']}</span>
                    <hr style="margin:6px 0; border:0; border-top:1px solid #CBD5E1;"/>
                    <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                        <span>最高溫：</span><b style="color:#EF4444;">{row['maxt']}°C</b>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                        <span>最低溫：</span><b style="color:#2563EB;">{row['mint']}°C</b>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:4px; padding-top:4px; border-top:1px dashed #E2E8F0;">
                        <span>平均溫：</span><b style="color:#0F172A; font-size:14px;">{avg_t}°C</b>
                    </div>
                </div>
                """

                # 著色氣泡
                folium.CircleMarker(
                    location=[coord['lat'], coord['lon']],
                    radius=26,  # 增大圓圈
                    popup=folium.Popup(popup_content, max_width=250),
                    tooltip=f"{r_name}：平均 {avg_t}°C (點擊查看詳情)",
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    weight=3
                ).add_to(m)

                # 溫度數字標籤
                folium.Marker(
                    location=[coord['lat'], coord['lon']],
                    icon=folium.DivIcon(
                        html=f"""<div style="font-weight:800; color:white; text-shadow: 1px 1px 3px #000; font-size:13px; text-align:center; transform: translate(-50%, -50%);">{avg_t}°</div>"""
                    )
                ).add_to(m)

        # 輸出高寬比充實的大尺寸地圖
        st_folium(m, width=760, height=660)

        # 地圖下方溫度圖例橫條 (步驟 17)
        st.markdown("""
        <div class="legend-bar">
            <span style="color:#2563EB;">● &lt; 20°C (藍: 寒冷/偏涼)</span>
            <span style="color:#10B981;">● 20°C ~ 25°C (綠: 舒適宜人)</span>
            <span style="color:#F59E0B;">● 25°C ~ 30°C (黃: 溫暖舒適)</span>
            <span style="color:#EF4444;">● &gt; 30°C (紅: 炎熱高溫)</span>
        </div>
        """, unsafe_allow_html=True)

    # ==================== 【右側小模組區塊】：精緻資訊小卡 ====================
    with col_side:
        df_region = database.get_forecast_by_region(selected_region)
        first_day = df_region.iloc[0] if not df_region.empty else None

        # 小 Block 1：當前地區氣象數值卡 (4宮格小指標)
        st.markdown(f"##### 📌 {selected_region} - 即時氣候指標")
        if first_day is not None:
            avg_t = round((first_day['mint'] + first_day['maxt']) / 2, 1)
            diff_t = round(first_day['maxt'] - first_day['mint'], 1)

            m1, m2 = st.columns(2)
            with m1:
                st.metric("🔥 今日最高溫", f"{first_day['maxt']} °C")
                st.metric("🌡️ 預估日溫差", f"{diff_t} °C")
            with m2:
                st.metric("❄️ 今日最低溫", f"{first_day['mint']} °C")
                st.metric("🌤️ 今日平均溫", f"{avg_t} °C")

        st.markdown("---")

        # 小 Block 2：一週氣溫折線圖 (精緻緊湊)
        st.markdown(f"##### 📈 {selected_region} - 一週高低溫走勢")
        if not df_region.empty:
            fig, ax = plt.subplots(figsize=(5.5, 2.7), dpi=130)

            dates = df_region['dataDate'].apply(lambda x: x[5:]).tolist()
            maxts = df_region['maxt'].tolist()
            mints = df_region['mint'].tolist()

            ax.plot(dates, maxts, marker='o', markersize=5, color='#EF4444', linewidth=2, label='最高溫 MaxT')
            ax.plot(dates, mints, marker='o', markersize=5, color='#2563EB', linewidth=2, label='最低溫 MinT')

            for i, (d, mx, mn) in enumerate(zip(dates, maxts, mints)):
                ax.text(i, mx + 0.4, f"{int(mx)}°", ha='center', va='bottom', fontsize=8, fontweight='bold', color='#B91C1C')
                ax.text(i, mn - 0.7, f"{int(mn)}°", ha='center', va='top', fontsize=8, fontweight='bold', color='#1D4ED8')

            ax.set_ylim(min(mints) - 3, max(maxts) + 3)
            ax.set_ylabel("°C", fontsize=9)
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.legend(loc='upper right', fontsize=8, frameon=True)
            plt.xticks(fontsize=8)
            plt.yticks(fontsize=8)
            plt.tight_layout()

            st.pyplot(fig)

        st.markdown("---")

        # 小 Block 3：一週預報精簡表格
        st.markdown(f"##### 📋 {selected_region} - 一週預報數據表")
        if not df_region.empty:
            simple_df = df_region[['dataDate', 'mint', 'maxt']].copy()
            simple_df.columns = ['日期', '最低溫', '最高溫']
            simple_df['均溫'] = ((simple_df['最低溫'] + simple_df['最高溫']) / 2).round(1)
            st.dataframe(simple_df, height=180, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
