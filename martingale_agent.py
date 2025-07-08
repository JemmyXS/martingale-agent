import os
import requests
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env.eth")
API_KEY = os.getenv("RECALL_API_KEY")
API_URL = os.getenv("RECALL_API_URL")
if not API_KEY:
    raise ValueError("RECALL_API_KEY not set in .env")

class TradingClient:
    def __init__(self, api_key, api_url):
        self.client = requests.Session()
        self.client.headers.update(
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )
        self.base_url = api_url

    def get_token_price(self, token_address, chain=None, specific_chain=None):
        params = {
            "token": token_address,
            "chain": chain,
            "specificChain": specific_chain,
        }
        response = self.client.get(f"{self.base_url}/price", params=params)
        return response.json()

    def execute_trade(self, from_token, to_token, amount, from_chain=None, to_chain=None, reason=None):
        trade = {
            "fromToken": from_token,
            "toToken": to_token,
            "amount": str(amount),
            "reason": reason or "Martingale Strategy",
            "fromChain": from_chain,
            "toChain": to_chain,
        }
        try:
            response = self.client.post(f"{self.base_url}/trade/execute", json=trade)
            return response.json()
        except requests.exceptions.RequestException as error:
            if error.response:
                raise Exception(
                    f"Trade failed: {error.response.json()['error']['message']}"
                )
            raise error

    def get_portfolio(self):
        response = self.client.get(f"{self.base_url}/agent/portfolio")
        return response.json()

# 策略参数
FROM_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"   # USDC
TO_TOKEN = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"     # WETH

BASE_AMOUNT = 20              # 每次马丁格尔的初始下单额
MAX_TOTAL_AMOUNT = 100        # 总资金上限
MAX_STEPS = 5                 # 最多加仓次数
SLEEP_SEC = 10

class MartingaleAgent:
    def __init__(self):
        self.trader = TradingClient(API_KEY, API_URL)
        self.reset()

    def reset(self):
        self.level = 0
        self.entry_price = None
        self.last_order_price = None
        self.total_amount = 0     # 累计投入的USDC
        self.total_token = 0      # 累计买入WETH数量

    def get_price(self):
        result = self.trader.get_token_price(TO_TOKEN)
        try:
            return float(result["price"])
        except Exception as e:
            print("获取价格失败:", e, result)
            return None

    def generate_reason(self, action_type, current_price, amount, level=None, avg_cost=None, price_change=None):
        """生成详细的交易推理过程描述"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if action_type == "initial_buy":
            reason = f"""
【马丁格尔策略 - 初始建仓】{timestamp}
📊 当前WETH价格: ${current_price:.4f}
💰 下单金额: {amount} USDC
🎯 策略逻辑: 执行马丁格尔策略初始建仓，在价格${current_price:.4f}时买入WETH
📈 预期收益: 价格反弹时通过分批加仓降低平均成本
⚠️ 风险提示: 马丁格尔策略具有资金风险，最大加仓次数{MAX_STEPS}次，总资金上限{MAX_TOTAL_AMOUNT} USDC
🔍 市场分析: 当前价格作为基准价格，后续加仓将基于此价格计算跌幅
"""
        
        elif action_type == "martingale_buy":
            price_drop = ((self.last_order_price - current_price) / self.last_order_price) * 100
            reason = f"""
【马丁格尔策略 - 第{level}层加仓】{timestamp}
📊 当前WETH价格: ${current_price:.4f}
📉 价格跌幅: {price_drop:.2f}% (从${self.last_order_price:.4f}下跌至${current_price:.4f})
💰 下单金额: {amount} USDC (第{level}层加仓，金额为初始金额的{2**level}倍)
📊 累计投入: {self.total_amount} USDC
🎯 策略逻辑: 价格下跌超过0.2%，执行马丁格尔加仓策略，通过加倍投入降低平均成本
📈 成本分析: 当前持仓均价${avg_cost:.4f}，新订单将帮助进一步降低平均成本
⚠️ 风险控制: 已加仓{level}次，剩余加仓次数{MAX_STEPS-level}次，剩余资金{MAX_TOTAL_AMOUNT-self.total_amount} USDC
🔍 技术分析: 价格跌破上次买入价格0.2%触发点，符合加仓条件
"""
        
        elif action_type == "take_profit":
            profit_percentage = ((current_price - avg_cost) / avg_cost) * 100
            reason = f"""
【马丁格尔策略 - 止盈平仓】{timestamp}
📊 当前WETH价格: ${current_price:.4f}
📈 持仓均价: ${avg_cost:.4f}
💰 盈利比例: {profit_percentage:.2f}%
🎯 策略逻辑: 当前价格${current_price:.4f}高于持仓均价${avg_cost:.4f}的2%，达到止盈条件
📊 交易统计: 累计投入{self.total_amount} USDC，累计买入{self.total_token:.6f} WETH
✅ 策略结果: 马丁格尔策略成功，通过分批加仓在价格反弹时获得盈利
🔍 市场分析: 价格反弹超过2%止盈线，策略目标达成
"""
        
        elif action_type == "stop_loss":
            loss_percentage = ((current_price - avg_cost) / avg_cost) * 100
            reason = f"""
