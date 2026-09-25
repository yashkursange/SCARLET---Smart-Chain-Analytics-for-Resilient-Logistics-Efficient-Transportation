import numpy as np

class NaiveForecast:
    def predict(self, df):
        # Naive forecast = previous day's demand (which is lag_1)
        return df['lag_1'].values

class SeasonalNaiveForecast:
    def predict(self, df):
        # Seasonal naive forecast = demand from 7 days earlier (which is lag_7)
        return df['lag_7'].values
