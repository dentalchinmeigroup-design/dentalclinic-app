import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import time

# --- 設定連線範圍 ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- 1. 連線設定 ---
def connect_to_google_sheets():
    """連線到 Google Sheets"""
    spreadsheet_name = "dental_assessment_data" 
    try:
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("❌ 找不到 Secrets 設定！")
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

# --- 2. 快取讀取資料 ---
@st.cache_data(ttl=5) # 縮短一點快取時間，讓更新反應更快
def load_data_from_sheet(_worksheet):
    return _worksheet.get_all_records()

# --- 3. 核心功能：依據標題寫入資料 (解決 0 分問題) ---
def save_data_using_headers(worksheet, data_dict):
    """
    聰明的寫入功能：先看 Sheet 的標題在哪裡，再把資料填入正確的格子。
    如果遇到新欄位，會自動補在最後面。
    """
    # 1. 取得目前 Sheet 上所有的標題 (第一列)
    existing_headers = worksheet.row_values(1)
    
    # 如果是空表，就建立標題
    if not existing_headers:
        existing_headers = list(data_dict.keys())
        worksheet.append_row(existing_headers)
    
    # 2. 檢查有沒有新欄位 (data_dict 有，但 Sheet 沒有的)
    new_cols = [k for k in data_dict.keys() if k not in existing_headers]
    if new_cols:
        # 把新欄位補在 Sheet 第一列的最後面
        worksheet.add_cols(len(new_cols))
        for i, col_name in enumerate(new_cols):
            worksheet.update_cell(1, len(existing_headers) + i + 1, col_name)
        # 更新本地標題清單
        existing_headers.extend(new_cols)
        
    # 3. 依照標題順序，準備要寫入的一整列資料
    row_values = []
    for header in existing_headers:
        # 從 data_dict 拿資料，如果沒有就填空字串
        val = data_dict.get(header, "")
        row_values.append(val)
        
    # 4. 寫入
    worksheet.append_row(row_values)

# --- 4. 輔助函數 ---
def find_row_index(all_values, name, assess_date):
    if not all_values: return None
    df = pd.DataFrame(all_values)
    # 搜尋姓名和日期
    match = df.index[(df["姓名"] == name) & (df["日期"] == str(assess_date))].tolist()
    if match:
        return match[0] + 2 # +2 是因為 Google Sheet row 從 1 開始且有標題
    return None

def show_guidelines():
    with st.expander("📖 查看評分標準與職能定義說明", expanded=False):
        tab_a, tab_b = st.tabs(["📊 分數級距定義", "📝 職能定義說明"])
        with tab_a:
            st.markdown("""
            * **10分 (表現卓越)**：超越要求，表現卓越。
            * **8-9分 (完全符合)**：完全符合基本要求，表現穩定。
            * **5-7分 (部分符合)**：部分符合，但有建議改善事項。
            * **3-4分 (不符合)**：不符合，首次列入改善追蹤。
            * **0-2分 (多次不符合)**：多次不符合，需持續改善追蹤。
            """)
        with tab_b:
            st.markdown("""
            ### 1. 專業技能
            * **跟診/櫃台**：具備職務所需的各項專業知識與技能，能充份滿足工作需求。
            ### 2. 核心職能
            * **勤務配合**：遵循規範，維持良好的出勤紀律。
            * **人際協作**：與同儕保持良好互動，具備良好的團隊合作能力。
            ### 3. 行政職能
            * **基礎/進階/應變**：能完成行政與支援工作，並有效執行主管交辦任務，具備應變能力。
            """)

