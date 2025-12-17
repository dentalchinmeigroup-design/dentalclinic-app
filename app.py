import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

def main():
    st.set_page_config(page_title="專業技能考核表", layout="wide") # 改為 wide 寬螢幕模式以容納表格
    st.title("日沐 ‧ 勤美 ‧ 小日子")
    st.subheader("線上考核系統 (多主管評分版)")

    # 建立 Google Sheets 連線
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("連線設定尚未完成，請檢查 Streamlit Secrets 設定。")
        st.stop()

    st.markdown("---")

    # --- 1. 基本資料 ---
    st.header("1. 基本資料")
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("姓名", placeholder="請輸入姓名")
        rank = st.text_input("職等", placeholder="請輸入職等")
    with col2:
        assess_date = st.date_input("評量日期", date.today())
        manager_1 = st.text_input("初考主管", placeholder="請輸入姓名")
    with col3:
        manager_2 = st.text_input("覆考主管", placeholder="請輸入姓名")
        boss_name = st.text_input("核決老闆", placeholder="請輸入姓名", value="老闆")

    st.markdown("---")

    # --- 評分標準說明 ---
    with st.expander("ℹ️ 查看評分標準 (請點我展開)", expanded=False):
        st.markdown("""
        * **10分**：表現卓越 (超越要求)。
        * **8-9分**：表現穩定 (完全符合)。
        * **5-7分**：部分符合 (有改善空間)。
        * **3-4分**：不符合 (首次改善追蹤)。
        * **0-2分**：多次不符合 (持續追蹤)。
        * **N/A**：不適用。
        """)

    # --- 2. 考核項目表格 (Data Editor) ---
    st.header("2. 考核項目評分")
    st.info("💡 操作說明：請直接點擊下方表格內的數字進行修改 (預設為 2 分)。")

    # 定義所有資料 (已移除「核心職能」標題，改歸類為「職能表現」或僅列出)
    data = [
        # 專業技能
        {"類別": "專業技能", "考核項目": "跟診技能", "考核標準說明": "器械準備熟練，無重大缺失；耗材不足能立即補充。"},
        {"類別": "專業技能", "考核項目": "櫃台技能", "考核標準說明": "準確完成約診、報表與櫃檯行政作業。"},
        
        # 原核心職能 (文字保留，但類別名稱調整)
        {"類別": "職能表現", "考核項目": "跟診執行", "考核標準說明": "確保診療不中斷，即時支援醫師需求。"},
        {"類別": "職能表現", "考核項目": "櫃台溝通", "考核標準說明": "與醫師、病人有良好雙向溝通；態度親切專業。"},
        {"類別": "職能表現", "考核項目": "勤務配合(職能)", "考核標準說明": "遵守出勤與請假規範，配合排班。"},
        {"類別": "職能表現", "考核項目": "勤務配合(配合)", "考核標準說明": "積極參與牙科訓練課程，確實出席。"},
        {"類別": "職能表現", "考核項目": "人際協作(人際)", "考核標準說明": "日常能與同儕互助幫忙，高峰期主動支援。"},
        {"類別": "職能表現", "考核項目": "人際協作(協作)", "考核標準說明": "尊重並聽從前輩指示，帶領新人時展現良好態度。"},

        # 行政職能
        {"類別": "行政職能", "考核項目": "危機處理", "考核標準說明": "能即時處理突發事件，主動預防問題。"},
        {"類別": "行政職能", "考核項目": "基礎職能", "考核標準說明": "確實完成行政工作(維修/牙材/牙模)。"},
        {"類別": "行政職能", "考核項目": "進階職能", "考核標準說明": "理解診所及老闆要求，妥善效率完成任務。"},
        {"類別": "行政職能", "考核項目": "應變能力", "考核標準說明": "因應老闆臨時需求，展現靈活態度。"},
    ]

    # 建立 DataFrame
    df = pd.DataFrame(data)
    
    # 新增四個角色的評分欄位，預設為 2 分
    df["同仁自評"] = 2
    df["初考評分"] = 2
    df["覆考評分"] = 2
    df["最終評分"] = 2

    # 設定欄位顯示格式 (讓表格好看一點)
    column_config = {
        "類別": st.column_config.TextColumn("類別", width="small", disabled=True),
        "考核項目": st.column_config.TextColumn("項目", width="small", disabled=True),
        "考核標準說明": st.column_config.TextColumn("指標說明 (唯讀)", width="large", disabled=True),
        "同仁自評": st.column_config.NumberColumn("自評", min_value=0, max_value=10, step=1, required=True),
        "初考評分": st.column_config.NumberColumn("初考", min_value=0, max_value=10, step=1, required=True),
        "覆考評分": st.column_config.NumberColumn("覆考", min_value=0, max_value=10, step=1, required=True),
        "最終評分": st.column_config.NumberColumn("最終(老闆)", min_value=0, max_value=10, step=1, required=True),
    }

    # 顯示表格供編輯
    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500  # 表格高度
    )

    st.markdown("---")

    # --- 3. 評語區 ---
    st.header("3. 綜合評語與建議")
    
    col_text1, col_text2, col_text3 = st.columns(3)
    with col_text1:
        self_comment = st.text_area("同仁自評 (文字)", height=150, placeholder="請輸入自評內容...")
    with col_text2:
        manager1_comment = st.text_area("初考主管評語", height=150, placeholder="初考主管建議...")
    with col_text3:
        manager2_comment = st.text_area("覆考主管評語", height=150, placeholder="覆考主管建議...")

    # 最終建議
    st.subheader("🏆 考核結論")
    action = st.selectbox("最終考核建議 (請選擇)", ["通過", "需觀察", "需輔導", "工作調整", "其他"])

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 4. 提交按鈕 ---
    if st.button("🚀 提交完整考核表", type="primary", use_container_width=True):
        if not name:
            st.error("請務必填寫姓名！")
        else:
            with st.spinner("正在將龐大的資料寫入雲端..."):
                
                # 準備要寫入的一列資料 (row)
                row_data = {
                    "姓名": name,
                    "職等": rank,
                    "評量日期": assess_date.strftime("%Y-%m-%d"),
                    "初考主管": manager_1,
                    "覆考主管": manager_2,
                    "核決老闆": boss_name,
                    "自評文字": self_comment,
                    "初考評語": manager1_comment,
                    "覆考評語": manager2_comment,
                    "最終建議": action,
                    "填寫時間": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # 將表格內的每一個分數「攤平」放進去
                # 格式會變成： "跟診技能_自評": 8, "跟診技能_初考": 7 ...
                for index, row in edited_df.iterrows():
                    item = row["考核項目"]
                    row_data[f"{item}_自評"] = row["同仁自評"]
                    row_data[f"{item}_初考"] = row["初考評分"]
                    row_data[f"{item}_覆考"] = row["覆考評分"]
                    row_data[f"{item}_最終"] = row["最終評分"]

                # 轉換成 DataFrame
                new_df = pd.DataFrame([row_data])

                # 寫入 Google Sheets
                try:
                    existing_data = conn.read(worksheet="Sheet1", ttl=0)
                    updated_df = pd.concat([existing_data, new_df], ignore_index=True)
                except:
                    updated_df = new_df

                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"✅ 成功！{name} 的全方位考核資料已存檔。")
                st.balloons()

if __name__ == "__main__":
    main()
