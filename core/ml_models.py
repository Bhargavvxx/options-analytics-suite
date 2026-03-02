import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


class StockPricePredictor:
    """
    Machine learning models for stock price prediction
    """
    def __init__(self):
        self.lr_model = None
        self.xgb_model = None
        self.lstm_model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.feature_cols = None
        self.metrics = {}  # Store train/test metrics

    def prepare_features(self, prices, n_features=5):
        """
        Prepare features for model training
        """
        # Handle DataFrame inputs
        if isinstance(prices, pd.DataFrame):
            prices = prices.squeeze()  # Convert to Series if single-column
        
        # Handle other input types
        if isinstance(prices, (float, int)):
            prices = pd.Series([prices])
        elif isinstance(prices, np.ndarray):
            prices = pd.Series(prices)
        elif not isinstance(prices, pd.Series):
            prices = pd.Series(prices)

        # Create technical indicators
        df = pd.DataFrame({'price': prices.values}, index=prices.index if hasattr(prices, 'index') else None)
        df['returns'] = df['price'].pct_change().fillna(0)
        df['ma5'] = df['price'].rolling(5).mean().bfill()
        df['ma20'] = df['price'].rolling(20).mean().bfill()
        df['ma50'] = df['price'].rolling(50).mean().bfill()
        df['volatility'] = df['returns'].rolling(21).std().fillna(0) * np.sqrt(252)
        df['momentum'] = (df['price'] / df['price'].shift(5) - 1).fillna(0)
        df['dist_ma20'] = (df['price'] / df['ma20'] - 1).fillna(0)
        df.dropna(inplace=True)
        self.feature_cols = ['ma5', 'ma20', 'ma50', 'volatility', 'momentum', 'dist_ma20', 'returns']
        return df

    def _train_test_split(self, features, target_col='price', test_ratio=0.2):
        """Split data into train and test sets (time-series aware, no shuffle)"""
        X = features[self.feature_cols].values
        y = features[target_col].values
        split_idx = int(len(X) * (1 - test_ratio))
        return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

    def train_linear_regression(self, features, target_col='price'):
        X_train, X_test, y_train, y_test = self._train_test_split(features, target_col)
        self.lr_model = LinearRegression()
        self.lr_model.fit(X_train, y_train)
        
        # Compute test metrics
        y_pred = self.lr_model.predict(X_test)
        self.metrics['lr'] = {
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred))
        }
        return self.lr_model

    def train_xgboost(self, features, target_col='price'):
        X_train, X_test, y_train, y_test = self._train_test_split(features, target_col)
        
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            objective='reg:squarederror',
            random_state=42
        )
        
        self.xgb_model.fit(X_train, y_train)
        
        # Compute test metrics
        y_pred = self.xgb_model.predict(X_test)
        self.metrics['xgb'] = {
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred))
        }
        return self.xgb_model

    def prepare_lstm_data(self, prices, time_steps=60):
        # Handle DataFrame inputs
        if isinstance(prices, pd.DataFrame):
            prices = prices.squeeze()
        
        # Scale the data
        scaled_data = self.scaler.fit_transform(prices.values.reshape(-1, 1))
        
        # Create sequences
        X, y = [], []
        for i in range(time_steps, len(scaled_data)):
            X.append(scaled_data[i-time_steps:i, 0])
            y.append(scaled_data[i, 0])
        X, y = np.array(X), np.array(y)
        X = X.reshape(X.shape[0], X.shape[1], 1)
        return X, y, scaled_data

    def train_lstm(self, prices, epochs=50, batch_size=32, time_steps=60):
        X, y, _ = self.prepare_lstm_data(prices, time_steps)
        
        # Time-series train/test split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        self.lstm_model = Sequential([ 
            LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(1)
        ])
        self.lstm_model.compile(optimizer='adam', loss='mean_squared_error')
        self.lstm_model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=0)
        
        # Compute test metrics (in original scale)
        y_pred_scaled = self.lstm_model.predict(X_test, verbose=0)
        y_pred = self.scaler.inverse_transform(y_pred_scaled).flatten()
        y_actual = self.scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
        self.metrics['lstm'] = {
            'mae': mean_absolute_error(y_actual, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_actual, y_pred))
        }
        return self.lstm_model

    def predict_next_price(self, prices):
        """
        Predict the next price using all trained models.
        
        Returns:
        --------
        results : dict
            Dictionary with model names as keys and predicted prices as values
        """
        results = {}
        # Handle DataFrame inputs
        if isinstance(prices, pd.DataFrame):
            prices = prices.squeeze()
        
        features = self.prepare_features(prices)
        
        # Linear Regression prediction
        if self.lr_model:
            X = features[self.feature_cols].iloc[-1:].values
            results['lr'] = float(self.lr_model.predict(X)[0])
        
        # XGBoost prediction
        if self.xgb_model:
            X = features[self.feature_cols].iloc[-1:].values
            results['xgb'] = float(self.xgb_model.predict(X)[0])
        
        # LSTM prediction
        if self.lstm_model and len(prices) > 60:
            _, _, scaled_data = self.prepare_lstm_data(prices)
            X = scaled_data[-60:].reshape(1, 60, 1)
            scaled_pred = self.lstm_model.predict(X, verbose=0)[0, 0]
            results['lstm'] = float(self.scaler.inverse_transform([[scaled_pred]])[0][0])
        
        # Ensemble prediction
        if len(results) >= 2:
            results['ensemble'] = float(np.mean(list(results.values())))
        
        return results