import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. 狀態初始化與配置 ---
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# 根據狀態決定側邊欄開關
st.set_page_config(
    page_title="樂活五線譜", 
    layout="wide",
    initial_sidebar_state="collapsed" if st.session_state.submitted else "expanded"
)

# --- 2. 標題與樣式優化 ---
st.markdown(
    """
    <style>
    .main-title { font-size: 22px !important; font-weight: bold; margin-bottom: 5px; }
    </style>
    <div class="main-title">📈 樂活五線譜自動生成</div>
    """, 
    unsafe_allow_html=True
)

# --- 3. 側邊欄：使用者輸入區 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號 (如: 2330 或 AAPL)", value="2330")

# 直接使用日期選擇器
start_date = st.sidebar.date_input("起始日期", value=datetime.now() - timedelta(days=1000))
end_date = st.sidebar.date_input("結束日期", value=datetime.now())

# 按下按鈕時觸發 rerun
if st.sidebar.button("開始計算", use_container_width=True):
    st.session_state.submitted = True
    st.rerun() 

# --- 4. 核心執行區 ---
if st.session_state.submitted:
    with st.spinner('數據計算中...'):
        # A. 自動轉大寫處理
        base_id = stock_id.strip().upper().replace(".TW", "").replace(".TWO", "")
        
        # B. 嘗試抓取資料 (美股 -> 台股上市 -> 台股上櫃)
        df = yf.download(base_id, start=start_date, end=end_date, progress=False)
        final_id = base_id
        if df.empty:
            df = yf.download(f"{base_id}.TW", start=start_date, end=end_date, progress=False)
            final_id = f"{base_id}.TW"
        if df.empty:
            df = yf.download(f"{base_id}.TWO", start=start_date, end=end_date, progress=False)
            final_id = f"{base_id}.TWO"

        if df.empty:
            st.error(f"❌ 找不到股票代號 '{base_id}'，請重新設定。")
            st.session_state.submitted = False
        else:
            # 顯示目前分析標的
            st.markdown(f"**📊 目前分析標的: {final_id}**")
            
            # --- C. 核心計算區 ---
            df = df.reset_index()
            
            # 【關鍵修復】剔除含有 NaN 的行，避免 np.polyfit 計算出 NaN
            df = df.dropna()
            
            y = df['Close'].values.squeeze()
            if y.ndim > 1: y = y[:, 0]
            
            # 動態長度對齊，修復 X 軸 BUG
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            middle_line = slope * x + intercept
            std_dev = np.std(y - middle_line)
            
            # --- D. 繪圖區 ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1.5)))
            
            # 五線譜設定
            names = ['極端樂觀', '樂觀', '趨勢中線', '悲觀', '極端悲觀']
            colors = ['#FF4B4B', '#FFA500', '#1E90FF', '#32CD32', '#008000']
            multipliers = [2, 1, 0, -1, -2]
            
            for m, name, color in zip(multipliers, names, colors):
                fig.add_trace(go.Scatter(
                    x=df['Date'], 
                    y=middle_line + m * std_dev, 
                    name=name, 
                    line=dict(
                        color=color, 
                        width=1.2, 
                        dash='solid' if m == 0 else 'dash'
                    ),
                    mode='lines'
                ))

            # 圖表佈局 (圖例置中平均分布)
            fig.update_layout(
                xaxis_title=None, yaxis_title='價格',
                hovermode="x unified", template="plotly_white", height=450,
                margin=dict(l=5, r=5, t=60, b=5),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", y=1.02, 
                    xanchor="center", x=0.5, 
                    font=dict(size=10),
                    itemwidth=30 # 讓虛線在圖例中顯現
                )
            )

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # --- E. 數據摘要 ---
            curr_p, mid_p = float(y[-1]), float(middle_line[-1])
            sd_pos = (curr_p - mid_p) / std_dev
            
            st.subheader("📊 數據摘要")
            c1, c2, c3 = st.columns(3)
            c1.metric("最後收盤", f"{curr_p:.2f}")
            c2.metric("回歸中線", f"{mid_p:.2f}")
            status = "高於中線" if sd_pos > 0 else "低於中線"
            c3.metric("目前區間", f"{sd_pos:.2f} σ", delta=f"{status}")

else:
    st.info("💡 請點開左上角選單 [ > ] 設定參數後按「開始計算」。")
