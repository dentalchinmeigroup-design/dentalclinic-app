import streamlit as st
import pandas as pd
from datetime import date, datetime
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

# --- 2. 安全讀取與寫入 (自動重試機制) ---
def safe_read_data(worksheet):
    for i in range(3):
        try:
            return worksheet.get_all_records()
        except Exception as e:
            time.sleep(1.5)
            if i == 2:
                st.error(f"連線繁忙，請稍後再試。({e})")
                st.stop()

@st.cache_data(ttl=5)
def load_data_from_sheet(_worksheet):
    return safe_read_data(_worksheet)

def safe_batch_update(worksheet, updates):
    for i in range(3):
        try:
            worksheet.batch_update(updates)
            return True
        except Exception:
            time.sleep(2)
    st.error("寫入失敗，請檢查網路或稍後再試。")
    return False

# --- 3. 核心功能：依據標題寫入資料 ---
def save_data_using_headers(worksheet, data_dict):
    for attempt in range(3):
        try:
            raw_headers = worksheet.row_values(1)
            existing_headers = [h.strip() for h in raw_headers]
            
            if not existing_headers:
                existing_headers = list(data_dict.keys())
                worksheet.append_row(existing_headers)
                raw_headers = existing_headers
            
            new_cols = [k for k in data_dict.keys() if k not in existing_headers]
            if new_cols:
                worksheet.add_cols(len(new_cols))
                for i, col_name in enumerate(new_cols):
                    worksheet.update_cell(1, len(raw_headers) + i + 1, col_name)
                existing_headers.extend(new_cols)
                
            row_values = []
            for header in existing_headers:
                val = data_dict.get(header, "")
                row_values.append(val)
                
            worksheet.append_row(row_values)
            return 
        except Exception:
            time.sleep(1.5)

# --- 4. 輔助函數：分數計算與資料尋找 ---
def calculate_dynamic_score(record, suffix):
    items = get_assessment_items()
    total = 0
    for item in items:
        key = f"{item['考核項目']}{suffix}"
        val = record.get(key, 0)
        if str(val) == "N/A": continue
        try:
            total += int(float(val))
        except:
            total += 0
    return total

def normalize_date(date_str):
    """將各種日期的字串格式統一化，避免比對失敗"""
    try:
        # 嘗試解析 YYYY-MM-DD 或 YYYY/MM/DD
        d = pd.to_datetime(str(date_str))
        return d.strftime("%Y-%m-%d")
    except:
        return str(date_str)

def find_row_index(all_values, name, assess_date):
    """
    更強大的搜尋功能：
    1. 忽略姓名空格
    2. 統一日期格式後再比對
    """
    if not all_values: return None
    df = pd.DataFrame(all_values)
    
    # 資料處理：統一格式
    target_date = normalize_date(assess_date)
    df["normalized_date"] = df["日期"].apply(normalize_date)
    df["clean_name"] = df["姓名"].astype(str).str.strip()
    target_name = name.strip()
    
    match = df.index[(df["clean_name"] == target_name) & (df["normalized_date"] == target_date)].tolist()
    
    if match:
        return match[0] + 2 # +2 (1-based index + header)
    return None

# --- 5. Session State ---
def init_session_state():
    # 這裡我們不需要複雜的計數器了，因為新的 UI 邏輯會自動刷新
    pass

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
            * **N/A (不適用)**：此項目不列入考核。
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

SCORE_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"]

# --- 6. 新的 UI 渲染函數：直覺式條列選單 ---
def render_assessment_ui(prefix, default_scores=None):
    """
    prefix: 用來區分不同分頁的 key (例如 'self', 'primary')
    default_scores: 如果是編輯模式，傳入原本的分數 dict
    回傳: 使用者選填的分數 dict
    """
    items = get_assessment_items()
    user_scores = {}
    
    st.markdown("### 📝 詳細評分項目")
    st.info("💡 點擊右側選單即可直接選擇分數，無需點擊兩下。")
    
    for idx, item in enumerate(items):
        with st.container():
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**{idx+1}. {item['考核項目']}**")
                st.caption(f"說明：{item['說明']}")
            with c2:
                # 決定預設值
                current_val = 0
                if default_scores:
                    # 嘗試抓取既有分數，如果沒有則預設 0
                    val = default_scores.get(item['考核項目'], 0)
                    if val in SCORE_OPTIONS:
                        current_val = val
                
                # 這裡的 index 是為了讓選單預設停在該分數上
                try:
                    default_idx = SCORE_OPTIONS.index(current_val)
                except:
                    default_idx = 0
                
                score = st.selectbox(
                    f"評分 ({item['考核項目']})", 
                    options=SCORE_OPTIONS,
                    index=default_idx,
                    key=f"{prefix}_score_{idx}",
                    label_visibility="collapsed" # 隱藏標籤讓版面更乾淨
                )
                user_scores[item['考核項目']] = score
            st.divider() # 加分隔線更清楚
            
    return user_scores

