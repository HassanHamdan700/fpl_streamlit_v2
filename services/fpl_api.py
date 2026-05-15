import requests
import streamlit as st

BASE_URL = "https://fantasy.premierleague.com/api"

@st.cache_data(ttl=3600)
def get_bootstrap_static():
    """Fetches general FPL data (players, teams, events)."""
    try:
        response = requests.get(f"{BASE_URL}/bootstrap-static/?utm_source=chatgpt.com", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching bootstrap data: {e}")
        return None

@st.cache_data(ttl=300)
def get_manager_team(team_id: int):
    """Fetches data for a specific FPL manager."""
    try:
        response = requests.get(f"{BASE_URL}/entry/{team_id}/?utm_source=chatgpt.com", timeout=10)
        if response.status_code == 404:
            return {"error": "Team not found"}
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching team data: {e}")
        return None

@st.cache_data(ttl=300)
def get_manager_picks(team_id: int, gameweek: int):
    """Fetches the players selected by a manager for a given gameweek."""
    try:
        response = requests.get(f"{BASE_URL}/entry/{team_id}/event/{gameweek}/picks/?utm_source=chatgpt.com", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching gameweek picks: {e}")
        return None

@st.cache_data(ttl=3600)
def get_fixtures():
    """Fetches all fixtures for the season."""
    try:
        response = requests.get(f"{BASE_URL}/fixtures/?utm_source=chatgpt.com", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching fixtures: {e}")
        return None
@st.cache_data(ttl=60)
def get_live_gameweek_data(gameweek: int):
    """Fetches live points for all players for a specific gameweek."""
    try:
        response = requests.get(f"{BASE_URL}/event/{gameweek}/live/?utm_source=chatgpt.com", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching live gameweek data: {e}")
        return None
@st.cache_data(ttl=3600)
def get_gameweek_info():
    """Identifies the current and next relevant gameweeks."""
    data = get_bootstrap_static()
    if not data:
        return {"current": 1, "next": 2, "finished": False}
    
    events = data.get('events', [])
    current_gw = next((e['id'] for e in events if e.get('is_current')), None)
    next_gw = next((e['id'] for e in events if e.get('is_next')), None)
    
    # If pre-season, current_gw remains None
    return {
        "current": current_gw or 1,
        "next": next_gw or (current_gw + 1 if current_gw else 1),
        "is_active": any(e.get('is_current') for e in events)
    }
