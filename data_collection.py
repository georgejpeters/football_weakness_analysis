from selenium import webdriver
from selenium_stealth import stealth
from bs4 import BeautifulSoup


def stealth_scraper(link):
    options = webdriver.ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/96.0.4664.110 Safari/537.36")
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
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    return soup


def scrape_fbref(link):
    soup = stealth_scraper(link)
    stats_table = soup.find("table", {"id": "stats_standard_15"})
    stats = stats_table.find("tbody")
    data = []
    rows = stats.find_all("tr")
    for row in rows:
        cols = row.find_all(["td", "th"])
        cols = [ele.text.strip() for ele in cols]
        data.append(cols)
    print(data)
    # find subheader containing column names
    header = stats_table.find("thead").find_all("tr")[1].find_all("th")
    column_names = [col.text for col in header]
    df = pd.DataFrame(data, columns=column_names)
    df = df.iloc[:, :-10]

    print(df)


def scrape_WhoScored(link):
    soup = stealth_scraper(link)
    stats_table = soup.find("div", {"id": "team-squad-stats-summary"})

    name = stats_table.find_all("span", {"class": "iconize iconize-icon-left"})
    name_text = [n.text for n in name]
    rating = stats_table.find_all("td", {"class": "rating"})
    mins = stats_table.find_all("td", {"class": "minsPlayed"})
    mins_and_rating = [[int(mins[idx].text.strip()), float(r.text)] for idx, r in enumerate(rating)]
    whoscored_ratings_dict = dict(zip(name_text, mins_and_rating))
    whoscored_ratings = pd.DataFrame.from_dict(whoscored_ratings_dict, orient="index", columns=["Mins", "Rating"])
    return whoscored_ratings
