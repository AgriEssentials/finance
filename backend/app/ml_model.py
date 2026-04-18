"""
Machine Learning Module
Handles model training, saving, loading, and prediction
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib
import os
from typing import Dict, Any, Tuple
from datetime import datetime


class StockPredictor:
    """Class to handle ML predictions for stock price movement"""
    
    def __init__(self, mode: str = 'intraday'):
        """
        Initialize predictor
        
        Args:
            mode: 'intraday', 'swing', or 'longterm'
        """
        self.mode = mode
        self.model = None
        self.scaler = StandardScaler()
        
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to backend/, then to models/
        models_dir = os.path.join(os.path.dirname(current_dir), 'models')
        
        self.model_path = os.path.join(models_dir, f"{mode}_model.pkl")
        self.scaler_path = os.path.join(models_dir, f"{mode}_scaler.pkl")
        self.is_trained = False
        
        # Try to load existing model
        self.load_model()
    
    def prepare_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Prepare target variable for training
        
        Args:
            df: DataFrame with Close prices
            
        Returns:
            Series with target (1 if price goes up, 0 otherwise)
        """
        if self.mode == 'intraday':
            # Target: next 3 candles close higher
            future_return = df['Close'].shift(-3) / df['Close'] - 1
            target = (future_return > 0).astype(int)
        else:
            # Target: next 3-5 days close higher
            future_return = df['Close'].shift(-5) / df['Close'] - 1
            target = (future_return > 0).astype(int)
        
        return target
    
    def train(self, features: pd.DataFrame, target: pd.Series) -> Dict[str, Any]:
        """
        Train the model
        
        Args:
            features: DataFrame with feature columns
            target: Series with target values
            
        Returns:
            Dictionary with training metrics
        """
        # Remove NaN values
        mask = ~(features.isna().any(axis=1) | target.isna())
        features_clean = features[mask]
        target_clean = target[mask]
        
        if len(features_clean) < 50:
            return {
                "success": False,
                "error": "Insufficient data for training (minimum 50 samples required)"
            }
        
        # Scale features
        X_scaled = self.scaler.fit_transform(features_clean)
        
        # Train model
        self.model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_scaled, target_clean)
        
        # Calculate training accuracy
        train_accuracy = self.model.score(X_scaled, target_clean)
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        return {
            "success": True,
            "training_samples": len(features_clean),
            "accuracy": round(train_accuracy, 4),
            "mode": self.mode,
            "feature_importance": dict(zip(
                features.columns,
                self.model.coef_[0].tolist()
            ))
        }
    
    def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Make prediction
        
        Args:
            features: DataFrame with feature columns (single row or multiple)
            
        Returns:
            Dictionary with prediction results
        """
        if not self.is_trained or self.model is None:
            # Return neutral prediction if model not trained
            return {
                "up_probability": 0.5,
                "prediction": "Neutral",
                "confidence": "Low",
                "model_trained": False
            }
        
        # Ensure features is 2D DataFrame with proper column names
        if len(features.shape) == 1:
            # Convert Series to DataFrame with feature names
            feature_names = self.get_feature_names()
            X = pd.DataFrame([features.values], columns=feature_names)
        else:
            X = features
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Get probability
        probabilities = self.model.predict_proba(X_scaled)
        up_prob = probabilities[0][1]  # Probability of class 1 (up)
        
        # Determine prediction and confidence
        if up_prob > 0.6:
            prediction = "Up"
            confidence = "High" if up_prob > 0.7 else "Medium"
        elif up_prob < 0.4:
            prediction = "Down"
            confidence = "High" if up_prob < 0.3 else "Medium"
        else:
            prediction = "Neutral"
            confidence = "Low"
        
        return {
            "up_probability": round(up_prob * 100, 2),
            "prediction": prediction,
            "confidence": confidence,
            "model_trained": True
        }
    
    def save_model(self):
        """Save model and scaler to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
    
    def load_model(self):
        """Load model and scaler from disk"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
        except Exception as e:
            print(f"Could not load model: {e}")
            self.is_trained = False
    
    def get_feature_names(self) -> list:
        """Get list of feature names expected by the model"""
        return ['rsi', 'macd_histogram', 'volume_ratio', 'atr', 'ema_diff']


def train_model_for_symbol(symbol: str, df: pd.DataFrame, mode: str) -> Dict[str, Any]:
    """
    Train model for a specific symbol
    
    Args:
        symbol: Stock symbol
        df: DataFrame with historical data and indicators
        mode: 'intraday', 'swing', or 'longterm'
        
    Returns:
        Training results
    """
    from app.indicators import prepare_ml_features
    
    # Prepare features
    features = prepare_ml_features(df, mode)
    
    # Initialize predictor
    predictor = StockPredictor(mode)
    
    # Prepare target
    target = predictor.prepare_target(df)
    
    # Train
    result = predictor.train(features, target)
    result['symbol'] = symbol
    result['timestamp'] = datetime.now().isoformat()
    
    return result


# Global predictor instances
predictors = {
    'intraday': StockPredictor('intraday'),
    'swing': StockPredictor('swing'),
    'longterm': StockPredictor('longterm')
}