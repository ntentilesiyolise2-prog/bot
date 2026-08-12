import xgboost as xgb
import numpy as np
import pandas as pd
import joblib
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class XGBoostModel:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_path = "models/xgboost_model.pkl"
        self._load_or_init()

    def _load_or_init(self):
        os.makedirs("models", exist_ok=True)
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Loaded XGBoost model.")
            except:
                self.model = None
        if self.model is None:
            logger.info("Initializing new XGBoost model.")

    def train(self, X, y):
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        logger.info("XGBoost trained and saved.")

    def predict(self, features):
        if self.model is None:
            return 0.5
        return self.model.predict_proba(features)[0][1]

    def get_feature_importance(self):
        if self.model is None:
            return {}
        return dict(zip(self.model.get_booster().get_score(importance_type='weight').keys(),
                        self.model.get_booster().get_score(importance_type='weight').values()))
