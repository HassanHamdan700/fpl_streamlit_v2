import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static

st.set_page_config(page_title="FPL Trends", page_icon="📈", layout="wide")

# --- HEADER SECTION ---
st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">GLOBAL <span style="color: #00ff87;">TRENDS</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">Market Sentiment • Top Scorers • Community Consensus</p>
    </div>
""", unsafe_allow_html=True)

# Fetch central data
with st.spinner("Analyzing market momentum..."):
    bootstrap_data = get_bootstrap_static()

if bootstrap_data:
    events = bootstrap_data.get('events', [])
    current_event = next((e for e in events if e.get('is_current')), None) or events[0]
    next_event = next((e for e in events if e.get('is_next')), None)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f'''<div class="metric-card">
            <h3>Current Window</h3>
            <p>GW {current_event.get('id')}</p>
            <span style="color: #00ff87">Active Phase</span>
        </div>''', unsafe_allow_html=True)
    
    with col2:
        avg = current_event.get('average_entry_score', 0)
        st.markdown(f'''<div class="metric-card" style="border-left-color: #02efff">
            <h3>Global Average</h3>
            <p>{avg} pts</p>
            <span style="color: #02efff">Community Baseline</span>
        </div>''', unsafe_allow_html=True)
        
    with col3:
        next_id = next_event.get('id') if next_event else "Final"
        # Format deadline time
        deadline_str = "TBD"
        if next_event:
            from datetime import datetime
            try:
                dt = datetime.strptime(next_event['deadline_time'], "%Y-%m-%dT%H:%M:%SZ")
                deadline_str = dt.strftime("%a %d %b, %H:%M")
            except:
                deadline_str = next_event['deadline_time']
                
        st.markdown(f'''<div class="metric-card" style="border-left-color: #ff185e">
            <h3>Next Deadline</h3>
            <p>GW {next_id}</p>
            <span style="color: #ff185e; font-weight: 700;">{deadline_str}</span>
        </div>''', unsafe_allow_html=True)

    st.divider()
    
    st.subheader("🔥 Top Market Performers (Total Points)")
    elements = bootstrap_data.get('elements', [])
    df = pd.DataFrame(elements)
    
    if not df.empty:
        # Get highest point scorers
        top_players = df.nlargest(20, 'total_points')[['web_name', 'total_points', 'now_cost', 'selected_by_percent', 'form']]
        top_players['now_cost'] = top_players['now_cost'] / 10.0
        
        st.dataframe(
            top_players.rename(columns={
                'web_name': 'Player',
                'total_points': 'Total Pts',
                'now_cost': 'Cost (£m)',
                'selected_by_percent': 'TSB (%)',
                'form': 'Current Form'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.info("💡 **Market Sentiment:** High 'TSB' (The Scouting Box) percentage indicates a 'template' player. For rapid rank gains, look for players with high Form but low TSB.")
else:
    st.error("Failed to load FPL market data.")
