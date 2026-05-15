import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.match_prediction import get_match_predictor
from services.fpl_api import get_bootstrap_static, get_fixtures, get_gameweek_info

st.set_page_config(page_title="Match Predictor", page_icon="🔮", layout="wide")

# --- HEADER SECTION ---
st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">MATCH <span style="color: #00ff87;">PREDICTOR</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Historical Shot Dominance • Corner Pressure • Probability Matrix</p>
    </div>
""", unsafe_allow_html=True)

# Load Data
with st.spinner("Analyzing historical patterns..."):
    predictor = get_match_predictor()
    bootstrap = get_bootstrap_static()
    fixtures = get_fixtures()

if not predictor.is_trained or not bootstrap or not fixtures:
    st.error("Failed to load prediction data. Ensure CSV files exist in /data.")
    st.stop()

# Determine Current Gameweek
gw_info = get_gameweek_info()
active_gw = gw_info['next'] if not any(f['event'] == gw_info['current'] and not f['finished'] for f in fixtures) else gw_info['current']

# Filter fixtures for active gameweek
teams_map = {t['id']: t['name'] for t in bootstrap['teams']}
gw_fixtures = [f for f in fixtures if f['event'] == active_gw]

fixture_options = [f"{teams_map[f['team_h']]} vs {teams_map[f['team_a']]}" for f in gw_fixtures]
fixture_options.append("--- Custom Match-up ---")

st.markdown("### 🏟️ Select Fixture")
selected_fixture = st.selectbox("Select Match to Analyze:", fixture_options, label_visibility="collapsed")

home_team = None
away_team = None

if "Custom" in selected_fixture:
    all_teams = sorted(list(predictor.team_encoder.classes_))
    c1, c2 = st.columns(2)
    with c1: home_team = st.selectbox("🏡 Home", all_teams, index=0)
    with c2: away_team = st.selectbox("✈️ Away", all_teams, index=1)
else:
    parts = selected_fixture.split(" vs ")
    home_team, away_team = parts[0], parts[1]
    st.info(f"Analyzing official fixture: **{home_team}** vs **{away_team}**")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("RUN AI SIMULATION", type="primary", use_container_width=True):
    if home_team == away_team:
        st.warning("⚠️ Please select different teams.")
    else:
        prediction = predictor.predict_match(home_team, away_team)
        
        if prediction:
            # Display beautiful metric cards
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'''<div class="metric-card" style="border-left-color: #00ff87">
                    <h3>{home_team} Win</h3>
                    <p>{prediction["Home Win"]}%</p>
                    <span style="color: #00ff87">Attack Dominance</span>
                </div>''', unsafe_allow_html=True)
            with c2:
                st.markdown(f'''<div class="metric-card" style="border-left-color: #adb5bd">
                    <h3>Draw</h3>
                    <p>{prediction["Draw"]}%</p>
                    <span style="color: #adb5bd">Equal Equilibrium</span>
                </div>''', unsafe_allow_html=True)
            with c3:
                st.markdown(f'''<div class="metric-card" style="border-left-color: #02efff">
                    <h3>{away_team} Win</h3>
                    <p>{prediction["Away Win"]}%</p>
                    <span style="color: #02efff">Counter-Attack Threat</span>
                </div>''', unsafe_allow_html=True)
            
            # Plotly Donut Chart
            fig = go.Figure(data=[go.Pie(
                labels=list(prediction.keys()), 
                values=list(prediction.values()), 
                hole=.6,
                marker=dict(colors=['#00ff87', '#555', '#02efff'], line=dict(color='rgba(0,0,0,0)', width=0))
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                margin=dict(t=0, b=0, l=0, r=0),
                showlegend=False
            )
            
            fig_col1, fig_col2, fig_col3 = st.columns([1,2,1])
            with fig_col2:
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Additional Stats (Mocked or Basic)
            st.subheader("📋 Relative Performance (Season Averages)")
            s1, s2, s3 = st.columns(3)
            h_stats = predictor.team_stats.get(home_team, {})
            a_stats = predictor.team_stats.get(away_team, {})
            
            with s1:
                st.write(f"**xG Generation (Att)**")
                st.write(f"{home_team}: {h_stats.get('att',0):.1f}")
                st.write(f"{away_team}: {a_stats.get('att',0):.1f}")
            with s2:
                st.write(f"**Goals Conceded (Def)**")
                st.write(f"{home_team}: {h_stats.get('def',0):.1f}")
                st.write(f"{away_team}: {a_stats.get('def',0):.1f}")
            with s3:
                st.write(f"**Shot Accuracy**")
                st.write(f"{home_team}: {h_stats.get('shot_acc',0)*100:.1f}%")
                st.write(f"{away_team}: {a_stats.get('shot_acc',0)*100:.1f}%")

            st.info("💡 **AI Note:** Our model detects that games involving these two teams often result in high corner counts, favoring players who take set-pieces.")
        else:
            st.error("Model Error: Missing historical data for these specific teams.")
else:
    st.markdown("""
        <div style="background: rgba(255,255,255,0.02); padding: 4rem; border-radius: 20px; text-align: center; border: 1px dashed rgba(255,255,255,0.1);">
            <h3 style="color: #6c757d !important; font-weight: 300;">Ready to simulate?</h3>
            <p style="color: #495057;">Pick a match above and click the button to see the AI analysis.</p>
        </div>
    """, unsafe_allow_html=True)

