import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 網頁配置：手機版預設收起選單，使用寬版佈局
st.set_page_config(
    page_title="樂活五線譜線上查詢器", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

st.title("📈 樂活五線譜自動生成")

# --- 2. 側邊欄：使用者輸入區 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號 (台股:2330 / 美股:AAPL)", value="2330")

# 直接使用日期選擇器
start_date = st.sidebar.date_input("起始日期", value=datetime.now() - timedelta(days=1000))
end_date = st.sidebar.date_input("結束日期", value=datetime.now())

# 手機優化按鈕：寬度滿版
submit_btn = st.sidebar.button("開始計算", use_container_width=True)

if submit_btn:
    # 確保結束日期不早於起始日期
    if start_date >= end_date:
        st.error("❌ 錯誤：起始日期必須早於結束日期")
    else:
        with st.spinner('數據計算中...'):
            # A. 處理股票代號
            base_id = stock_id.strip().upper()
            
            # B. 嘗試抓取資料 
            # 1. 先嘗試原代號 (美股優先)
            df = yf.download(base_id, start=start_date, end=end_date, progress=False)
            final_id = base_id
            
            if df.empty:
                df = yf.download(f"{base_id}.TW", start=start_date, end=end_date, progress=False)
                final_id = f"{base_id}.TW"
            
            if df.empty:
                df = yf.download(f"{base_id}.TWO", start=start_date, end=end_date, progress=False)
                final_id = f"{base_id}.TWO"

            if df.empty:
                st.error(f"❌ 找不到股票代號 '{base_id}'，或該日期區間無交易資料。")
            else:
                # --- C. 核心計算區 (動態對齊長度，修復 BUG) ---
                df = df.reset_index()
                y = df['Close'].values.squeeze()
                
                # 處理多重索引問題
                if y.ndim > 1:
                    y = y[:, 0]
                
                # 動態計算資料長度，確保 X 軸與日期完全對齊
                data_length = len(y)
                x = np.arange(data_length)
                
                # 線性回歸
                slope, intercept = np.polyfit(x, y, 1)
                middle_line = slope * x + intercept
                std_dev = np.std(y - middle_line)
                
                # --- D. 繪圖區 (手機 UI 優化版) ---
                fig = go.Figure()
                
                # 畫股價線
                fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1.5)))
                
                # 畫五線譜
                names = ['極端樂觀 (+2SD)', '樂觀 (+1SD)', '趨勢中線', '悲觀 (-1SD)', '極端悲觀 (-2SD)']
                colors = ['#FF4B4B', '#FFA500', '#1E90FF', '#32CD32', '#008000']
                multipliers = [2, 1, 0, -1, -2]
                
                for m, name, color in zip(multipliers, names, colors):
                    fig.add_trace(go.Scatter(
                        x=df['Date'], 
                        y=middle_line + m * std_dev, 
                        name=name, 
                        line=dict(color=color, width=1, dash='dash' if m != 0 else 'solid')
                    ))

                # 圖表佈局設定
                fig.update_layout(
                    title=f'{final_id} 分析',
                    xaxis_title=None, 
                    yaxis_title='股價',
                    hovermode="x unified", 
                    template="plotly_white",
                    height=500,
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend=dict(
                        orientation="h",   # 圖例橫向
                        yanchor="bottom",
                        y=1.02,            # 置於圖表上方
                        xanchor="right",
                        x=1,
                        font=dict(size=10)
                    )
                )

                # 顯示圖表
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                # --- E. 數據摘要 (手機自動堆疊) ---
                curr_p = float(y[-1])
                mid_p = float(middle_line[-1])
                sd_pos = (curr_p - mid_p) / std_dev
                
                st.subheader("📊 數據摘要")
                c1, c2, c3 = st.columns(3)
                c1.metric("最後收盤價", f"{curr_p:.2f}")
                c2.metric("回歸中線", f"{mid_p:.2f}")
                
                # 根據 SD 位置判斷顏色提示 (選擇性參考)
                status = "偏高" if sd_pos > 0 else "偏低"
                c3.metric("目前 SD 區間", f"{sd_pos:.2f} σ", delta=f"{status}")

else:
    st.info("💡 請在左側選單設定「股票代號」與「日期範圍」後點擊開始計算。")
