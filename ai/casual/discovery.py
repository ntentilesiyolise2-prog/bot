import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from utils.logger import setup_logger

logger = setup_logger(__name__)

class CausalDiscovery:
    def __init__(self, lookback=100):
        self.lookback = lookback
        self.importance = {}

    async def compute_causality(self, df, target='Close'):
        if df.empty or len(df) < self.lookback:
            return {}
        X = df[['Open','High','Low','Volume']].values
        y = df[target].values
        y_lag = np.roll(y, 1)
        y_lag[0] = y[0]
        X_aug = np.column_stack([X, y_lag])
        X_aug = X_aug[1:]
        y = y[1:]
        if len(X_aug) < 10:
            return {}
        lasso = LassoCV(cv=3, max_iter=1000)
        lasso.fit(X_aug, y)
        coef = lasso.coef_
        self.importance = dict(zip(['Open','High','Low','Volume','Lag_Close'], coef))
        return self.importance
