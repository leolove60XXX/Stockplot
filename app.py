import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 網頁配置：加入 initial_sidebar_state，讓手機版預設收起選單
st.set_page_config(
    page_title="樂活五線譜線上查詢器", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

st.title("📈 樂活五線譜自動生成")

# --- 2. 側邊欄：使用者輸入區 ---
st.sidebar.header("查詢設定")
stock_id = st.sidebar.text_input("股票代號 (輸入數字即可)", value="2884")
# 新增：選擇計算模式
mode = st.sidebar.radio("時間設定模式", ["固定天數", "自定義起始日"])

if mode == "固定天數":
    lookback_days = st.sidebar.slider("觀察天數", min_value=250, max_value=2000, value=1000)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
else:
    # 自定義日期模式
    start_date = st.sidebar.date_input("起始日期", value=datetime.now() - timedelta(days=1000))
    end_date = st.sidebar.date_input("結束日期", value=datetime.now())
    # 算出實際天數，供後續繪圖標題使用
    lookback_days = (end_date.date() - start_date).days if isinstance(end_date, datetime) else (end_date - start_date).days

# 手機優化：讓按鈕在側邊欄也能撐滿寬度
submit_btn = st.sidebar.button("開始計算", use_container_width=True)

if submit_btn:
    with st.spinner('計算中...'):
        # 1. 自動偵測後綴邏輯
        base_id = stock_id.strip().upper().replace(".TW", "").replace(".TWO", "")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        df = yf.download(f"{base_id}.TW", start=start_date, end=end_date, progress=False)
        final_id = f"{base_id}.TW"
        
        if df.empty:
            df = yf.download(f"{base_id}.TWO", start=start_date, end=end_date, progress=False)
            final_id = f"{base_id}.TWO"

        if df.empty:
            st.error("❌ 找不到資料，請檢查代號是否正確")
        else:
            df = df.reset_index()
            y = df['Close'].values.squeeze()
            if y.ndim > 1:
                y = y[:, 0]
                
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            middle_line = slope * x + intercept
            std_dev = np.std(y - middle_line)
            
            # --- 3. 繪圖區 (手機優化版) ---
            fig = go.Figure()
            
            # 畫股價線
            fig.add_trace(go.Scatter(x=df['Date'], y=y, name='收盤價', line=dict(color='black', width=1.5)))
            
            names = ['極端樂觀 (+2SD)', '樂觀 (+1SD)', '趨勢中線', '悲觀 (-1SD)', '極端悲觀 (-2SD)']
            colors = ['red', 'orange', 'blue', 'lightgreen', 'green']
            multipliers = [2, 1, 0, -1, -2]
            
            for m, name, color in zip(multipliers, names, colors):
                fig.add_trace(go.Scatter(
                    x=df['Date'], 
                    y=middle_line + m * std_dev, 
                    name=name, 
                    line=dict(color=color, width=1, dash='dash' if m != 0 else 'solid')
                ))

            # 關鍵：手機 UI 佈局調整
            fig.update_layout(
                title=f'{final_id} 分析',
                xaxis_title=None, 
                yaxis_title='股價',
                hovermode="x unified", 
                template="plotly_white",
                height=500, # 手機上高度不宜太高
                margin=dict(l=10, r=10, t=50, b=10), # 縮小邊界讓圖表更大
                legend=dict(
                    orientation="h",   # 圖例橫向排列
                    yanchor="bottom",
                    y=1.02,            # 放在圖表上方
                    xanchor="right",
                    x=1,
                    font=dict(size=10) # 縮小圖例字體
                )
            )

            # 顯示圖表
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # --- 4. 數據摘要 (手機會自動轉為垂直堆疊) ---
            curr_p = float(y[-1])
            mid_p = float(middle_line[-1])
            sd_pos = (curr_p - mid_p) / std_dev
            
            st.subheader("📊 數據摘要")
            c1, c2, c3 = st.columns(3)
            # 在手機上，這三個 c 會自動變成三列，看起來很整齊
            c1.metric("當前股價", f"{curr_p:.2f}")
            c2.metric("中線位置", f"{mid_p:.2f}")
            # 加入 delta 顯示與中線的偏離度
            c3.metric("目前 SD 區間", f"{sd_pos:.2f}", delta=f"相對中線 {sd_pos:.2f}σ")

else:
    st.info("💡 請點擊左側（或點開左上角選單）的「開始計算」")
