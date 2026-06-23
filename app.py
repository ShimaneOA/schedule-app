import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
from streamlit_calendar import calendar as st_calendar
from supabase import create_client, Client

# --- 画面初期設定 ---
st.set_page_config(page_title="簡易版desknet's風スケジュール", layout="wide")

# --- 代表的な10色のカラーパレット定義 ---
COLOR_PALETTE = {
    "青系 🐳": "#e3f2fd",
    "赤系 🍎": "#ffe3e3",
    "緑系 🍏": "#e8f5e9",
    "黄系 🍋": "#fffde7",
    "橙系 🍊": "#fff3e0",
    "紫系 🍇": "#f3e5f5",
    "桃系 🌸": "#fce4ec",
    "茶系 🐻": "#efebe9",
    "灰系 🐘": "#f5f5f5",
    "水色 💧": "#e0f7fa"
}

# --- セッション状態の初期化 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "selected_color" not in st.session_state:
    st.session_state.selected_color = "#e3f2fd" # 初期値：青系
if "active_date" not in st.session_state:
    st.session_state.active_date = datetime(2026, 6, 3).date() # 初期基準日
if "popup_date" not in st.session_state:
    st.session_state.popup_date = None  # ポップアップ表示用の日付
if "show_popup" not in st.session_state:
    st.session_state.show_popup = False
if "just_registered" not in st.session_state:
    st.session_state.just_registered = False
if "last_select_date" not in st.session_state:
    st.session_state.last_select_date = None
if "last_click_date" not in st.session_state:
    st.session_state.last_click_date = None
if "last_click_time" not in st.session_state:
    st.session_state.last_click_time = 0.0
if "week_click_date" not in st.session_state:
    st.session_state.week_click_date = None
if "week_click_user" not in st.session_state:
    st.session_state.week_click_user = None
if "week_click_event_id" not in st.session_state:
    st.session_state.week_click_event_id = None

# --- 動的CSS生成（登録ボタンの色をプルダウンの選択に連動させる） ---
st.markdown(f"""
<style>
    .reportview-container {{ background: #f5f6f8; }}
    
    /* フォーム内の「登録する」ボタンの背景色を選択された色コードに強制連動 */
    div[data-testid="stSidebar"] div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] {{
        background-color: {st.session_state.selected_color} !important;
        color: #333333 !important;
        font-weight: bold !important;
        border: 1px solid #ababab !important;
        width: 100% !important;
        height: 40px !important;
        margin-top: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border-radius: 4px;
    }}
    
    /* サイドバー内の文字重なりを解消するための余白調整 */
    div[data-testid="stSidebarBlockContainer"] {{ padding-top: 25px !important; padding-bottom: 10px !important; }}
    .stSelectbox, .stTextInput, .stDateInput, .stTimeInput {{
        margin-bottom: 8px !important;
    }}
    
    /* テーブル共通スタイル */
    .desknets-table {{ width: 100%; border-collapse: collapse; font-size: 13px; background-color: white; }}
    .desknets-table th, .desknets-table td {{ border: 1px solid #ccd1d9; padding: 5px; vertical-align: top; width: 12.5%; }}
    .desknets-table th {{ background-color: #f2f4f7; color: #333; text-align: center; font-weight: bold; }}
    .name-col {{ background-color: #f8fafc; font-weight: bold; vertical-align: middle !important; text-align: center; }}
    
    /* 予定付箋 */
    .event-block {{ color: #333; padding: 4px 6px; border-radius: 3px; margin-bottom: 3px; font-size: 11px; line-height: 1.3; border-left: 4px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    /* マトリックスセルの透明ボタン */
    div[data-testid='stButton'] button.cell-btn {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0; cursor: pointer; z-index: 1;
    }}
    .matrix-cell {{ position: relative; }}
    /* サイドバーを非表示 */
    [data-testid="stSidebar"] {{ display: none; }}
    [data-testid="collapsedControl"] {{ display: none; }}
    .main .block-container {{ max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important; }}
</style>
""", unsafe_allow_html=True)

# --- Supabase接続 ---
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

