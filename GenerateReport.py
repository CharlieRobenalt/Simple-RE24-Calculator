import pandas as pd
import csv
from pybaseball import statcast, playerid_reverse_lookup

# Used to calculate Expected Runs and ERC (Expected Runs Created)
class ExpectedRuns:
    # Run Matrix Runners: {outs: expected runs}
    RunMatrix = {
        "___" : { 0 : 0.48, 1 : 0.25, 2 : 0.10, 3 : 0.00 },
        "1__" : { 0 : 0.87, 1 : 0.48, 2 : 0.21, 3 : 0.00 },
        "_2_" : { 0 : 1.12, 1 : 0.67, 2 : 0.31, 3 : 0.00 },
        "__3" : { 0 : 1.38, 1 : 0.86, 2 : 0.32, 3 : 0.00 },
        "12_" : { 0 : 1.55, 1 : 0.96, 2 : 0.42, 3 : 0.00 },
        "1_3" : { 0 : 1.78, 1 : 1.31, 2 : 0.48, 3 : 0.00 },
        "_23" : { 0 : 2.04, 1 : 1.41, 2 : 0.67, 3 : 0.00 },
        "123" : { 0 : 2.69, 1 : 1.61, 2 : 0.96, 3 : 0.00 }
    }

    #Calculate Expected Runs based on outs and runners
    def calculateERC(self, outs_pre, runners_pre, outs_post, runners_post, runs):

        ExpectedRuns_pre = 0 if outs_pre >= 3 else self.RunMatrix[runners_pre][outs_pre]
        ExpectedRuns_post = 0 if outs_post >= 3 else self.RunMatrix[runners_post][outs_post]

        #ERC fulmula: ERC = runs - pre-state expectancy + post-state expectancy 
        ERC = runs -  ExpectedRuns_pre + ExpectedRuns_post
        return ERC

# Converts Statcast runner ID to a '123' style string of the base state
def get_base_state(on_1b, on_2b, on_3b) -> str:
    base_state = ""
    base_state += "1" if pd.notna(on_1b) else "_"
    base_state += "2" if pd.notna(on_2b) else "_"
    base_state += "3" if pd.notna(on_3b) else "_"
    return base_state


# Gather user input for the game date
print("Please enter the game date in YYYY-MM-DD format (e.g., 2025-11-01):")
game_date = input().strip()
# Gather user input for the home team abbreviation 
print("Please enter the home team abbreviation (e.g., TOR for Toronto Blue Jays):")
home_team = input().strip()

# Fetch Statcast data for the game
rawData = statcast(start_dt=game_date, end_dt=game_date)
game_pks = rawData["game_pk"].unique()

# Only Use game where the home team is the specified team for this example
target_game_pk = rawData[rawData["home_team"] == home_team]["game_pk"].iloc[0]
game_df = rawData[rawData["game_pk"] == target_game_pk].copy()

# Get the home and away team names for labeling
away_team = game_df["away_team"].iloc[0]
away_label = f"Away ({away_team})"
home_label = f"Home ({home_team})"

#Filter out rows without events and sort by inning and at-bat number
events_df = game_df[game_df["events"].notna()].copy()
events_df = events_df.sort_values(by=["inning", "at_bat_number"]).reset_index(drop=True)

# BATTER NAME LOOKUP 
print("Resolving batter names...")
unique_batter_ids = events_df["batter"].dropna().astype(int).unique().tolist()

try:
    id_lookup_df = playerid_reverse_lookup(unique_batter_ids, key_type="mlbam")
    id_lookup_df["full_name"] = (
        id_lookup_df["name_first"].str.title() + " " + id_lookup_df["name_last"].str.title()
    )
    batter_name_map = dict(zip(id_lookup_df["key_mlbam"], id_lookup_df["full_name"]))
except Exception:
    batter_name_map = {}


