import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# --- 設定連線範圍 ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def connect_to_google_sheets():
    """連線到 Google Sheets"""
    spreadsheet_name = "dental_assessment_data" 
    try:
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("❌ 找不到 Secrets 設定！請確認 .streamlit/secrets.toml 檔案。")
            st.stop()

        creds_dict = dict(st.secrets["connections"]["gsheets"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        sh = client.open(spreadsheet_name)
        return sh
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

def main():
    st.set_page_config(page_title="專業技能考核系統", layout="wide")
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子 | 考核系統")
    
    # 初始化連線
    sh = connect_to_google_sheets()

    # --- 建立分頁 (Tabs) ---
    tab1, tab2 = st.tabs(["📝 員工/主管填寫", "🔍 後台查閱 (老闆專用)"])

    # ==========================================
    # Tab 1: 填寫區 (寫入資料)
    # ==========================================
    with tab1:
        st.subheader("新增考核紀錄")
        
        # --- 1. 說明區 ---
        with st.expander("📖 查看評分標準", expanded=False):
            st.markdown("""
            * **10分**：表現卓越。
            * **8-9分**：完全符合。
            * **5-7分**：部分符合。
            * **3-4分**：不符合。
            * **0-2分**：多次不符合。
            """)

        # --- 2. 資料輸入 ---
        st.markdown("### 1. 受評人資料")
        c1, c2, c3, c4 = st.columns(4)
        with c1: name = st.text_input("姓名", placeholder="請輸入姓名")
        with c2: rank = st.text_input("職等", placeholder="請輸入職等")
        with c3: assess_date = st.date_input("評量日期", date.today())
        with c4: boss_name = st.text_input("最高核決", value="請輸入姓名")

        st.markdown("### 2. 考核評分")
        
        # 定義資料結構
        data_structure = [
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

        # 建立編輯表格
        if "df_input" not in st.session_state:
            df = pd.DataFrame(data_structure)
            df["自評"] = 0
            df["初考"] = 0
            df["覆考"] = 0
            df["最終"] = 0
            st.session_state.df_input = df

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
            st.session_state.df_input,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=450
        )

        # 即時計算總分
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("自評總分", edited_df["自評"].sum())
        t2.metric("初考總分", edited_df["初考"].sum())
        t3.metric("覆考總分", edited_df["覆考"].sum())
        t4.metric("最終總分", edited_df["最終"].sum())

        st.markdown("### 3. 評語與建議")
        mc1, mc2 = st.columns(2)
        with mc1: manager_1 = st.text_input("初考主管簽名")
        with mc2: manager_2 = st.text_input("覆考主管簽名")

        c1, c2, c3 = st.columns(3)
        with c1: self_comment = st.text_area("自評文字")
        with c2: manager1_comment = st.text_area("初考評語")
        with c3: manager2_comment = st.text_area("覆考評語")

        action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])
        
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚀 提交完整考核表", type="primary", use_container_width=True):
            if not name:
                st.error("請填寫姓名！")
            else:
                with st.spinner("正在寫入..."):
                    try:
                        try:
                            worksheet = sh.worksheet("Assessment_Data")
                        except:
                            worksheet = sh.add_worksheet(title="Assessment_Data", rows=100, cols=100)

                        # 準備資料
                        row_data = [
                            name, rank, assess_date.strftime("%Y-%m-%d"),
                            manager_1, manager_2, boss_name,
                            int(edited_df["自評"].sum()), int(edited_df["初考"].sum()), 
                            int(edited_df["覆考"].sum()), int(edited_df["最終"].sum()),
                            self_comment, manager1_comment, manager2_comment, action,
                            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        
                        # 定義標題 (注意：這邊也要用「減號」來配合您的 Google Sheet)
                        headers = ["姓名", "職等", "日期", "初考主管", "覆考主管", "最高核決",
                                   "自評總分", "初考總分", "覆考總分", "最終總分",
                                   "自評文字", "初考評語", "覆考評語", "最終建議", "填寫時間"]
                        
                        for _, row in edited_df.iterrows():
                            item = row["考核項目"]
                            # 【修正】寫入時也改用「減號 -」
                            if f"{item}-自評" not in headers:
                                headers.extend([f"{item}-自評", f"{item}-初考", f"{item}-覆考", f"{item}-最終"])
                            row_data.extend([int(row["自評"]), int(row["初考"]), int(row["覆考"]), int(row["最終"])])

                        # 如果是新表，先寫入標題
                        if not worksheet.get_all_values():
                            worksheet.append_row(headers)
                        
                        worksheet.append_row(row_data)
                        st.success("✅ 提交成功！")
                        st.balloons()
                    except Exception as e:
                        st.error(f"錯誤: {e}")

    # ==========================================
    # Tab 2: 後台查閱 (讀取資料)
    # ==========================================
    with tab2:
        st.header("🔍 考核紀錄查詢")
        
        password = st.text_input("請輸入管理員密碼", type="password")
        if password == "1234": 
            try:
                worksheet = sh.worksheet("Assessment_Data")
                data = worksheet.get_all_records()
                
                if not data:
                    st.info("目前還沒有任何考核資料。")
                else:
                    df_all = pd.DataFrame(data)
                    
                    st.markdown("#### 1. 選擇要查看的考核單")
                    options = [f"{row['姓名']} | {row['日期']} (最終分:{row['最終總分']})" for i, row in df_all.iterrows()]
                    selected_option = st.selectbox("請選擇人員", options)
                    
                    selected_index = options.index(selected_option)
                    record = df_all.iloc[selected_index]

                    st.markdown("---")
                    st.subheader(f"📄 考核詳情：{record['姓名']}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.info(f"**職等**：{record['職等']}")
                    col2.info(f"**日期**：{record['日期']}")
                    col3.info(f"**初考主管**：{record['初考主管']}")
                    col4.info(f"**覆考主管**：{record['覆考主管']}")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("自評總分", record['自評總分'])
                    m2.metric("初考總分", record['初考總分'])
                    m3.metric("覆考總分", record['覆考總分'])
                    m4.metric("🏆 最終總分", record['最終總分'])

                    st.markdown("#### 💬 綜合評語")
                    st.text_area("同仁自評", value=record['自評文字'], disabled=True)
                    c1, c2 = st.columns(2)
                    c1.text_area("初考評語", value=record['初考評語'], disabled=True)
                    c2.text_area("覆考評語", value=record['覆考評語'], disabled=True)
                    
                    result_text = record['最終建議']
                    if "通過" in str(result_text):
                        st.success(f"📌 最終建議：{result_text}")
                    else:
                        st.warning(f"📌 最終建議：{result_text}")

                    st.markdown("#### 📊 細項評分表")
                    
                    detail_rows = []
                    items = ["跟診技能", "櫃台技能", "跟診執行", "櫃台溝通", "勤務配合(職能)", "勤務配合(配合)", "人際協作(人際)", "人際協作(協作)", "危機處理", "基礎職能", "進階職能", "應變能力"]
                    
                    for item in items:
                        detail_rows.append({
                            "考核項目": item,
                            # 【關鍵修正】這裡全部改成「減號 -」，對應您的 Google Sheet 欄位
                            "自評": str(record.get(f"{item}-自評", "-")),
                            "初考": str(record.get(f"{item}-初考", "-")),
                            "覆考": str(record.get(f"{item}-覆考", "-")),
                            "最終": str(record.get(f"{item}-最終", "-")),
                        })
                            
                    detail_df = pd.DataFrame(detail_rows)
                    
                    # 使用 st.table (靜態表格)，這絕對不會出現黑點
                    st.table(detail_df) 

            except Exception as e:
                st.error(f"讀取失敗，請確認資料庫已有資料。錯誤詳情: {e}")
        elif password:
            st.error("密碼錯誤！")

if __name__ == "__main__":
    main()
