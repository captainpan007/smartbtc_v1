# ai_model.py

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score
import joblib
from utils.indicators import calculate_rsi, calculate_bollinger_bands, calculate_adx, detect_hammer, detect_doji, detect_engulfing, calculate_pattern_probability, calc_macd, calc_stochrsi

class AIPredictor:
    def __init__(self, data_path="core/data/historical/BTCUSDT_4h.csv", model_path="models/xgboost_model.pkl", window_size=180):
        self.data_path = data_path
        self.model_path = model_path
        self.window_size = window_size
        self.model = None
        self.scaler = MinMaxScaler()
        self.df = None

    def load_data(self):
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def prepare_features(self, df=None):
        if df is None:
            if self.df is None:
                self.load_data()
            df = self.df.copy()
        else:
            df = df.copy()

        # 计算特征
        df['rsi'] = calculate_rsi(df['close'], window=14)
        df = calculate_bollinger_bands(df, window=20)
        df['bb_width'] = (df['upper'] - df['lower']) / df['ma']
        df['adx'] = calculate_adx(df)
        df['volume_change'] = df['volume'] / df['volume'].shift(1)
        df['macd'], df['macd_signal'], _ = calc_macd(df['close'])
        df['stoch_rsi'] = calc_stochrsi(df['close'])
        df['hammer_up_prob'], _ = calculate_pattern_probability(df, detect_hammer, lookback=5)
        df['doji_up_prob'], _ = calculate_pattern_probability(df, detect_doji, lookback=5)
        df['engulfing_up_prob'], _ = calculate_pattern_probability(df, lambda d: detect_engulfing(d)[0] and detect_engulfing(d)[1] == "bullish", lookback=5)
        df['trend'] = df['close'].pct_change(5).shift(1)
        df['volume_trend'] = df['volume'].pct_change(5).shift(1)
        df['volatility'] = df['close'].rolling(20).std()
        df['price_range'] = (df['high'] - df['low']) / df['close']

        # 标签：未来5根K线的涨跌分类
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1
        df['label'] = (df['future_return'] > 0).astype(int)

        return df

    def train_rolling(self, df):
        if len(df) < self.window_size + 5:
            print("Not enough data for training")
            return False

        df = self.prepare_features(df.iloc[-self.window_size:])
        features = ['rsi', 'bb_width', 'adx', 'volume_change', 'macd', 'stoch_rsi', 'hammer_up_prob', 'engulfing_up_prob', 'trend', 'volume_trend', 'volatility', 'price_range']
        X = df[features].dropna()
        y = df['label'].loc[X.index]

        if len(X) < 50:
            print("Not enough data points for training after feature preparation")
            return False

        X_scaled = self.scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        self.model = xgb.XGBClassifier(max_depth=5, n_estimators=100, random_state=42)
        self.model.fit(X_scaled, y)

        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, "models/scaler.pkl")
        return True

    def predict(self, df):
        if self.model is None:
            print("No model found, training with rolling window...")
            self.train_rolling(df)

        df = self.prepare_features(df)
        features = ['rsi', 'bb_width', 'adx', 'volume_change', 'macd', 'stoch_rsi', 'hammer_up_prob', 'engulfing_up_prob', 'trend', 'volume_trend', 'volatility', 'price_range']
        X = df[features].iloc[-1:]

        if self.model is None:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load("models/scaler.pkl")

        X_scaled = self.scaler.transform(X)
        prediction = self.model.predict(X_scaled)[0]
        prob = self.model.predict_proba(X_scaled)[0]
        confidence = prob[1] if prediction == 1 else prob[0]
        return prediction, confidence

if __name__ == "__main__":
    predictor = AIPredictor()
    predictor.load_data()
    predictor.train_rolling(predictor.df)