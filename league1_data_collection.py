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


def stealth_scraper(link, buttons=None):
    options = webdriver.ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "HeadlessChrome/96.0.4664.110 Safari/537.36")
    options.add_argument("start-maximized")
    options.add_argument("--headless")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    # WhoScored and TransferMarkt use cloudlfare so have to work around, not the most efficient solution but as this is a small scale scrape its acceptable
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    driver.get(link)
    # if any buttons need to be clicked on the page to load all data
    if buttons:
        for b in buttons:
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, b)))
            button = driver.find_element(By.XPATH, b)
            print(button.text)
            # button.click()
            webdriver.ActionChains(driver).move_to_element(button).click(button).perform()
            # driver.execute_script("arguments[0].click();", button)
            # WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "outfielderBlockPerGame")))
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    driver.quit()
    return soup


def scrape_fbref(link):
    soup = stealth_scraper(link)
    stats_table = soup.find("table", {"id": "stats_shooting_15"})
    total_stats = stats_table.find("tfoot")
    sot = int(total_stats.find("td", {"data-stat": "shots_on_target"}).text.strip())
    gps = float(total_stats.find("td", {"data-stat": "goals_per_shot"}).text.strip())

    appearances_table = soup.find("table", {"id": "stats_playing_time_15"}).find("tbody")
    player = appearances_table.find_all("th", {"data-stat": "player", "scope": "row"})
    player = [p.text.strip() for p in player]
    appearances = appearances_table.find_all("td", {"data-stat": "games"})
    appearances = [int(a.text.strip()) for a in appearances]
    appearances_dict = dict(zip(player, appearances))

    return sot, gps, appearances_dict


def scrape_WhoScored(link):
    buttons = ['//a[contains(@href,"#team-squad-archive-stats-defensive")]']
    soup = stealth_scraper(link)  # , buttons)
    stats_table = soup.find("div", {"id": "team-squad-archive-stats-summary"})
    name = stats_table.find_all("span", {"class": "iconize iconize-icon-left"})
    name = [n.text for n in name]
    rating = stats_table.find_all("td", {"class": "rating"})
    rating = [float(r.text) for r in rating]
    mins = stats_table.find_all("td", {"class": "minsPlayed"})
    mins = [int(m.text) for m in mins]
    goals = stats_table.find_all("td", {"class": "goal"})
    goals = [g.text.strip() for g in goals]
    assists = stats_table.find_all("td", {"class": "assistTotal"})
    assists = [a.text.strip() for a in assists]
    aerWonPg = stats_table.find_all("td", {"class": "aerialWonPerGame"})
    aerWonPg = [a.text.strip() for a in aerWonPg]
    numeric_columns = ["Rating", "Mins", "Goals", "Assists", "AerWonPg"]
    rename_dict = dict(zip(range(6), ["Name"] + numeric_columns))
    stats_df = pd.DataFrame([name, rating, mins, goals, assists, aerWonPg]).T.rename(columns=rename_dict)
    stats_df[numeric_columns] = stats_df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    return stats_df


def format_dataset(team, whoscored_stats, fbref_stats, appearances):
    stats_names = set(whoscored_stats["Name"])
    app_names = set(appearances.keys())
    identical_names = stats_names.intersection(app_names)
    stats_names = stats_names - identical_names
    performance_names = app_names - identical_names
    for name in stats_names:
        option = process.extractOne(name, performance_names)
        # if confidence over 75
        if option[1] >= 75:
            appearances[name] = appearances.pop(option[0])
    appearances_df = pd.DataFrame.from_dict(appearances, columns=["Apps"], orient="index")
    whoscored_stats.set_index("Name", inplace=True)

    stats_df = whoscored_stats.join(appearances_df)
    stats_df["AerWon"] = stats_df.AerWonPg * stats_df.Apps
    select_players = stats_df[stats_df["Apps"] >= 5]
    rating = select_players["Rating"].mean()
    stats_df.drop(["AerWonPg", "Apps", "Mins", "Rating"], axis=1, inplace=True)
    stats_df = stats_df.sum()
    stats_df["Rating"] = rating
    stats_df["ShotsOnTarget"] = fbref_stats[0]
    stats_df["GoalsPerShot"] = fbref_stats[1]
    stats_df["Team"] = team
    return stats_df


if __name__ == '__main__':
    championship_teams = {"Sunderland": ["https://www.whoscored.com/Teams/16/Archive/England-Sunderland?stageId=20803",
                                         "https://fbref.com/en/squads/8ef52968/2021-2022/Sunderland-Stats"],
                          "Ipswich": ["https://www.whoscored.com/Teams/165/Archive/England-Ipswich",
                                      "https://fbref.com/en/squads/b74092de/2022-2023/Ipswich-Town-Stats"]
                          }
    stats_list = []
    for team, links in championship_teams.items():
        whoscored_stats = scrape_WhoScored(links[0])
        sot, gps, apps = scrape_fbref(links[1])
        fb_stats = [sot, gps]
        stats = format_dataset(team, whoscored_stats, fb_stats, apps)
        stats_list.append(stats)
    target_team_stats = pd.concat(stats_list, axis=1).T.set_index("Team")

    print(target_team_stats)
