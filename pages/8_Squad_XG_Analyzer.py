import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static, get_fixtures, get_gameweek_info, get_manager_picks
from services.ml_prediction import get_predictor

st.set_page_config(page_title="Squad xG Analyzer", page_icon="⚡", layout="wide")

# Initialize session state for the squad
if 'my_squad' not in st.session_state:
    st.session_state.my_squad = []

# --- DATA FETCHING ---
@st.cache_data
def load_base_data():
    bootstrap = get_bootstrap_static()
    fixtures = get_fixtures()
    gw_info = get_gameweek_info()
    return bootstrap, fixtures, gw_info

bootstrap_data, all_fixtures, gw_info = load_base_data()
predictor = get_predictor()

# Target Gameweek
next_gw = gw_info['next']

# --- HELPER FUNCTIONS ---
def get_player_prediction(player_id, df_elements, team_gw_fdr):
    player_data = df_elements[df_elements['id'] == player_id].iloc[0]
    
    # Prepare inference data
    inference_df = pd.DataFrame({
        'form': [pd.to_numeric(player_data['form'], errors='coerce')],
        'selected_by_percent': [pd.to_numeric(player_data['selected_by_percent'], errors='coerce')],
        'now_cost': [player_data['now_cost'] / 10.0],
        'minutes_played_best': [player_data['minutes'] / 90.0],
        'fdr_upcoming': [team_gw_fdr.get(player_data['team'], 3)]
    })
    
    points = predictor.predict_points(inference_df)[0]
    return round(points, 2)

# --- HEADER SECTION ---
st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">SQUAD <span style="color: #02efff;">ANALYZER</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Build your team and project <b>Gameweek {next_gw}</b> Expected Points</p>
    </div>
""", unsafe_allow_html=True)

if bootstrap_data:
    elements = bootstrap_data.get('elements', [])
    teams = {t['id']: t['name'] for t in bootstrap_data.get('teams', [])}
    df_elements = pd.DataFrame(elements)
    
    # Calculate FDR for next GW
    team_gw_fdr = {}
    for t in bootstrap_data['teams']:
        match = next((f for f in all_fixtures if f['event'] == next_gw and (f['team_h'] == t['id'] or f['team_a'] == t['id'])), None)
        if match:
            is_home = match['team_h'] == t['id']
            team_gw_fdr[t['id']] = match['team_h_difficulty'] if is_home else match['team_a_difficulty']
        else:
            team_gw_fdr[t['id']] = 3

    # --- SQUAD MANAGEMENT ---
    col_input1, col_input2 = st.columns([2, 1])
    
    with col_input1:
        st.subheader("🛠️ Build Your Squad")
        player_names = df_elements['web_name'].tolist()
        selected_player_name = st.selectbox("Search & Add Player:", [""] + player_names, index=0, key="player_search")
        
        if selected_player_name:
            player_info = df_elements[df_elements['web_name'] == selected_player_name].iloc[0]
            if player_info['id'] not in st.session_state.my_squad:
                if len(st.session_state.my_squad) < 11:
                    st.session_state.my_squad.append(player_info['id'])
                    st.toast(f"Added {selected_player_name} to squad!")
                else:
                    st.warning("Squad is full (11 players max).")
            else:
                st.info(f"{selected_player_name} is already in your squad.")

    with col_input2:
        st.subheader("📥 Import from FPL")
        import_id = st.text_input("Enter Team ID:", placeholder="e.g. 12345", key="import_id")
        if st.button("Sync My Team", use_container_width=True):
            if import_id.isdigit():
                picks = get_manager_picks(import_id, gw_info['current'])
                if picks and 'picks' in picks:
                    # Only take the starting 11 (positions 1-11)
                    st.session_state.my_squad = [p['element'] for p in picks['picks'] if p['position'] <= 11]
                    st.success("Successfully imported starting XI!")
                    st.rerun()
                else:
                    st.error("Could not find team or gameweek data.")
            else:
                st.error("Please enter a valid numeric ID.")

    st.divider()

    # --- SQUAD DISPLAY ---
    if st.session_state.my_squad:
        squad_data = []
        total_xpts = 0
        total_cost = 0
        
        for p_id in st.session_state.my_squad:
            p_info = df_elements[df_elements['id'] == p_id].iloc[0]
            xpts = get_player_prediction(p_id, df_elements, team_gw_fdr)
            squad_data.append({
                'id': p_id,
                'Name': p_info['web_name'],
                'Team': teams[p_info['team']],
                'Pos': {1:'GK', 2:'DEF', 3:'MID', 4:'FWD'}[p_info['element_type']],
                'Cost': p_info['now_cost'] / 10.0,
                'xPts': xpts
            })
            total_xpts += xpts
            total_cost += p_info['now_cost'] / 10.0
            
        squad_df = pd.DataFrame(squad_data)
        
        # Dashboard Summary
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(f'''<div class="metric-card" style="border-left-color: #00ff87">
                <h3>Total Squad xPts</h3>
                <p>{total_xpts:.2f}</p>
                <span style="color: #00ff87; font-weight: 700;">Projected GW{next_gw}</span>
            </div>''', unsafe_allow_html=True)
        with col_m2:
            st.markdown(f'''<div class="metric-card" style="border-left-color: #02efff">
                <h3>Avg. xPts / Player</h3>
                <p>{total_xpts/len(squad_data):.2f}</p>
                <span style="color: #02efff; font-weight: 700;">Efficiency Index</span>
            </div>''', unsafe_allow_html=True)
        with col_m3:
            st.markdown(f'''<div class="metric-card" style="border-left-color: #ff185e">
                <h3>Squad Value</h3>
                <p>£{total_cost:.1f}m</p>
                <span style="color: #ff185e; font-weight: 700;">{len(squad_data)} / 11 Players</span>
            </div>''', unsafe_allow_html=True)

        st.markdown("### 🏟️ Squad Breakdown")
        
        # Grouping by position for display
        pos_order = {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
        squad_df['pos_sort'] = squad_df['Pos'].map(pos_order)
        squad_df = squad_df.sort_values('pos_sort')
        
        cols = st.columns(4)
        positions = ['GK', 'DEF', 'MID', 'FWD']
        
        for i, pos in enumerate(positions):
            with cols[i]:
                st.markdown(f"#### {pos}")
                pos_players = squad_df[squad_df['Pos'] == pos]
                for _, row in pos_players.iterrows():
                    with st.container():
                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #00ff87;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <b style="font-size: 1rem;">{row['Name']}</b><br>
                                        <small style="color: #adb5bd;">{row['Team']} • £{row['Cost']}m</small>
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="color: #00ff87; font-weight: 800; font-size: 1.1rem;">{row['xPts']}</span><br>
                                        <small style="color: #6c757d;">xPts</small>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"🗑️", key=f"remove_{row['id']}", help=f"Remove {row['Name']}"):
                            st.session_state.my_squad.remove(row['id'])
                            st.rerun()
                            
        if st.button("Reset Squad", type="secondary"):
            st.session_state.my_squad = []
            st.rerun()

    else:
        st.markdown("""
            <div style="background: rgba(255,255,255,0.03); padding: 5rem; border-radius: 24px; text-align: center; border: 1px dashed var(--glass-border);">
                <h2 style="color: #adb5bd !important; font-weight: 300;">Your Squad is Empty</h2>
                <p style="color: #6c757d; font-size: 1.1rem;">Add players manually or import your FPL team to see xG pointed projections.</p>
            </div>
        """, unsafe_allow_html=True)

else:
    st.error("Could not connect to FPL Servers. Please check your internet connection.")
