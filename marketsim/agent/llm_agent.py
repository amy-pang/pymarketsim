import os
import random
from marketsim.agent.agent import Agent
from marketsim.market.market import Market
from marketsim.fourheap.order import Order
from marketsim.private_values.private_values import PrivateValues
from marketsim.fourheap.constants import BUY, SELL
from dotenv import load_dotenv
from together import Together

class LLMAgent(Agent):
    def __init__(self, agent_id: int, market: Market, q_max: int):
        self.agent_id = agent_id
        self.market = market
        self.q_max = q_max

        load_dotenv()
        self.api_key = os.getenv('LLAMA_API_KEY')
        self.client = Together(api_key=self.api_key)

    def get_llm_response(self, prompt: str) -> str:
        """Get response from LLM."""
        response = self.client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    def get_id(self) -> int:
        return self.agent_id
    
    def take_action(self, side):
        """Submits order to market for HBL?"""
        t = self.market.get_time()
        estimate = self.estimate_fundamental()
        spread = self.shade[1] - self.shade[0]
        price = estimate + side*spread*random.random() + self.shade[0]

        return Order(
            price=price,
            quantity=1,
            agent_id=self.get_id(),
            time=t,
            order_type=side,
            order_id=random.randint(1, 10000000)
                     )
    
    def update_position(self, q, p):
        self.position += q
        self.cash += p

    def __str__(self):
        return f'ZI{self.agent_id}'
        
    def get_pos_value(self) -> float:
        return self.pv.value_at_position(self.position)
    
    def reset(self):
        self.position = 0
        self.cash = 0
        # ? : self.pv = PrivateValues(self.q_max, self.pv_var) 