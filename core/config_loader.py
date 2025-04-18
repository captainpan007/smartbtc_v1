# core/config_loader.py
import yaml
import os

DEFAULT_CONFIG = {
    "binance": {
        "api_key": "YOUR_BINANCE_API_KEY",
        "api_secret": "YOUR_BINANCE_API_SECRET",
        "commission_rate": 0.00075 # 手续费率 (可根据实际情况调整, 如使用BNB抵扣)
    },
    "risk": {
        "initial_balance": 10000.0, # 初始模拟资金
        "sl_atr_multiplier": 2.0,  # ATR 止损倍数
        "tp_atr_multiplier": 3.0,  # ATR 止盈倍数 (新增)
        "max_drawdown_pct": 0.20,  # 最大回撤容忍度
        "max_position_risk_pct": 0.02 # 单笔交易最大风险敞口（占总资金）
    },
    "telegram": {
        "enabled": False, # 是否启用 Telegram 通知
        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_TELEGRAM_CHAT_ID"
    },
    "strategy_params": { # 新增: 策略参数示例
        "rsi_period": 14,
        "rsi_low": 35,
        "rsi_high": 65,
        "ma_short": 10,
        "ma_long": 30,
        "adx_threshold": 25
        # ... 可添加更多策略参数 ...
    },
    "ai_model": { # 新增: AI模型相关配置
        "model_path": "models/xgboost_model.pkl",
        "scaler_path": "models/scaler.pkl",
        "window_size": 180,
        "confidence_threshold": 0.6 # AI 预测置信度阈值示例
    },
     "trading": { # 新增：交易相关配置
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "slippage_base_rate": 0.0005 # 基础滑点率
    }
}

def load_config(path="config/settings.yaml"):
    """
    加载配置。如果文件不存在或无法解析，则返回默认配置。
    """
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)
                # 可以考虑在这里合并默认配置和加载的配置，以确保所有键都存在
                # 但为了简单起见，这里仅加载文件内容
                return loaded_config
        except Exception as e:
            print(f"[Config] 无法加载配置文件 '{path}': {e}. 使用默认配置。")
            return DEFAULT_CONFIG
    else:
        print(f"[Config] 配置文件 '{path}' 不存在. 使用默认配置。")
        # 首次运行时可以考虑保存一份默认配置文件
        # try:
        #     os.makedirs(os.path.dirname(path), exist_ok=True)
        #     with open(path, "w", encoding="utf-8") as f:
        #         yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True)
        #     print(f"[Config] 已在 '{path}' 创建默认配置文件。请填入您的 API 密钥等信息。")
        # except Exception as e:
        #      print(f"[Config] 创建默认配置文件失败: {e}")
        return DEFAULT_CONFIG

# 在其他模块中这样使用:
# from core.config_loader import load_config
# config = load_config()
# api_key = config.get("binance", {}).get("api_key")
# initial_balance = config.get("risk", {}).get("initial_balance", 10000.0)