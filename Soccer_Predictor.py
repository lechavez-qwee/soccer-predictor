import requests
from functools import lru_cache
import concurrent.futures
import os
from dotenv import load_dotenv

load_dotenv()

# --- MISTRAL API ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-tiny"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# --- API-FOOTBALL ---
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_URL = "https://v3.football.api-sports.io"
API_FOOTBALL_HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

# --- Validate keys on startup ---
if not MISTRAL_API_KEY or not API_FOOTBALL_KEY:
    raise EnvironmentError (
        "Missing API keys. Please set MISTRAL_API_KEY and API_FOOTBALL_KEY "
        " in your environment or in a .env file."
    )

TEAM_ALIASES = {
    "Man Utd": "Manchester United",
    "Man City": "Manchester City",
    "Spurs": "Tottenham Hotspur",
    "Arsenal": "Arsenal",
    "Chelsea": "Chelsea",
    "Liverpool": "Liverpool",
    "Newcastle": "Newcastle United",
    "West Ham": "West Ham United",
    "Leicester": "Leicester City",
    "Brighton": "Brighton & Hove Albion",
    "Wolves": "Wolverhampton Wanderers",
    "Villa": "Aston Villa",
    "Palace": "Crystal Palace",
    "Brentford": "Brentford",
    "Fulham": "Fulham",
    "Luton": "Luton Town",
    "Sheffield Utd": "Sheffield United",
    "Burnley": "Burnley",
    "Nott'm Forest": "Nottingham Forest",
    "Bournemouth": "AFC Bournemouth",
    "Everton": "Everton"
}

# --- Cached API Calls ---
@lru_cache(maxsize=32)
def get_team_id(team_name, season=2024, league_id=39):
    official_name = TEAM_ALIASES.get(team_name, team_name)
    params = {"league": league_id, "season": season}
    try:
        response = requests.get(
            f"{API_FOOTBALL_URL}/teams",
            headers=API_FOOTBALL_HEADERS,
            params=params
        )
        if response.status_code == 200:
            teams = response.json().get("response", [])
            for team in teams:
                if team["team"]["name"].lower() == official_name.lower():
                    return team["team"]["id"]
    except Exception as e:
        print(f"Error fetching team ID: {e}")
    return None

def get_team_form(team_id, season=2024, league_id=39):
    try:
        params = {"team": team_id, "season": season, "league": league_id}
        response = requests.get(
            f"{API_FOOTBALL_URL}/teams/matches",
            headers=API_FOOTBALL_HEADERS,
            params=params
        )
        if response.status_code == 200:
            matches = response.json().get("response", [])
            if not matches:
                return "No form data available (no matches found)."
            last_matches = matches[-5:] if len(matches) > 5 else matches  # Limit to last 5 matches
            form = []
            for match in last_matches:
                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                score = f"{match['goals']['home']}-{match['goals']['away']}"
                form.append(f"{home} {score} {away}")
            return ", ".join(form)
        elif response.status_code == 429:
            return "Data rate limit exceeded."
    except Exception as e:
        print(f"Error fetching team form: {e}")
    return "No form data available."

def get_head_to_head(team1_id, team2_id, season=2024, league_id=39):
    try:
        params = {"h2h": f"{team1_id}-{team2_id}", "season": season, "league": league_id}
        response = requests.get(
            f"{API_FOOTBALL_URL}/fixtures/headtohead",
            headers=API_FOOTBALL_HEADERS,
            params=params
        )
        if response.status_code == 200:
            matches = response.json().get("response", [])
            h2h = []
            for match in matches:
                home = match["teams"]["home"]["name"]
                away = match["teams"]["away"]["name"]
                score = f"{match['goals']['home']}-{match['goals']['away']}"
                h2h.append(f"{home} {score} {away}")
            return ", ".join(h2h)
        elif response.status_code == 404:
            return "No head-to-head data found."
    except Exception as e:
        print(f"Error fetching head-to-head: {e}")
    return "No head-to-head data available."