# --- ポップアップ登録ダイアログ ---
@st.dialog("📅 予定を登録する")
def show_register_popup(target_date, preset_user=None):
    st.write(f"**📆 {target_date.strftime('%Y年%m月%d日')}** の予定を登録します")
    
    # 色選択
    popup_color_name = st.selectbox("🎨 予定の色", list(COLOR_PALETTE.keys()), key="popup_color")
    popup_color_code = COLOR_PALETTE[popup_color_name]
    st.markdown(f"""
    <div style="background-color:{popup_color_code}; padding:6px; border-radius:4px; border:1px solid #babaa1; text-align:center; margin-bottom:8px;">
        <span style="font-size:12px; font-weight:bold; color:#333;">🎨 この色で登録されます</span>
    </div>
    """, unsafe_allow_html=True)
    
    user_list = list(USER_CREDS.keys())
    default_user_idx = user_list.index(preset_user) if preset_user and preset_user in user_list else 0
    popup_user = st.selectbox("対象者/設備", user_list, index=default_user_idx, key="popup_user")
    popup_title = st.text_input("予定タイトル", key="popup_title")
    col1, col2 = st.columns(2)
    with col1:
        popup_start = st.time_input("開始時間", value=datetime.strptime("09:00", "%H:%M").time(), key="popup_start")
    with col2:
        popup_end = st.time_input("終了時間", value=datetime.strptime("10:00", "%H:%M").time(), key="popup_end")
    
    st.markdown("---")
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("✅ 登録する", use_container_width=True, type="primary"):
            if popup_title:
                supabase.table("schedules").insert({
                    "user_name": popup_user, "category": "カスタム", "title": popup_title,
                    "date": str(target_date), "start_time": str(popup_start)[:5],
                    "end_time": str(popup_end)[:5], "created_by": st.session_state.username,
                    "color": popup_color_code
                }).execute()
                # 登録完了フラグを立ててrerun → ポップアップを呼ばずに閉じる
                st.session_state.just_registered = True
                st.rerun()
            else:
                st.warning("タイトルを入力してください。")
    with btn_col2:
        if st.button("❌ キャンセル", use_container_width=True):
            st.session_state.just_registered = True
            st.rerun()

# --- ポップアップ編集・削除ダイアログ ---
@st.dialog("✏️ 予定を編集・削除する")
def show_edit_popup(event_id, df):
    # 常にDBから最新データを取得（削除後のrerunでdfが古くなるのを防ぐ）
    res = supabase.table("schedules").select("*").eq("id", event_id).execute()
    if not res.data:
        st.rerun()
        return
    df_fresh = pd.DataFrame(res.data)
    if df_fresh.empty:
        st.rerun()
        return
    row = df_fresh.iloc[0]
    is_editable = (row['created_by'] == st.session_state.username) or (st.session_state.username == "admin")

    st.write(f"**[{row['date']}]　{row['title']}**　(登録者: {row['created_by']})")

    if not is_editable:
        st.warning(f"この予定は登録者本人（{row['created_by']}）以外は編集・削除できません。")
        return

    current_color_code = row['color'] if row['color'] else "#e3f2fd"
    matched_names = [k for k, v in COLOR_PALETTE.items() if v == current_color_code]
    default_idx = list(COLOR_PALETTE.keys()).index(matched_names[0]) if matched_names else 0

    col1, col2 = st.columns(2)
    with col1:
        edit_user = st.selectbox("対象者/設備", list(USER_CREDS.keys()), index=list(USER_CREDS.keys()).index(row['user_name']), key="edit_user")
        edit_title = st.text_input("予定タイトル", value=row['title'], key="edit_title")
        edit_color_name = st.selectbox("予定の色", list(COLOR_PALETTE.keys()), index=default_idx, key="edit_color")
    with col2:
        cur_date = datetime.strptime(row['date'], "%Y-%m-%d").date()
        edit_date = st.date_input("日付", value=cur_date, key="edit_date")
        cur_start = datetime.strptime(row['start_time'], "%H:%M").time()
        edit_start = st.time_input("開始時間", value=cur_start, key="edit_start")
        cur_end = datetime.strptime(row['end_time'], "%H:%M").time()
        edit_end = st.time_input("終了時間", value=cur_end, key="edit_end")

    st.markdown("---")
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("⚙️ 変更を保存", use_container_width=True, type="primary", key="edit_save"):
            supabase.table("schedules").update({
                "user_name": edit_user, "title": edit_title, "date": str(edit_date),
                "start_time": str(edit_start)[:5], "end_time": str(edit_end)[:5],
                "color": COLOR_PALETTE[edit_color_name]
            }).eq("id", event_id).execute()
            # 保存完了フラグを立ててrerun → ポップアップを呼ばずに閉じる
            st.session_state.just_registered = True
            st.rerun()
    with btn_col2:
        if st.button("🗑️ 削除する", use_container_width=True, key="edit_delete"):
            supabase.table("schedules").delete().eq("id", event_id).execute()
            # 削除完了フラグを立ててrerun → ポップアップを呼ばずに閉じる
            st.session_state.just_registered = True
            st.rerun()

