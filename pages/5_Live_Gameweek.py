import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static, get_live_gameweek_data, get_manager_team, get_manager_picks

st.set_page_config(page_title="Live Gameweek", page_icon="📡", layout="wide")
st.title("📡 Live Gameweek Dashboard")

# Fetch Central Data
bootstrap = get_bootstrap_static()
if not bootstrap:
    st.error("Could not load FPL data.")
    st.stop()

# Determined Current Gameweek
events = bootstrap.get('events', [])
current_event = next((e for e in events if e.get('is_current')), None)
if not current_event:
    current_event = events[0] if events else None

if not current_event:
    st.warning("No gameweek events found.")
    st.stop()

gw_id = current_event['id']

# --- HEADER SECTION ---
st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem 0 3rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">LIVE <span style="color: #00ff87;">STATS</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Gameweek {gw_id} Tracking • Real-time Data</p>
    </div>
""", unsafe_allow_html=True)

# Quick GW Stats in custom cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'''<div class="metric-card">
        <h3>Average Score</h3>
        <p>{current_event.get('average_entry_score', 0)}</p>
        <span style="color: #00ff87; font-weight: 700;">Global Avg</span>
    </div>''', unsafe_allow_html=True)
with col2:
    st.markdown(f'''<div class="metric-card" style="border-left-color: #02efff">
        <h3>Highest Score</h3>
        <p>{current_event.get('highest_score', 0)}</p>
        <span style="color: #02efff; font-weight: 700;">Top Manager</span>
    </div>''', unsafe_allow_html=True)
with col3:
    st.markdown(f'''<div class="metric-card" style="border-left-color: #ff185e">
        <h3>Active Transfers</h3>
        <p>{current_event.get('transfers_made', 0) // 1000}K</p>
        <span style="color: #ff185e; font-weight: 700;">This Week</span>
    </div>''', unsafe_allow_html=True)
with col4:
    status = "Finished" if current_event.get('finished') else "Live"
    st.markdown(f'''<div class="metric-card" style="border-left-color: #7632ff">
        <h3>GW Status</h3>
        <p>{status}</p>
        <span style="color: #7632ff; font-weight: 700;">{current_event['name']}</span>
    </div>''', unsafe_allow_html=True)

st.divider()

# Manager Specific Live Data
col_left, col_right = st.columns([2, 3])

with col_left:
    st.subheader("🕵️ Manager Tracker")
    team_id = st.text_input("Enter FPL Team ID:", placeholder="e.g. 192837", key="live_team_id")
    
    if team_id:
        if team_id.isdigit():
            with st.spinner("Calculating live score..."):
                manager_picks = get_manager_picks(int(team_id), gw_id)
                live_data = get_live_gameweek_data(gw_id)
                
                if manager_picks and live_data:
                    player_live_map = {p['id']: p['stats'] for p in live_data.get('elements', [])}
                    bootstrap_players = {p['id']: p for p in bootstrap.get('elements', [])}
                    
                    picks = manager_picks.get('picks', [])
                    total_pts = 0
                    
                    rows = []
                    for pick in picks:
                        pid = pick['element']
                        mult = pick['multiplier']
                        stats = player_live_map.get(pid, {})
                        p_info = bootstrap_players.get(pid, {})
                        p_pts = stats.get('total_points', 0)
                        active_pts = p_pts * mult
                        if mult > 0: total_pts += active_pts
                        
                        rows.append({
                            "Player": p_info.get('web_name', 'Unknown'),
                            "Points": p_pts,
                            "Net": active_pts if mult > 0 else "Benched"
                        })
                    
                    st.markdown(f"""
                        <div class="metric-card" style="background: rgba(0, 255, 135, 0.05); text-align: center;">
                            <h3 style="color: white !important;">LIVE GW TOTAL</h3>
                            <p style="font-size: 3rem; color: #00ff87 !important;">{total_pts}</p>
                            <span>Including Captain Multipliers</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.table(pd.DataFrame(rows).head(15))
        else:
            st.error("Invalid Team ID")
    else:
        st.info("Input your Team ID to see a live breakdown of your points and bonus predictions.")

with col_right:
    st.subheader("🌟 Top Live Performers")
    live_data = get_live_gameweek_data(gw_id)
    if live_data:
        elements = live_data.get('elements', [])
        top_live = sorted(elements, key=lambda x: x['stats']['total_points'], reverse=True)[:10]
        bootstrap_players = {p['id']: p['web_name'] for p in bootstrap.get('elements', [])}
        
        top_rows = []
        for p in top_live:
            top_rows.append({
                "Player": bootstrap_players.get(p['id'], "Unknown"),
                "Points": p['stats']['total_points'],
                "Goals": p['stats']['goals_scored'],
                "Assists": p['stats']['assists'],
                "BPS": p['stats']['bps']
            })
        
        st.dataframe(pd.DataFrame(top_rows), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🚀 Bonus Point Watch")
        st.caption("Bonus points are calculated by the official BPS system and awarded after the game concludes.")
        # Logic to show players leading in BPS in live games
        bps_leaders = sorted(elements, key=lambda x: x['stats']['bps'], reverse=True)[:5]
        for p in bps_leaders:
            name = bootstrap_players.get(p['id'], "Unknown")
            bps = p['stats']['bps']
            st.write(f"- **{name}**: {bps} BPS (Projected +3 bonus)")

