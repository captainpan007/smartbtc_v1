# ✅ 通知模块：core/notifier.py
# 功能：通过 Telegram Bot 向群组或个人发送交易信号或警报


# core/notifier.py

from core.config_loader import load_config
import requests

class Notifier:
    def __init__(self, config=None, enabled=True):
        self.enabled = enabled
        cfg = load_config().get("telegram", {})
        self.token = cfg.get("bot_token", "")
        self.chat_id = cfg.get("chat_id", "")
        
        if config is not None:
            self.token = config.get("notifier", {}).get("telegram_token")
            self.chat_id = config.get("notifier", {}).get("chat_id")

    def notify(self, message):
        if not self.enabled or not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            print(f"[Notifier] ❌ Telegram Error: {e}")

