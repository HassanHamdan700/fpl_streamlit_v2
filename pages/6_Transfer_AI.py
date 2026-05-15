import streamlit as st
import pandas as pd
import numpy as np
from services.fpl_api import get_bootstrap_static, get_manager_picks, get_manager_team, get_fixtures, get_gameweek_info
from services.ml_prediction import get_predictor
from services.match_prediction import get_match_predictor

st.set_page_config(page_title="AI Transfer Planner", page_icon="📈", layout="wide")

# Load core data
with st.spinner("Crunching global player data and fixture schedules..."):
    bootstrap = get_bootstrap_static()
    predictor = get_predictor()
    match_predictor = get_match_predictor()
    fixtures = get_fixtures()

if not bootstrap or not fixtures:
    st.error("Could not reach FPL Servers. Please check your internet connection.")
    st.stop()

# Helper: Get Upcoming FDR for each team
gw_info = get_gameweek_info()
current_gw = gw_info['current']
next_gw = gw_info['next']

team_next_fdr = {}
for t in bootstrap['teams']:
    match = next((f for f in fixtures if f['event'] == next_gw and (f['team_h'] == t['id'] or f['team_a'] == t['id'])), None)
    if match:
        is_home = match['team_h'] == t['id']
        team_next_fdr[t['id']] = match['team_h_difficulty'] if is_home else match['team_a_difficulty']
    else:
        team_next_fdr[t['id']] = 3 # Average for blank/unknown

# --- HEADER SECTION ---
st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">TRANSFER <span style="color: #00ff87;">PLANNER</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">AI-Powered Squad Optimization • GW {0} Ready</p>
    </div>