# Initialize ExpectedRuns calculator
calculator = ExpectedRuns()
# Name of the output CSV file
output_csv = "GenerateReport.csv"

# Define the fieldnames for the CSV output
fieldnames = [
    "game_id",
    "inning",
    "half",
    "batter",
    "event",
    "outs_pre",
    "runners_pre",
    "outs_post",
    "runners_post",
    "runs_scored",
    "erc",
]

# Write the results to a CSV file
with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i in range(len(events_df)):
        play = events_df.iloc[i]

        outs_pre = int(play["outs_when_up"])
        runners_pre = get_base_state(play["on_1b"], play["on_2b"], play["on_3b"])

        # Determine state after the play by looking ahead to the next PA in the same half-inning
        is_same_half = (
            i + 1 < len(events_df)
            and events_df.iloc[i + 1]["inning_topbot"] == play["inning_topbot"]
        )

        if is_same_half:
            next_play = events_df.iloc[i + 1]
            outs_post = int(next_play["outs_when_up"])
            runners_post = get_base_state(next_play["on_1b"], next_play["on_2b"], next_play["on_3b"])
        else:
            outs_post = 3
            runners_post = "___"

        # Calculate runs scored on the play
        post_score = play.get("post_bat_score", 0)
        pre_score = play.get("bat_score", 0)
        runs_scored = int(post_score - pre_score) if pd.notna(post_score) and pd.notna(pre_score) else 0

        erc = calculator.calculateERC(outs_pre, runners_pre, outs_post, runners_post, runs_scored)

        # Resolve batter name from the lookup dictionary
        batter_id = play["batter"]
        batter_name = batter_name_map.get(batter_id, str(batter_id))

        writer.writerow({
            "game_id": target_game_pk,
            "inning": play["inning"],
            "half": play["inning_topbot"],
            "batter": batter_name,
            "event": play["events"],
            "outs_pre": outs_pre,
            "runners_pre": runners_pre,
            "outs_post": outs_post,
            "runners_post": runners_post,
            "runs_scored": runs_scored,
            "erc": erc,
        })

# Sample Game completed and written to CSV
print(f"Done! Written {len(events_df)} plays to {output_csv}")






# Generate HTML report from the CSV file


# 1. Read the CSV file into a DataFrame
csv_file = "GenerateReport.csv"
df = pd.read_csv(csv_file)


# 2. Assign team lables based on the inning_topbot column
# Top = Awway, Bottom = Home
# Strip whitespace and convert to lowercase so 'Top', 'top', 'TOP' all match
half_clean = df["half"].astype(str).str.strip().str.lower()
df["team"] = half_clean.map(lambda h: away_label if h.startswith("t") else (home_label if h.startswith("b") else "Unknown"))

# 3. Calcualate team totals (Actual Runs vs Total ERC)
# Must add 0.48 to the total ERC per inning to account for the average runs scored to begin an inning
INNING_BASELINE_RE = 0.48
team_summary = (
    df.groupby("team")
    .agg(
        actual_runs=("runs_scored", "sum"),
        raw_erc=("erc", "sum"),
        innings_batted=("inning", "nunique"),  # Count distinct innings batted
        total_plays=("event", "count"),
    )
    .reset_index()
)

# Add the baseline runs to the total ERC for each team
team_summary["baseline_runs"] = team_summary["innings_batted"] * INNING_BASELINE_RE
team_summary["total_erc"] = (team_summary["raw_erc"] + team_summary["baseline_runs"]).round(3)

team_summary["variance"] = (team_summary["actual_runs"] - team_summary["total_erc"]).round(3)


# 4. Find the top 3 players from each team based on ERC
batter_summary = (
    df.groupby(["team", "batter"])
    .agg(
        total_erc=("erc", "sum"),
        runs_scored=("runs_scored", "sum"),
        plate_appearances=("event", "count"),
    )
    .reset_index()
)
batter_summary["total_erc"] = batter_summary["total_erc"].round(3)