def get_assessment_items():
    return [
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

def main():
    st.set_page_config(page_title="考核系統流程版", layout="wide")
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子 | 考核系統 (流程版)")
    
    sh = connect_to_google_sheets()
    try:
        worksheet = sh.worksheet("Assessment_Data")
    except:
        worksheet = sh.add_worksheet(title="Assessment_Data", rows=100, cols=100)

    tabs = st.tabs(["1️⃣ 員工自評", "2️⃣ 初考主管審核", "3️⃣ 覆考主管審核", "4️⃣ 老闆最終核決"])

    # ==========================================
    # Tab 1: 員工自評
    # ==========================================
    with tabs[0]:
        st.header("📝 員工自評區")
        st.info("填寫完畢後，資料將自動送往下一關主管。")
        show_guidelines()

        col1, col2, col3 = st.columns(3)
        with col1: name = st.text_input("姓名", placeholder="請輸入姓名")
        with col2: role = st.selectbox("您的職務身份", ["一般員工", "初考主管 (管理者)", "覆考主管 (護理長)"])
        with col3: assess_date = st.date_input("評量日期", date.today())

        if role == "一般員工": next_status = "待初考"
        elif role == "初考主管 (管理者)": next_status = "待覆考"
        else: next_status = "待核決"

        # 初始化 Session State 中的 DataFrame，這樣我們才能在送出後重置它
        if "df_self" not in st.session_state:
            df = pd.DataFrame(get_assessment_items())
            df["自評"] = 0
            st.session_state.df_self = df

        edited_df = st.data_editor(
            st.session_state.df_self,
            column_config={
                "自評": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                "類別": st.column_config.TextColumn(disabled=True),
                "考核項目": st.column_config.TextColumn(disabled=True),
                "說明": st.column_config.TextColumn(disabled=True, width="large"),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_self_widget" # 給 widget 一個 key
        )
        
        # 使用 key 來綁定 session state，方便清空
        self_comment = st.text_area("自評文字", placeholder="請輸入...", key="self_comment_key")

        if st.button("🚀 送出自評", type="primary"):
            if not name:
                st.error("請填寫姓名")
            else:
                with st.spinner("資料傳送中..."):
                    load_data_from_sheet.clear()
                    
                    # 1. 準備好資料字典 (Key 要跟 Sheet 標題一樣)
                    # 這樣就不怕欄位順序亂掉了
                    data_to_save = {
                        "目前狀態": next_status,
                        "姓名": name,
                        "職務身份": role,
                        "日期": assess_date.strftime("%Y-%m-%d"),
                        "自評總分": int(edited_df["自評"].sum()),
                        "初考總分": 0, "覆考總分": 0, "最終總分": 0,
                        "自評文字": self_comment,
                        "初考評語": "", "覆考評語": "", "最終建議": "",
                        "填寫時間": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # 把細項分數也加進去
                    for _, row in edited_df.iterrows():
                        item = row["考核項目"]
                        data_to_save[f"{item}-自評"] = int(row["自評"])
                        data_to_save[f"{item}-初考"] = 0
                        data_to_save[f"{item}-覆考"] = 0
                        data_to_save[f"{item}-最終"] = 0

                    # 2. 呼叫聰明的寫入函數
                    save_data_using_headers(worksheet, data_to_save)

                    # 3. 清空輸入框 (解決重複顯示問題)
                    st.session_state["self_comment_key"] = ""  # 清空評語
                    del st.session_state["df_self"] # 刪除舊的 DataFrame，下次重跑會重新 init 為 0

                    st.success(f"✅ 自評已送出！案件已轉移至【{next_status}】列表。")
                    time.sleep(1)
                    st.rerun()

    # ==========================================
    # Tab 2: 初考主管審核
    # ==========================================
    with tabs[1]:
        st.header("👮‍♂️ 初考主管審核區")
        show_guidelines()
        pwd1 = st.text_input("🔒 初考主管密碼", type="password", key="pwd_primary")
        
        if pwd1 == "1111": 
            data = load_data_from_sheet(worksheet)
            df_all = pd.DataFrame(data)

            if not df_all.empty and "目前狀態" in df_all.columns:
                pending_df = df_all[df_all["目前狀態"] == "待初考"]
                if pending_df.empty:
                    st.info("🎉 目前沒有待審核的初考案件。")
                else:
                    target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                    selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_primary")
                    
                    target_name = selected_target.split(" (")[0]
                    target_date = selected_target.split(" (")[1].replace(")", "")
                    record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                    st.markdown("---")
                    st.subheader(f"正在審核：{target_name}")
                    # 這裡的數字應該會正確了，因為我們改用了 header mapping 寫入
                    st.write(f"**員工自評總分**：{record.get('自評總分', 0)}")
                    st.info(f"🗨️ **員工自評內容**：{record.get('自評文字', '')}")

                    items = get_assessment_items()
                    input_data = []
                    for item in items:
                        i_name = item["考核項目"]
                        input_data.append({
                            "考核項目": i_name,
                            "說明": item["說明"],
                            "自評 (參考)": record.get(f"{i_name}-自評", 0),
                            "初考評分": 0 
                        })
                    
                    df_primary = pd.DataFrame(input_data)
                    edited_primary = st.data_editor(
                        df_primary,
                        column_config={
                            "自評 (參考)": st.column_config.NumberColumn(disabled=True),
                            "初考評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                            "說明": st.column_config.TextColumn(disabled=True, width="medium"),
                            "考核項目": st.column_config.TextColumn(disabled=True),
                        },
                        hide_index=True, use_container_width=True, key="editor_primary"
                    )

                    # 綁定 Key 以便清空
                    manager_comment = st.text_area("初考評語", key="comment_primary_key")
                    
                    if st.button("✅ 提交初考", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            load_data_from_sheet.clear()
                            row_idx = find_row_index(data, target_name, target_date)
                            if row_idx:
                                headers = list(data[0].keys())
                                updates = []
                                try:
                                    # 批次更新邏輯
                                    status_col = headers.index("目前狀態") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待覆考"]]})
                                    
                                    score_sum_col = headers.index("初考總分") + 1
                                    total_score = int(edited_primary["初考評分"].sum())
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                    comment_col = headers.index("初考評語") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[manager_comment]]})

                                    for _, r in edited_primary.iterrows():
                                        col_name = f"{r['考核項目']}-初考"
                                        if col_name in headers:
                                            col_idx = headers.index(col_name) + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[int(r['初考評分'])]]})
                                    
                                    worksheet.batch_update(updates)

                                    # 清空評語，避免留給下一位
                                    st.session_state["comment_primary_key"] = ""
                                    
                                    st.success("✅ 初考完成！")
                                    time.sleep(1)
                                    st.rerun()

                                except ValueError as e:
                                    st.error(f"欄位對應錯誤: {e}")

    # ==========================================
    # Tab 3: 覆考主管審核
    # ==========================================
    with tabs[2]:
        st.header("👩‍⚕️ 覆考主管 (護理長) 審核區")
        show_guidelines()
        pwd2 = st.text_input("🔒 覆考主管密碼", type="password", key="pwd_secondary")

        if pwd2 == "2222": 
            data = load_data_from_sheet(worksheet)
            df_all = pd.DataFrame(data)

            if not df_all.empty and "目前狀態" in df_all.columns:
                pending_df = df_all[df_all["目前狀態"] == "待覆考"]
                if pending_df.empty:
                    st.info("🎉 目前沒有待審核的覆考案件。")
                else:
                    target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                    selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_secondary")
                    
                    target_name = selected_target.split(" (")[0]
                    target_date = selected_target.split(" (")[1].replace(")", "")
                    record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                    st.markdown("---")
                    user_role = record.get('職務身份', '一般員工')
                    st.subheader(f"正在審核：{target_name} ({user_role})")
                    
                    c1, c2 = st.columns(2)
                    c1.info(f"**自評總分**：{record.get('自評總分', 0)}\n\n💬 {record.get('自評文字', '')}")
                    if record.get('初考總分', 0) > 0: 
                        c2.warning(f"**初考總分**：{record.get('初考總分', 0)}\n\n💬 {record.get('初考評語', '')}")
                    else:
                        c2.warning("*(無初考紀錄)*")

                    items = get_assessment_items()
                    input_data = []
                    for item in items:
                        i_name = item["考核項目"]
                        input_data.append({
                            "考核項目": i_name,
                            "說明": item["說明"],
                            "自評": record.get(f"{i_name}-自評", 0),
                            "初考": record.get(f"{i_name}-初考", 0),
                            "覆考評分": 0
                        })
                    
                    df_sec = pd.DataFrame(input_data)
                    edited_sec = st.data_editor(
                        df_sec,
                        column_config={
                            "自評": st.column_config.NumberColumn(disabled=True),
                            "初考": st.column_config.NumberColumn(disabled=True),
                            "覆考評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                            "說明": st.column_config.TextColumn(disabled=True, width="medium"),
                            "考核項目": st.column_config.TextColumn(disabled=True),
                        },
                        hide_index=True, use_container_width=True, key="editor_sec"
                    )

                    sec_comment = st.text_area("覆考評語", key="comment_sec_key")
                    
                    if st.button("✅ 提交覆考", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            load_data_from_sheet.clear()
                            row_idx = find_row_index(data, target_name, target_date)
                            if row_idx:
                                headers = list(data[0].keys())
                                updates = []
                                
                                status_col = headers.index("目前狀態") + 1
                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待核決"]]})
                                
                                score_sum_col = headers.index("覆考總分") + 1
                                total_score = int(edited_sec["覆考評分"].sum())
                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                comment_col = headers.index("覆考評語") + 1
                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[sec_comment]]})

                                for _, r in edited_sec.iterrows():
                                    col_name = f"{r['考核項目']}-覆考"
                                    if col_name in headers:
                                        col_idx = headers.index(col_name) + 1
                                        updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[int(r['覆考評分'])]]})
                                
                                worksheet.batch_update(updates)

                                # 清空評語
                                st.session_state["comment_sec_key"] = ""

                                st.success("✅ 覆考完成！")
                                time.sleep(1)
                                st.rerun()

    # ==========================================
    # Tab 4: 老闆最終核決
    # ==========================================
    with tabs[3]:
        st.header("🏆 老闆核決區")
        show_guidelines() 
        pwd3 = st.text_input("🔒 老闆密碼", type="password", key="pwd_boss")

        if pwd3 == "8888": 
            data = load_data_from_sheet(worksheet)
            df_all = pd.DataFrame(data)
            view_mode = st.radio("檢視模式", ["待核決案件", "歷史已完成案件"], horizontal=True)

            if not df_all.empty and "目前狀態" in df_all.columns:
                if view_mode == "待核決案件":
                    pending_df = df_all[df_all["目前狀態"] == "待核決"]
                else:
                    pending_df = df_all[df_all["目前狀態"] == "已完成"]

                if pending_df.empty:
                    st.info(f"🎉 目前沒有 {view_mode}。")
                else:
                    target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                    selected_target = st.selectbox("請選擇對象", target_options, key="sel_boss")
                    
                    target_name = selected_target.split(" (")[0]
                    target_date = selected_target.split(" (")[1].replace(")", "")
                    record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                    st.markdown("---")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("自評總分", record.get('自評總分', 0))
                    col2.metric("初考總分", record.get('初考總分', 0))
                    col3.metric("覆考總分", record.get('覆考總分', 0))
                    
                    if view_mode == "歷史已完成案件":
                        col4.metric("🏆 最終總分", record.get('最終總分', 0))
                        st.success(f"📌 最終建議：{record.get('最終建議', '')}")
                        
                        st.markdown("### 詳細成績單")
                        items = get_assessment_items()
                        detail_rows = []
                        for item in items:
                            i_name = item["考核項目"]
                            detail_rows.append({
                                "考核項目": i_name,
                                "自評": str(record.get(f"{i_name}-自評", "-")),
                                "初考": str(record.get(f"{i_name}-初考", "-")),
                                "覆考": str(record.get(f"{i_name}-覆考", "-")),
                                "最終": str(record.get(f"{i_name}-最終", "-")),
                            })
                        st.table(pd.DataFrame(detail_rows))
                    else: 
                        st.warning("請填寫最終成績以完成考核。")
                        items = get_assessment_items()
                        input_data = []
                        for item in items:
                            i_name = item["考核項目"]
                            input_data.append({
                                "考核項目": i_name,
                                "說明": item["說明"],
                                "自評": record.get(f"{i_name}-自評", 0),
                                "初考": record.get(f"{i_name}-初考", 0),
                                "覆考": record.get(f"{i_name}-覆考", 0),
                                "最終評分": 0 
                            })
                        
                        df_boss = pd.DataFrame(input_data)
                        edited_boss = st.data_editor(
                            df_boss,
                            column_config={
                                "自評": st.column_config.NumberColumn(disabled=True),
                                "初考": st.column_config.NumberColumn(disabled=True),
                                "覆考": st.column_config.NumberColumn(disabled=True),
                                "最終評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                                "說明": st.column_config.TextColumn(disabled=True, width="medium"),
                                "考核項目": st.column_config.TextColumn(disabled=True),
                            },
                            hide_index=True, use_container_width=True, key="editor_boss"
                        )
                        
                        final_action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])
                        
                        if st.button("🏆 核決並歸檔", type="primary"):
                            with st.spinner("正在歸檔..."):
                                load_data_from_sheet.clear()
                                row_idx = find_row_index(data, target_name, target_date)
                                if row_idx:
                                    headers = list(data[0].keys())
                                    updates = []
                                    status_col = headers.index("目前狀態") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["已完成"]]})
                                    
                                    score_sum_col = headers.index("最終總分") + 1
                                    total_score = int(edited_boss["最終評分"].sum())
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                    suggest_col = headers.index("最終建議") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, suggest_col), "values": [[final_action]]})

                                    for _, r in edited_boss.iterrows():
                                        col_name = f"{r['考核項目']}-最終"
                                        if col_name in headers:
                                            col_idx = headers.index(col_name) + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[int(r['最終評分'])]]})
                                    
                                    worksheet.batch_update(updates)
                                    st.balloons()
                                    st.success("🎉 考核流程圓滿結束！")
                                    time.sleep(2)
                                    st.rerun()

if __name__ == "__main__":
    main()