""".format(next_gw), unsafe_allow_html=True)

# Inputs
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    team_id = st.text_input("Enter FPL Team ID:", placeholder="e.g. 128374", key="transfer_planner_id")
with col_in2:
    st.write("<br>", unsafe_allow_html=True)
    st.info(f"Next Deadline: GW {next_gw}")

if team_id and team_id.isdigit():
    with st.spinner("Analyzing squad weaknesses..."):
        picks_data = get_manager_picks(int(team_id), current_gw)
        manager_data = get_manager_team(int(team_id))
        
        if picks_data and "picks" in picks_data:
            current_picks = [p['element'] for p in picks_data['picks']]
            bank = (manager_data.get('last_deadline_bank', 0) / 10.0)
            
            elements_df = pd.DataFrame(bootstrap['elements'])
            elements_df['now_cost_m'] = elements_df['now_cost'] / 10.0
            teams_map = {t['id']: t['name'] for t in bootstrap['teams']}
            
            # Predict Points using NEXT GW difficulty
            inf_df = pd.DataFrame({
                'form': pd.to_numeric(elements_df['form'], errors='coerce').fillna(0),
                'selected_by_percent': pd.to_numeric(elements_df['selected_by_percent'], errors='coerce').fillna(0),
                'now_cost': elements_df['now_cost_m'],
                'minutes_played_best': elements_df['minutes'] / 90.0,
                'fdr_upcoming': elements_df['team'].map(team_next_fdr).fillna(3)
            })
            elements_df['xPts'] = predictor.predict_points(inf_df)
            
            # Team Analysis
            my_team_df = elements_df[elements_df['id'].isin(current_picks)].copy()
            my_team_df['team_name'] = my_team_df['team'].map(teams_map)
            
            st.markdown(f"### 🛡️ Your GW {current_gw} Squad")
            
            # Show squad in a nice table
            squad_display = my_team_df[['web_name', 'team_name', 'element_type', 'now_cost_m', 'xPts']].copy()
            pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
            squad_display['Pos'] = squad_display['element_type'].map(pos_map)
            
            st.dataframe(
                squad_display.sort_values('element_type').rename(columns={
                    'web_name': 'Player', 'team_name': 'Team', 'now_cost_m': 'Value', 'xPts': 'Proj. Pts'
                })[['Player', 'Team', 'Pos', 'Value', 'Proj. Pts']],
                use_container_width=True,
                hide_index=True
            )

            st.divider()
            
            # Interactive Selection
            st.subheader("🔄 Strategic Swap")
            col_sel1, col_sel2 = st.columns([1,1])
            
            with col_sel1:
                sell_name = st.selectbox("Select Player to SELL:", my_team_df.sort_values('xPts')['web_name'].tolist())
                sell_player = my_team_df[my_team_df['web_name'] == sell_name].iloc[0]
                sell_price = sell_player['now_cost_m']
                total_budget = sell_price + bank
            
            with col_sel2:
                st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; border-left: 4px solid #00ff87;">
                        <p style="margin-bottom: 0; font-size: 0.9rem; color: #adb5bd;">Total Replacement Budget</p>
                        <h2 style="margin-top: 0; color: #00ff87 !important;">£{total_budget:.1f}m</h2>
                        <span style="font-size: 0.8rem; color: #6c757d;">(£{sell_price:.1f}m player + £{bank:.1f}m bank)</span>
                    </div>
                """, unsafe_allow_html=True)

            # Replacement scouting
            pos_id = sell_player['element_type']
            replacements = elements_df[
                (elements_df['element_type'] == pos_id) & 
                (elements_df['now_cost_m'] <= total_budget) &
                (~elements_df['id'].isin(current_picks)) &
                (elements_df['chance_of_playing_next_round'].fillna(100) >= 75)
            ].copy()
            
            replacements['gain'] = replacements['xPts'] - sell_player['xPts']
            significant_recs = replacements.sort_values(by='xPts', ascending=False)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if not significant_recs.empty:
                st.subheader(f"💎 Best {pos_map[pos_id]} Replacements")
                
                # Highlight Top 1
                best_buy = significant_recs.iloc[0]
                
                # Visual Comparison
                comp_1, comp_2, comp_3 = st.columns([1, 0.5, 1])
                with comp_1:
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #ff185e; background: rgba(255, 24, 94, 0.05);">
                        <h3 style="color: #ff185e !important;">SELL</h3>
                        <p>{sell_player['web_name']}</p>
                        <span style="color: #adb5bd;">{sell_player['xPts']:.1f} xPts</span>
                    </div>''', unsafe_allow_html=True)
                with comp_2:
                    st.markdown("<h1 style='text-align: center; padding-top: 20px;'>➡️</h1>", unsafe_allow_html=True)
                with comp_3:
                    st.markdown(f'''<div class="metric-card" style="border-left-color: #00ff87; background: rgba(0, 255, 135, 0.05);">
                        <h3 style="color: #00ff87 !important;">BUY</h3>
                        <p>{best_buy['web_name']}</p>
                        <span style="color: #adb5bd;">{best_buy['xPts']:.1f} xPts</span>
                    </div>''', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Table of options
                recs_display = significant_recs.head(8).copy()
                recs_display['Team'] = recs_display['team'].map(teams_map)
                
                st.dataframe(
                    recs_display[['web_name', 'Team', 'now_cost_m', 'xPts', 'gain']].rename(columns={
                        'web_name': 'Replacement', 'now_cost_m': 'Cost', 'xPts': 'Proj. Pts', 'gain': 'Net Gain'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Strategic verdict
                gain_val = best_buy['gain']
                if gain_val > 1.5:
                    st.success(f"🔥 **Verdict: STRONG BUY.** Transferring in {best_buy['web_name']} provides a massive +{gain_val:.1f} gain in immediate projections.")
                elif gain_val > 0.5:
                    st.info(f"⚖️ **Verdict: MARGINAL GAIN.** This move improves your squad by {gain_val:.1f} xPts. Worth it if you have no other fires to fix.")
                else:
                    st.warning("⚠️ **Verdict: LOW IMPACT.** The AI calculates that this move doesn't significantly improve your scoring potential this week.")
                
            else:
                st.error("No valid replacements found within your current budget.")

        else:
            st.error("Manager ID not found. Verify your ID in the FPL URL.")
else:
    st.markdown("""
        <div style="background: rgba(255,255,255,0.03); padding: 3rem; border-radius: 20px; text-align: center; border: 1px dashed var(--glass-border);">
            <h2 style="color: #adb5bd !important;">Ready to Optimize?</h2>
            <p style="color: #6c757d;">Enter your Team ID above to start the AI analysis.</p>
        </div>
    """, unsafe_allow_html=True)
