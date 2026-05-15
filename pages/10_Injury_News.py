import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static, get_gameweek_info

st.set_page_config(page_title="Injury & News Room", page_icon="🏥", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def load_injury_data():
    bootstrap = get_bootstrap_static()
    gw_info = get_gameweek_info()
    return bootstrap, gw_info

bootstrap_data, gw_info = load_injury_data()

# --- HEADER SECTION ---
st.markdown(f"""<div style="text-align: center; padding: 1rem 0 2rem 0;">
<h1 style="font-size: 3.5rem; margin-bottom: 0;">NEWS <span style="color: #ff185e;">CENTRAL</span></h1>
<p style="font-size: 1.2rem; color: #adb5bd;">Injury Tracking • Suspensions • Press Conference Updates</p>
</div>""", unsafe_allow_html=True)

if bootstrap_data:
    teams = {t['id']: t['name'] for t in bootstrap_data['teams']}
    elements = bootstrap_data['elements']
    
    # Filter for Top Players only (High ownership or Premium price)
    # Status: 'a'=Available, 'i'=Injured, 's'=Suspended, 'u'=Unavailable, 'd'=Doubtful
    news_players = [
        p for p in elements 
        if p['status'] != 'a' and (float(p['selected_by_percent']) > 10.0 or p['now_cost'] >= 70)
    ]
    
    # Group by Team
    team_news = {}
    for p in news_players:
        t_name = teams[p['team']]
        if t_name not in team_news:
            team_news[t_name] = []
        team_news[t_name].append(p)

    # UI Layout: Two columns
    col_news, col_alerts = st.columns([2, 1])

    with col_news:
        st.markdown("### 🏥 The Treatment Room")
        
        search_team = st.multiselect("Filter by Team:", sorted(teams.values()), placeholder="Search team news...")
        
        display_teams = search_team if search_team else sorted(team_news.keys())
        
        for t_name in display_teams:
            if t_name in team_news:
                with st.expander(f"📌 {t_name}", expanded=True):
                    for p in team_news[t_name]:
                        # Status Color Coding
                        status_color = "#ff185e" # Default red for injured/unavailable
                        status_label = "Unavailable"
                        
                        if p['status'] == 'd':
                            status_color = "#f39c12" # Orange for doubtful
                            status_label = "Doubtful"
                        elif p['status'] == 's':
                            status_color = "#7632ff" # Purple for suspended
                            status_label = "Suspended"
                            
                        chance = p.get('chance_of_playing_next_round')
                        chance_str = f"{chance}%" if chance is not None else "Unknown"
                        
                        st.markdown(f"""<div style="background: rgba(255,255,255,0.02); padding: 12px; border-radius: 10px; border-left: 4px solid {status_color}; margin-bottom: 10px;">
<div style="display: flex; justify-content: space-between; align-items: start;">
<div>
<b style="font-size: 1.1rem; color: white;">{p['web_name']}</b> 
<span style="background: {status_color}22; color: {status_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-left: 8px;">{status_label}</span>
<p style="color: #adb5bd; margin-top: 5px; font-size: 0.95rem;">{p['news']}</p>
</div>
<div style="text-align: right;">
<small style="color: #6c757d;">Playing Chance</small><br>
<b style="color: {status_color}; font-size: 1.1rem;">{chance_str}</b>
</div>
</div>
</div>""", unsafe_allow_html=True)

    with col_alerts:
        st.markdown("### 📣 Press & Social Feed")
        
        st.info("🕒 **Note:** Live Twitter/X and Web Scraping integrations are scheduled for the next update. Below are recent trends.")
        
        # Simulated Press Conference News
        mock_news = [
            {"title": "Pep Guardiola on Rotation", "desc": "Hinted at heavy rotation due to Champions League clash.", "tag": "Manager Quote"},
            {"title": "Arteta on Saka Fitness", "desc": "Late fitness test expected for the winger.", "tag": "Highly Critical"},
            {"title": "Klopp Replacement News", "desc": "Internal reports suggest young assets might start.", "tag": "Differential Hint"}
        ]
        
        for news in mock_news:
            st.markdown(f"""<div class="metric-card" style="border-left-color: #02efff; padding: 1rem;">
<small style="color: #02efff; font-weight: 700;">{news['tag']}</small>
<h4 style="margin: 5px 0; color: white;">{news['title']}</h4>
<p style="color: #adb5bd; font-size: 0.9rem; margin: 0;">{news['desc']}</p>
</div>""", unsafe_allow_html=True)

        st.markdown("### 📊 Global Injury Stats")
        total_out = len(news_players)
        doubtful = len([p for p in news_players if p['status'] == 'd'])
        suspended = len([p for p in news_players if p['status'] == 's'])
        
        st.markdown(f"""<div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 16px; border: 1px solid var(--glass-border);">
<p style="margin: 5px 0;">Total Flagged: <b style="color: white;">{total_out}</b></p>
<p style="margin: 5px 0;">Doubtful: <b style="color: #f39c12;">{doubtful}</b></p>
<p style="margin: 5px 0;">Suspended: <b style="color: #7632ff;">{suspended}</b></p>
</div>""", unsafe_allow_html=True)

else:
    st.error("Error loading news feed data.")
