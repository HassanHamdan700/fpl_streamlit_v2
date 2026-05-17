import streamlit as st
import datetime
from concurrent.futures import ThreadPoolExecutor
from services.fpl_api import (
    get_bootstrap_static,
    get_manager_team,
    get_manager_picks,
    get_live_gameweek_data,
    get_gameweek_info,
    get_live_fixtures
)

st.set_page_config(
    page_title="Live Points Pro",
    page_icon="⚡",
    layout="wide"
)

# =========================
# ADVANCED GLASSMORHISM CSS
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap');
    
    * { font-family: 'Outfit', sans-serif; }

    .main {
        background: radial-gradient(circle at top left, #0d1117, #010409);
    }
    
    .total-points-card {
        background: rgba(0, 255, 135, 0.1);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(0, 255, 135, 0.2);
        padding: 2.5rem;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
    }
    
    .total-points-val {
        font-size: 6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00ff87 0%, #60efff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
        margin: 0.5rem 0;
    }
    
    .total-points-label {
        font-size: 1.1rem;
        font-weight: 700;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 4px;
    }

    .chip-badge {
        background: rgba(255, 255, 255, 0.05);
        color: #00ff87;
        padding: 6px 16px;
        border-radius: 100px;
        font-size: 0.85rem;
        font-weight: 700;
        border: 1px solid rgba(0, 255, 135, 0.2);
    }

    .player-card {
        background: rgba(22, 27, 34, 0.6);
        backdrop-filter: blur(8px);
        padding: 1.25rem;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 12px;
        position: relative;
        overflow: hidden;
    }
    
    .player-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(0, 255, 135, 0.3);
        background: rgba(22, 27, 34, 0.8);
    }

    .player-name {
        font-weight: 700;
        font-size: 1.2rem;
        color: white;
        margin-bottom: 2px;
    }

    .player-points {
        font-size: 2rem;
        font-weight: 800;
        color: #00ff87;
        text-shadow: 0 0 15px rgba(0, 255, 135, 0.4);
    }

    .captain-badge {
        background: linear-gradient(135deg, #ff185e 0%, #ff4b1f 100%);
        color: white;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 900;
        margin-left: 8px;
    }

    .sub-badge {
        background: rgba(0, 255, 135, 0.1);
        color: #00ff87;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 800;
        text-transform: uppercase;
        border: 1px solid rgba(0, 255, 135, 0.2);
        margin-bottom: 5px;
        display: inline-block;
    }

    .match-status {
        font-size: 0.65rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        margin-bottom: 5px;
        display: inline-block;
    }

    .status-live { background: rgba(255, 24, 94, 0.1); color: #ff185e; border: 1px solid rgba(255, 24, 94, 0.2); }
    .status-finished { background: rgba(107, 114, 128, 0.1); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.2); }
    .status-upcoming { background: rgba(0, 242, 255, 0.1); color: #00f2ff; border: 1px solid rgba(0, 242, 255, 0.2); }

    .stat-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# TITLE & SYNC
# =========================
st.title("⚡ Live Points Pro")
last_sync = datetime.datetime.now().strftime("%H:%M:%S")
st.markdown(f"<p style='color:#9ca3af; margin-top:-1rem;'>Real-time tracking • Estimated Bonus • Last sync: <b>{last_sync}</b></p>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    manager_id = st.text_input("Enter Manager ID", value=st.session_state.get("last_manager_id", ""), placeholder="e.g. 123456")

gw_info = get_gameweek_info()
current_gw = gw_info.get("current", 1)

with col2:
    target_gw = st.number_input("Gameweek", min_value=1, max_value=38, value=current_gw)

if manager_id:
    st.session_state["last_manager_id"] = manager_id
    try:
        m_id = int(manager_id)
    except:
        st.error("Invalid Manager ID.")
        st.stop()

    with st.spinner("Fetching data from FPL..."):
        with ThreadPoolExecutor() as executor:
            f_boot = executor.submit(get_bootstrap_static)
            f_team = executor.submit(get_manager_team, m_id)
            f_picks = executor.submit(get_manager_picks, m_id, target_gw)
            f_live = executor.submit(get_live_gameweek_data, target_gw)
            f_fix = executor.submit(get_live_fixtures)

            boot = f_boot.result()
            team = f_team.result()
            picks_data = f_picks.result()
            live = f_live.result()
            fixtures = f_fix.result()

    if not all([boot, team, picks_data, live]):
        st.error("Could not load data.")
        st.stop()

    p_map = {p["id"]: p for p in boot["elements"]}
    t_map = {t["id"]: t for t in boot["teams"]}
    l_map = {p["id"]: p["stats"] for p in live["elements"]}
    
    # Match Status Map (team_id -> status)
    match_map = {}
    if fixtures:
        gw_fixtures = [f for f in fixtures if f.get("event") == target_gw]
        for f in gw_fixtures:
            status = "Upcoming"
            if f.get("finished"): status = "Finished"
            elif f.get("started"): status = "Live"
            
            match_map[f["team_h"]] = status
            match_map[f["team_a"]] = status

    manager_name = f"{team.get('player_first_name', '')} {team.get('player_last_name', '')}"
    team_name = team.get("name", "My Team")
    picks = picks_data.get("picks", [])
    active_chip = picks_data.get("active_chip")

    st.markdown(f"### 🛡️ {team_name} <span style='font-size:0.9rem;color:#4b5563;font-weight:normal;'>by {manager_name}</span>", unsafe_allow_html=True)

    starters = []
    bench = []
    for pick in picks:
        p_id = pick["element"]
        stc = p_map.get(p_id, {})
        ls = l_map.get(p_id, {})
        ptype = stc.get("element_type")
        mult = pick["multiplier"]
        team_id = stc.get("team")
        
        mins = ls.get("minutes", 0)
        m_pts = 1 if 0 < mins < 60 else (2 if mins >= 60 else 0)
        goals = ls.get("goals_scored", 0)
        g_pts = (goals*6) if ptype in [1,2] else ((goals*5) if ptype==3 else (goals*4))
        a_pts = ls.get("assists", 0) * 3
        cs_pts = 4 if (ls.get("clean_sheets",0)>0 and ptype in [1,2]) else (1 if (ls.get("clean_sheets",0)>0 and ptype==3) else 0)
        c_pts = (ls.get("yellow_cards",0)*-1) + (ls.get("red_cards",0)*-3)
        gc_pts = ((ls.get("goals_conceded",0)//2)*-1) if ptype in [1,2] else 0
        s_pts = (ls.get("saves",0)//3) if ptype==1 else 0
        b_pts = ls.get("bonus", 0)
        if b_pts == 0:
            bps = ls.get("bps", 0)
            if bps >= 30: b_pts = 3
            elif bps >= 24: b_pts = 2
            elif bps >= 18: b_pts = 1

        raw = m_pts + g_pts + a_pts + cs_pts + c_pts + gc_pts + s_pts + b_pts
        raw += (ls.get("penalties_saved",0)*5) + (ls.get("penalties_missed",0)*-2) + (ls.get("own_goals",0)*-2)
        
        final = raw * mult
        
        status = match_map.get(team_id, "Upcoming")
        
        data = {
            "name": stc.get("web_name", "Unknown"),
            "team": t_map.get(team_id, {}).get("name", "TBC"),
            "points": final,
            "raw": raw,
            "minutes": mins,
            "goals": goals,
            "assists": ls.get("assists", 0),
            "bonus": b_pts,
            "mult": mult,
            "is_cap": pick["is_captain"],
            "type": ptype,
            "sub_in": False,
            "status": status
        }
        if pick["position"] <= 11 or active_chip == "bboost":
            starters.append(data)
        else:
            bench.append(data)

    # Auto-Sub
    if active_chip != "bboost":
        for i, s in enumerate(starters):
            if s["minutes"] == 0 and s["status"] != "Upcoming":
                for j, b in enumerate(bench):
                    if b["minutes"] > 0:
                        if (s["type"] == 1 and b["type"] == 1) or (s["type"] != 1 and b["type"] != 1):
                            starters[i], bench[j] = bench[j], starters[i]
                            starters[i]["sub_in"] = True
                            break

    total = sum(p["points"] for p in starters)
    if active_chip == "bboost": total += sum(p["points"] for p in bench)

    chip_html = f"<div class='chip-badge'>{active_chip.replace('_', ' ').title()} ACTIVE</div>" if active_chip else ""
    st.markdown(f"""
        <div class="total-points-card">
            <div class="total-points-label">Total Live Gameweek Points</div>
            <div class="total-points-val">{total}</div>
            {chip_html}
        </div>
    """, unsafe_allow_html=True)

    # Formation Grid
    rows = {1: "Goalkeeper", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
    for p_type, label in rows.items():
        row_players = [p for p in starters if p["type"] == p_type]
        if row_players:
            st.markdown(f"<div class='section-title'>{label}</div>", unsafe_allow_html=True)
            cols = st.columns(len(row_players))
            for i, p in enumerate(row_players):
                with cols[i]:
                    c_tag = f"<span class='captain-badge'>{'TC' if p['mult']==3 else 'C'}</span>" if p["is_cap"] else ""
                    sub_tag = "<div class='sub-badge'>🔄 Sub In</div>" if p["sub_in"] else ""
                    
                    status_class = f"status-{p['status'].lower()}"
                    status_tag = f"<div class='match-status {status_class}'>{p['status']}</div>"
                    
                    stats = []
                    if p["goals"] > 0: stats.append(f"⚽ {p['goals']}")
                    if p["assists"] > 0: stats.append(f"🤝 {p['assists']}")
                    if p["bonus"] > 0: stats.append(f"⭐ {p['bonus']}")
                    stats_str = " | ".join(stats) if stats else "No active returns"

                    st.markdown(f"""
                        <div class="player-card">
                            {sub_tag} {status_tag}
                            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                <div>
                                    <div class="player-name">{p['name']}{c_tag}</div>
                                    <div style="font-size:0.75rem;color:#6b7280;margin-bottom:8px;">{p['team']}</div>
                                    <div class="small-stat">{stats_str}</div>
                                </div>
                                <div class="player-points">{p['points']}</div>
                            </div>
                            <div class="stat-row">
                                <span>{p['minutes']} MINS</span>
                                <span>{p['raw']} RAW PTS</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    if bench:
        st.markdown("<div class='section-title'>Bench</div>", unsafe_allow_html=True)
        bcols = st.columns(4)
        for i, p in enumerate(bench):
            with bcols[i]:
                status_class = f"status-{p['status'].lower()}"
                st.markdown(f"""
                    <div class="player-card" style="opacity:0.6;">
                        <div class='match-status {status_class}' style='zoom:0.8;'>{p['status']}</div>
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div>
                                <div class="player-name" style="font-size:1rem;">{p['name']}</div>
                                <div style="font-size:0.7rem;color:#4b5563;">{p['team']}</div>
                            </div>
                            <div class="player-points" style="font-size:1.4rem;">{p['points']}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

else:
    st.info("💡 Enter your FPL Manager ID to begin live tracking.")
    if st.button("Example: Load Elite Team"):
        st.session_state["last_manager_id"] = "1"
        st.rerun()