# Filter top 3 per team
top_batters = (
    batter_summary.sort_values(["team", "total_erc"], ascending=[True, False])
    .groupby("team")
    .head(3)
    .reset_index(drop=True)
)

# 5. Build HTML Markup
team_rows_html = ""
for _, row in team_summary.iterrows():
    team_rows_html += f"""
    <tr>
        <td><strong>{row['team']}</strong></td>
        <td>{int(row['actual_runs'])}</td>
        <td>{row['total_erc']:+.3f}</td>
        <td>{int(row['total_plays'])}</td>
    </tr>
    """

# Generate rows separately for home and away teams
away_rows_html = "".join(
    f"<tr><td>{row['batter']}</td><td><strong>{row['total_erc']:+.3f}</strong></td>"
    f"<td>{int(row['runs_scored'])}</td><td>{int(row['plate_appearances'])}</td></tr>"
    for _, row in top_batters[top_batters["team"] == away_label].iterrows()
)

home_rows_html = "".join(
    f"<tr><td>{row['batter']}</td><td><strong>{row['total_erc']:+.3f}</strong></td>"
    f"<td>{int(row['runs_scored'])}</td><td>{int(row['plate_appearances'])}</td></tr>"
    for _, row in top_batters[top_batters["team"] == home_label].iterrows()
)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expected Runs Contribution (ERC) Game Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 40px auto;
            max-width: 850px;
            padding: 0 20px;
            color: #222;
            background-color: #f8fafc;
        }}
        h1 {{
            font-size: 26px;
            margin-bottom: 6px;
            color: #0f172a;
        }}
        p.subtitle {{
            color: #64748b;
            margin-top: 0;
            margin-bottom: 24px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            border: 1px solid #e2e8f0;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .grid-2 {{
                grid-template-columns: 1fr;
            }}
        }}
        h2 {{
            font-size: 18px;
            margin-top: 0;
            margin-bottom: 16px;
            color: #1e293b;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #f1f5f9;
            font-weight: 600;
            color: #475569;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <h1>Run Expectancy (ERC) Post-Game Report</h1>
    <p class="subtitle">{away_label} @ {home_label} | Evaluated from <code>{csv_file}</code></p>

    <div class="card">
        <h2>Team Summary: Actual Runs vs. Expected Runs Added</h2>
        <table>
            <thead>
                <tr>
                    <th>Team</th>
                    <th>Actual Runs</th>
                    <th>Accumulated ERC</th>
                    <th>Total PAs</th>
                </tr>
            </thead>
            <tbody>
                {team_rows_html}
            </tbody>
        </table>
    </div>

   <div class="grid-2">
        <div class="card">
            <h2>{away_label} - Top 3 Players</h2>
            <table>
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Total ERC</th>
                        <th>Runs</th>
                        <th>PAs</th>
                    </tr>
                </thead>
                <tbody>
                    {away_rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>{home_label} - Top 3 Players</h2>
            <table>
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Total ERC</th>
                        <th>Runs</th>
                        <th>PAs</th>
                    </tr>
                </thead>
                <tbody>
                    {home_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div class="card">
        <h2>Plays of the Game</h2>
        <table>
            <thead>
                <tr>
                    <th>Inning</th>
                    <th>Half</th>
                    <th>Batter</th>
                    <th>Event</th>
                    <th>Runs Scored</th>
                    <th>ERC Change</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"<tr><td>{row['inning']}</td><td>{row['half']}</td><td>{row['batter']}</td>"
                f"<td>{row['event']}</td><td>{int(row['runs_scored'])}</td><td>{row['erc']:+.3f}</td></tr>"
                for _, row in df.nlargest(3, "erc").iterrows())}
            </tbody>
        </table>
    </div>


</body>
</html>
"""

output_html_file = "GeneratedReport.html"
with open(output_html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Report generated successfully: {output_html_file}")