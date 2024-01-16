import pandas as pd
import numpy as np
from fuzzywuzzy import process
from sklearn.neighbors import KNeighborsRegressor
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import MinMaxScaler


def build_dataset():
    player_stats = pd.read_csv("Datasets/Player Stats 17-22.csv", index_col=0)
    top5_leagues = ["EPL", "Bundesliga", "LaLiga", "Ligue1", "SeriaA"]
    # remove data of players not in top 5 leagues
    player_stats = player_stats.copy()[player_stats["League"].isin(top5_leagues)]
    team_stats = player_stats.groupby(["Season", "Squad"], as_index=False).sum(numeric_only=True)
    # dropping 22/23 as player data is incomplete
    team_stats = team_stats.copy()[team_stats["Season"] != "2022-2023"]
    team_stats.drop(["Minutes"], axis=1, inplace=True)
    team_stats["Season"] = team_stats["Season"].str.replace("-", "/")
    # team_stats.to_csv("Datasets/Team Stats 17-21.csv")

    team_performances = pd.read_csv("Datasets/Team Performance.csv")
    team_performances = team_performances[["Season", "Squad", "Goals Conceded"]]

    stats_names = set(team_stats["Squad"])
    performance_names = set(team_performances["Squad"])

    identical_names = stats_names.intersection(performance_names)
    stats_names = stats_names - identical_names
    performance_names = performance_names - identical_names
    name_dict = {}
    for name in stats_names:
        option = process.extractOne(name, performance_names)
        # if confidence over 75
        if option[1] >= 75:
            name_dict[option[0]] = name
    team_performances.replace({"Squad": name_dict}, inplace=True)
    valid_names = list(identical_names) + list(name_dict.values())
    team_performances = team_performances[team_performances["Squad"].isin(valid_names)]
    team_stats = team_stats[team_stats["Squad"].isin(valid_names)]

    # adding goals conceded to team stats
    team_data = team_stats.merge(team_performances, on=["Season", "Squad"])
    team_data.dropna(inplace=True)
    team_data.drop_duplicates(subset=["Season", "Squad"], inplace=True)
    team_data.to_csv("Datasets/Team Data 17-22.csv")


def calculate_feature_importance(X, y, features):
    # permutation feature importance for knn regressor
    scaler = MinMaxScaler()
    # normalise data data
    X = scaler.fit_transform(X)
    model = KNeighborsRegressor()
    # fit the model
    model.fit(X, y)
    all_importances = []
    # perform permutation importance scoring 5 times
    for i in range(5):
        results = permutation_importance(model, X, y, scoring='neg_mean_squared_error')
        importance = results.importances_mean
        all_importances.append(importance)
    all_importances = np.asarray(all_importances)
    # average results of permutation feature importance over five runs
    mean_all_importances = np.mean(all_importances, axis=0)
    importance_dict = dict(zip(features, mean_all_importances))
    importance_df = pd.DataFrame.from_dict(importance_dict, orient="index", columns=["Importance"])
    importance_df.sort_values(by=["Importance"], inplace=True, ascending=False)
    return importance_df


def feature_selection():
    team_stats = pd.read_csv("Datasets/Team Data 17-22.csv", index_col=0)
    # Goal creating actions assists and gca from dribbles all dropped as they are directly related to goals
    offensive_target_stats = team_stats.drop(["Season", "Squad", "Age", "Goals", "GCA", "Assists", "GcaDrib", "Goals Conceded"], axis=1)
    X_offensive = offensive_target_stats
    y_offensive = team_stats[["Goals"]]
    offensive_importances = calculate_feature_importance(X_offensive, y_offensive, offensive_target_stats.columns)
    # somewhat arbitrary importance threshold to keep stats that influence outcome strongly keeping top 6ish
    #offensive_importances = offensive_importances[offensive_importances["Importance"] >= 7]

    defensive_target_stats = team_stats.drop(["Season", "Squad", "Age", "Goals Conceded"], axis=1)
    X_defensive = defensive_target_stats
    y_defensive = team_stats[["Goals Conceded"]]
    defensive_importances = calculate_feature_importance(X_defensive, y_defensive, defensive_target_stats.columns)
    #defensive_importances = defensive_importances[defensive_importances["Importance"] >= 3]
    print("--------------------")
    print("Offensive Importances")
    print("--------------------")
    print(offensive_importances)
    print("--------------------")
    print("Defensive Importances")
    print("--------------------")
    print(defensive_importances)




if __name__ == '__main__':
    # calling this function builds and writes to disk the necessary dataset for feature selection
    # build_dataset()
    # calling this function analyses the data and computed the feature importance scores
    feature_selection()