def safe_sum_scores_from_dict(score_dict):
    total = 0
    for val in score_dict.values():
        if str(val) == "N/A": continue
        try:
            total += int(float(val))
        except:
            pass
    return total

def main():
    st.set_page_config(page_title="考核系統流程版", layout="wide")
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子 | 考核系統 (直覺版)")
    
    init_session_state() 
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
        show_guidelines()

        col1, col2, col3 = st.columns(3)
        with col1: name = st.text_input("姓名", placeholder="請輸入姓名")
        with col2: role = st.selectbox("您的職務身份", ["一般員工", "初考主管 (管理者)", "覆考主管 (護理長)"])
        with col3: assess_date = st.date_input("評量日期", date.today())

        if role == "一般員工": next_status = "待初考"
        elif role == "初考主管 (管理者)": next_status = "待覆考"
        else: next_status = "待核決"

        # --- 使用新的 UI 渲染函數 ---
        user_scores = render_assessment_ui("self")
        
        self_comment = st.text_area("自評文字", placeholder="請輸入...", key="self_comment_area")

        if st.button("🚀 送出自評", type="primary"):
            if not name:
                st.error("請填寫姓名")
            else:
                with st.spinner("資料傳送中..."):
                    load_data_from_sheet.clear()
                    total_score = safe_sum_scores_from_dict(user_scores)

                    data_to_save = {
                        "目前狀態": next_status,
                        "姓名": name,
                        "職務身份": role,
                        "日期": assess_date.strftime("%Y-%m-%d"),
                        "自評總分": total_score,
                        "初考總分": 0, "覆考總分": 0, "最終總分": 0,
                        "自評文字": self_comment,
                        "初考評語": "", "覆考評語": "", "最終建議": "",
                        "填寫時間": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    for item_name, score in user_scores.items():
                        data_to_save[f"{item_name}-自評"] = score
                        data_to_save[f"{item_name}-初考"] = 0
                        data_to_save[f"{item_name}-覆考"] = 0
                        data_to_save[f"{item_name}-最終"] = 0

                    save_data_using_headers(worksheet, data_to_save)
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
                    
                    real_self_score = calculate_dynamic_score(record, '-自評')
                    st.write(f"**員工自評總分**：{real_self_score}")
                    st.info(f"🗨️ **員工自評內容**：{record.get('自評文字', '')}")

                    # --- 顯示新的 UI ---
                    # 這裡不需要傳入 default_scores，因為初考主管是填新的分數
                    manager_scores = render_assessment_ui("primary")

                    manager_comment = st.text_area("初考評語", key="comment_primary_area")
                    
                    if st.button("✅ 提交初考", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            load_data_from_sheet.clear()
                            row_idx = find_row_index(data, target_name, target_date)
                            
                            if row_idx:
                                headers = list(data[0].keys())
                                clean_headers = [h.strip() for h in headers]
                                updates = []
                                try:
                                    status_col = clean_headers.index("目前狀態") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待覆考"]]})
                                    
                                    total_score = safe_sum_scores_from_dict(manager_scores)
                                    score_sum_col = clean_headers.index("初考總分") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                    comment_col = clean_headers.index("初考評語") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[manager_comment]]})

                                    for item_name, score in manager_scores.items():
                                        col_name = f"{item_name}-初考"
                                        if col_name in clean_headers:
                                            col_idx = clean_headers.index(col_name) + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                    
                                    safe_batch_update(worksheet, updates)
                                    st.success("✅ 初考完成！")
                                    time.sleep(1)
                                    st.rerun()
                                except ValueError as e:
                                    st.error(f"欄位對應錯誤: {e}")
                            else:
                                st.error("❌ 找不到原始資料列，請確認日期格式是否一致。")

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
                    
                    real_self_score = calculate_dynamic_score(record, '-自評')
                    real_primary_score = calculate_dynamic_score(record, '-初考')
                    
                    c1, c2 = st.columns(2)
                    c1.info(f"**自評總分**：{real_self_score}\n\n💬 {record.get('自評文字', '')}")
                    if real_primary_score > 0:
                        c2.warning(f"**初考總分**：{real_primary_score}\n\n💬 {record.get('初考評語', '')}")
                    else:
                        c2.warning("*(無初考紀錄)*")

                    # --- 顯示新的 UI ---
                    manager_scores = render_assessment_ui("secondary")

                    sec_comment = st.text_area("覆考評語", key="comment_sec_area")
                    
                    if st.button("✅ 提交覆考", type="primary"):
                        with st.spinner("更新資料庫中..."):
                            load_data_from_sheet.clear()
                            row_idx = find_row_index(data, target_name, target_date)
                            if row_idx:
                                headers = list(data[0].keys())
                                clean_headers = [h.strip() for h in headers]
                                updates = []
                                try:
                                    status_col = clean_headers.index("目前狀態") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待核決"]]})
                                    
                                    total_score = safe_sum_scores_from_dict(manager_scores)
                                    score_sum_col = clean_headers.index("覆考總分") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                    comment_col = clean_headers.index("覆考評語") + 1
                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[sec_comment]]})

                                    for item_name, score in manager_scores.items():
                                        col_name = f"{item_name}-覆考"
                                        if col_name in clean_headers:
                                            col_idx = clean_headers.index(col_name) + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                    
                                    safe_batch_update(worksheet, updates)
                                    st.success("✅ 覆考完成！")
                                    time.sleep(1)
                                    st.rerun()
                                except ValueError as e:
                                    st.error(f"欄位錯誤: {e}")
                            else:
                                st.error("❌ 找不到原始資料列。")

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
                    
                    # --- 1. 顯示完整評語紀錄 ---
                    st.markdown("### 📝 各階段評語紀錄")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.info(f"**🗣️ 員工自評**\n\n{record.get('自評文字', '無')}")
                    with c2:
                        st.warning(f"**👮‍♂️ 初考評語**\n\n{record.get('初考評語', '無')}")
                    with c3:
                        st.error(f"**👩‍⚕️ 覆考評語**\n\n{record.get('覆考評語', '無')}")

                    st.markdown("---")
                    
                    real_self = calculate_dynamic_score(record, '-自評')
                    real_prim = calculate_dynamic_score(record, '-初考')
                    real_sec = calculate_dynamic_score(record, '-覆考')
                    real_final = calculate_dynamic_score(record, '-最終')

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("自評總分", real_self)
                    col2.metric("初考總分", real_prim)
                    col3.metric("覆考總分", real_sec)
                    
                    if view_mode == "歷史已完成案件":
                        col4.metric("🏆 最終總分", real_final)
                        st.success(f"📌 最終建議：{record.get('最終建議', '')}")
                        st.success(f"🏅 最終考績：{record.get('最終考績', '未評定')}")
                        
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
                        st.warning("請填寫最終成績與考績以完成考核。")
                        
                        # --- 顯示新的 UI ---
                        boss_scores = render_assessment_ui("boss")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            final_action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])
                        with c2:
                            final_grade = st.selectbox("🏅 最終考績", ["S", "A+", "A", "A-", "B"])
                        
                        if st.button("🏆 核決並歸檔", type="primary"):
                            with st.spinner("正在歸檔..."):
                                load_data_from_sheet.clear()
                                row_idx = find_row_index(data, target_name, target_date)
                                if row_idx:
                                    headers = list(data[0].keys())
                                    clean_headers = [h.strip() for h in headers]
                                    updates = []
                                    
                                    try:
                                        if "最終考績" not in clean_headers:
                                            st.toast("正在新增【最終考績】欄位...", icon="🔧")
                                            worksheet.update_cell(1, len(clean_headers) + 1, "最終考績")
                                            clean_headers.append("最終考績")
                                            time.sleep(1)

                                        status_col = clean_headers.index("目前狀態") + 1
                                        updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["已完成"]]})
                                        
                                        total_score = safe_sum_scores_from_dict(boss_scores)
                                        score_sum_col = clean_headers.index("最終總分") + 1
                                        updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                        suggest_col = clean_headers.index("最終建議") + 1
                                        updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, suggest_col), "values": [[final_action]]})
                                        
                                        grade_col = clean_headers.index("最終考績") + 1
                                        updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, grade_col), "values": [[final_grade]]})

                                        for item_name, score in boss_scores.items():
                                            col_name = f"{item_name}-最終"
                                            if col_name in clean_headers:
                                                col_idx = clean_headers.index(col_name) + 1
                                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                        
                                        safe_batch_update(worksheet, updates)
                                        st.balloons()
                                        st.success("🎉 考核流程圓滿結束！")
                                        time.sleep(2)
                                        st.rerun()
                                    except ValueError as e:
                                        st.error(f"欄位錯誤: {e}")
                                else:
                                    st.error("❌ 找不到原始資料列。")

if __name__ == "__main__":
    main()
