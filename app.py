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

# --- 2. 安全讀取與寫入 ---
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

# --- 4. 輔助函數 ---
def calculate_dynamic_score(record, suffix, ref_suffix="-自評"):
    items = get_assessment_items()
    total = 0
    max_score = 0
    for item in items:
        key = f"{item['考核項目']}{suffix}"
        val = record.get(key, 0)
        ref_key = f"{item['考核項目']}{ref_suffix}"
        ref_val = record.get(ref_key, 0)
        
        if str(ref_val) == "N/A": continue
        max_score += 10
        
        if str(val) == "N/A": continue
        try:
            total += int(float(val))
        except:
            total += 0
    return total, max_score

def normalize_date(date_str):
    try:
        d = pd.to_datetime(str(date_str))
        return d.strftime("%Y-%m-%d")
    except:
        return str(date_str).strip()

def find_row_index(all_values, name, assess_date):
    if not all_values: return None, None
    df = pd.DataFrame(all_values)
    target_date = normalize_date(assess_date)
    df["normalized_date"] = df["日期"].apply(normalize_date)
    df["clean_name"] = df["姓名"].astype(str).str.strip()
    target_name = name.strip()
    match = df.index[(df["clean_name"] == target_name) & (df["normalized_date"] == target_date)].tolist()
    if match:
        return match[0] + 2, df 
    return None, df

# --- 5. 計算平均值作為預設值 ---
def calculate_average_defaults(record):
    items = get_assessment_items()
    defaults = {}
    
    role = record.get('職務身份', '一般員工')
    group = record.get('初考組別', '')
    
    stages = ['-自評']
    if role == '一般員工':
        if group != '免初考':
            stages.append('-初考')
        stages.append('-覆考')
    elif role == '主管':
        stages.append('-覆考')
    
    for item in items:
        name = item['考核項目']
        scores = []
        for s in stages:
            val = record.get(f"{name}{s}", 0)
            if str(val) != 'N/A':
                try:
                    scores.append(float(val))
                except:
                    pass
        
        if scores:
            avg = int(sum(scores) / len(scores) + 0.5)
            avg = max(0, min(10, avg))
            defaults[name] = avg
        else:
            defaults[name] = 0
            
    return defaults

# --- 6. 資安防護網 ---
def add_security_watermark(username):
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    css = f"""
    <style>
    div.stApp {{
        user-select: none; 
        -webkit-user-select: none;
    }}
    input, textarea {{
        user-select: text !important;
        -webkit-user-select: text !important;
    }}
    .watermark {{
        position: fixed;
        bottom: 10px;
        right: 10px;
        font-size: 12px;
        color: rgba(150, 150, 150, 0.4);
        z-index: 9999;
        pointer-events: none;
        font-family: sans-serif;
    }}
    </style>
    <script>
    document.addEventListener('contextmenu', event => event.preventDefault());
    </script>
    <div class="watermark">日沐‧勤美‧小日子 內部機密 | {username} | {timestamp} | 禁止外流</div>
    """
    st.markdown(css, unsafe_allow_html=True)

def show_completion_screen(title, message, unique_key):
    st.success(f"✅ {title}")
    st.markdown(f"### {message}")
    st.markdown("---")
    st.info("💡 為了資訊安全，考核內容已隱藏。如需修改或查詢，請聯繫管理單位。")
    if st.button("🔄 返回首頁 / 填寫下一筆", key=unique_key):
        for key in list(st.session_state.keys()):
            if key.startswith("submitted_"):
                del st.session_state[key]
        st.rerun()

def init_session_state():
    keys = [
        "key_counter_self", "key_counter_clinical", "key_counter_front", 
        "key_counter_sec", "key_counter_boss",
        "submitted_self", "submitted_clinical", "submitted_front", 
        "submitted_sec", "submitted_boss"
    ]
    for k in keys:
        if k not in st.session_state:
            st.session_state[k] = 0 if "counter" in k else False