def get_team_squad(team_id, season=2024, league_id=39):
    try:
        params = {"team": team_id, "season": season, "league": league_id}
        response = requests.get(
            f"{API_FOOTBALL_URL}/players",
            headers=API_FOOTBALL_HEADERS,
            params=params
        )
        if response.status_code == 200:
            players = response.json().get("response", [])
            if not players:
                return "No squad data available."
            squad = []
            for player in players:
                if player.get('statistics'):  # Check if 'statistics' exists
                    position = player['statistics'][0]['games']['position']
                    squad.append(f"{player['player']['name']} ({position})")
            return ", ".join(squad[:10])  # Return first 10 players
    except Exception as e:
        print(f"Error fetching team squad: {e}")
    return "No squad data available."

def get_league_standings(league_id=39, season=2024):
    try:
        params = {"league": league_id, "season": season}
        response = requests.get(
            f"{API_FOOTBALL_URL}/standings",
            headers=API_FOOTBALL_HEADERS,
            params=params
        )
        if response.status_code == 200:
            data = response.json()
            if not data.get("response"):
                return "No standings data available."
            standings = data["response"][0]["league"]["standings"][0]
            table = []
            for team in standings:
                table.append(f"{team['rank']}. {team['team']['name']} ({team['points']} pts)")
            return ", ".join(table[:5])  # Return top 5 teams
    except Exception as e:
        print(f"Error fetching standings: {e}")
    return "No standings data available."

def fetch_all_data(team1_id, team2_id, season=2024, league_id=39):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_form1 = executor.submit(get_team_form, team1_id, season, league_id)
        future_form2 = executor.submit(get_team_form, team2_id, season, league_id)
        future_squad1 = executor.submit(get_team_squad, team1_id, season, league_id)
        future_squad2 = executor.submit(get_team_squad, team2_id, season, league_id)
        future_h2h = executor.submit(get_head_to_head, team1_id, team2_id, season, league_id)
        future_standings = executor.submit(get_league_standings, league_id, season)

        team1_form = future_form1.result()
        team2_form = future_form2.result()
        team1_squad = future_squad1.result()
        team2_squad = future_squad2.result()
        h2h = future_h2h.result()
        standings = future_standings.result()

    return {
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_squad": team1_squad,
        "team2_squad": team2_squad,
        "h2h": h2h,
        "standings": standings
    }

def get_match_prediction(team1, team2, season=2024, league_id=39):
    team1_id = get_team_id(team1, season=season, league_id=league_id)
    team2_id = get_team_id(team2, season=season, league_id=league_id)

    if not team1_id or not team2_id:
        return "No team data available."

    print("Fetching live data...")
    data = fetch_all_data(team1_id, team2_id, season=season, league_id=league_id)

    system_prompt = f"""
    You are an expert soccer analyst. For the given match between {team1} (home) and {team2}
    (away), use the following live data:

    - Current Premier League standings: {data['standings']}
    - {team1} recent form: {data['team1_form']}
    - {team2} recent form: {data['team2_form']}
    - {team1} squad: {data['team1_squad']}
    - {team2} squad: {data['team2_squad']}
    - Head-to-head: {data['h2h']}

    Provide:
    1. Predicted score
    2. Reasons for the prediction, including recent form, head-to-head history, and key players.
    3. Player performance insights.
    4. Drama/stakes: Context of the match.
    5. Home/away advantage.
    Be concise but insightful. Use soccer terminology and slang.
    """.strip()

    user_prompt = f"Predict the outcome of {team1} vs {team2}".strip()

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    try:
        response = requests.post(MISTRAL_URL, headers=MISTRAL_HEADERS, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error fetching prediction: {e}"

def main():
    print("Soccer Match Predictor \nType 'exit' to quit")
    league_id = 39
    season = 2024
    while True:
        team1 = input("\nEnter home team: ")
        if team1.lower() == "exit":
            break
        team2 = input("Enter away team: ")
        if team2.lower() == "exit":
            break

        prediction = get_match_prediction(team1, team2, season=season, league_id=league_id)
        print("\n---")
        print(f"Prediction for {team1} vs {team2}: \n")
        print(prediction)
        print("---")

if __name__ == "__main__":
    main()
