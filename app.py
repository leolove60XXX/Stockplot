import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import io
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
    /* 1. 強制讓側邊欄與其內部容器允許溢出顯示 (不裁切彈窗) */
    [data-testid="stSidebar"], 
    [data-testid="stSidebarUserContent"],
    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    /* 2. 增加側邊欄頂部間距，避免年份彈出時頂到瀏覽器邊緣 */
    [data-testid="stSidebarUserContent"] {
        padding-top: 53px !important;
    }

    /* 2A. 手機版特別修正 (針對 768px 以下螢幕) */
    @media (max-width: 768px) {
        [data-testid="stSidebarUserContent"] {
            padding-top: 80px !important; /* 手機版多推一點，避免被手機狀態列遮住 */
        }

    /* 3. 調寬側邊欄，確保日曆元件有足夠寬度 */
    [data-testid="stSidebar"] {
        min-width: 350px !important;
    }

    /* 4. 確保日曆彈窗 (Popover) 的 z-index 極高 */
    div[data-baseweb="popover"] {
        z-index: 999999 !important;
    }

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
            # --- C. 精準抓取證交所中文名稱 (修正版) ---
            @st.cache_data(ttl=86400) # 每天自動更新一次
            def load_full_tw_stock_mapping():
                """
                從 MOPS 下載上市(L)、上櫃(O)、興櫃(R)的所有公司基本資料 CSV
                並建立 {代號: 簡稱} 的對照表
                """
                urls = [
                    "https://mopsfin.twse.com.tw/opendata/t187ap03_L.csv", # 上市
                    "https://mopsfin.twse.com.tw/opendata/t187ap03_O.csv", # 上櫃
                    "https://mopsfin.twse.com.tw/opendata/t187ap03_R.csv"  # 興櫃
                ]
                mapping = {}
                
                for url in urls:
                        try:
                            response = requests.get(url, headers=headers, timeout=10)
                            if response.status_code == 200:
                                # 關鍵修正：處理可能的 BOM 與編碼，並強制移除雙引號
                                content = response.text.replace('"', '') 
                                df = pd.read_csv(io.StringIO(content))
                                
                                # 清洗標頭與內容
                                df.columns = [c.strip() for c in df.columns]
                                if '公司代號' in df.columns and '公司簡稱' in df.columns:
                                    # 建立字典映射，確保代號是純數字字串
                                    temp_dict = dict(zip(df['公司代號'].astype(str).str.strip(), df['公司簡稱'].astype(str).str.strip()))
                                    mapping.update(temp_dict)
                        except Exception as e:
                            print(f"無法載入 {url}: {e}")
                            continue
                        
                return mapping
            
            def get_tw_stock_name(base_id, final_id):
                """
                優先從 CSV 資料庫找中文名稱，找不到則用 yfinance 備援
                """
                clean_no = str(base_id).split('.')[0].strip()
                
                # 1. 從全台股 CSV 資料庫查找
                tw_mapping = load_full_tw_stock_mapping()
                if clean_no in tw_mapping:
                    return tw_mapping[clean_no]
                
                # 2. 備援：yfinance 查找 (美股或新上市股)
                try:
                    t = yf.Ticker(final_id)
                    name = t.info.get('shortName') or t.info.get('longName')
                    if name: return name
                except:
                    pass
                    
                return ""
            # 執行抓取
            comp_name = get_tw_stock_name(base_id, final_id)

            # 顯示標題
            st.markdown(f"### 📊 目前分析標的: {base_id} {comp_name}", unsafe_allow_html=True)

            
            # --- C. 核心計算區 ---
            df = df.reset_index()
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


