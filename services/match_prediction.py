import pandas as pd
import numpy as np
import os
import glob
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
import streamlit as st

class MatchPredictor:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        # Upgraded to Gradient Boosting for better accuracy on tabular data
        self.model = GradientBoostingClassifier(n_estimators=150, learning_rate=0.1, max_depth=4, random_state=42)
        self.team_encoder = LabelEncoder()
        self.is_trained = False
        self.team_stats = {}

    def load_data(self):
        """Loads all CSV files and handles encoding/formatting."""
        all_files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        if not all_files:
            return pd.DataFrame()
        
        df_list = []
        for file in all_files:
            try:
                df = pd.read_csv(file, encoding='latin1')
                # Keep only relevant columns if they exist
                cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 'AvgH', 'AvgD', 'AvgA']
                df = df[[c for c in cols if c in df.columns]]
                df_list.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
                
        if not df_list:
            return pd.DataFrame()
            
        full_df = pd.concat(df_list, ignore_index=True)
        full_df['Date_Parsed'] = pd.to_datetime(full_df['Date'], format='mixed', dayfirst=True, errors='coerce')
        full_df = full_df.sort_values('Date_Parsed').reset_index(drop=True)
        return full_df

    def prepare_features(self, df):
        """Advanced feature engineering using shots, corners, and market odds."""
        if df.empty or 'HomeTeam' not in df.columns or 'FTR' not in df.columns:
            return pd.DataFrame(), pd.Series()
            
        all_teams = pd.concat([df['HomeTeam'], df['AwayTeam']]).unique()
        self.team_encoder.fit(all_teams)
        
        # Derived Stats: Shot Accuracy and Corner Pressure
        # Use simple means for now as a baseline for each team
        home_metrics = df.groupby('HomeTeam').agg({
            'FTHG': 'mean', 'FTAG': 'mean', 'HS': 'mean', 'HST': 'mean', 'HC': 'mean'
        }).rename(columns={'FTHG': 'GF', 'FTAG': 'GA', 'HS': 'Shots', 'HST': 'SoT', 'HC': 'Corners'})
        
        away_metrics = df.groupby('AwayTeam').agg({
            'FTAG': 'mean', 'FTHG': 'mean', 'AS': 'mean', 'AST': 'mean', 'AC': 'mean'
        }).rename(columns={'FTAG': 'GF', 'FTHG': 'GA', 'AS': 'Shots', 'AST': 'SoT', 'AC': 'Corners'})
        
        for team in all_teams:
            # Combine Home and Away stats
            hm = home_metrics.loc[team] if team in home_metrics.index else away_metrics.loc[team]
            am = away_metrics.loc[team] if team in away_metrics.index else home_metrics.loc[team]
            
            self.team_stats[team] = {
                'att': (hm['GF'] + am['GF']) / 2,
                'def': (hm['GA'] + am['GA']) / 2,
                'shot_acc': (hm['SoT'] + am['SoT']) / (hm['Shots'] + am['Shots'] + 0.1),
                'corners': (hm['Corners'] + am['Corners']) / 2
            }
            
        features = []
        for idx, row in df.iterrows():
            ht = row['HomeTeam']
            at = row['AwayTeam']
            
            # Feature Vector
            feat = {
                'HomeTeamEnc': self.team_encoder.transform([ht])[0],
                'AwayTeamEnc': self.team_encoder.transform([at])[0],
                'HomeAtt': self.team_stats[ht]['att'],
                'HomeDef': self.team_stats[ht]['def'],
                'AwayAtt': self.team_stats[at]['att'],
                'AwayDef': self.team_stats[at]['def'],
                'HomeShotAcc': self.team_stats[ht]['shot_acc'],
                'AwayShotAcc': self.team_stats[at]['shot_acc'],
                'HomeCorners': self.team_stats[ht]['corners'],
                'AwayCorners': self.team_stats[at]['corners']
            }
            # Include market odds as a "True Probability" hint if training
            if 'AvgH' in row and not np.isnan(row['AvgH']):
                feat['MktHomeProb'] = 1.0 / row['AvgH']
                feat['MktDrawProb'] = 1.0 / row['AvgD']
                feat['MktAwayProb'] = 1.0 / row['AvgA']
            else:
                feat['MktHomeProb'] = 0.33
                feat['MktDrawProb'] = 0.33
                feat['MktAwayProb'] = 0.33
                
            features.append(feat)
            
        X = pd.DataFrame(features)
        res_map = {'H': 0, 'D': 1, 'A': 2}
        y = df['FTR'].map(res_map)
        
        valid_idx = y.notna()
        return X[valid_idx], y[valid_idx]

    def train(self):
        """Triggers the full ML pipeline."""
        df = self.load_data()
        X, y = self.prepare_features(df)
        if not X.empty:
            self.model.fit(X, y)
            self.is_trained = True
            return True
        return False

    def predict_match(self, home_team, away_team):
        """Infers results based on historical dominance and shot efficiency."""
        if not self.is_trained:
            self.train()
                
        if home_team not in self.team_encoder.classes_ or away_team not in self.team_encoder.classes_:
            return None
            
        # For prediction, we use the average market probability of these teams' history
        # (Since we don't have the "Live" odds input from user yet)
        x_infer = pd.DataFrame([{
            'HomeTeamEnc': self.team_encoder.transform([home_team])[0],
            'AwayTeamEnc': self.team_encoder.transform([away_team])[0],
            'HomeAtt': self.team_stats[home_team]['att'],
            'HomeDef': self.team_stats[home_team]['def'],
            'AwayAtt': self.team_stats[away_team]['att'],
            'AwayDef': self.team_stats[away_team]['def'],
            'HomeShotAcc': self.team_stats[home_team]['shot_acc'],
            'AwayShotAcc': self.team_stats[away_team]['shot_acc'],
            'HomeCorners': self.team_stats[home_team]['corners'],
            'AwayCorners': self.team_stats[away_team]['corners'],
            'MktHomeProb': 0.4, # Default neutral-ish priors
            'MktDrawProb': 0.25,
            'MktAwayProb': 0.35
        }])
        
        probs = self.model.predict_proba(x_infer)[0]
        return {
            'Home Win': round(probs[0] * 100, 1),
            'Draw': round(probs[1] * 100, 1),
            'Away Win': round(probs[2] * 100, 1)
        }

@st.cache_resource
def get_match_predictor():
    predictor = MatchPredictor(data_dir="data")
    predictor.train()
    return predictor
