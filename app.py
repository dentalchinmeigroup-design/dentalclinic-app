import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# 設定 Google Sheets 連線範圍
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def connect_to_google_sheets():
    """建立與 Google Sheets 的直接連線 (加強版)"""
    # 1. 先定義檔案名稱 (移到最外面，避免報錯時找不到變數)
    spreadsheet_name = "dental_assessment_data" 
    
    try:
        # 檢查 Secrets 是否存在
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("❌ 找不到 Secrets 設定！請檢查 .streamlit/secrets.toml 是否正確。")
            st.stop()

        # 2. 從 Streamlit Secrets 讀取憑證
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # 【關鍵修正】處理 Private Key 的換行符號問題
        # 有時候複製貼上會讓 \n 變成文字，導致驗證失敗，這裡自動修復它
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        # 3. 建立連線
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # 4. 開啟試算表
        sh = client.open(spreadsheet_name)
        return sh

    except Exception as e:
        st.error(f"""
        ❌ 連線失敗！請依照下列步驟檢查：
        
        1. **Google 試算表名稱**：是否已改為 `{spreadsheet_name}` (完全一致，不要有空格)？
        2. **權限設定**：是否已將 `client_email` 加入試算表的「編輯者」？
        3. **詳細錯誤訊息**：{e}
        """)
        st.stop()

