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


def scrape_fbref_teamstats(team, link):
    """scrapes and collates a given team's stats from fbref.com"""
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


def team_stat_scraper(write_out=False):
    """scrapes stats for list of teams for given seasons"""
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
            temp_stats_df = scrape_fbref_teamstats(team, l)
            data.append(temp_stats_df)
            print(f"Added record {i + 1} for {team}")
    stats_df = pd.concat(data, ignore_index=True)
    if write_out:
        stats_df.to_csv("Datasets/Championship Goal Team Stats.csv")


def extract_stat(table_soup, stat_name, data_type):
    stat = table_soup.find_all("td", {"data-stat": stat_name})
    if data_type == "int":
        stat = [int(s.text.strip()) if s.text.strip() != "" else 0 for s in stat]
    elif data_type == "float":
        stat = [float(s.text.strip()) if s.text.strip() != "" else 0 for s in stat]
    else:
        stat = [s.text.strip() if s.text.strip() != "" else "0" for s in stat]
    return stat


def scrape_soup(link, page):
    split_link = link.split("/")
    split_link[-2] = page
    page_link = "/".join(split_link)
    soup = stealth_scraper(page_link)
    return soup


def scrape_fbref_playerstats(link):
    pages = ["stats", "shooting", "gca", "passing"]
    soup = scrape_soup(link, pages[0])
    table_standard = soup.find("table", {"id": "stats_standard"}).find("tbody")
    names_standard = extract_stat(table_standard, "player", "string")
    team_standard = extract_stat(table_standard, "team", "string")
    age_standard = extract_stat(table_standard, "age", "string")
    age_standard = [int(a.split("-")[0]) for a in age_standard]
    # print(age_standard)
    goals_standard = extract_stat(table_standard, "goals", "int")
    assists_standard = extract_stat(table_standard, "assists", "int")
    progp_standard = extract_stat(table_standard, "progressive_passes", "int")
    standard_df = pd.DataFrame(
        [names_standard, team_standard, age_standard, goals_standard, assists_standard, progp_standard]).T.rename(
        {0: "Name", 1: "Team", 2: "Age", 3: "Goals", 4: "Assists", 5: "ProgP"}, axis=1).set_index("Name")

    soup = scrape_soup(link, pages[1])
    table_shooting = soup.find("table", {"id": "stats_shooting"}).find("tbody")
    names_shooting = extract_stat(table_shooting, "player", "string")
    sot_shooting = extract_stat(table_shooting, "shots_on_target", "int")
    gps_shooting = extract_stat(table_shooting, "goals_per_shot", "float")
    shooting_df = pd.DataFrame([names_shooting, sot_shooting, gps_shooting]).T.rename(
        {0: "Name", 1: "SoT", 2: "G/Sh"}, axis=1).set_index("Name")

    soup = scrape_soup(link, pages[2])
    table_gca = soup.find("table", {"id": "stats_gca"}).find("tbody")
    names_gca = extract_stat(table_gca, "player", "string")
    sca_gca = extract_stat(table_gca, "sca", "int")
    gca_df = pd.DataFrame([names_gca, sca_gca]).T.rename({0: "Name", 1: "SCA"}, axis=1).set_index("Name")

    soup = scrape_soup(link, pages[3])
    table_passing = soup.find("table", {"id": "stats_passing"}).find("tbody")
    names_passing = extract_stat(table_passing, "player", "string")
    ppa_passing = extract_stat(table_passing, "passes_into_penalty_area", "int")
    kp_passing = extract_stat(table_passing, "assisted_shots", "int")
    passing_df = pd.DataFrame([names_passing, ppa_passing, kp_passing]).T.rename({0: "Name", 1: "PassesPA", 2: "KP"},
                                                                                 axis=1).set_index("Name")
    stats_df = standard_df.join([shooting_df, gca_df, passing_df])

    stats_df["Creation Rank"] = stats_df["Assists"].rank(ascending=False) + stats_df["ProgP"].rank(ascending=False) + \
                                stats_df["SCA"].rank(ascending=False) + stats_df["PassesPA"].rank(ascending=False) + \
                                stats_df["KP"].rank(ascending=False)
    stats_df["Scoring Rank"] = stats_df["Goals"].rank(ascending=False) + stats_df["SoT"].rank(ascending=False) + \
                               stats_df["G/Sh"].rank(ascending=False)
    return stats_df


def player_stat_scraper():
    links = {"Championship": "https://fbref.com/en/comps/10/stats/Championship-Stats",
             "LigaMX": "https://fbref.com/en/comps/31/stats/Liga-MX-Stats",
             "Serie-B": "https://fbref.com/en/comps/18/stats/Serie-B-Stats",
             "Bundesliga2": "https://fbref.com/en/comps/33/stats/2-Bundesliga-Stats"}
    dataframes = []
    for league, link in links.items():
        temp_df = scrape_fbref_playerstats(link)
        dataframes.append(temp_df)
        print(f"Record added for {league}")
    stats_df = pd.concat(dataframes)
    stats_df.to_csv("Datasets/Transfer Target Stats.csv")


if __name__ == '__main__':
    t0 = time.time()
    player_stat_scraper()
    t1 = time.time()
    print(t1 - t0)
