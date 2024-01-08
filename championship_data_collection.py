import pandas as pd
import numpy as np
from selenium import webdriver
from selenium_stealth import stealth
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from fuzzywuzzy import process
from league1_data_collection import stealth_scraper
import re
from statistics import mean


def scrape_fbref(team, link):
    soup = stealth_scraper(link)
    summary_stats = soup.find("table", {"id": "stats_standard_10"}).find("tfoot")
    team_totals = summary_stats.find_all("tr")[0]
    opponent_totals = summary_stats.find_all("tr")[1]
    goals_scored = int(team_totals.find("td", {"data-stat": "goals"}).text)
    progressive_passes = int(team_totals.find("td", {"data-stat": "progressive_passes"}).text)
    goals_conceded = int(opponent_totals.find("td", {"data-stat": "goals"}).text)
    # find total stats at bottom of table
    shooting_stats = soup.find("table", {"id": "stats_shooting_10"})
    # select shooting stats for the team not the opponent
    shooting_stats_summary = shooting_stats.find("tfoot").find_all("tr")[0]
    shots_on_target = int(shooting_stats_summary.find("td", {"data-stat": "shots_on_target"}).text)
    goals_per_shot = shooting_stats.find_all("td", {"data-stat": "goals_per_shot"})
    # iterate over goals per shot replacing non-decimal numbers with 0,
    goals_per_shot = [float(g.text.strip()) if re.match(r'\d+(?:,\d*)?', g.text.strip()) else 0 for g in goals_per_shot]
    # find average goals per shot of top 10 goals per shot players in a team as to not punish teams with large squads
    goals_per_shot = round(mean(sorted(goals_per_shot, reverse=True)[:10]), 5)

    passing_stats = soup.find("table", {"id": "stats_passing_10"}).find("tfoot").find_all("tr")[0]
    passes_pa = int(passing_stats.find("td", {"data-stat": "passes_into_penalty_area"}).text)
    # progressive_passes = int(passing_stats.find("td", {"data-stat": "progressive_passes"}).text)
    assisted_shots = int(passing_stats.find("td", {"data-stat": "assisted_shots"}).text)

    defensive_stats = soup.find("table", {"id": "stats_defense_10"}).find("tfoot").find_all("tr")[0]
    blocks = int(defensive_stats.find("td", {"data-stat": "blocked_shots"}).text.strip())

    misc_stats = soup.find("table", {"id": "stats_misc_10"}).find("tfoot").find_all("tr")[0]
    recoveries = int(misc_stats.find("td", {"data-stat": "ball_recoveries"}).text.strip())
    aerials_won = int(misc_stats.find("td", {"data-stat": "aerials_won"}).text.strip())
    # stats = [goals_scored, goals_conceded, blocks, aerials_won, progressive_passes, recoveries, shots_on_target,
    #         goals_per_shot, passes_pa, assisted_shots]
    stats = {"Team": team, "GS": goals_scored, "GA": goals_conceded, "Blocks": blocks, "AerWon": aerials_won,
             "ProgP": progressive_passes, "Recoveries": recoveries, "SoT": shots_on_target,
             "GoalsPerShot": goals_per_shot, "PassesPA": passes_pa, "AssistedShots": assisted_shots}
    stats = pd.DataFrame.from_dict(stats, orient="index").T
    return stats


if __name__ == '__main__':
    # Getting seasons for teams recently promoted to the championship where they finished top half
    team_links = {"Wigan": ["https://fbref.com/en/squads/e59ddc76/2022-2023/Wigan-Athletic-Stats"],
                  "Sunderland": ["https://fbref.com/en/squads/8ef52968/2022-2023/Sunderland-Stats"],
                  "Luton": ["https://fbref.com/en/squads/e297cd13/2021-2022/Luton-Town-Stats",
                            "https://fbref.com/en/squads/e297cd13/2022-2023/Luton-Town-Stats"],
                  "Blackburn": ["https://fbref.com/en/squads/e090f40b/2021-2022/Blackburn-Rovers-Stats",
                                "https://fbref.com/en/squads/e090f40b/2022-2023/Blackburn-Rovers-Stats"],
                  "Coventry": ["https://fbref.com/en/squads/f7e3dfe9/2021-2022/Coventry-City-Stats",
                               "https://fbref.com/en/squads/f7e3dfe9/2022-2023/Coventry-City-Stats"]}
    data = []
    for team, links in team_links.items():
        for i, l in enumerate(links):
            temp_stats_df = scrape_fbref(team, l)
            data.append(temp_stats_df)
            print(f"Added record {i+1} for {team}")
    stats_df = pd.concat(data, ignore_index=True)
    stats_df.to_csv("Championship Goal Team Stats.csv")

