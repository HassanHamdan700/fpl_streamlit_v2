import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from services.fpl_api import (
    get_bootstrap_static,
    get_live_fixtures,
    get_gameweek_info
)
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Live Match Center", page_icon="⚽", layout="wide")

# =========================
# PREMIUM LIVE MATCH CSS
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;800&display=swap');
    * { font-family: 'Outfit', sans-serif !important; }

    .match-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.4);
    }
    
    .status-badge {
        font-weight: 800;
        font-size: 0.65rem;
        padding: 5px 15px;
        border-radius: 100px;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 1.5rem;
        display: inline-block;
    }
    
    .scoreboard-grid {
        display: grid;
        grid-template-columns: 1fr 140px 1fr;
        align-items: center;
        text-align: center;
        gap: 15px;
    }
    
    .team-badge-img {
        width: 60px;
        height: 60px;
        object-fit: contain;
        display: block;
        margin: 0 auto 10px auto;
    }
    
    .team-name-pro {
        font-size: 1.4rem;
        font-weight: 800;
        color: white;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .score-container {
        background: #000;
        padding: 0.5rem;
        border-radius: 14px;
        font-size: 3rem;
        font-weight: 800;
        color: #00ff87;
        border: 1px solid rgba(0, 255, 135, 0.2);
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }
    
    .stat-pill-pro {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        color: #e2e8f0;
        display: flex;
        align-items: center;
        gap: 6px;
        margin: 3px;
    }
    
    .stat-section-title {
        color: #9ca3af;
        font-size: 0.6rem;
        font-weight: 900;
        margin-top: 12px;
        margin-bottom: 4px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .live-indicator {
        width: 6px;
        height: 6px;
        background: #ff185e;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        animation: pulse-red 1.5s infinite;
    }
    
    @keyframes pulse-red {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Live Match Center")

with st.spinner("Updating Feed..."):
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_boot = executor.submit(get_bootstrap_static)
        f_fix = executor.submit(get_live_fixtures)
        f_gw = executor.submit(get_gameweek_info)
        boot, fixtures, gw_info = f_boot.result(), f_fix.result(), f_gw.result()

if not all([boot, fixtures, gw_info]):
    st.error("Live feed offline.")
    st.stop()

players_map = {p['id']: p for p in boot['elements']}
teams_map = {t['id']: {'name': t['name'], 'code': t['code']} for t in boot['teams']}
current_gw = gw_info.get("current", 1)
available_gws = sorted(list(set([f['event'] for f in fixtures if f['event']])))
selected_gw = st.sidebar.selectbox("Select Gameweek", available_gws, index=available_gws.index(current_gw) if current_gw in available_gws else 0)

gw_fixtures = sorted([f for f in fixtures if f.get('event') == selected_gw], key=lambda x: (not x.get('started'), x.get('kickoff_time') or ""))

for fix in gw_fixtures:
    started, finished = fix.get('started'), fix.get('finished_provisional') or fix.get('finished')
    
    st_style = "background:rgba(2, 239, 255, 0.1); color:#02efff; border:1px solid rgba(2, 239, 255, 0.2);"
    st_text = "Upcoming"
    if finished:
        st_style = "background:rgba(255, 24, 94, 0.1); color:#ff185e; border:1px solid rgba(255, 24, 94, 0.2);"
        st_text = "Full Time"
    elif started:
        st_style = "background:rgba(0, 255, 135, 0.1); color:#00ff87; border:1px solid rgba(0, 255, 135, 0.2);"
        st_text = f"<span class='live-indicator'></span> {fix.get('minutes', 0)}' LIVE"

    t_h, t_a = teams_map.get(fix['team_h']), teams_map.get(fix['team_a'])
    badge_h = f"https://resources.premierleague.com/premierleague/badges/t{t_h['code']}.png"
    badge_a = f"https://resources.premierleague.com/premierleague/badges/t{t_a['code']}.png"
    sc_h, sc_a = fix.get('team_h_score', ''), fix.get('team_a_score', '')
    div = "-" if started else "vs"

    # BUILD CARD
    card_html = f"""
    <div class="match-card">
        <center><div class="status-badge" style="{st_style}">{st_text}</div></center>
        <div class="scoreboard-grid">
            <div class="team-side">
                <img src="{badge_h}" class="team-badge-img">
                <div class="team-name-pro">{t_h['name']}</div>
            </div>
            <div class="score-container">
                <span>{sc_h}</span>
                <span style="font-size: 1.2rem; color: #4b5563;">{div}</span>
                <span>{sc_a}</span>
            </div>
            <div class="team-side">
                <img src="{badge_a}" class="team-badge-img">
                <div class="team-name-pro">{t_a['name']}</div>
            </div>
        </div>
    """

    if started:
        fx_stats = fix.get('stats', [])
        card_html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 1.5rem;">'
        for side in ['h', 'a']:
            side_html = '<div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 12px; height: 100%;">'
            for skey in ['goals_scored', 'assists', 'bonus']:
                sobj = next((s for s in fx_stats if s['identifier'] == skey), None)
                if sobj and sobj.get(side):
                    side_html += f'<div class="stat-section-title">{skey.replace("_"," ")}</div>'
                    side_html += '<div style="display: flex; flex-wrap: wrap;">'
                    icon = "⚽" if skey == 'goals_scored' else ("🤝" if skey == 'assists' else "⭐")
                    for itm in sobj.get(side):
                        pname = players_map.get(itm['element'], {}).get('web_name', 'Unknown')
                        side_html += f'<div class="stat-pill-pro">{icon} <b>{pname}</b> {itm["value"]}</div>'
                    side_html += '</div>'
            side_html += '</div>'
            card_html += side_html
        card_html += '</div>'

    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)
