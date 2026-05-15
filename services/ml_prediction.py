import pandas as pd
import numpy as np
import xgboost as xgb
import streamlit as st
from services.fpl_api import get_bootstrap_static, get_fixtures

class FPLPredictor:
    def __init__(self):
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=150, 
            learning_rate=0.05, 
            max_depth=6,
            random_state=42
        )
        self.is_trained = False
        self.feature_cols = ['form', 'selected_by_percent', 'now_cost', 'minutes_played_best', 'fdr_upcoming']
        
    def _prepare_training_data(self):
        bootstrap = get_bootstrap_static()
        if not bootstrap:
            X = pd.DataFrame(np.random.rand(100, len(self.feature_cols)), columns=self.feature_cols)
            y = X['form'] * 2
            return X, y
            
        elements = bootstrap['elements']
        df = pd.DataFrame(elements)
        
        # Real training features
        X = pd.DataFrame({
            'form': pd.to_numeric(df['form'], errors='coerce').fillna(0),
            'selected_by_percent': pd.to_numeric(df['selected_by_percent'], errors='coerce').fillna(0),
            'now_cost': df['now_cost'] / 10.0,
            'minutes_played_best': df['minutes'] / 90.0, # normalized to games
            'fdr_upcoming': 3 # Base for training
        })
        
        # Target: total_points / games_played (to learn 'points per appearance')
        # We handle divisions by zero
        games = (df['minutes'] / 90.0).clip(lower=1)
        y = (pd.to_numeric(df['total_points'], errors='coerce').fillna(0) / games)
        
        return X, y

    def train(self):
        X, y = self._prepare_training_data()
        self.xgb_model.fit(X, y)
        self.is_trained = True

    def predict_points(self, players_df: pd.DataFrame):
        """
        Input players_df should have: 
        form, selected_by_percent, now_cost, minutes_played_best, fdr_upcoming
        """
        if not self.is_trained:
            self.train()
            
        for col in self.feature_cols:
            if col not in players_df.columns:
                players_df[col] = 0
                
        X_infer = players_df[self.feature_cols]
        predictions = self.xgb_model.predict(X_infer)
        
        # Scale: Base appearance (2) + performance logic
        # If FDR is high (hard), penalize. If FDR is low (easy), boost.
        # FDR scale is 2 (easy) to 5 (hard)
        difficulty_mod = (3.5 - players_df['fdr_upcoming']) * 0.5 
        
        scaled_points = (predictions * 0.8) + 2.0 + difficulty_mod
        return np.clip(scaled_points, 0, 16)

@st.cache_resource
def get_predictor():
    predictor = FPLPredictor()
    predictor.train()
    return predictor
