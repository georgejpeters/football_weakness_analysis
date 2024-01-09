import pandas as pd
pd.set_option('display.max_columns', None)

if __name__ == '__main__':
    stats = pd.read_csv("Datasets/Championship Goal Team Stats.csv", index_col=0)
    goal_team_stats = stats[stats["Team"] != "Wigan"]
    wigan_stats = stats[stats["Team"] == "Wigan"]
    average_stats = goal_team_stats.mean(numeric_only=True)
    stat_difference = wigan_stats-average_stats
    print(stats)
    # Analysing this stat difference shows that it seems that Wigan's attack last season was the largest issue,
    # the delta is larger for GS and they seem strong enough on Aerials won and Blocks
    print(stat_difference)
