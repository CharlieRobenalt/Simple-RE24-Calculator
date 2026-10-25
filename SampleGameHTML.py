import pandas as pd

# 1. Read the CSV file into a DataFrame
csv_file = "SampleGame.csv"
df = pd.read_csv(csv_file)

# 2. Assign team lables based on the inning_topbot column
# Top = Awway, Bottom = Home
# For Sample ALCS Game 1 Top = CLE, Bottom = TB
# Strip whitespace and convert to lowercase so 'Top', 'top', 'TOP' all match
half_clean = df["half"].astype(str).str.strip().str.lower()
df["team"] = half_clean.map(lambda h: "Away (LAD)" if h.startswith("t") else ("Home (TOR)" if h.startswith("b") else "Unknown"))

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

# Generate rows separately for LAD and TOR
lad_rows_html = "".join(
    f"<tr><td>{row['batter']}</td><td><strong>{row['total_erc']:+.3f}</strong></td>"
    f"<td>{int(row['runs_scored'])}</td><td>{int(row['plate_appearances'])}</td></tr>"
    for _, row in top_batters[top_batters["team"] == "Away (LAD)"].iterrows()
)

tor_rows_html = "".join(
    f"<tr><td>{row['batter']}</td><td><strong>{row['total_erc']:+.3f}</strong></td>"
    f"<td>{int(row['runs_scored'])}</td><td>{int(row['plate_appearances'])}</td></tr>"
    for _, row in top_batters[top_batters["team"] == "Home (TOR)"].iterrows()
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
    <p class="subtitle">Evaluated from <code>{csv_file}</code></p>

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
            <h2>Away (LAD) - Top 3 Players</h2>
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
                    {lad_rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Home (TOR) - Top 3 Players</h2>
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
                    {tor_rows_html}
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

output_html_file = "SampleGameReport.html"
with open(output_html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Report generated successfully: {output_html_file}")