import streamlit as st
import pandas as pd
from services.fpl_api import get_manager_team, get_bootstrap_static

st.set_page_config(page_title="My FPL Team", page_icon="🛡️", layout="wide")

# --- HEADER SECTION ---
st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">MANAGER <span style="color: #00ff87;">OFFICE</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Command Center • Performance Analytics • Season Tracker</p>
    </div>
""", unsafe_allow_html=True)

# Quick search input
col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    team_id = st.text_input("Enter FPL Team ID:", placeholder="Found in your Points URL (e.g. 192837)", key="manager_office_id")
with col_in2:
    st.write("<br>", unsafe_allow_html=True)
    load_clicked = st.button("Sync Office", type="primary", use_container_width=True)

if team_id and (load_clicked or st.session_state.get('auto_load', False)):
    if not team_id.isdigit():
        st.warning("Please enter a numeric ID.")
    else:
        with st.spinner("Accessing FPL Mainframe..."):
            team_data = get_manager_team(team_id)
            if team_data and "error" not in team_data:
                st.success(f"Connection Secure: **{team_data.get('player_first_name', '')} {team_data.get('player_last_name', '')}**")
                
                # Show Quick Team Stats in glass cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #02efff">
                        <h3>Overall Rank</h3>
                        <p>{team_data.get('summary_overall_rank', 0):,}</p>
                        <span style="color: #02efff; font-weight: 700;">Global Standing</span>
                    </div>''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #00ff87">
                        <h3>Total Points</h3>
                        <p>{team_data.get('summary_overall_points', 0)}</p>
                        <span style="color: #00ff87; font-weight: 700;">Season Total</span>
                    </div>''', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #ff185e">
                        <h3>GW Score</h3>
                        <p>{team_data.get('summary_event_points', '--')}</p>
                        <span style="color: #ff185e; font-weight: 700;">Current Gameweek</span>
                    </div>''', unsafe_allow_html=True)
                with col4:
                    val = team_data.get('last_deadline_value', 0)/10
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #7632ff">
                        <h3>Squad Value</h3>
                        <p>£{val:.1f}m</p>
                        <span style="color: #7632ff; font-weight: 700;">Incl. £{team_data.get('last_deadline_bank',0)/10:.1f}m Bank</span>
                    </div>''', unsafe_allow_html=True)
                
                st.divider()
                
                col_left, col_right = st.columns([2, 1])
                
                with col_left:
                    st.subheader("🏆 Classic Leagues")
                    leagues = team_data.get("leagues", {}).get("classic", [])
                    if leagues:
                        league_rows = []
                        for league in leagues:
                            league_rows.append({
                                "League": league['name'],
                                "Rank": f"{league['entry_rank']:,}",
                                "Status": "⬆️" if league['entry_rank'] < league['entry_last_rank'] else "⬇️" if league['entry_rank'] > league['entry_last_rank'] else "↔️"
                            })
                        st.table(pd.DataFrame(league_rows).head(10))
                    else:
                        st.info("No active leagues found.")

                with col_right:
                    st.subheader("💡 Manager Insights")
                    # Analysis of rank
                    rank = team_data.get('summary_overall_rank', 1000000)
                    if rank < 10000:
                        st.balloons()
                        st.success("💎 **Elite Tier:** You are in the top 0.1% of managers worldwide!")
                    elif rank < 100000:
                        st.info("🌟 **Top Tier:** Excellent positioning for a top 50k finish.")
                    else:
                        st.warning("📈 **Growth Opportunity:** The AI suggests focusing on 'Differential' picks to climb the ranks quickly.")
                        
                    st.markdown("""
                        <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px;">
                            <p style="color: #adb5bd; font-size: 0.9rem;">
                                <b>Pro Tip:</b> Use the <b>Transfer AI</b> page to see how your specific squad can be improved using our ML projections.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Access Denied: Could not find Manager ID in FPL database.")
else:
    st.markdown("""
        <div style="background: rgba(255,255,255,0.03); padding: 5rem; border-radius: 24px; text-align: center; border: 1px dashed var(--glass-border);">
            <h2 style="color: #adb5bd !important; font-weight: 300;">Ready to Sync?</h2>
            <p style="color: #6c757d; font-size: 1.1rem;">Enter your Team ID above to access your personal dashboard.</p>
        </div>
    """, unsafe_allow_html=True)
    st.caption("How to find your ID? Check the URL when viewing your team on the official site.")

