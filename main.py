import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from services.fpl_api import (
    get_bootstrap_static,
    get_fixtures,
    get_gameweek_info
)
from concurrent.futures import ThreadPoolExecutor

from services.ml_prediction import get_predictor
from services.match_prediction import get_match_predictor


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="FPL AI Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main {
    background-color: #0e1117;
}

.block-container {
    padding-top: 5rem;
    padding-bottom: 5rem;
}

.metric-card {
    background: #161b22;
    padding: 1.2rem;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.06);
    transition: 0.2s ease-in-out;
}

.metric-card:hover {
    border: 1px solid #00ff87;
    transform: translateY(-2px);
}

.metric-title {
    color: #9ca3af;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.metric-value {
    color: white;
    font-size: 1.6rem;
    font-weight: 700;
}

.metric-sub {
    color: #00ff87;
    font-size: 0.9rem;
    margin-top: 0.4rem;
}

.section-title {
    color: white;
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.ai-box {
    background: #161b22;
    border-radius: 16px;
    padding: 1rem;
    margin-bottom: 1rem;
    border-left: 4px solid #00ff87;
}

.small-text {
    color: #9ca3af;
    font-size: 0.9rem;
}

.status-pill {
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: rgba(0,255,135,0.15);
    color: #00ff87;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-block;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .metric-value {
        font-size: 1.2rem;
    }
    .metric-title {
        font-size: 0.75rem;
    }
    h1 {
        font-size: 1.8rem !important;
    }
    .status-pill {
        font-size: 0.7rem;
    }
    .metric-card {
        padding: 0.8rem;
    }
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# LOAD DATA
# =========================================================

with st.spinner("Loading FPL AI Engine..."):

    # Parallelize data fetching to speed up initial load
    with ThreadPoolExecutor() as executor:
        f_boot = executor.submit(get_bootstrap_static)
        f_fix = executor.submit(get_fixtures)
        f_gw = executor.submit(get_gameweek_info)
        f_pred = executor.submit(get_predictor)
        f_match = executor.submit(get_match_predictor)
        
        bootstrap = f_boot.result()
        fixtures = f_fix.result()
        gw_info = f_gw.result()
        predictor = f_pred.result()
        match_predictor = f_match.result()

# =========================================================
# VALIDATION
# =========================================================

if not bootstrap or not fixtures:
    st.error("Failed to load FPL data.")
    st.stop()

# =========================================================
# DATA PREP (CACHED)
# =========================================================

@st.cache_data(ttl=600)
def get_prepared_data(_bootstrap, _fixtures, _gw_info, _predictor):
    elements_df = pd.DataFrame(_bootstrap["elements"])
    teams_df = pd.DataFrame(_bootstrap["teams"])
    next_gw = _gw_info["next"]
    
    # Team maps
    team_map = dict(zip(teams_df["id"], teams_df["name"]))
    position_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    
    # Fixture difficulty
    team_gw_fdr = {}
    for t in _bootstrap["teams"]:
        match = next(
            (f for f in _fixtures if f["event"] == next_gw and (f["team_h"] == t["id"] or f["team_a"] == t["id"])),
            None
        )
        if match:
            is_home = match["team_h"] == t["id"]
            team_gw_fdr[t["id"]] = match["team_h_difficulty"] if is_home else match["team_a_difficulty"]
        else:
            team_gw_fdr[t["id"]] = 3

    # Numeric cleanup
    elements_df["form"] = pd.to_numeric(elements_df["form"], errors="coerce").fillna(0)
    elements_df["selected_by_percent"] = pd.to_numeric(elements_df["selected_by_percent"], errors="coerce").fillna(0)
    elements_df["cost"] = elements_df["now_cost"] / 10

    # ML Inference
    inf_df = pd.DataFrame({
        "form": elements_df["form"],
        "selected_by_percent": elements_df["selected_by_percent"],
        "now_cost": elements_df["cost"],
        "minutes_played_best": elements_df["minutes"] / 90,
        "fdr_upcoming": elements_df["team"].map(team_gw_fdr).fillna(3)
    })
    elements_df["xPts"] = _predictor.predict_points(inf_df)
    elements_df["team_name"] = elements_df["team"].map(team_map)
    elements_df["position"] = elements_df["element_type"].map(position_map)
    elements_df["efficiency"] = (elements_df["xPts"] / elements_df["cost"])
    
    # Static Picks
    top_xpts = elements_df.nlargest(1, "xPts").iloc[0]
    captain_pick = elements_df[elements_df["cost"] >= 9].nlargest(1, "xPts").iloc[0]
    differential = elements_df[elements_df["selected_by_percent"] < 10].nlargest(1, "xPts").iloc[0]
    best_fixture_team_id = min(team_gw_fdr, key=team_gw_fdr.get)
    best_fixture_team = team_map[best_fixture_team_id]
    
    return {
        "elements_df": elements_df,
        "team_gw_fdr": team_gw_fdr,
        "team_map": team_map,
        "top_xpts": top_xpts,
        "captain_pick": captain_pick,
        "differential": differential,
        "best_fixture_team": best_fixture_team,
        "next_gw": next_gw
    }

# Run preparation
ready_data = get_prepared_data(bootstrap, fixtures, gw_info, predictor)

# Extract variables
elements_df = ready_data["elements_df"]
team_gw_fdr = ready_data["team_gw_fdr"]
team_map = ready_data["team_map"]
top_xpts = ready_data["top_xpts"]
captain_pick = ready_data["captain_pick"]
differential = ready_data["differential"]
best_fixture_team = ready_data["best_fixture_team"]
next_gw = ready_data["next_gw"]

# =========================================================
# TOP BAR
# =========================================================

from datetime import datetime, timezone

# Get deadline info
events = bootstrap.get("events", [])
now_utc = datetime.now(timezone.utc)

# Find first event with deadline in the future
next_event = None
for e in events:
    deadline_dt = datetime.strptime(e['deadline_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if deadline_dt > now_utc:
        next_event = e
        break

if not next_event:
    next_event = next((e for e in events if e["is_next"]), events[-1])

# Format deadlines for display
def format_fpl_date(date_str):
    if not date_str or date_str == "TBD": return "TBD"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%a %d %b, %H:%M")
    except:
        return date_str

deadline_next_val = next_event.get("deadline_time", "")
deadline_next_str = format_fpl_date(deadline_next_val)

# Get upcoming (the one after next)
upcoming_event = next((e for e in events if e["id"] == next_event["id"] + 1), None)
deadline_upcoming_str = format_fpl_date(upcoming_event.get("deadline_time", "")) if upcoming_event else "End of Season"

top1, top2, top3 = st.columns([1,1.5,1])

with top1:
    st.markdown(
        f"""<div class="status-pill">GW {next_gw} ACTIVE</div>""",
        unsafe_allow_html=True
    )

with top2:
    # Using a more robust countdown container
    st.markdown(f"""<div class="small-text" style="color: #00ff87; font-weight: 700; margin-bottom: 5px;">
    GW {next_event['id']} DEADLINE COUNTDOWN
    </div>""", unsafe_allow_html=True)
    
    # Using st.components for reliable JS execution
    st.components.v1.html(f"""
        <div id="fpl-countdown" style="display: flex; gap: 10px; align-items: center; justify-content: flex-start; color: white; font-family: sans-serif; height: 50px;">
            <div style="text-align: center; min-width: 35px;">
                <div id="cd-days" style="font-size: 1.1rem; font-weight: 800; line-height:1;">00</div>
                <div style="font-size: 0.6rem; color: #9ca3af; text-transform: uppercase;">Days</div>
            </div>
            <div style="padding-bottom: 12px; font-weight: 800; color: white;">:</div>
            <div style="text-align: center; min-width: 35px;">
                <div id="cd-hours" style="font-size: 1.1rem; font-weight: 800; line-height:1;">00</div>
                <div style="font-size: 0.6rem; color: #9ca3af; text-transform: uppercase;">Hours</div>
            </div>
            <div style="padding-bottom: 12px; font-weight: 800; color: white;">:</div>
            <div style="text-align: center; min-width: 35px;">
                <div id="cd-mins" style="font-size: 1.1rem; font-weight: 800; line-height:1;">00</div>
                <div style="font-size: 0.6rem; color: #9ca3af; text-transform: uppercase;">Mins</div>
            </div>
            <div style="padding-bottom: 12px; font-weight: 800; color: white;">:</div>
            <div style="text-align: center; min-width: 35px;">
                <div id="cd-secs" style="font-size: 1.1rem; font-weight: 800; line-height:1;">00</div>
                <div style="font-size: 0.6rem; color: #9ca3af; text-transform: uppercase;">Secs</div>
            </div>
        </div>
        <script>
            const deadline = new Date("{deadline_next_val}").getTime();
            function update() {{
                const now = new Date().getTime();
                const t = deadline - now;
                if (t >= 0) {{
                    document.getElementById("cd-days").textContent = Math.floor(t / (1000 * 60 * 60 * 24)).toString().padStart(2, '0');
                    document.getElementById("cd-hours").textContent = Math.floor((t % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)).toString().padStart(2, '0');
                    document.getElementById("cd-mins").textContent = Math.floor((t % (1000 * 60 * 60)) / (1000 * 60)).toString().padStart(2, '0');
                    document.getElementById("cd-secs").textContent = Math.floor((t % (1000 * 60)) / 1000).toString().padStart(2, '0');
                }}
            }}
            update();
            setInterval(update, 1000);
        </script>
    """, height=60)

with top3:
    st.markdown(
        f"""
        <div class="small-text">
        UPCOMING: GW {next_event['id']+1} DEADLINE
        </div>
        <div style="color: #9ca3af; font-size: 0.85rem;">
        {deadline_upcoming_str}
        </div>
        """,
        unsafe_allow_html=True
    )

with top3:
    st.markdown(
        f"""
        <div class="small-text">
        UPCOMING: GW {next_event['id']+1 if upcoming_event else 'N/A'} DEADLINE
        </div>
        <div style="color: #9ca3af; font-size: 0.85rem;">
        {deadline_upcoming_str}
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================

st.markdown("""
<h1 style='color:white; margin-bottom:0;'>
⚽ FPL AI Dashboard
</h1>

<p style='color:#9ca3af; margin-top:0.3rem;'>
Advanced Predictions • AI Insights • Live Analytics
</p>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# KPI ROW
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">TOP PROJECTED</div>
        <div class="metric-value">{top_xpts['web_name']}</div>
        <div class="metric-sub">{top_xpts['xPts']:.1f} xPts</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">AI CAPTAIN</div>
        <div class="metric-value">{captain_pick['web_name']}</div>
        <div class="metric-sub">{captain_pick['xPts']:.1f} xPts</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">DIFFERENTIAL</div>
        <div class="metric-value">{differential['web_name']}</div>
        <div class="metric-sub">
        {differential['selected_by_percent']}% Owned
        </div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">BEST FIXTURE</div>
        <div class="metric-value">{best_fixture_team}</div>
        <div class="metric-sub">
        Fixture Difficulty: Easy
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3 = st.tabs([
    "🔥 Projections",
    "📊 Analytics",
    "🧠 AI Insights"
])

# =========================================================
# TAB 1
# =========================================================

with tab1:

    left, right = st.columns([2,1])

    # ----------------------------------------
    # Projection Chart
    # ----------------------------------------

    with left:

        st.markdown(
            "<div class='section-title'>Top Player Projections</div>",
            unsafe_allow_html=True
        )

        top_players = elements_df.nlargest(10, "xPts")

        fig = px.bar(
            top_players.sort_values("xPts"),
            x="xPts",
            y="web_name",
            orientation="h",
            text="xPts",
            color="xPts",
            color_continuous_scale="Greens"
        )

        fig.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font_color="white",
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
            height=500
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    # ----------------------------------------
    # Captain Gauge
    # ----------------------------------------

    with right:

        st.markdown(
            "<div class='section-title'>Captain Confidence</div>",
            unsafe_allow_html=True
        )

        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=87,
            title={
                'text': captain_pick["web_name"],
                'font': {'color': "white"}
            },
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#00ff87"},
                'bgcolor': "#161b22"
            }
        ))

        gauge.update_layout(
            paper_bgcolor="#161b22",
            font_color="white",
            height=350
        )

        st.plotly_chart(
            gauge,
            use_container_width=True,
            config={"displayModeBar": False}
        )

# =========================================================
# TAB 2
# =========================================================

with tab2:

    col1, col2 = st.columns([2,1])

    # ----------------------------------------
    # Efficiency Table
    # ----------------------------------------

    with col1:

        st.markdown(
            "<div class='section-title'>Efficiency Rankings</div>",
            unsafe_allow_html=True
        )

        eff_df = elements_df.nlargest(
            15,
            "efficiency"
        )[
            [
                "web_name",
                "team_name",
                "position",
                "cost",
                "xPts",
                "efficiency"
            ]
        ]

        st.dataframe(
            eff_df.rename(columns={
                "web_name": "Player",
                "team_name": "Team",
                "position": "Pos",
                "cost": "Cost",
                "xPts": "xPts",
                "efficiency": "xPts/£"
            }),
            use_container_width=True,
            hide_index=True
        )

    # ----------------------------------------
    # Team Fixture Ratings
    # ----------------------------------------

    with col2:

        st.markdown(
            "<div class='section-title'>Fixture Ratings</div>",
            unsafe_allow_html=True
        )

        fixture_df = pd.DataFrame({
            "Team": [
                team_map[t]
                for t in team_gw_fdr.keys()
            ],
            "Difficulty": [
                team_gw_fdr[t]
                for t in team_gw_fdr.keys()
            ]
        })

        fixture_df = fixture_df.sort_values(
            "Difficulty"
        )

        fig2 = px.bar(
            fixture_df.head(10),
            x="Difficulty",
            y="Team",
            orientation="h",
            color="Difficulty"
        )

        fig2.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font_color="white",
            height=500,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(
            fig2,
            use_container_width=True,
            config={"displayModeBar": False}
        )

# =========================================================
# TAB 3
# =========================================================

with tab3:

    left, right = st.columns([1.2,1])

    with left:

        st.markdown(
            "<div class='section-title'>AI Signals</div>",
            unsafe_allow_html=True
        )

        st.markdown(f"""
        <div class="ai-box">
            🔥 <b>{captain_pick['web_name']}</b>
            projected as highest captain upside this GW.
        </div>

        <div class="ai-box">
            📈 <b>{best_fixture_team}</b>
            fixtures rated easiest by prediction engine.
        </div>

        <div class="ai-box">
            🧠 <b>{differential['web_name']}</b>
            flagged as elite low-ownership differential.
        </div>

        <div class="ai-box">
            ⚠️ Premium attackers outperforming defenders this GW.
        </div>
        """, unsafe_allow_html=True)

    with right:

        st.markdown(
            "<div class='section-title'>Top Differentials</div>",
            unsafe_allow_html=True
        )

        diff_df = elements_df[
            elements_df["selected_by_percent"] < 10
        ].nlargest(10, "xPts")

        fig3 = px.scatter(
            diff_df,
            x="selected_by_percent",
            y="xPts",
            size="xPts",
            hover_name="web_name",
            color="xPts"
        )

        fig3.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font_color="white",
            height=450,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(
            fig3,
            use_container_width=True,
            config={"displayModeBar": False}
        )

# =========================================================
# FOOTER
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)

st.divider()

st.caption(
    "FPL AI Dashboard v3.0 • Powered by Official FPL API + Machine Learning"
)