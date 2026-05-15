import streamlit as st
import pandas as pd
from services.fpl_api import get_bootstrap_static, get_fixtures

# Support Data
with st.spinner("Loading schedules..."):
    bootstrap = get_bootstrap_static()
    fixtures = get_fixtures()

if not bootstrap or not fixtures:
    st.error("Could not fetch FPL data.")
    st.stop()

teams = {t['id']: t['name'] for t in bootstrap['teams']}
team_short = {t['id']: t['short_name'] for t in bootstrap['teams']}
current_gw = next((e['id'] for e in bootstrap['events'] if e['is_current']), 1)

# --- HEADER SECTION ---
st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">FIXTURE <span style="color: #00ff87;">ANALYZER</span></h1>
        <p style="font-size: 1.2rem; color: #adb5bd;">FDR Heatmap • Upcoming Schedule • Strategic Rotation</p>
    </div>
""", unsafe_allow_html=True)

# Options
col_opt1, col_opt2 = st.columns([2, 1])
with col_opt1:
    lookahead = st.select_slider("Analysis Horizon (Gameweeks):", options=[3, 4, 5, 6, 8, 10, 12], value=6)
with col_opt2:
    st.write("<br>", unsafe_allow_html=True)
    sort_method = st.selectbox("Sort Teams By:", ["FDR (Easiest First)", "Name (A-Z)"])

end_gw = current_gw + lookahead

# Prepare Grid
data_grid = []
for team_id, team_name in teams.items():
    total_diff = 0
    row = {"Team": team_name}
    for gw in range(current_gw, end_gw + 1):
        match = next((f for f in fixtures if f['event'] == gw and (f['team_h'] == team_id or f['team_a'] == team_id)), None)
        if match:
            is_home = match['team_h'] == team_id
            opponent_id = match['team_a'] if is_home else match['team_h']
            diff = match['team_h_difficulty'] if is_home else match['team_a_difficulty']
            loc = "H" if is_home else "A"
            row[f"GW{gw}"] = f"{team_short[opponent_id]} ({loc})|{diff}"
            total_diff += diff
        else:
            row[f"GW{gw}"] = "BLANK|5" # Blank is difficulty 5 usually
            total_diff += 5
    row["Aggregate FDR"] = total_diff
    data_grid.append(row)

df_fdr = pd.DataFrame(data_grid)
if sort_method == "FDR (Easiest First)":
    df_fdr = df_fdr.sort_values(by="Aggregate FDR")
else:
    df_fdr = df_fdr.sort_values(by="Team")

df_fdr = df_fdr.set_index("Team")

# Styling Function
def color_fdr(val):
    if "|" not in str(val): return ""
    diff = int(val.split("|")[1])
    # Colors matching FPL theme but more vibrant
    if diff <= 2: return "background-color: rgba(0, 255, 135, 0.4); color: white; font-weight: bold;"
    if diff == 3: return "background-color: rgba(255, 255, 255, 0.05); color: #adb5bd;"
    if diff == 4: return "background-color: rgba(255, 24, 94, 0.4); color: white; font-weight: bold;"
    return "background-color: rgba(55, 0, 60, 0.6); color: #ff185e; font-weight: 800;"

def format_text(val):
    if "|" not in str(val): return val
    return val.split("|")[0]

# Render
st.markdown(f"### 🗓️ Upcoming Schedule (Next {lookahead} GWs)")

# Apply styling
styled_df = df_fdr.style.applymap(color_fdr).format(format_text)
st.dataframe(styled_df, use_container_width=True, height=750)

st.divider()

# Summary Insights
st.subheader("💡 Strategic Recommendations")

# Calculate easiest run
team_total_diff = {row['Team']: row['Aggregate FDR'] for index, row in df_fdr.reset_index().iterrows()}
easiest = sorted(team_total_diff.items(), key=lambda x: x[1])[:4]
hardest = sorted(team_total_diff.items(), key=lambda x: x[1], reverse=True)[:4]

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.markdown("""
        <div style="background: rgba(0,255,135,0.05); padding: 20px; border-radius: 12px; border-left: 5px solid #00ff87;">
            <h4 style="color: #00ff87; margin: 0;">🎯 Target for Investment</h4>
            <div style="margin-top: 10px;">
    """, unsafe_allow_html=True)
    for t, s in easiest:
        avg = s / (lookahead + 1)
        st.markdown(f"**{t}** (Avg Diff: {avg:.1f})")
    st.markdown("</div></div>", unsafe_allow_html=True)

with col_s2:
    st.markdown("""
        <div style="background: rgba(255,24,94,0.05); padding: 20px; border-radius: 12px; border-left: 5px solid #ff185e;">
            <h4 style="color: #ff185e; margin: 0;">⚠️ Avoid / Sell Warning</h4>
            <div style="margin-top: 10px;">
    """, unsafe_allow_html=True)
    for t, s in hardest:
        avg = s / (lookahead + 1)
        st.markdown(f"**{t}** (Avg Diff: {avg:.1f})")
    st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.info("💡 **Pro Tip:** Look for teams with green fixtures for the next 4 gameweeks but avoid those with a 'BLANK' (no game) scheduled as it leads to a 0-point score for all their players.")