USER_CREDS = {
    "乾 貴規": "taka123", "和田 章": "userApass", "山田 尚子": "userBpass",
    "熱田 衣智": "userCpass", "商談室(設備)": "room123", "admin": "admin999"
}

# --- ログインロジック ---
if not st.session_state.logged_in:
    st.title("👥 グループウェア・スケジュール")
    with st.form("login_form"):
        user_select = st.selectbox("社員名を選択してください", list(USER_CREDS.keys()))
        password_input = st.text_input("パスワードを入力してください", type="password")
        if st.form_submit_button("ログイン"):
            if USER_CREDS[user_select] == password_input:
                st.session_state.logged_in = True
                st.session_state.username = user_select
                st.rerun()
            else: st.error("パスワードが間違っています。")
    st.stop()

def load_data():
    res = supabase.table("schedules").select("*").execute()
    if res.data:
        return pd.DataFrame(res.data)
    return pd.DataFrame(columns=["id","user_name","category","title","date","start_time","end_time","created_by","color"])

df_schedules = load_data()

# --- メインヘッダー：タイトル・ユーザー情報・ログアウト ---
st.markdown(
    "<div style='background-color:#0275d8; padding:10px 16px; border-radius:6px; "
    "color:white; font-weight:bold; font-size:16px;'>📅 スケジュール管理</div>",
    unsafe_allow_html=True
)
st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

header_left, header_mid, header_right = st.columns([4, 2, 1])
with header_left:
    view_mode = st.radio("表示切替", ["組織週間 (マトリックス)", "個人月間 (カレンダー)"], horizontal=True)
with header_mid:
    st.markdown(
        f"<div style='text-align:right; padding-top:6px; color:#555; font-size:14px;'>"
        f"👤 <strong>{st.session_state.username}</strong> さん</div>",
        unsafe_allow_html=True
    )
