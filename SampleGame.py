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



print("Game data for 2025 WS Game 7 (LAD vs TOR)")

# Fetch Statcast data for the game
rawData = statcast(start_dt='2025-11-01', end_dt='2025-11-01')
game_pks = rawData["game_pk"].unique()

# Only Use game where the home team is "TOR" (Toronto Blue Jays) for this example
target_game_pk = rawData[rawData["home_team"] == "TOR"]["game_pk"].iloc[0]
game_df = rawData[rawData["game_pk"] == target_game_pk].copy()

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
output_csv = "SampleGame.csv"

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