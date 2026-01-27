import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. 網頁配置 (必須放在第一行) ---
# 初始化 session_state
if "submitted" not in st.session_state:
    st.session_state.submitted = False

st.set_page_config(
    page_title="樂活五線譜線上查詢器", 
    layout="wide",
    initial_sidebar_state="collapsed" if st.session_state.submitted else "expanded"
)

# --- 2. 標題與樣式優化 ---
# 縮小手機版標題字體，並加入當前查詢標的顯示
st.markdown(
    """
    <h1 style='font-size: 24px; text-align: left; margin-bottom: 0px;'>📈 樂活五線譜自動生成</h1>
    """, 
    unsafe_allow_html=True
)

# --- 3. 側邊欄：使用者輸入區 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號 (台股:2330 / 美股:AAPL)", value="2330")

# 直接使用日期選擇器
start_date = st.sidebar.date_input("起始日期", value=datetime.now() - timedelta(days=1000))
end_date = st.sidebar.date_input("結束日期", value=datetime.now())

# 手機優化按鈕
submit_btn = st.sidebar.button("開始計算", use_container_width=True)

# 邏輯觸發區
if submit_btn:
    # 標記已提交，這會影響下次 rerun 時側邊欄的狀態
    st.session_state.submitted = True
    
    # 確保結束日期不早於起始日期
    if start_date >= end_date:
        st.error("❌ 錯誤：起始日期必須早於結束日期")
    else:
        with st.spinner('數據計算中...'):
            # A. 處理股票代號
            base_id = stock_id.strip().upper()
            
            # B. 嘗試抓取資料 (自動偵測市場)
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
                # 顯示當前分析對象 (對手機用戶很友善)
                st.caption(f"📊 當前分析標的: {final_id}")
                
                # --- C. 核心計算區 ---
                df = df.reset_index()
                y = df['Close'].values.squeeze()
                
                if y.ndim > 1:
                    y = y[:, 0]
                
                data_length = len(y)
                x = np.arange(data_length)
                
                slope, intercept = np.polyfit(x, y, 1)
                middle_line = slope * x + intercept
                std_dev = np.std(y - middle_line)
                
                # --- D. 繪圖區 (手機 UI 優化版) ---
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1.5)))
                
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

                fig.update_layout(
                    title=None, # 標題已在下方 caption 顯示
                    xaxis_title=None, 
                    yaxis_title='價格',
                    hovermode="x unified", 
                    template="plotly_white",
                    height=500,
                    margin=dict(l=5, r=5, t=30, b=5), # 縮減邊界
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=10)
                    )
                )

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                # --- E. 數據摘要 ---
                curr_p = float(y[-1])
                mid_p = float(middle_line[-1])
                sd_pos = (curr_p - mid_p) / std_dev
                
                st.subheader("📊 數據摘要")
                c1, c2, c3 = st.columns(3)
                c1.metric("最後收盤價", f"{curr_p:.2f}")
                c2.metric("回歸中線", f"{mid_p:.2f}")
                status = "高於中線" if sd_pos > 0 else "低於中線"
                c3.metric("目前 SD 區間", f"{sd_pos:.2f} σ", delta=f"{status}")
                
                # 強制觸發一次 rerun 以確保 sidebar 收合 (僅在第一次提交時)
                # st.rerun() # 如果發現側邊欄沒收，可以開啟這行

# 初始進入顯示提示
if not st.session_state.submitted:
    st.info("💡 請點開左上選單設定「股票代號」後點擊開始計算。")