【马丁格尔策略 - 止损平仓】{timestamp}
📊 当前WETH价格: ${current_price:.4f}
📉 持仓均价: ${avg_cost:.4f}
💰 亏损比例: {loss_percentage:.2f}%
🎯 策略逻辑: 当前价格${current_price:.4f}低于持仓均价${avg_cost:.4f}的5%，触发止损条件
📊 交易统计: 累计投入{self.total_amount} USDC，累计买入{self.total_token:.6f} WETH
⚠️ 风险控制: 价格持续下跌超过5%止损线，执行风险控制措施
🔍 市场分析: 市场趋势不利，及时止损避免更大损失
"""
        
        else:
            reason = f"Martingale Strategy - {action_type} at ${current_price:.4f}"
        
        return reason.strip()

    def place_order(self, amount, action_type="martingale_buy"):
        # 限制总资金
        if self.total_amount + amount > MAX_TOTAL_AMOUNT:
            amount = MAX_TOTAL_AMOUNT - self.total_amount
            if amount <= 0:
                print("已经达到总资金上限，无法继续加仓。")
                return
        
        current_price = self.get_price()
        if current_price is None:
            print("无法获取当前价格，取消下单")
            return
            
        avg_cost = self.get_avg_cost()
        
        # 生成详细的推理过程
        reason = self.generate_reason(
            action_type=action_type,
            current_price=current_price,
            amount=amount,
            level=self.level,
            avg_cost=avg_cost
        )
        
        print(f"⏳ 开始第{self.level}层加仓，下单 USDC 数量: {amount}")
        print(f"📝 交易理由:\n{reason}")
        
        try:
            resp = self.trader.execute_trade(
                FROM_TOKEN, TO_TOKEN, amount, reason=reason
            )
            print("✅  下单结果:", resp)
            # 兼容 resp['toAmount'] 和 resp['transaction']['toAmount']
            token_bought = 0
            if "toAmount" in resp:
                token_bought = float(resp.get("toAmount", 0))
            elif "transaction" in resp and "toAmount" in resp["transaction"]:
                token_bought = float(resp["transaction"]["toAmount"])
            self.total_amount += amount
            self.total_token += token_bought
            print(f"累计买入WETH: {self.total_token}, 累计花费USDC: {self.total_amount}")
        except Exception as e:
            print("❌  下单失败:", e)

    def get_avg_cost(self):
        if self.total_token > 0:
            return self.total_amount / self.total_token
        return None

    def close_position(self, action_type="take_profit"):
        try:
            portfolio = self.trader.get_portfolio()
        except Exception as e:
            print("❌ 查询持仓失败:", e)
            return

        to_token_balance = 0
        assets = portfolio.get("tokens", []) if isinstance(portfolio, dict) else []
        for asset in assets:
            token_addr = asset.get("token", "").lower()
            if token_addr == TO_TOKEN.lower():
                to_token_balance = float(asset.get("amount", 0))
                break

        if to_token_balance > 0:
            current_price = self.get_price()
            avg_cost = self.get_avg_cost()
            
            # 生成平仓的详细推理过程
            reason = self.generate_reason(
                action_type=action_type,
                current_price=current_price,
                amount=to_token_balance,
                avg_cost=avg_cost
            )
            
            print(f"🪙 平仓，卖出 WETH 数量: {to_token_balance}")
            print(f"📝 平仓理由:\n{reason}")
            
            try:
                result = self.trader.execute_trade(
                    TO_TOKEN, FROM_TOKEN, to_token_balance, reason=reason
                )
                print("✅ 平仓结果:", result)
            except Exception as e:
                print("❌ 平仓失败:", e)
        else:
            print("没有可平仓的 WETH 持仓")

    def run_one_cycle(self):
        print("🚦 启动马丁格尔策略 Agent")
        while self.level < MAX_STEPS:
            price = self.get_price()
            if price is None:
                print("无法获取价格，重试中...")
                time.sleep(SLEEP_SEC)
                continue

            if self.level == 0:
                self.entry_price = price
                self.last_order_price = price
                amount = BASE_AMOUNT
                self.place_order(amount, "initial_buy")
                self.level += 1
                print(f"等待下一轮观察价格...（{SLEEP_SEC}秒）")
                time.sleep(SLEEP_SEC)
                continue

            if price < self.last_order_price * 0.998:
                amount = BASE_AMOUNT * (2 ** self.level)
                self.place_order(amount, "martingale_buy")
                self.last_order_price = price
                self.level += 1
                print(f"等待下一轮观察价格...（{SLEEP_SEC}秒）")
                time.sleep(SLEEP_SEC)
            else:
                avg_cost = self.get_avg_cost()
                avg_cost_str = f"{avg_cost:.6f}" if avg_cost else "None"
                # 止盈（2%）或止损（-5%）判断
                if avg_cost and price >= avg_cost * 1.02:
                    self.close_position("take_profit")
                    print(f"🎉 当前价格 {price} 高于持仓均价2% {avg_cost * 1.02}，盈利平仓，策略结束。")
                    return True
                elif avg_cost and price <= avg_cost * 0.95:
                    self.close_position("stop_loss")
                    print(f"⚠️ 当前价格 {price} 低于持仓均价5% {avg_cost * 0.95}，止损平仓，策略结束。")
                    return False
                else:
                    print(f"价格未下跌0.2%，当前价格: {price}, 上次下单价: {self.last_order_price}，持仓均价: {avg_cost_str}")
                    time.sleep(SLEEP_SEC)
        else:
            print("已达最大加仓次数，策略终止。")
        return False

    def run(self):
        while True:
            self.reset()
            res = self.run_one_cycle()
            if res:
                print("🔄 策略已盈利平仓，重新开启新一轮...")
            else:
                print("❌ 策略终止或止损，等待人工介入或重启。")
                break

if __name__ == "__main__":
    agent = MartingaleAgent()
    agent.run()
