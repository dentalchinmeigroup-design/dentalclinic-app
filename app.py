import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

def main():
    # 設定為寬螢幕模式，讓表格和儀表板更清楚
    st.set_page_config(page_title="專業技能考核表", layout="wide")
    
    st.title("✨ 日沐 ‧ 勤美 ‧ 小日子")
    st.subheader("全方位績效考核系統")

    # 建立 Google Sheets 連線
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("連線設定尚未完成，請檢查 Streamlit Secrets 設定。")
        st.stop()

    st.markdown("---")

    # --- 1. 考核標準與指標定義 (APP 的說明書) ---
    with st.expander("📖 點此查看：考核指標定義 & 評分標準", expanded=False):
        tab1, tab2 = st.tabs(["📊 評分標準 (分數級距)", "📝 指標定義說明 (詳細內容)"])
        
        with tab1:
            st.info("請依照下列分數級距，進行自評與他評，務必如實、客觀填寫。")
            st.markdown("""
            | 分數 | 定義 | 說明 |
            | :---: | :--- | :--- |
            | **10** | **超越要求** | 表現卓越，無可挑惕。 |
            | **8-9** | **完全符合** | 基本要求完全符合，表現穩定。 |
            | **5-7** | **部分符合** | 但有建議改善事項。 |
            | **3-4** | **不符合** | 首次列入改善追蹤。 |
            | **0-2** | **多次不符合** | 需持續改善追蹤。 |
            | **N/A** | **不適用** | 不列入計算。 |
            """)
            
        with tab2:
            st.warning("此為各項職能之詳細定義，評分時請參考此標準。")
            st.markdown("""
            | 評核面向 | 考核重點 | 專業能力定義說明  |
            | :--- | :--- | :--- |
            | **專業技能** | **跟診/櫃台** | 具備職務所需的各項專業知識與技能，能充份滿足工作需求。 |
            | **核心職能** | **勤務配合** | 遵循規範，維持良好的出勤紀律，並能在工作中展現積極的態度與持續進取的企圖心。 |
            | **核心職能** | **人際協作** | 與同儕保持良好互動，尊重並服從上下級指示，具備良好的團隊合作能力。 |
            | **行政職能** | **基礎/進階** | 具備確保診所日常營運穩定的專業能力，能完成行政與支援工作，並有效執行主管交辦任務。 |
            | **行政職能** | **應變/危機** | 同時具備高度應變與問題解決能力，能即時處理突發需求，主動支援並展現團隊合作精神。 |
            """)

    st.markdown("---")

    # --- 2. 基本資料區 ---
    st.header("1. 受評人資料")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        name = st.text_input("姓名", placeholder="請輸入姓名")
    with c2:
        rank = st.text_input("職等", placeholder="請輸入職等")
    with c3:
        assess_date = st.date_input("評量日期", date.today())
    with c4:
        boss_name = st.text_input("最高核決", value="邱上展")

    st.markdown("---")

    # --- 3. 考核評分區 (核心功能) ---
    st.header("2. 考核項目評分")
    st.info("💡 **操作方式**：請直接點擊表格內的數字進行修改（預設 2 分）。下方儀表板會 **即時計算總分**。")

    # 準備資料
    data = [
        # 專業技能
        {"類別": "專業技能", "考核項目": "跟診技能", "說明": "器械準備熟練，無重大缺失。"},
        {"類別": "專業技能", "考核項目": "櫃台技能", "說明": "準確完成約診與行政作業。"},
        # 職能表現
        {"類別": "職能表現", "考核項目": "跟診執行", "說明": "確保診療不中斷，即時支援。"},
        {"類別": "職能表現", "考核項目": "櫃台溝通", "說明": "溝通良好，態度親切專業。"},
        {"類別": "職能表現", "考核項目": "勤務配合(職能)", "說明": "遵守出勤與請假規範。"},
        {"類別": "職能表現", "考核項目": "勤務配合(配合)", "說明": "積極參與訓練課程。"},
        {"類別": "職能表現", "考核項目": "人際協作(人際)", "說明": "與同儕互助，主動支援。"},
        {"類別": "職能表現", "考核項目": "人際協作(協作)", "說明": "尊重前輩，引導新人。"},
        # 行政職能
        {"類別": "行政職能", "考核項目": "危機處理", "說明": "即時處理突發，預防問題。"},
        {"類別": "行政職能", "考核項目": "基礎職能", "說明": "確實完成維修/牙材/牙模。"},
        {"類別": "行政職能", "考核項目": "進階職能", "說明": "理解要求，效率完成任務。"},
        {"類別": "行政職能", "考核項目": "應變能力", "說明": "因應臨時需求，態度靈活。"},
    ]

    # 初始化 DataFrame
    if "df_initial" not in st.session_state:
        df = pd.DataFrame(data)
        df["同仁自評"] = 2
        df["初考評分"] = 2
        df["覆考評分"] = 2
        df["最終評分"] = 2
        st.session_state.df_initial = df

    # 設定表格欄位
    column_config = {
        "類別": st.column_config.TextColumn("類別", width="small", disabled=True),
        "考核項目": st.column_config.TextColumn("項目", width="medium", disabled=True),
        "說明": st.column_config.TextColumn("重點提示", width="large", disabled=True),
        "同仁自評": st.column_config.NumberColumn("自評", min_value=0, max_value=10, step=1, required=True),
        "初考評分": st.column_config.NumberColumn("初考", min_value=0, max_value=10, step=1, required=True),
        "覆考評分": st.column_config.NumberColumn("覆考", min_value=0, max_value=10, step=1, required=True),
        "最終評分": st.column_config.NumberColumn("最終", min_value=0, max_value=10, step=1, required=True),
    }

    # 顯示可編輯表格
    edited_df = st.data_editor(
        st.session_state.df_initial,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500,
        key="editor"
    )

    # --- 4. 即時儀表板 (Scoreboard) ---
    st.markdown("### 📊 成績總覽 (自動計算)")
    
    total_self = edited_df["同仁自評"].sum()
    total_init = edited_df["初考評分"].sum()
    total_rev = edited_df["覆考評分"].sum()
    total_final = edited_df["最終評分"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("同仁自評總分", f"{total_self} 分")
    m2.metric("初考主管總分", f"{total_init} 分", delta_color="normal")
    m3.metric("覆考主管總分", f"{total_rev} 分", delta_color="normal")
    m4.metric("🏆 最終核定總分", f"{total_final} 分", delta_color="inverse")

    st.markdown("---")

    # --- 5. 綜合評語區 ---
    st.header("3. 綜合評語與建議")
    
    mc1, mc2 = st.columns(2)
    with mc1:
        manager_1 = st.text_input("初考主管姓名", placeholder="簽名...")
    with mc2:
        manager_2 = st.text_input("覆考主管姓名", placeholder="簽名...")

    col_text1, col_text2, col_text3 = st.columns(3)
    with col_text1:
        self_comment = st.text_area("同仁自評 (文字)", height=150, placeholder="具體表現或檢討...")
    with col_text2:
        manager1_comment = st.text_area("初考主管評語", height=150, placeholder="主管建議...")
    with col_text3:
        manager2_comment = st.text_area("覆考主管評語", height=150, placeholder="主管建議...")

    st.subheader("🏁 最終考核結論")
    action = st.selectbox("請選擇建議事項", ["通過", "需觀察", "需輔導", "工作調整", "其他"])

    st.markdown("<br>", unsafe_allow_html=True)

    # # --- 6. 提交按鈕 (智慧型版本) ---
    if st.button("🚀 提交完整考核表", type="primary", use_container_width=True):
        if not name:
            st.error("請務必填寫姓名！")
        else:
            with st.spinner("正在處理龐大的考核資料..."):
                
                # 準備資料
                row_data = {
                    "姓名": name,
                    "職等": rank,
                    "評量日期": assess_date.strftime("%Y-%m-%d"),
                    "初考主管": manager_1,
                    "覆考主管": manager_2,
                    "核決老闆": boss_name,
                    "自評總分": total_self,
                    "初考總分": total_init,
                    "覆考總分": total_rev,
                    "最終總分": total_final,
                    "自評文字": self_comment,
                    "初考評語": manager1_comment,
                    "覆考評語": manager2_comment,
                    "最終建議": action,
                    "填寫時間": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # 攤平細項分數
                for index, row in edited_df.iterrows():
                    item = row["考核項目"]
                    row_data[f"{item}_自評"] = row["同仁自評"]
                    row_data[f"{item}_初考"] = row["初考評分"]
                    row_data[f"{item}_覆考"] = row["覆考評分"]
                    row_data[f"{item}_最終"] = row["最終評分"]

                new_df = pd.DataFrame([row_data])
                TARGET_SHEET = "Assessment_Data"

                try:
                    # 嘗試讀取現有資料
                    existing_data = conn.read(worksheet=TARGET_SHEET, ttl=0)
                    updated_df = pd.concat([existing_data, new_df], ignore_index=True)
                    # 如果讀取成功，代表分頁存在，使用 update (但前提是欄位要夠寬，或透過下方 create 修復)
                    conn.update(worksheet=TARGET_SHEET, data=updated_df)
                    st.success(f"✅ 成功！資料已更新至 '{TARGET_SHEET}'。")
                    
                except Exception:
                    # 【關鍵修復】: 如果讀取失敗 (分頁不存在)，或是 update 失敗 (欄位不夠)
                    # 我們直接呼叫 create，它會自動依據資料寬度建立新分頁
                    try:
                        conn.create(worksheet=TARGET_SHEET, data=new_df)
                        st.success(f"✅ 成功！已建立全新分頁 '{TARGET_SHEET}' 並存檔。")
                    except Exception as e:
                        st.error(f"寫入失敗，請檢查 Google 試算表權限或欄位數量。錯誤: {e}")
                        st.stop()

                st.balloons()

if __name__ == "__main__":
    main()
