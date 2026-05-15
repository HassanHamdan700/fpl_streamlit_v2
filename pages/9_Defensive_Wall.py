import streamlit as st
import pandas as pd
import numpy as np
import math
from services.fpl_api import get_bootstrap_static, get_fixtures, get_gameweek_info
from services.match_prediction import get_match_predictor

st.set_page_config(page_title="Defensive Wall", page_icon="🛡️", layout="wide")

# --- DATA FETCHING ---
@st.cache_data
def load_app_data():
    bootstrap = get_bootstrap_static()
    all_fixtures = get_fixtures()
    gw_info = get_gameweek_info()
    return bootstrap, all_fixtures, gw_info

bootstrap_data, all_fixtures, gw_info = load_app_data()
match_predictor = get_match_predictor()

# Target Gameweek
next_gw = gw_info['next']

# --- TEAM NAME MAPPING ---
# Maps FPL Team Names to CSV Team Names
TEAM_NAME_MAP = {
    "Man Utd": "Man United",
    "Spurs": "Tottenham",
    "Leicester City": "Leicester",
    "Ipswich Town": "Ipswich",
    "Nott'm Forest": "Nott'm Forest",
    "Sheffield Utd": "Sheffield United"
}

def normalize_name(name):
    return TEAM_NAME_MAP.get(name, name)

# --- CLEAN SHEET CALCULATION ---
def calculate_cs_odds(home_team, away_team, predictor):
    h_norm = normalize_name(home_team)
    a_norm = normalize_name(away_team)
    
    if h_norm not in predictor.team_stats or a_norm not in predictor.team_stats:
        return 25.0, 25.0 # Default fallback
    
    h_stats = predictor.team_stats[h_norm]
    a_stats = predictor.team_stats[a_norm]
    
    # Simple Poisson Model
    # Avg league goals ~1.5 per team
    avg_league_goals = 1.45
    
    # Expected goals for Home
    xG_h = (h_stats['att'] * a_stats['def']) / avg_league_goals
    # Expected goals for Away
    xG_a = (a_stats['att'] * h_stats['def']) / avg_league_goals
    
    # Prob of scoring 0 (Clean Sheet)
    # P(0) = e^-xG
    cs_prob_h = math.exp(-xG_a) * 100
    cs_prob_a = math.exp(-xG_h) * 100
    
    return round(cs_prob_h, 1), round(cs_prob_a, 1)

# --- HEADER SECTION ---
st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">DEFENSIVE <span style="color: #ff185e;">WALL</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Clean Sheet Probabilities & Match Odds for <b>Gameweek {next_gw}</b></p>
    </div>
""", unsafe_allow_html=True)

if bootstrap_data and all_fixtures:
    teams_dict = {t['id']: t['name'] for t in bootstrap_data['teams']}
    next_fixtures = [f for f in all_fixtures if f['event'] == next_gw]
    
    if not next_fixtures:
        st.warning(f"No fixtures found for Gameweek {next_gw}. It might be a blank week or data hasn't been updated yet.")
    else:
        # Top Recommendations Section
        st.markdown("### 🏆 Top Defensive Picks")
        recommendations = []
        
        for f in next_fixtures:
            h_name = teams_dict[f['team_h']]
            a_name = teams_dict[f['team_a']]
            cs_h, cs_a = calculate_cs_odds(h_name, a_name, match_predictor)
            
            recommendations.append({'Team': h_name, 'CS Prob': cs_h, 'Opponent': a_name, 'Venue': 'Home'})
            recommendations.append({'Team': a_name, 'CS Prob': cs_a, 'Opponent': h_name, 'Venue': 'Away'})
            
        rec_df = pd.DataFrame(recommendations).sort_values('CS Prob', ascending=False).head(4)
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        cols = [col_r1, col_r2, col_r3, col_r4]
        
        for i, (_, row) in enumerate(rec_df.iterrows()):
            with cols[i]:
                st.markdown(f"""<div class="metric-card" style="border-left-color: #ff185e;">
<h3 style="color: #ff185e !important;">TOP CS PICK #{i+1}</h3>
<p>{row['Team']}</p>
<span style="font-weight: 700; color: #ff185e;">{row['CS Prob']}% Probability</span><br>
<small style="color: #6c757d;">vs {row['Opponent']} ({row['Venue']})</small>
</div>""", unsafe_allow_html=True)
        
        st.divider()
        
        # All Matches Grid
        st.markdown(f"### 🏟️ Gameweek {next_gw} Match Projections")
        
        for f in next_fixtures:
            h_name = teams_dict[f['team_h']]
            a_name = teams_dict[f['team_a']]
            
            # Predict Match Results (W/D/L)
            match_odds = match_predictor.predict_match(normalize_name(h_name), normalize_name(a_name))
            # Calculate Clean Sheet Odds
            cs_h, cs_a = calculate_cs_odds(h_name, a_name, match_predictor)
            
            with st.container():
                st.markdown(f"""<div style="background: rgba(255,255,255,0.03); border: 1px solid var(--glass-border); border-radius: 16px; padding: 20px; margin-bottom: 20px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
<div style="flex: 1; text-align: center;">
<h4 style="margin:0; font-size: 1.2rem;">{h_name}</h4>
<span style="background: rgba(0,255,135,0.1); color: #00ff87; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">HOME</span>
</div>
<div style="flex: 0.5; text-align: center;">
<span style="font-family: 'Outfit', sans-serif; font-weight: 700; color: #adb5bd;">VS</span>
</div>
<div style="flex: 1; text-align: center;">
<h4 style="margin:0; font-size: 1.2rem;">{a_name}</h4>
<span style="background: rgba(2,239,255,0.1); color: #02efff; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">AWAY</span>
</div>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
<div style="background: rgba(255,24,94,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,24,94,0.1);">
<small style="color: #ff185e; font-weight: 700; text-transform: uppercase;">Clean Sheet Odds</small>
<div style="display: flex; justify-content: space-between; margin-top: 10px;">
<span>{h_name}: <b>{cs_h}%</b></span>
<span>{a_name}: <b>{cs_a}%</b></span>
</div>
<div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; margin-top: 8px; overflow: hidden; display: flex;">
<div style="width: {cs_h}%; background: #ff185e;"></div>
<div style="width: {100-cs_h-cs_a}%; background: transparent;"></div>
<div style="width: {cs_a}%; background: #ff185e; opacity: 0.6;"></div>
</div>
</div>
<div style="background: rgba(0,255,135,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(0,255,135,0.1);">
<small style="color: #00ff87; font-weight: 700; text-transform: uppercase;">Win Probabilities</small>
<div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.9rem;">
<span>Win: {match_odds['Home Win'] if match_odds else '--'}%</span>
<span>Draw: {match_odds['Draw'] if match_odds else '--'}%</span>
<span>Win: {match_odds['Away Win'] if match_odds else '--'}%</span>
</div>
<div style="height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin-top: 8px; overflow: hidden; display: flex;">
<div style="width: {match_odds['Home Win'] if match_odds else 33}%; background: #00ff87;"></div>
<div style="width: {match_odds['Draw'] if match_odds else 33}%; background: #adb5bd;"></div>
<div style="width: {match_odds['Away Win'] if match_odds else 33}%; background: #02efff;"></div>
</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

        st.info("💡 **AI Methodology:** Clean sheet probabilities are derived from a Poisson distribution model comparing the defensive strength of the team against the attacking efficiency of their opponent. Match results are predicted using a Gradient Boosting model trained on 5 years of historical Premier League data.")

else:
    st.error("Error loading FPL match data.")