def main():
    st.set_page_config(page_title="專業技能考核表", layout="wide")
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子")
    st.subheader("全方位績效考核系統")

    # 測試連線 (程式一開始就先連線)
    sh = connect_to_google_sheets()

    st.markdown("---")

    # --- 1. 考核標準與指標定義 ---
    with st.expander("📖 點此查看：考核指標定義 & 評分標準 ", expanded=False):
        tab1, tab2 = st.tabs(["📊 評分標準 (分數級距)", "📝 指標定義說明 (詳細內容)"])
        with tab1:
            st.info("請依照下列分數級距，進行自評與他評。")
            st.markdown("""
            * **10分**：表現卓越 (超越要求)。
            * **8-9分**：表現穩定 (完全符合)。
            * **5-7分**：部分符合 (有改善空間)。
            * **3-4分**：不符合 (首次改善追蹤)。
            * **0-2分**：多次不符合 (持續追蹤)。
            * **N/A**：不適用。
            """)
        with tab2:
            st.warning("各項職能詳細定義：")
            st.markdown("""
            | 評核面向 | 考核重點 | 說明 |
            | :--- | :--- | :--- |
            | **專業技能** | **跟診/櫃台** | 具備職務所需的各項專業知識與技能。 |
            | **核心職能** | **勤務配合** | 遵循規範，維持出勤紀律與積極態度。 |
            | **核心職能** | **人際協作** | 與同儕保持良好互動，具備團隊合作能力。 |
            | **行政職能** | **基礎/進階** | 能完成行政與支援工作，有效執行任務。 |
            | **行政職能** | **應變/危機** | 具備應變與問題解決能力。 |
            """)

    st.markdown("---")

    # --- 2. 基本資料區 ---
    st.header("1. 受評人資料")
    c1, c2, c3, c4 = st.columns(4)
    with c1: name = st.text_input("姓名", placeholder="請輸入姓名")
    with c2: rank = st.text_input("職等", placeholder="請輸入職等")
    with c3: assess_date = st.date_input("評量日期", date.today())
    with c4: boss_name = st.text_input("最高核決", value="請輸入姓名")

    st.markdown("---")

    # --- 3. 考核評分區 ---
    st.header("2. 考核項目評分")
    st.info("💡 **操作方式**：請直接點擊表格內的數字進行修改（預設 2 分）。")

    # 資料結構
    data = [
        {"類別": "專業技能", "考核項目": "跟診技能", "說明": "器械準備熟練，無重大缺失。"},
        {"類別": "專業技能", "考核項目": "櫃台技能", "說明": "準確完成約診與行政作業。"},
        {"類別": "職能表現", "考核項目": "跟診執行", "說明": "確保診療不中斷，即時支援。"},
        {"類別": "職能表現", "考核項目": "櫃台溝通", "說明": "溝通良好，態度親切專業。"},
        {"類別": "職能表現", "考核項目": "勤務配合(職能)", "說明": "遵守出勤與請假規範。"},
        {"類別": "職能表現", "考核項目": "勤務配合(配合)", "說明": "積極參與訓練課程。"},
        {"類別": "職能表現", "考核項目": "人際協作(人際)", "說明": "與同儕互助，主動支援。"},
        {"類別": "職能表現", "考核項目": "人際協作(協作)", "說明": "尊重前輩，引導新人。"},
        {"類別": "行政職能", "考核項目": "危機處理", "說明": "即時處理突發，預防問題。"},
        {"類別": "行政職能", "考核項目": "基礎職能", "說明": "確實完成維修/牙材/牙模。"},
        {"類別": "行政職能", "考核項目": "進階職能", "說明": "理解要求，效率完成任務。"},
        {"類別": "行政職能", "考核項目": "應變能力", "說明": "因應臨時需求，態度靈活。"},
    ]

    if "df_initial" not in st.session_state:
        df = pd.DataFrame(data)
        df["自評"] = 2
        df["初考"] = 2
        df["覆考"] = 2
        df["最終"] = 2
        st.session_state.df_initial = df

    column_config = {
        "類別": st.column_config.TextColumn(width="small", disabled=True),
        "考核項目": st.column_config.TextColumn(width="medium", disabled=True),
        "說明": st.column_config.TextColumn(width="large", disabled=True),
        "自評": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
        "初考": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
        "覆考": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
        "最終": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
    }

    edited_df = st.data_editor(
        st.session_state.df_initial,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # --- 4. 儀表板 ---
    st.markdown("### 📊 成績總覽")
    total_self = edited_df["自評"].sum()
    total_init = edited_df["初考"].sum()
    total_rev = edited_df["覆考"].sum()
    total_final = edited_df["最終"].sum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("自評總分", f"{total_self}")
    m2.metric("初考總分", f"{total_init}")
    m3.metric("覆考總分", f"{total_rev}")
    m4.metric("最終總分", f"{total_final}")

    st.markdown("---")

    # --- 5. 評語區 ---
    st.header("3. 評語與建議")
    mc1, mc2 = st.columns(2)
    with mc1: manager_1 = st.text_input("初考主管簽名")
    with mc2: manager_2 = st.text_input("覆考主管簽名")

    c_text1, c_text2, c_text3 = st.columns(3)
    with c_text1: self_comment = st.text_area("自評文字")
    with c_text2: manager1_comment = st.text_area("初考評語")
    with c_text3: manager2_comment = st.text_area("覆考評語")

    action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 6. 提交按鈕 ---
    if st.button("🚀 提交完整考核表", type="primary", use_container_width=True):
        if not name:
            st.error("請填寫姓名！")
        else:
            with st.spinner("正在連線 Google Sheets 並寫入資料..."):
                try:
                    # 嘗試取得工作表
                    try:
                        worksheet = sh.worksheet("Assessment_Data")
                    except:
                        # 如果找不到，就建立一個新的 (100列 x 100欄)
                        worksheet = sh.add_worksheet(title="Assessment_Data", rows=100, cols=100)

                    # 準備資料
                    current_time = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    row_data = [
                        name, rank, assess_date.strftime("%Y-%m-%d"),
                        manager_1, manager_2, boss_name,
                        int(total_self), int(total_init), int(total_rev), int(total_final),
                        self_comment, manager1_comment, manager2_comment, action,
                        current_time
                    ]
                    
                    # 準備標題 (僅在第一次寫入時使用)
                    headers = [
                        "姓名", "職等", "日期", "初考主管", "覆考主管", "核決老闆",
                        "自評總分", "初考總分", "覆考總分", "最終總分",
                        "自評文字", "初考評語", "覆考評語", "最終建議", "填寫時間"
                    ]
                    
                    # 從表格中提取細項
                    for index, row in edited_df.iterrows():
                        item = row["考核項目"]
                        # 加入標題
                        if f"{item}_自評" not in headers:
                            headers.extend([f"{item}_自評", f"{item}_初考", f"{item}_覆考", f"{item}_最終"])
                        # 加入分數
                        row_data.extend([
                            int(row["自評"]), int(row["初考"]), int(row["覆考"]), int(row["最終"])
                        ])

                    # 檢查表格是否為空 (如果是空的，先寫入標題)
                    if not worksheet.get_all_values():
                        worksheet.append_row(headers)
                    
                    # 寫入資料
                    worksheet.append_row(row_data)
                    
                    st.success("✅ 寫入成功！資料已安全儲存。")
                    st.balloons()

                except Exception as e:
                    st.error(f"寫入發生錯誤: {e}")

if __name__ == "__main__":
    main()