with header_right:
    if st.button("🚪 ログアウト", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()



base_date_const = datetime.today().date()  # 常に今日の日付を基準にする

# ==========================================
# 1. 組織週間ビュー（マトリックス）
# ==========================================
if view_mode == "組織週間 (マトリックス)":
    st.caption("💡 枠をダブルクリック（ダブルタップ）で予定登録、予定をクリックで編集・削除ができます！")

    # 今週の日付リストを生成（日曜始まり）
    today = datetime.today().date()
    days_since_sunday = (today.weekday() + 1) % 7
    start_of_week = today - timedelta(days=days_since_sunday)
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]
    weekday_names = ["日", "月", "火", "水", "木", "金", "土"]
    weekday_colors = ["#d9534f", "#333", "#333", "#333", "#333", "#0275d8", "#0275d8"]
    users = [u for u in USER_CREDS.keys() if u != "admin"]

    # ポップアップ処理
    import time as _time
    if st.session_state.just_registered:
        st.session_state.just_registered = False
        st.session_state.last_click_date = None
        st.session_state.last_click_time = 0.0
    elif st.session_state.get("week_click_date") and st.session_state.get("week_click_user"):
        _date = st.session_state.week_click_date
        _user = st.session_state.week_click_user
        st.session_state.week_click_date = None
        st.session_state.week_click_user = None
        show_register_popup(_date, preset_user=_user)
    elif st.session_state.get("week_click_event_id"):
        _eid = st.session_state.week_click_event_id
        st.session_state.week_click_event_id = None
        show_edit_popup(_eid, df_schedules)

    # 今週の表示ラベル
    st.markdown(
        f"<div style='font-size:15px; font-weight:bold; color:#0275d8; margin-bottom:8px;'>"
        f"📅 {start_of_week.strftime('%Y年%m月%d日')} 〜 {week_days[-1].strftime('%m月%d日')}</div>",
        unsafe_allow_html=True
    )

    # ヘッダー行
    hdr_cols = st.columns([1.2] + [1]*7)
    with hdr_cols[0]:
        st.markdown(
            "<div style='text-align:center; font-weight:bold; background:#f2f4f7; "
            "padding:6px; border:1px solid #ccd1d9; font-size:12px;'>氏名</div>",
            unsafe_allow_html=True
        )
    for i, (day, w_name) in enumerate(zip(week_days, weekday_names)):
        with hdr_cols[i+1]:
            is_today = (day == today)
            bg = "#fff3cd" if is_today else "#f2f4f7"
            border = "2px solid #f0ad4e" if is_today else "1px solid #ccd1d9"
            st.markdown(
                f"<div style='text-align:center; font-weight:bold; color:{weekday_colors[i]}; "
                f"background:{bg}; padding:6px; border:{border}; font-size:12px;'>"
                f"{day.month}/{day.day}<br>({w_name})</div>",
                unsafe_allow_html=True
            )

    # 社員×曜日のマトリックス
    for user in users:
        row_cols = st.columns([1.2] + [1]*7)
        with row_cols[0]:
            st.markdown(
                f"<div style='padding:4px; font-weight:bold; font-size:12px; "
                f"border:1px solid #ccd1d9; min-height:90px; background:#fafafa; "
                f"display:flex; align-items:center; justify-content:center; "
                f"text-align:center;'>{user}</div>",
                unsafe_allow_html=True
            )
        for i, day in enumerate(week_days):
            with row_cols[i+1]:
                day_str = str(day)
                is_today = (day == today)
                bg = "#fffbef" if is_today else "white"
                border = "2px solid #f0ad4e" if is_today else "1px solid #ccd1d9"
                events = df_schedules[
                    (df_schedules['user_name'] == user) &
                    (df_schedules['date'] == day_str)
                ]
                events_html = ""
                for _, ev in events.iterrows():
                    ev_bg = ev['color'] if ev['color'] else "#e3f2fd"
                    events_html += (
                        f"<div style='background:{ev_bg}; border-left:3px solid #999; "
                        f"padding:2px 3px; margin-bottom:2px; border-radius:2px; font-size:10px; "
                        f"overflow:hidden; white-space:nowrap; text-overflow:ellipsis;'>"
                        f"<span style='color:#555;'>{ev['start_time']}</span> "
                        f"<strong>{ev['title']}</strong></div>"
                    )
                # 枠全体を透明ボタンで覆う（ダブルクリックで登録）
                cell_container = st.container()
                with cell_container:
                    # 予定と透明ボタンを重ねて表示
                    st.markdown(
                        f"<div class='matrix-cell' style='border:{border}; min-height:90px; "
                        f"padding:3px; background:{bg}; position:relative;'>"
                        f"{events_html}</div>",
                        unsafe_allow_html=True
                    )
                    # 透明な全面ボタン（ダブルクリックで登録）
                    btn_style = (
                        "background:transparent; border:none; position:relative; "
                        "width:100%; margin-top:-6px; color:transparent; "
                        "cursor:pointer; font-size:1px;"
                    )
                    if st.button("　", key=f"w_add_{user}_{day_str}",
                                 help=f"{user} / {day.month}/{day.day}（ダブルクリックで登録）",
                                 use_container_width=True):
                        now = _time.time()
                        click_key = f"{user}_{day_str}"
                        if (click_key == st.session_state.last_click_date and
                                now - st.session_state.last_click_time < 0.8):
                            st.session_state.last_click_date = None
                            st.session_state.last_click_time = 0.0
                            st.session_state.week_click_date = day
                            st.session_state.week_click_user = user
                            st.rerun()
                        else:
                            st.session_state.last_click_date = click_key
                            st.session_state.last_click_time = now
                # 予定クリックで編集（予定バーの下に小さく表示）
                for _, ev in events.iterrows():
                    if st.button(f"✏️{ev['title'][:5]}", key=f"w_edit_{ev['id']}",
                                 help="クリックして編集・削除", use_container_width=True):
                        st.session_state.week_click_event_id = int(ev['id'])
                        st.rerun()

