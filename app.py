import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. 狀態初始化與配置 ---
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# 這裡的 initial_sidebar_state 會根據狀態決定開關
st.set_page_config(
    page_title="樂活五線譜", 
    layout="wide",
    initial_sidebar_state="collapsed" if st.session_state.submitted else "expanded"
)

# --- 2. 標題與樣式 ---
st.markdown(
    """
    <style>
    /* 強制縮小手機標題的 CSS */
    .main-title { font-size: 22px !important; font-weight: bold; margin-bottom: 5px; }
    </style>
    <div class="main-title">📈 樂活五線譜自動生成</div>
    """, 
    unsafe_allow_html=True
)

# --- 3. 側邊欄 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號", value="2330")
start_date = st.sidebar.date_input("起始日期", value=datetime.now() - timedelta(days=1000))
end_date = st.sidebar.date_input("結束日期", value=datetime.now())

# 修改點：按下按鈕時同時觸發 rerun
if st.sidebar.button("開始計算", use_container_width=True):
    st.session_state.submitted = True
    st.rerun() # 強制重新整理頁面，讓 initial_sidebar_state="collapsed" 生效

# --- 4. 核心執行區 (只要 submitted 為 True 就顯示成果) ---
if st.session_state.submitted:
    with st.spinner('數據計算中...'):
        base_id = stock_id.strip().upper()
        
        # 抓取資料
        df = yf.download(base_id, start=start_date, end=end_date, progress=False)
        final_id = base_id
        if df.empty:
            df = yf.download(f"{base_id}.TW", start=start_date, end=end_date, progress=False)
            final_id = f"{base_id}.TW"
        if df.empty:
            df = yf.download(f"{base_id}.TWO", start=start_date, end=end_date, progress=False)
            final_id = f"{base_id}.TWO"

        if df.empty:
            st.error(f"❌ 找不到股票代號 '{base_id}'")
            # 找不到資料時把狀態改回來，讓側邊欄彈出來修正
            st.session_state.submitted = False
        else:
            # 顯示目前分析代號 (手機版重要提示)
            st.success(f"✅ 已完成 {final_id} 的數據分析")
            
            # 計算區
            df = df.reset_index()
            y = df['Close'].values.squeeze()
            if y.ndim > 1: y = y[:, 0]
            
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            middle_line = slope * x + intercept
            std_dev = np.std(y - middle_line)
            
            # 繪圖
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1.5)))
            
            names = ['極端樂觀', '樂觀', '趨勢中線', '悲觀', '極端悲觀']
            colors = ['#FF4B4B', '#FFA500', '#1E90FF', '#32CD32', '#008000']
            multipliers = [2, 1, 0, -1, -2]
            
            for m, name, color in zip(multipliers, names, colors):
                fig.add_trace(go.Scatter(
                    x=df['Date'], y=middle_line + m * std_dev, 
                    name=name, line=dict(color=color, width=1, dash='dash' if m != 0 else 'solid')
                ))

            fig.update_layout(
                xaxis_title=None, yaxis_title='價格',
                hovermode="x unified", template="plotly_white", height=450,
                margin=dict(l=5, r=5, t=30, b=5),
                legend=dict(
                    orientation="h",      # 橫向排列
                    yanchor="bottom",
                    y=1.02,               # 置於圖表上方
                    xanchor="center",     # 關鍵：將圖例的錨點設為中間
                    x=0.5,                # 關鍵：將中間點放在圖表 50% 的位置
                    font=dict(size=10),
                    traceorder="normal",  # 確保順序依照 names 定義
                    itemsizing="constant" # 讓圖例標誌大小一致
                    ),
            )

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # 數據摘要
            curr_p, mid_p = float(y[-1]), float(middle_line[-1])
            sd_pos = (curr_p - mid_p) / std_dev
            
            st.subheader("📊 數據摘要")
            c1, c2, c3 = st.columns(3)
            c1.metric("當前收盤", f"{curr_p:.2f}")
            c2.metric("回歸中線", f"{mid_p:.2f}")
            c3.metric("SD 區間", f"{sd_pos:.2f} σ", delta=f"{'偏高' if sd_pos > 0 else '偏低'}")

else:
    st.info("💡 請點擊左上角選單 [ > ] 設定參數後按「開始計算」")
