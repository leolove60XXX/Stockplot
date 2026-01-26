import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 網頁配置
st.set_page_config(page_title="樂活五線譜線上查詢器", layout="wide")
st.title("📈 樂活五線譜自動生成系統")

# --- 側邊欄：使用者輸入區 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號 (台股請加 .TW)", value="2884.TW")
lookback_days = st.sidebar.slider("觀察天數", min_value=250, max_value=2000, value=1000)

if st.sidebar.button("開始計算"):
    with st.spinner('計算中...'):
        # 1. 抓取資料 (完全沿用您成功的邏輯)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        df = yf.download(stock_id, start=start_date, end=end_date)

        if df.empty:
            st.error("找不到資料")
        else:
            # --- 核心計算區 (完全沿用您成功的代碼) ---
            df = df.reset_index()
            # 關鍵點：使用 squeeze() 確保 y 是純一維數值
            y = df['Close'].values.squeeze()
            
            # 如果是 Multi-index 導致 squeeze 失效，改用 iloc 強制轉一維
            if y.ndim > 1:
                y = y[:, 0]
                
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            middle_line = slope * x + intercept
            
            # 計算標準差
            std_dev = np.std(y - middle_line)
            
            # --- 繪圖區 (完全沿用您成功的 go.Scatter 邏輯) ---
            fig = go.Figure()
            
            # 畫股價線
            fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1)))
            
            # 畫五線譜
            names = ['極端樂觀 (+2SD)', '樂觀 (+1SD)', '趨勢中線', '悲觀 (-1SD)', '極端悲觀 (-2SD)']
            colors = ['red', 'orange', 'blue', 'lightgreen', 'green']
            multipliers = [2, 1, 0, -1, -2]
            
            for m, name, color in zip(multipliers, names, colors):
                # 這裡就是您成功畫出來的核心代碼
                fig.add_trace(go.Scatter(
                    x=df['Date'], 
                    y=middle_line + m * std_dev, 
                    name=name, 
                    line=dict(color=color, dash='dash' if m != 0 else 'solid')
                ))

            fig.update_layout(
                title=f'{stock_id} 樂活五線譜分析 ({lookback_days}天)',
                xaxis_title='日期', 
                yaxis_title='股價',
                hovermode="x unified", 
                template="plotly_white",
                height=600 # 增加高度
            )

            # 在 Streamlit 中顯示圖表
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 數據摘要 ---
            curr_p = float(y[-1])
            mid_p = float(middle_line[-1])
            sd_pos = (curr_p - mid_p) / std_dev
            
            st.subheader("📊 數據摘要")
            c1, c2, c3 = st.columns(3)
            c1.metric("當前股價", f"{curr_p:.2f}")
            c2.metric("中線位置", f"{mid_p:.2f}")
            c3.metric("目前 SD 區間", f"{sd_pos:.2f}")

else:
    st.info("請點擊左側「開始計算」")
