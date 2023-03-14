# Singleton: use this for stats caching/logging like behaviour

import pandas as pd

class Stats:
    def __init__(self) -> None:
        self.df = pd.DataFrame(columns=['memory', 'conflicts', 'quant instantiations'])
    def add(self, stats):
        keys = ['memory', 'conflicts', 'quant instantiations'] # set(self.df.columns) & set(stats.keys())
        stats = dict(zip(keys, [stats.get_key_value(x) for x in keys]))

        df2 = pd.DataFrame.from_records(stats, index=[0])
        self.df = pd.concat([self.df, df2])

    def print(self):
        print("[STATS]")
        print(self.df.to_csv(index=False))

STATS = Stats()