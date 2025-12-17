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

# --- 輔助函數：尋找資料所在的列數 (Row Index) ---
def find_row_index(worksheet, name, assess_date):
    """根據姓名和日期，找出 Google Sheet 中的列數 (從 1 開始)"""
    all_values = worksheet.get_all_values()
    # 假設姓名在第 1 欄 (index 0)，日期在第 3 欄 (index 2)
    # 請根據您的 Sheet 實際標題順序調整這裡的 index
    headers = all_values[0]
    try:
        name_idx = headers.index("姓名")
        date_idx = headers.index("日期")
    except:
        return None

    for i, row in enumerate(all_values):
        if i == 0: continue # 跳過標題
        # 比對姓名和日期 (日期轉字串比對)
        if row[name_idx] == name and row[date_idx] == str(assess_date):
            return i + 1 # Google Sheet 行數從 1 開始
    return None

# --- 輔助函數：定義評分細項 ---
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

    # --- 建立分頁 (Tabs) ---
    tabs = st.tabs(["1️⃣ 員工自評", "2️⃣ 初考主管審核", "3️⃣ 覆考主管審核", "4️⃣ 老闆最終核決"])

    # ==========================================
    # Tab 1: 員工自評 (流程起點)
    # ==========================================
    with tabs[0]:
        st.header("📝 員工自評區")
        st.info("填寫完畢後，資料將自動送往下一關主管。")

        col1, col2, col3 = st.columns(3)
        with col1: name = st.text_input("姓名", placeholder="請輸入您的姓名")
        with col2: 
            # 關鍵邏輯：選擇身份決定下一關去哪
            role = st.selectbox("您的職務身份", ["一般員工", "初考主管 (管理者)", "覆考主管 (護理長)"])
        with col3: assess_date = st.date_input("評量日期", date.today())

        # 根據身份決定初始狀態
        if role == "一般員工":
            next_status = "待初考"
            next_step_hint = "提交後將傳送給：初考主管"
        elif role == "初考主管 (管理者)":
            next_status = "待覆考"
            next_step_hint = "提交後將傳送給：覆考主管 (您跳過了初考階段)"
        else: # 護理長
            next_status = "待核決"
            next_step_hint = "提交後將傳送給：老闆 (您跳過了初覆考階段)"

        st.caption(f"ℹ️ {next_step_hint}")

        # 建立評分表 (只開放自評欄位)
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
                "說明": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_self"
        )
        
        self_comment = st.text_area("自評文字", placeholder="請輸入您的自評內容...")

        if st.button("🚀 送出自評", type="primary"):
            if not name:
                st.error("請填寫姓名")
            else:
                with st.spinner("資料傳送中..."):
                    # 準備標題 (確保包含目前狀態)
                    headers = ["目前狀態", "姓名", "職務身份", "日期", 
                               "自評總分", "初考總分", "覆考總分", "最終總分",
                               "自評文字", "初考評語", "覆考評語", "最終建議", "填寫時間"]
                    
                    # 準備資料 row
                    # 預設其他分數為 0，避免空值
                    row_data = [
                        next_status, name, role, assess_date.strftime("%Y-%m-%d"),
                        int(edited_df["自評"].sum()), 0, 0, 0,
                        self_comment, "", "", "", 
                        pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]

                    # 處理細項分數 (全部扁平化)
                    for _, row in edited_df.iterrows():
                        item = row["考核項目"]
                        # 檢查標題是否存在
                        if f"{item}-自評" not in headers:
                            headers.extend([f"{item}-自評", f"{item}-初考", f"{item}-覆考", f"{item}-最終"])
                        # 填入自評分數，其他預設 0
                        row_data.extend([int(row["自評"]), 0, 0, 0])

                    # 寫入 Sheet
                    all_values = worksheet.get_all_values()
                    if not all_values:
                        worksheet.append_row(headers)
                    elif all_values[0] != headers:
                        # 簡單防呆：如果標題變了，這裡只做簡單處理，實務上建議固定標題
                        pass 

                    worksheet.append_row(row_data)
                    st.success(f"✅ 自評已送出！案件已轉移至【{next_status}】列表。")
                    time.sleep(2)
                    st.rerun()

    # ==========================================
    # Tab 2: 初考主管審核
    # ==========================================
    with tabs[1]:
        st.header("👮‍♂️ 初考主管審核區")
        pwd1 = st.text_input("🔒 初考主管密碼", type="password", key="pwd_primary")
        
        if pwd1 == "1111": # 預設密碼
            # 1. 從 Sheet 撈出所有資料
            data = worksheet.get_all_records()
            df_all = pd.DataFrame(data)

            if not df_all.empty and "目前狀態" in df_all.columns:
                # 2. 篩選：只顯示「待初考」的單子
                pending_df = df_all[df_all["目前狀態"] == "待初考"]

                if pending_df.empty:
                    st.info("🎉 目前沒有待審核的初考案件。")
                else:
                    st.write(f"待審核案件：{len(pending_df)} 筆")
                    
                    # 選擇要審核的人
                    target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                    selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_primary")
                    
                    # 找出該筆資料
                    target_name = selected_target.split(" (")[0]
                    target_date = selected_target.split(" (")[1].replace(")", "")
                    record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                    st.markdown("---")
                    st.subheader(f"正在審核：{target_name}")
                    st.write(f"**員工自評總分**：{record['自評總分']}")
                    st.info(f"🗨️ **員工自評內容**：{record['自評文字']}")

                    # 3. 建立評分表 (讀取自評，填寫初考)
                    items = get_assessment_items()
                    input_data = []
                    for item in items:
                        i_name = item["考核項目"]
                        input_data.append({
                            "考核項目": i_name,
                            "說明": item["說明"],
                            "自評 (參考)": record.get(f"{i_name}-自評", 0),
                            "初考評分": 0 # 預設
                        })
                    
                    df_primary = pd.DataFrame(input_data)
                    edited_primary = st.data_editor(
                        df_primary,
                        column_config={
                            "自評 (參考)": st.column_config.NumberColumn(disabled=True),
                            "初考評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                            "說明": st.column_config.TextColumn(disabled=True),
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="editor_primary"
                    )

                    manager_comment = st.text_area("初考評語", key="comment_primary")
                    
                    if st.button("✅ 提交初考 (傳送給覆考主管)", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            # 1. 找出這筆資料在 Sheet 的第幾列
                            row_idx = find_row_index(worksheet, target_name, target_date)
                            
                            if row_idx:
                                headers = worksheet.row_values(1)
                                updates = []

                                # 更新狀態 -> 待覆考
                                try:
                                    status_col = headers.index("目前狀態") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待覆考"]]})
                                    
                                    # 更新初考總分
                                    score_sum_col = headers.index("初考總分") + 1
                                    total_score = int(edited_primary["初考評分"].sum())
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                    # 更新初考評語
                                    comment_col = headers.index("初考評語") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[manager_comment]]})

                                    # 更新細項分數
                                    for _, r in edited_primary.iterrows():
                                        col_name = f"{r['考核項目']}-初考"
                                        if col_name in headers:
                                            col_idx = headers.index(col_name) + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[int(r['初考評分'])]]})
                                    
                                    # 執行批次更新
                                    worksheet.batch_update(updates)
                                    st.success("✅ 初考完成！案件已移交給覆考主管。")
                                    time.sleep(2)
                                    st.rerun()

                                except ValueError as e:
                                    st.error(f"欄位對應錯誤，請檢查 Sheet 標題。{e}")
                            else:
                                st.error("❌ 找不到原始資料列，請聯繫管理員。")

    # ==========================================
    # Tab 3: 覆考主管審核
    # ==========================================
    with tabs[2]:
        st.header("👩‍⚕️ 覆考主管 (護理長) 審核區")
        pwd2 = st.text_input("🔒 覆考主管密碼", type="password", key="pwd_secondary")

        if pwd2 == "2222": # 預設密碼
            data = worksheet.get_all_records()
            df_all = pd.DataFrame(data)

            if not df_all.empty and "目前狀態" in df_all.columns:
                # 篩選：只顯示「待覆考」的單子
                pending_df = df_all[df_all["目前狀態"] == "待覆考"]

                if pending_df.empty:
                    st.info("🎉 目前沒有待審核的覆考案件。")
                else:
                    st.write(f"待審核案件：{len(pending_df)} 筆")
                    target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                    selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_secondary")
                    
                    target_name = selected_target.split(" (")[0]
                    target_date = selected_target.split(" (")[1].replace(")", "")
                    record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                    st.markdown("---")
                    st.subheader(f"正在審核：{target_name} ({record['職務身份']})")
                    
                    # 顯示前兩關的資訊
                    c1, c2 = st.columns(2)
                    c1.info(f"**自評總分**：{record['自評總分']}\n\n💬 {record['自評文字']}")
                    if record['初考總分'] > 0: # 如果有經過初考
                        c2.warning(f"**初考總分**：{record['初考總分']}\n\n💬 {record['初考評語']}")
                    else:
                        c2.warning("*(此案件由主管直接發起，無初考紀錄)*")

                    # 建立評分表
                    items = get_assessment_items()
                    input_data = []
                    for item in items:
                        i_name = item["考核項目"]
                        input_data.append({
                            "考核項目": i_name,
                            "自評": record.get(f"{i_name}-自評", 0),
                            "初考": record.get(f"{i_name}-初考", 0),
                            "覆考評分": 0 # 預設
                        })
                    
                    df_sec = pd.DataFrame(input_data)
                    edited_sec = st.data_editor(
                        df_sec,
                        column_config={
                            "自評": st.column_config.NumberColumn(disabled=True),
                            "初考": st.column_config.NumberColumn(disabled=True),
                            "覆考評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="editor_sec"
                    )

                    sec_comment = st.text_area("覆考評語", key="comment_sec")
                    
                    if st.button("✅ 提交覆考 (傳送給老闆)", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            row_idx = find_row_index(worksheet, target_name, target_date)
                            if row_idx:
                                headers = worksheet.row_values(1)
                                updates = []
                                
                                # 更新狀態 -> 待核決
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
                                st.success("✅ 覆考完成！案件已移交給老闆核決。")
                                time.sleep(2)
                                st.rerun()

    # ==========================================
    # Tab 4: 老闆最終核決
    # ==========================================
    with tabs[3]:
        st.header("🏆 老闆核決區")
        pwd3 = st.text_input("🔒 老闆密碼", type="password", key="pwd_boss")

        if pwd3 == "8888": # 預設密碼
            data = worksheet.get_all_records()
            df_all = pd.DataFrame(data)

            # 這裡我們只顯示「待核決」的，但也提供一個選項看「已完成」的
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
                    
                    # 顯示總覽
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("自評總分", record['自評總分'])
                    col2.metric("初考總分", record['初考總分'])
                    col3.metric("覆考總分", record['覆考總分'])
                    
                    if view_mode == "歷史已完成案件":
                        col4.metric("🏆 最終總分", record['最終總分'])
                        st.success(f"📌 最終建議：{record['最終建議']}")
                        
                        # 顯示詳細成績單 (Static Table)
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

                    else: # 待核決模式
                        st.warning("請填寫最終成績以完成考核。")
                        
                        # 建立評分表
                        items = get_assessment_items()
                        input_data = []
                        for item in items:
                            i_name = item["考核項目"]
                            input_data.append({
                                "考核項目": i_name,
                                "自評": record.get(f"{i_name}-自評", 0),
                                "初考": record.get(f"{i_name}-初考", 0),
                                "覆考": record.get(f"{i_name}-覆考", 0),
                                "最終評分": 0 # 預設
                            })
                        
                        df_boss = pd.DataFrame(input_data)
                        edited_boss = st.data_editor(
                            df_boss,
                            column_config={
                                "自評": st.column_config.NumberColumn(disabled=True),
                                "初考": st.column_config.NumberColumn(disabled=True),
                                "覆考": st.column_config.NumberColumn(disabled=True),
                                "最終評分": st.column_config.NumberColumn(min_value=0, max_value=10, step=1, required=True),
                            },
                            hide_index=True,
                            use_container_width=True,
                            key="editor_boss"
                        )
                        
                        final_action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])
                        
                        if st.button("🏆 核決並歸檔", type="primary"):
                            with st.spinner("正在歸檔..."):
                                row_idx = find_row_index(worksheet, target_name, target_date)
                                if row_idx:
                                    headers = worksheet.row_values(1)
                                    updates = []
                                    
                                    # 更新狀態 -> 已完成
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
