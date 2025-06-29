import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RECALL_API_KEY")
if not API_KEY:
    raise ValueError("RECALL_API_KEY not set in .env")

BASE_URL = os.getenv("RECALL_API_URL", "https://api.competitions.recall.network")
ENDPOINT = f"{BASE_URL}/sandbox/api/trade/execute"
PRICE_API = f"{BASE_URL}/sandbox/api/price"

FROM_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"   # USDC
TO_TOKEN = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"     # WETH

BASE_AMOUNT = 100
MAX_STEPS = 5
SLEEP_SEC = 10

class MartingaleAgent:
    def __init__(self):
        self.level = 0
        self.entry_price = None
        self.total_amount = 0

    def get_price(self):
        params = {"fromToken": FROM_TOKEN, "toToken": TO_TOKEN}
        headers = {"Authorization": f"Bearer {API_KEY}"}
        try:
            resp = requests.get(PRICE_API, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception as e:
            print("获取价格失败:", e)
            return None

    def place_order(self, amount):
        payload = {
            "fromToken": FROM_TOKEN,
            "toToken": TO_TOKEN,
            "amount": str(amount),
            "reason": f"Martingale step {self.level}"
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        print(f"⏳ 开始第{self.level}层加仓，下单USDC数量: {amount}")
        resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=30)
        if resp.ok:
            print("✅  下单成功:", resp.json())
        else:
            print("❌  下单失败", resp.status_code, resp.text)

    def run(self):
        print("🚦 启动马丁格尔策略 Agent")
        while self.level < MAX_STEPS:
            price = self.get_price()
            if price is None:
                print("无法获取价格，重试中...")
                time.sleep(SLEEP_SEC)
                continue

            if self.level == 0:
                self.entry_price = price
                amount = BASE_AMOUNT
            else:
                if price < self.entry_price:
                    amount = BASE_AMOUNT * (2 ** self.level)
                else:
                    print(f"🎉 当前价格{price}高于入场价{self.entry_price}，盈利平仓，策略结束。")
                    break

            self.place_order(amount)
            self.total_amount += amount
            self.level += 1
            print(f"等待下一轮观察价格...（{SLEEP_SEC}秒）")
            time.sleep(SLEEP_SEC)
        else:
            print("已达最大加仓次数，策略终止。")

if __name__ == "__main__":
    agent = MartingaleAgent()
    agent.run()
