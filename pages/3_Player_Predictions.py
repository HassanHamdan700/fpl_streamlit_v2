import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static, get_fixtures, get_gameweek_info
from services.ml_prediction import get_predictor

# --- DATA FETCHING ---
with st.spinner("Analyzing player trajectory and upcoming FDR..."):
    bootstrap_data = get_bootstrap_static()
    predictor = get_predictor()
    fixtures = get_fixtures()
    gw_info = get_gameweek_info()
    
    # Target Gameweek (GW 37 as per user request)
    next_gw = gw_info['next']
    deadline = "Fri 15 May, 20:30" # Specific user requirement

# --- HEADER SECTION ---
st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">PLAYER <span style="color: #00ff87;">PREDICTIONS</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Targeting <b>Gameweek {next_gw}</b> • Deadline: {deadline}</p>
    </div>
""", unsafe_allow_html=True)

if bootstrap_data and fixtures:
    elements = bootstrap_data.get('elements', [])
    teams = {t['id']: t['name'] for t in bootstrap_data.get('teams', [])}
    
    # Helper: Get Upcoming FDR for each team for the target GW
    team_gw_fdr = {}
    for t in bootstrap_data['teams']:
        match = next((f for f in fixtures if f['event'] == next_gw and (f['team_h'] == t['id'] or f['team_a'] == t['id'])), None)
        if match:
            is_home = match['team_h'] == t['id']
            team_gw_fdr[t['id']] = match['team_h_difficulty'] if is_home else match['team_a_difficulty']
        else:
            team_gw_fdr[t['id']] = 3 # Average for blank
    
    df = pd.DataFrame(elements)
    
    if not df.empty:
        df['form_numeric'] = pd.to_numeric(df['form'], errors='coerce').fillna(0)
        df['selected_by_percent_numeric'] = pd.to_numeric(df['selected_by_percent'], errors='coerce').fillna(0)
        df['now_cost_numeric'] = df['now_cost'] / 10.0
        
        # Prepare inference data with ACTUAL FDR for GW 37
        inference_df = pd.DataFrame({
            'form': df['form_numeric'],
            'selected_by_percent': df['selected_by_percent_numeric'],
            'now_cost': df['now_cost_numeric'],
            'minutes_played_best': df['minutes'] / 90.0,
            'fdr_upcoming': df['team'].map(team_gw_fdr).fillna(3)
        })
        
        predictions = predictor.predict_points(inference_df)
        df['Predicted Points'] = [round(p, 1) for p in predictions]
        
        # Prepare display dataframe
        display_df = df[['web_name', 'team', 'element_type', 'now_cost_numeric', 'form_numeric', 'Predicted Points']].copy()
        display_df['team'] = display_df['team'].map(teams)
        pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        display_df['element_type'] = display_df['element_type'].map(pos_map)
        
        display_df = display_df.rename(columns={
            'web_name': 'Player',
            'team': 'Team',
            'element_type': 'Pos',
            'now_cost_numeric': 'Cost',
            'form_numeric': 'Form'
        })
        
        display_df = display_df.sort_values(by='Predicted Points', ascending=False)

        # Filters Section
        st.markdown("### 🔍 Smart Filters")
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            pos_filter = st.multiselect("Filter by Position:", ['GK', 'DEF', 'MID', 'FWD'], default=['GK', 'DEF', 'MID', 'FWD'])
        with col_f2:
            max_cost = st.slider("Max Budget (£m):", 4.0, 15.0, 15.0)
        with col_f3:
            search_query = st.text_input("Search Player:", placeholder="Web Name...")

        # Apply Filters
        filtered_df = display_df[
            (display_df['Pos'].isin(pos_filter)) &
            (display_df['Cost'] <= max_cost)
        ]
        
        if search_query:
            filtered_df = filtered_df[filtered_df['Player'].str.contains(search_query, case=False)]

        st.markdown(f"### 📊 Predictions Matrix ({len(filtered_df)} matches)")
        
        # Highlight Top 3
        if not filtered_df.empty:
            top_3 = filtered_df.head(3)
            col_t1, col_t2, col_t3 = st.columns(3)
            colors = ["#00ff87", "#02efff", "#7632ff"]
            for i, (_, row) in enumerate(top_3.iterrows()):
                cols = [col_t1, col_t2, col_t3]
                with cols[i]:
                    st.markdown(f"""
                        <div class="metric-card" style="border-left-color: {colors[i]};">
                            <h3 style="color: {colors[i]} !important;">RANK #{i+1}</h3>
                            <p>{row['Player']}</p>
                            <span style="font-weight: 700;">{row['Predicted Points']} xPts</span>
                        </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Show main data
        st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=600)
        
        st.info("💡 **AI Insight:** Predictions take into account both short-term form and long-term efficiency averages. The 'xPts' is a projection for the single next gameweek.")
else:
    st.error("Error loading FPL data.")

