import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from services.fpl_api import (
    get_bootstrap_static,
    get_live_fixtures,
    get_gameweek_info
)
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Live Matches", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.metric-card {
    background: #161b22;
    padding: 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.06);
    transition: 0.2s ease-in-out;
    margin-bottom: 0.5rem;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
}

.metric-card:hover {
    border: 1px solid #00ff87;
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0, 255, 135, 0.15);
}

.team-name {
    font-size: 1.8rem;
    font-weight: 700;
    color: white;
    font-family: 'Outfit', sans-serif !important;
}

.score {
    font-size: 3rem;
    font-weight: 800;
    color: #00ff87;
    padding: 0 1.5rem;
}

.match-status {
    font-size: 1rem;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 1rem;
    text-align: center;
    letter-spacing: 0.05em;
}

.stat-item {
    font-size: 1rem;
    margin-bottom: 0.5rem;
    color: #e2e8f0;
}
.stat-item-label {
    color: #9ca3af;
    font-weight: bold;
    margin-right: 5px;
    text-transform: uppercase;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Live Matches Dashboard")
st.markdown("<p style='color:#9ca3af; margin-top:-1rem; font-size: 1.2rem;'>Real-time Match Center: Time, Goals, Assists, and Bonus Points</p>", unsafe_allow_html=True)

with st.spinner("Fetching Live Match Data..."):
    with ThreadPoolExecutor() as executor:
        f_boot = executor.submit(get_bootstrap_static)
        f_fix = executor.submit(get_live_fixtures)
        f_gw = executor.submit(get_gameweek_info)
        
        bootstrap = f_boot.result()
        fixtures = f_fix.result()
        gw_info = f_gw.result()

if not bootstrap or not fixtures or not gw_info:
    st.error("Failed to load FPL data. Please try again.")
    st.stop()

# Helper mappings
teams_map = {t['id']: t for t in bootstrap['teams']}
players_map = {p['id']: p for p in bootstrap['elements']}

current_gw = gw_info.get("current", 1)

# Sidebar for GW Selection
st.sidebar.markdown("### ⚙️ View Options")
available_gws = sorted(list(set([f.get("event") for f in fixtures if f.get("event")])))
if not available_gws:
    st.info("No fixtures available.")
    st.stop()
selected_gw = st.sidebar.selectbox("Gameweek", available_gws, index=available_gws.index(current_gw) if current_gw in available_gws else 0)

gw_fixtures = [f for f in fixtures if f.get('event') == selected_gw]

if not gw_fixtures:
    st.info(f"No fixtures found for Gameweek {selected_gw}.")
    st.stop()

# Sort fixtures: live/started first
gw_fixtures = sorted(gw_fixtures, key=lambda x: (not x.get('started'), x.get('kickoff_time') or ""))

for fixture in gw_fixtures:
    team_h = teams_map.get(fixture['team_h'], {})
    team_a = teams_map.get(fixture['team_a'], {})
    team_h_name = team_h.get('name', 'Home')
    team_a_name = team_a.get('name', 'Away')
    
    score_h = fixture.get('team_h_score')
    score_a = fixture.get('team_a_score')
    
    started = fixture.get('started')
    finished = fixture.get('finished_provisional') or fixture.get('finished')
    minutes = fixture.get('minutes', 0)
    
    if finished:
        match_status = "Full Time"
        status_color = "#ff185e"
    elif started:
        match_status = f"{minutes}' LIVE"
        status_color = "#00ff87"
    else:
        ko_time_str = fixture.get('kickoff_time')
        if ko_time_str:
            try:
                ko_time = datetime.strptime(ko_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                match_status = ko_time.strftime("%A, %H:%M UTC")
            except:
                match_status = "Upcoming"
        else:
            match_status = "TBC"
        status_color = "#02efff"

    score_display_h = score_h if score_h is not None else ""
    score_display_a = score_a if score_a is not None else ""
    score_divider = "-" if started else "vs"

    st.markdown(f"""
    <div class="metric-card">
        <div class="match-status" style="color: {status_color};">{match_status}</div>
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 0.5rem;">
            <div class="team-name" style="flex: 1; text-align: right;">{team_h_name}</div>
            <div class="score">{score_display_h} <span style="color: #4b5563; font-size: 2rem;">{score_divider}</span> {score_display_a}</div>
            <div class="team-name" style="flex: 1; text-align: left;">{team_a_name}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if started:
        stats = fixture.get('stats', [])
        
        def render_stat(stat_id):
            stat_obj = next((s for s in stats if s['identifier'] == stat_id), None)
            if not stat_obj: return None, None
            
            h_data = stat_obj.get('h', [])
            a_data = stat_obj.get('a', [])
            
            def get_text(items):
                lines = []
                for item in items:
                    p = players_map.get(item['element'], {}).get('web_name', 'Unknown')
                    val = item['value']
                    lines.append(f"{p} ({val})")
                return ", ".join(lines)
                
            return get_text(h_data), get_text(a_data)

        g_h, g_a = render_stat('goals_scored')
        a_h, a_a = render_stat('assists')
        b_h, b_a = render_stat('bonus')
        bps_h, bps_a = render_stat('bps')
        
        # Only render if there's data
        has_data = any([g_h, g_a, a_h, a_a, b_h, b_a, bps_h, bps_a])
        if has_data:
            with st.container():
                c1, c2 = st.columns(2)
                
                with c1:
                    # Home Stats
                    html = ""
                    if g_h: html += f"<div class='stat-item'><span class='stat-item-label'>⚽ Goals:</span> {g_h}</div>"
                    if a_h: html += f"<div class='stat-item'><span class='stat-item-label'>🤝 Assists:</span> {a_h}</div>"
                    if b_h: html += f"<div class='stat-item'><span class='stat-item-label'>⭐ Bonus:</span> {b_h}</div>"
                    if bps_h: html += f"<div class='stat-item'><span class='stat-item-label'>📊 BPS:</span> {bps_h}</div>"
                    if html: st.markdown(f"<div style='background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 0 0 12px 12px; border: 1px solid rgba(255,255,255,0.05); border-top: none; margin-bottom: 2rem;'>{html}</div>", unsafe_allow_html=True)
                
                with c2:
                    # Away Stats
                    html = ""
                    if g_a: html += f"<div class='stat-item'><span class='stat-item-label'>⚽ Goals:</span> {g_a}</div>"
                    if a_a: html += f"<div class='stat-item'><span class='stat-item-label'>🤝 Assists:</span> {a_a}</div>"
                    if b_a: html += f"<div class='stat-item'><span class='stat-item-label'>⭐ Bonus:</span> {b_a}</div>"
                    if bps_a: html += f"<div class='stat-item'><span class='stat-item-label'>📊 BPS:</span> {bps_a}</div>"
                    if html: st.markdown(f"<div style='background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 0 0 12px 12px; border: 1px solid rgba(255,255,255,0.05); border-top: none; margin-bottom: 2rem;'>{html}</div>", unsafe_allow_html=True)
        else:
             st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