# ==========================================
# 2. 個人月間ビュー
# ==========================================
elif view_mode == "個人月間 (カレンダー)":
    select_user = st.selectbox("表示する社員を選択", [u for u in USER_CREDS.keys() if u != "admin"])
    year, month = 2026, 6

    st.caption("💡 枠をダブルクリック（ダブルタップ）で予定登録、予定バーをクリックで編集・削除ができます！")

    # DBの予定をstreamlit-calendar用のイベントリストに変換
    user_events = df_schedules[df_schedules['user_name'] == select_user]
    cal_events = []
    for _, row in user_events.iterrows():
        bg_color = row['color'] if row['color'] else "#90CAF9"
        # 色が薄い（明るい）場合はテキストを暗くする
        cal_events.append({
            "id": str(row['id']),
            "title": f"{row['start_time']} {row['title']}",
            "start": f"{row['date']}T{row['start_time']}:00",
            "end": f"{row['date']}T{row['end_time']}:00",
            "backgroundColor": bg_color,
            "borderColor": bg_color,
            "textColor": "#333333",
        })

    # カレンダーオプション
    cal_options = {
        "initialView": "dayGridMonth",
        "initialDate": f"{year}-{month:02d}-01",
        "locale": "ja",
        "firstDay": 0,  # 日曜始まり
        "selectable": True,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": ""
        },
        "height": 650,
        "dayMaxEvents": 3,
    }

    custom_css = """
        .fc-daygrid-day { cursor: pointer; }
        .fc-daygrid-day:hover { background-color: #f0f7ff !important; }
        .fc-day-sun .fc-daygrid-day-number { color: #d9534f; font-weight: bold; }
        .fc-day-sat .fc-daygrid-day-number { color: #0275d8; font-weight: bold; }
        .fc-event { font-size: 11px; border-radius: 3px; }
    """

    # カレンダー表示＆クリックイベント取得
    cal_result = st_calendar(
        events=cal_events,
        options=cal_options,
        custom_css=custom_css,
        callbacks=["dateClick", "eventClick"],
        key=f"personal_cal_{select_user}"
    )

    # 操作完了後のrerunではポップアップを開かずフラグをリセット
    import time as _time
    if st.session_state.just_registered:
        st.session_state.just_registered = False
        st.session_state.last_click_date = None
        st.session_state.last_click_time = 0.0
    else:
        # ダブルクリック・ダブルタップで登録ポップアップ
        if cal_result and cal_result.get("callback") == "dateClick":
            clicked_date_str = cal_result["dateClick"]["date"][:10]
            now = _time.time()
            if (clicked_date_str == st.session_state.last_click_date and
                    now - st.session_state.last_click_time < 0.8):
                # ダブルクリック検知
                st.session_state.last_click_date = None
                st.session_state.last_click_time = 0.0
                from datetime import date
                clicked_date = date.fromisoformat(clicked_date_str)
                show_register_popup(clicked_date)
            else:
                st.session_state.last_click_date = clicked_date_str
                st.session_state.last_click_time = now

        # 予定クリック時：編集・削除ポップアップ
        elif cal_result and cal_result.get("callback") == "eventClick":
            st.session_state.last_click_date = None
            st.session_state.last_click_time = 0.0
            event_id = int(cal_result["eventClick"]["event"]["id"])
            show_edit_popup(event_id, df_schedules)

# ==========================================
# 3. 🛠️ 修正・削除（カレンダーの予定をクリックで編集）
# ==========================================
st.caption("💡 カレンダー上の予定バーをクリックすると編集・削除ポップアップが開きます。")