def show_guidelines():
    """依據 PDF 內容顯示評分標準與職能定義"""
    
    # [關鍵修改] 警語移出 expander，置頂顯示
    st.error("⚠️ 本考核表內容屬診所機密，嚴禁翻拍外流")
    
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
            * **勤務配合**：遵循規範，維持良好的出勤紀律，並能在工作中展現積極的態度與持續進取的企圖心。
            * **人際協作**：與同儕保持良好互動，尊重並服從上下級指示，具備良好的團隊合作能力。
            ### 3. 行政職能
            * **基礎行政**：具備確保診所日常營運穩定的專業能力，能完成行政與支援工作，並有效執行主管交辦任務。
            * **應變與支援**：同時具備高度應變與問題解決能力，能即時處理突發需求，主動支援並展現團隊合作精神。
            """)

def get_assessment_items():
    return [
        {"類別": "專業技能", "考核項目": "跟診技能", "說明": "跟診：器械與診間準備，依照SOP操作，器械準備熟練，無重大缺失；耗材不足能立即補充。"},
        {"類別": "專業技能", "考核項目": "櫃台技能", "說明": "櫃台：準確完成約診、報表與櫃檯行政作業，確保資料正確無誤。"},
        {"類別": "職能表現", "考核項目": "跟診執行", "說明": "跟診：正確執行確保診療不中斷，即時支援醫師需求、維持看診流暢與病患舒適。"},
        {"類別": "職能表現", "考核項目": "櫃台溝通", "說明": "櫃台：與醫師、病人有良好雙向溝通；正確傳達資訊；態度親切專業。"},
        {"類別": "職能表現", "考核項目": "勤務配合(職能)", "說明": "遵守出勤與請假規範，配合排班並主動協調上班時段，確保診所營運正常。"},
        {"類別": "職能表現", "考核項目": "勤務配合(配合)", "說明": "積極參與牙科訓練課程，確實出席並將所學應用於工作。"},
        {"類別": "職能表現", "考核項目": "人際協作(人際)", "說明": "日常能與同儕互助幫忙。診所高峰期主動支援同事，展現跨站協作，確保流程順暢。"},
        {"類別": "職能表現", "考核項目": "人際協作(協作)", "說明": "能尊重並聽從前輩指示、保持友好互動，並在帶領新人時展現良好態度與指導能力。"},
        {"類別": "行政職能", "考核項目": "危機處理", "說明": "危機處理：能即時處理各種突發事件，並主動預防問題再次發生。團隊參與：主動參加診所活動，在需要時幫忙支援，展現參與度與團隊向心力。"},
        {"類別": "行政職能", "考核項目": "基礎職能", "說明": "基礎職能：能確實完成行政工作，如：維修、牙材、牙模等等，確保診所運作穩定。"},
        {"類別": "行政職能", "考核項目": "進階職能", "說明": "進階職能：能理解診所及老闆的工作要求，妥善效率完成交辦任務。"},
        {"類別": "行政職能", "考核項目": "應變能力", "說明": "應變能力：能因應老闆各種臨時需求，展現靈活與隨時投入的態度。"},
    ]

SCORE_OPTIONS_FULL = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"]
SCORE_OPTIONS_NUM = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# --- 7. UI 渲染函數 ---
def render_assessment_in_form(prefix, key_suffix, record=None, readonly_stages=None, is_self_eval=False, default_scores=None):
    items = get_assessment_items()
    user_scores = {}
    
    st.markdown("### 📝 詳細評分項目")
    
    for idx, item in enumerate(items):
        with st.container():
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**{idx+1}. {item['考核項目']}**")
                st.caption(f"說明：{item['說明']}")
                if record is not None and readonly_stages:
                    history_text = []
                    for suffix in readonly_stages:
                        stage_name = suffix.replace("-", "") 
                        score = record.get(f"{item['考核項目']}{suffix}", "-")
                        color = "blue" if "自評" in stage_name else "orange" if "初考" in stage_name else "red"
                        history_text.append(f":{color}[{stage_name}: {score}]")
                    if history_text:
                        st.markdown(" | ".join(history_text))

            with c2:
                options = SCORE_OPTIONS_FULL
                disabled = False
                current_index = 0
                
                # --- N/A 連動與預設值邏輯 ---
                if not is_self_eval and record is not None:
                    self_score = record.get(f"{item['考核項目']}-自評", 0)
                    
                    if str(self_score) == "N/A":
                        options = ["N/A"]
                        disabled = True
                        current_index = 0
                    else:
                        options = SCORE_OPTIONS_NUM
                        disabled = False
                        current_index = 0 
                        
                        if default_scores and item['考核項目'] in default_scores:
                            default_val = default_scores[item['考核項目']]
                            if default_val in options:
                                current_index = options.index(default_val)
                
                score = st.selectbox(
                    f"評分 ({item['考核項目']})", 
                    options=options,
                    index=current_index,
                    disabled=disabled,
                    key=f"{prefix}_score_{idx}_{key_suffix}", 
                    label_visibility="collapsed"
                )
                user_scores[item['考核項目']] = score
            st.divider()
    return user_scores

def safe_sum_scores_from_dict(score_dict):
    total = 0
    max_score = 0
    for val in score_dict.values():
        if str(val) == "N/A": continue
        try:
            total += int(float(val))
            max_score += 10
        except:
            pass
    return total, max_score

def main():
    st.set_page_config(page_title="考核系統", layout="wide")
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子 | 考核系統")
    
    init_session_state() 
    sh = connect_to_google_sheets()
    try:
        worksheet = sh.worksheet("Assessment_Data")
    except:
        worksheet = sh.add_worksheet(title="Assessment_Data", rows=100, cols=100)

    tabs = st.tabs(["1️⃣ 員工自評", "2️⃣ 初考(跟診)", "3️⃣ 初考(櫃檯)", "4️⃣ 覆考(護理長)", "5️⃣ 老闆核決"])

    # ==========================================
    # Tab 1: 員工自評
    # ==========================================
    with tabs[0]:
        if st.session_state.submitted_self:
            show_completion_screen("自評已提交", "資料已傳送給下一關主管。", "btn_back_self")
        else:
            st.header("📝 員工自評區")
            add_security_watermark("員工考核中")
            show_guidelines()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: 
                name = st.text_input("姓名", placeholder="請輸入姓名", key=f"name_{st.session_state.key_counter_self}")
            
            with col2: 
                role = st.selectbox("您的職務身份", ["一般員工", "主管", "護理長"], key=f"role_{st.session_state.key_counter_self}")
            
            with col3:
                primary_group = None
                if role == "一般員工":
                    primary_group = st.selectbox("上呈初考主管", ["跟診主管", "櫃檯主管"], help="請選擇負責考核您的直屬主管", key=f"pg_{st.session_state.key_counter_self}")
                else:
                    st.write("") 
                    st.info("✅ 此職務免填初考主管")
            
            with col4: 
                assess_date = st.date_input("評量日期", date.today(), key=f"date_{st.session_state.key_counter_self}")

            with st.form(key=f"form_self_{st.session_state.key_counter_self}"):
                if role == "一般員工": 
                    next_status = "待初考"
                elif role == "主管": 
                    next_status = "待覆考"
                else: 
                    next_status = "待核決"

                user_scores = render_assessment_in_form("self", st.session_state.key_counter_self, is_self_eval=True)
                self_comment = st.text_area("自評文字", placeholder="請輸入...")
                
                submitted = st.form_submit_button("🚀 送出自評", type="primary")

            if submitted:
                if not name:
                    st.error("請填寫姓名")
                else:
                    with st.spinner("資料傳送中..."):
                        load_data_from_sheet.clear()
                        total_score, max_score = safe_sum_scores_from_dict(user_scores)
                        
                        if primary_group:
                            group_val = "跟診" if primary_group == "跟診主管" else "櫃檯"
                        else:
                            group_val = "免初考"

                        data_to_save = {
                            "目前狀態": next_status,
                            "初考組別": group_val,
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
                        st.session_state.key_counter_self += 1
                        st.session_state.submitted_self = True
                        st.rerun()

    # ==========================================
    # Tab 2: 初考主管 (跟診)
    # ==========================================
    with tabs[1]:
        if st.session_state.submitted_clinical:
            show_completion_screen("初考(跟診)已完成", "案件已移交給覆考主管。", "btn_back_clin")
        else:
            st.header("🦷 初考主管審核 (跟診組)")
            add_security_watermark("跟診主管考核")
            show_guidelines() 
            pwd_clin = st.text_input("🔒 跟診主管密碼", type="password", key="pwd_clin")
            
            if pwd_clin == "1111": 
                data = load_data_from_sheet(worksheet)
                df_all = pd.DataFrame(data)

                if not df_all.empty and "目前狀態" in df_all.columns and "初考組別" in df_all.columns:
                    pending_df = df_all[
                        (df_all["目前狀態"] == "待初考") & 
                        (df_all["初考組別"] == "跟診")
                    ]
                    
                    if pending_df.empty:
                        st.info("🎉 目前沒有待審核的跟診組案件。")
                    else:
                        target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                        selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_clin")
                        
                        target_name = selected_target.split(" (")[0]
                        target_date = selected_target.split(" (")[1].replace(")", "")
                        record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                        st.markdown("---")
                        st.subheader(f"正在審核：{target_name}")
                        
                        real_self_score, self_max = calculate_dynamic_score(record, '-自評', '-自評')
                        st.write(f"**員工自評總分**：{real_self_score} / {self_max}")
                        st.info(f"🗨️ **員工自評內容**：{record.get('自評文字', '')}")

                        with st.form(key=f"form_clin_{st.session_state.key_counter_clinical}"):
                            manager_scores = render_assessment_in_form(
                                "clin", 
                                st.session_state.key_counter_clinical,
                                record=record,
                                readonly_stages=["-自評"],
                                is_self_eval=False
                            )
                            c1, c2 = st.columns(2)
                            with c1: manager_name = st.text_input("初考主管簽名")
                            with c2: manager_comment = st.text_area("初考評語")
                            submitted_clin = st.form_submit_button("✅ 提交初考", type="primary")
                        
                        if submitted_clin:
                            if not manager_name:
                                st.error("請簽名！")
                            else:
                                with st.spinner("更新資料庫中..."):
                                    load_data_from_sheet.clear()
                                    row_idx, debug_df = find_row_index(data, target_name, target_date)
                                    
                                    if row_idx:
                                        headers = list(data[0].keys())
                                        clean_headers = [h.strip() for h in headers]
                                        updates = []
                                        try:
                                            status_col = clean_headers.index("目前狀態") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待覆考"]]})
                                            
                                            total_score, max_score = safe_sum_scores_from_dict(manager_scores)
                                            score_sum_col = clean_headers.index("初考總分") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                            comment_col = clean_headers.index("初考評語") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[manager_comment]]})
                                            
                                            if "初考主管" in clean_headers:
                                                manager_col = clean_headers.index("初考主管") + 1
                                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, manager_col), "values": [[manager_name]]})

                                            for item_name, score in manager_scores.items():
                                                col_name = f"{item_name}-初考"
                                                if col_name in clean_headers:
                                                    col_idx = clean_headers.index(col_name) + 1
                                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                            
                                            safe_batch_update(worksheet, updates)
                                            st.session_state.key_counter_clinical += 1
                                            st.session_state.submitted_clinical = True
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(f"欄位錯誤: {e}")
                                    else:
                                        st.error("❌ 找不到資料。")

    # ==========================================
    # Tab 3: 初考主管 (櫃檯)
    # ==========================================
    with tabs[2]:
        if st.session_state.submitted_front:
            show_completion_screen("初考(櫃檯)已完成", "案件已移交給覆考主管。", "btn_back_front")
        else:
            st.header("🖥️ 初考主管審核 (櫃檯組)")
            add_security_watermark("櫃檯主管考核")
            show_guidelines()
            pwd_front = st.text_input("🔒 櫃檯主管密碼", type="password", key="pwd_front")
            
            if pwd_front == "3333": 
                data = load_data_from_sheet(worksheet)
                df_all = pd.DataFrame(data)

                if not df_all.empty and "目前狀態" in df_all.columns and "初考組別" in df_all.columns:
                    pending_df = df_all[
                        (df_all["目前狀態"] == "待初考") & 
                        (df_all["初考組別"] == "櫃檯")
                    ]
                    
                    if pending_df.empty:
                        st.info("🎉 目前沒有待審核的櫃檯組案件。")
                    else:
                        target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                        selected_target = st.selectbox("請選擇審核對象", target_options, key="sel_front")
                        
                        target_name = selected_target.split(" (")[0]
                        target_date = selected_target.split(" (")[1].replace(")", "")
                        record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date)].iloc[0]

                        st.markdown("---")
                        st.subheader(f"正在審核：{target_name}")
                        
                        real_self_score, self_max = calculate_dynamic_score(record, '-自評', '-自評')
                        st.write(f"**員工自評總分**：{real_self_score} / {self_max}")
                        st.info(f"🗨️ **員工自評內容**：{record.get('自評文字', '')}")

                        with st.form(key=f"form_front_{st.session_state.key_counter_front}"):
                            manager_scores = render_assessment_in_form(
                                "front", 
                                st.session_state.key_counter_front,
                                record=record,
                                readonly_stages=["-自評"],
                                is_self_eval=False
                            )
                            c1, c2 = st.columns(2)
                            with c1: manager_name = st.text_input("初考主管簽名")
                            with c2: manager_comment = st.text_area("初考評語")
                            submitted_front = st.form_submit_button("✅ 提交初考", type="primary")
                        
                        if submitted_front:
                            if not manager_name:
                                st.error("請簽名！")
                            else:
                                with st.spinner("更新資料庫中..."):
                                    load_data_from_sheet.clear()
                                    row_idx, debug_df = find_row_index(data, target_name, target_date)
                                    
                                    if row_idx:
                                        headers = list(data[0].keys())
                                        clean_headers = [h.strip() for h in headers]
                                        updates = []
                                        try:
                                            status_col = clean_headers.index("目前狀態") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待覆考"]]})
                                            
                                            total_score, max_score = safe_sum_scores_from_dict(manager_scores)
                                            score_sum_col = clean_headers.index("初考總分") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                            comment_col = clean_headers.index("初考評語") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[manager_comment]]})
                                            
                                            if "初考主管" in clean_headers:
                                                manager_col = clean_headers.index("初考主管") + 1
                                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, manager_col), "values": [[manager_name]]})

                                            for item_name, score in manager_scores.items():
                                                col_name = f"{item_name}-初考"
                                                if col_name in clean_headers:
                                                    col_idx = clean_headers.index(col_name) + 1
                                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                            
                                            safe_batch_update(worksheet, updates)
                                            st.session_state.key_counter_front += 1
                                            st.session_state.submitted_front = True
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(f"欄位錯誤: {e}")
                                    else:
                                        st.error("❌ 找不到資料。")

    # ==========================================
    # Tab 4: 覆考主管 (護理長)
    # ==========================================
    with tabs[3]:
        if st.session_state.submitted_sec:
            show_completion_screen("覆考已完成", "案件已移交給老闆核決。", "btn_back_sec")
        else:
            st.header("👩‍⚕️ 護理長 (覆考主管) 審核區")
            add_security_watermark("護理長考核")
            show_guidelines()
            pwd2 = st.text_input("🔒 護理長密碼", type="password", key="pwd_secondary")

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
                        
                        real_self, self_max = calculate_dynamic_score(record, '-自評', '-自評')
                        real_prim, prim_max = calculate_dynamic_score(record, '-初考', '-自評')
                        
                        c1, c2 = st.columns(2)
                        c1.info(f"**自評總分**：{real_self} / {self_max}\n\n💬 {record.get('自評文字', '')}")
                        
                        if record.get("初考組別", "") != "免初考" and real_prim > 0:
                            c2.warning(f"**初考總分**：{real_prim} / {prim_max}\n\n💬 {record.get('初考評語', '')}\n\n👮‍♂️ 簽名：{record.get('初考主管', '')}")
                        else:
                            c2.warning("*(本案件為主管職或免初考，無初考紀錄)*")

                        with st.form(key=f"form_sec_{st.session_state.key_counter_sec}"):
                            stages_to_show = ["-自評"]
                            if record.get("初考組別", "") != "免初考":
                                stages_to_show.append("-初考")

                            manager_scores = render_assessment_in_form(
                                "secondary", 
                                st.session_state.key_counter_sec,
                                record=record,
                                readonly_stages=stages_to_show,
                                is_self_eval=False
                            )
                            c1, c2 = st.columns(2)
                            with c1: sec_name = st.text_input("護理長 (覆考主管) 簽名")
                            with c2: sec_comment = st.text_area("覆考評語")
                            submitted_sec = st.form_submit_button("✅ 提交覆考", type="primary")
                        
                        if submitted_sec:
                            if not sec_name:
                                st.error("請簽名！")
                            else:
                                with st.spinner("更新資料庫中..."):
                                    load_data_from_sheet.clear()
                                    row_idx, debug_df = find_row_index(data, target_name, target_date)
                                    if row_idx:
                                        headers = list(data[0].keys())
                                        clean_headers = [h.strip() for h in headers]
                                        updates = []
                                        try:
                                            status_col = clean_headers.index("目前狀態") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, status_col), "values": [["待核決"]]})
                                            
                                            total_score, max_score = safe_sum_scores_from_dict(manager_scores)
                                            score_sum_col = clean_headers.index("覆考總分") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, score_sum_col), "values": [[total_score]]})

                                            comment_col = clean_headers.index("覆考評語") + 1
                                            updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, comment_col), "values": [[sec_comment]]})

                                            if "覆考主管" in clean_headers:
                                                manager_col = clean_headers.index("覆考主管") + 1
                                                updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, manager_col), "values": [[sec_name]]})

                                            for item_name, score in manager_scores.items():
                                                col_name = f"{item_name}-覆考"
                                                if col_name in clean_headers:
                                                    col_idx = clean_headers.index(col_name) + 1
                                                    updates.append({"range": gspread.utils.rowcol_to_a1(row_idx, col_idx), "values": [[score]]})
                                            
                                            safe_batch_update(worksheet, updates)
                                            st.session_state.key_counter_sec += 1
                                            st.session_state.submitted_sec = True
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(f"欄位錯誤: {e}")
                                    else:
                                        st.error("❌ 找不到原始資料列。")

    # ==========================================
    # Tab 5: 老闆最終核決
    # ==========================================
    with tabs[4]:
        st.header("🏆 老闆核決區")
        add_security_watermark("老闆核決中")
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
                    # 1. 日期排序 (新 -> 舊)
                    pending_df["dt_obj"] = pd.to_datetime(pending_df["日期"], errors='coerce').dt.date
                    pending_df = pending_df.sort_values(by="dt_obj", ascending=False)

                    # 2. 日期篩選
                    if not pending_df["dt_obj"].dropna().empty:
                        min_date = pending_df["dt_obj"].min()
                        max_date = pending_df["dt_obj"].max()
                        
                        st.markdown("### 🔍 篩選與選擇")
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            date_range = st.date_input("📅 篩選日期範圍", [min_date, max_date])
                        
                        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                            start_d, end_d = date_range
                            pending_df = pending_df[
                                (pending_df["dt_obj"] >= start_d) & 
                                (pending_df["dt_obj"] <= end_d)
                            ]
                    
                    if pending_df.empty:
                        st.warning("⚠️ 此日期範圍內無資料。")
                    else:
                        target_options = [f"{row['姓名']} ({row['日期']})" for i, row in pending_df.iterrows()]
                        selected_target = st.selectbox("請選擇對象", target_options, key="sel_boss")
                        
                        target_name = selected_target.split(" (")[0]
                        target_date_str = selected_target.split(" (")[1].replace(")", "")
                        record = pending_df[(pending_df["姓名"] == target_name) & (pending_df["日期"] == target_date_str)].iloc[0]

                        # --- 歷史趨勢圖 (只在歷史模式顯示) ---
                        if view_mode == "歷史已完成案件":
                            st.markdown("### 📈 該員工歷史成績趨勢")
                            # 找出該員工所有歷史資料
                            history_df = df_all[df_all["姓名"] == target_name].copy()
                            history_df["dt_obj"] = pd.to_datetime(history_df["日期"], errors='coerce')
                            history_df = history_df.sort_values("dt_obj") # 舊到新畫圖
                            
                            if not history_df.empty:
                                chart_data = history_df[["dt_obj", "最終總分"]].set_index("dt_obj")
                                st.line_chart(chart_data)

                        st.markdown("---")
                        
                        st.markdown("### 📝 各階段評語紀錄")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.info(f"**🗣️ 員工自評**\n\n{record.get('自評文字', '無')}")
                        with c2:
                            if record.get("初考組別", "") == "免初考":
                                st.warning("**⚠️ 此員工免初考**")
                            else:
                                st.warning(f"**👮‍♂️ 初考評語**\n\n{record.get('初考評語', '無')}\n\n(簽名: {record.get('初考主管', '')})")
                        with c3:
                            st.error(f"**👩‍⚕️ 覆考評語**\n\n{record.get('覆考評語', '無')}\n\n(簽名: {record.get('覆考主管', '')})")

                        st.markdown("---")
                        
                        real_self, s_max = calculate_dynamic_score(record, '-自評', '-自評')
                        real_prim, p_max = calculate_dynamic_score(record, '-初考', '-自評')
                        real_sec, sec_max = calculate_dynamic_score(record, '-覆考', '-自評')
                        real_final, f_max = calculate_dynamic_score(record, '-最終', '-自評')

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("自評總分", f"{real_self} / {s_max}")
                        
                        if record.get("初考組別", "") == "免初考":
                            col2.metric("初考總分", "免初考")
                        else:
                            col2.metric("初考總分", f"{real_prim} / {p_max}")
                            
                        col3.metric("覆考總分", f"{real_sec} / {sec_max}")
                        
                        if view_mode == "歷史已完成案件":
                            col4.metric("🏆 最終總分", f"{real_final} / {f_max}")
                            st.success(f"📌 最終建議：{record.get('最終建議', '')}")
                            st.success(f"🏅 最終考績：{record.get('最終考績', '未評定')}")
                            
                            # --- 下載按鈕 ---
                            csv = pending_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="📥 下載本頁搜尋結果 (Excel/CSV)",
                                data=csv,
                                file_name=f"assessment_export_{date.today()}.csv",
                                mime="text/csv",
                            )
                            
                            st.markdown("### 詳細成績單")
                            items = get_assessment_items()
                            detail_rows = []
                            for item in items:
                                i_name = item["考核項目"]
                                prim_score = "免初考" if record.get("初考組別", "") == "免初考" else str(record.get(f"{i_name}-初考", "-"))
                                
                                detail_rows.append({
                                    "考核項目": i_name,
                                    "自評": str(record.get(f"{i_name}-自評", "-")),
                                    "初考": prim_score,
                                    "覆考": str(record.get(f"{i_name}-覆考", "-")),
                                    "最終": str(record.get(f"{i_name}-最終", "-")),
                                })
                            st.table(pd.DataFrame(detail_rows))
                        else: 
                            st.warning("請填寫最終成績與考績以完成考核。")
                            
                            with st.form(key=f"form_boss_{st.session_state.key_counter_boss}"):
                                stages_to_show = ["-自評"]
                                if record.get("初考組別", "") != "免初考":
                                    stages_to_show.append("-初考")
                                stages_to_show.append("-覆考")

                                avg_defaults = calculate_average_defaults(record)
                                
                                boss_scores = render_assessment_in_form(
                                    "boss", 
                                    st.session_state.key_counter_boss,
                                    record=record,
                                    readonly_stages=stages_to_show,
                                    is_self_eval=False,
                                    default_scores=avg_defaults
                                )
                                c1, c2 = st.columns(2)
                                with c1: final_action = st.selectbox("最終建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])
                                with c2: final_grade = st.selectbox("🏅 最終考績", ["S", "A+", "A", "A-", "B"])
                                submitted_boss = st.form_submit_button("🏆 核決並歸檔", type="primary")
                            
                            if submitted_boss:
                                with st.spinner("正在歸檔..."):
                                    load_data_from_sheet.clear()
                                    row_idx, debug_df = find_row_index(data, target_name, target_date_str)
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
                                            
                                            total_score, max_score = safe_sum_scores_from_dict(boss_scores)
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
                                            st.session_state.key_counter_boss += 1
                                            st.session_state.submitted_boss = True
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(f"欄位錯誤: {e}")
                                    else:
                                        st.error("❌ 找不到原始資料列。")

if __name__ == "__main__":
    main()
