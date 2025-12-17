import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

def main():
    st.set_page_config(page_title="專業技能考核表", layout="centered")
    st.title("日沐 ‧ 勤美 ‧ 小日子")
    st.subheader("線上考核系統 (完整版)")

    # 建立 Google Sheets 連線
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error("連線設定尚未完成，請檢查 Streamlit Secrets 設定。")
        st.stop()

    st.markdown("---")

    # --- 1. 基本資料 ---
    st.header("1. 基本資料")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("姓名", placeholder="請輸入姓名")
        rank = st.text_input("職等", placeholder="請輸入職等")
    with col2:
        assess_date = st.date_input("評量日期", date.today())
        manager = st.text_input("考核主管", placeholder="請輸入主管姓名")

    st.markdown("---")

    # --- 評分標準說明 (摺疊選單) ---
    with st.expander("ℹ️ 點此查看：評分標準說明", expanded=False):
        st.markdown("""
        * **10分 (超越要求)**：表現卓越。
        * **8-9分 (完全符合)**：基本要求完全符合，表現穩定。
        * **5-7分 (部分符合)**：但有建議改善事項。
        * **3-4分 (不符合)**：首次列入改善追蹤。
        * **0-2分 (多次不符合)**：需持續改善追蹤。
        * **N/A**：不適用此項，不列入計算。
        """)

    st.markdown("---")

    # --- 2. 評分內容 (細項評分) ---
    # 修改說明：核心職能的文字說明已移除，預設分數改為 2
    sections = {
        "專業技能": [
            ("跟診技能", "器械準備熟練，無重大缺失；耗材不足能立即補充。"),
            ("櫃台技能", "準確完成約診、報表與櫃檯行政作業。")
        ],
        "核心職能 (僅顯示標題)": [
            ("跟診執行", ""),  # 文字說明已移除
            ("櫃台溝通", ""),
            ("勤務配合(職能)", ""),
            ("勤務配合(配合)", ""),
            ("人際協作(人際)", ""),
            ("人際協作(協作)", "")
        ],
        "行政職能": [
            ("危機處理", "能即時處理突發事件，主動預防問題。"),
            ("基礎職能", "確實完成行政工作(維修/牙材/牙模)。"),
            ("進階職能", "理解診所及老闆要求，妥善效率完成任務。"),
            ("應變能力", "因應老闆臨時需求，展現靈活態度。")
        ]
    }

    scores_data = {}
    st.header("2. 細項評分")
    
    for category, items in sections.items():
        st.subheader(f"📌 {category}")
        for title, desc in items:
            # 如果有說明文字就顯示，沒有就只顯示標題
            if desc:
                st.caption(f"{desc}")
            
            # 預設分數改為 2
            score = st.slider(f"{title}", 0, 10, 2, key=f"{category}_{title}")
            scores_data[f"{category}-{title}"] = score
        st.markdown("---")

    # --- 3. 綜合考評流程 (自評/初考/覆考/最終) ---
    st.header("3. 綜合考評流程")

    # (A) 同仁自評
    st.subheader("🔹 同仁自評")
    col_self_1, col_self_2 = st.columns([3, 1])
    with col_self_1:
        self_eval = st.text_area("同仁自評內容 (具體表現或檢討)", height=100)
    with col_self_2:
        self_score = st.number_input("自評分數", min_value=0.0, max_value=10.0, step=0.1, value=0.0)

    st.markdown("---")

    # (B) 初考主管
    st.subheader("🔹 初考主管")
    col_init_1, col_init_2 = st.columns([3, 1])
    with col_init_1:
        initial_eval = st.text_area("初考主管評語", height=100)
    with col_init_2:
        initial_score = st.number_input("初考分數", min_value=0.0, max_value=10.0, step=0.1, value=0.0)

    st.markdown("---")

    # (C) 覆考主管
    st.subheader("🔹 覆考主管")
    col_rev_1, col_rev_2 = st.columns([3, 1])
    with col_rev_1:
        review_eval = st.text_area("覆考主管評語", height=100)
    with col_rev_2:
        review_score = st.number_input("覆考分數", min_value=0.0, max_value=10.0, step=0.1, value=0.0)

    st.markdown("---")

    # (D) 最終成績與建議
    st.header("🏆 最終考核結果")
    col_fin_1, col_fin_2 = st.columns(2)
    
    with col_fin_1:
        final_score = st.number_input("✨ 最終成績 (老闆核定)", min_value=0.0, max_value=10.0, step=0.1, value=0.0)
    
    with col_fin_2:
        action = st.selectbox("考核建議", ["通過", "需觀察", "需輔導", "工作調整", "其他"])

    # --- 提交按鈕 ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 提交完整考核表", type="primary", use_container_width=True):
        if not name:
            st.error("請務必填寫姓名！")
        else:
            with st.spinner("正在寫入雲端資料庫..."):
                # 計算細項平均 (僅供參考，若需存入可保留)
                detail_avg = sum(scores_data.values()) / len(scores_data)
                
                # 準備寫入的資料
                row = {
                    "姓名": name,
                    "職等": rank,
                    "日期": assess_date.strftime("%Y-%m-%d"),
                    "考核主管": manager,
                    "細項平均": f"{detail_avg:.2f}", # 自動計算的拉桿平均
                    # --- 新增的欄位 ---
                    "自評內容": self_eval,
                    "自評分數": self_score,
                    "初考評語": initial_eval,
                    "初考分數": initial_score,
                    "覆考評語": review_eval,
                    "覆考分數": review_score,
                    "最終成績": final_score,
                    "考核建議": action,
                    "填寫時間": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                # 把細項分數也加入
                row.update(scores_data)
                
                new_df = pd.DataFrame([row])

                # 寫入 Google Sheets
                try:
                    existing_data = conn.read(worksheet="Sheet1", ttl=0)
                    updated_df = pd.concat([existing_data, new_df], ignore_index=True)
                except:
                    updated_df = new_df

                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"✅ 成功！{name} 的考核資料已完整存檔。")
                st.balloons()

if __name__ == "__main__":
    main()
