import pandas as pd

if __name__ == '__main__':
    transfer_targets = pd.read_csv("Datasets/Transfer Target Stats.csv", index_col=0)
    print(transfer_targets)