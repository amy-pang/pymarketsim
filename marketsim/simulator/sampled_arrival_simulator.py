import random
from marketsim.fourheap.constants import BUY, SELL
from marketsim.market.market import Market
from marketsim.fundamental.lazy_mean_reverting import LazyGaussianMeanReverting
from marketsim.agent.zero_intelligence_agent import ZIAgent
import torch.distributions as dist
import torch
from collections import defaultdict


class SimulatorSampledArrival:
    def __init__(self,
                 num_background_agents: int,
                 sim_time: int,
                 num_assets: int = 1,
                 lam: float = 0.1,
                 mean: float = 100,
                 r: float = .05,
                 shock_var: float = 10,
                 q_max: int = 10,
                 pv_var: float = 5e6,
                 shade=None,
                 eta: float = 0.2
                 ):

        if shade is None:
            shade = [10, 30]
        self.num_agents = num_background_agents
        self.num_assets = num_assets
        self.sim_time = sim_time
        self.lam = lam
        self.time = 0

        self.arrivals = defaultdict(list)
        self.arrivals_sampled = 10000
        self.arrival_times = sample_arrivals(lam, self.arrivals_sampled)
        self.arrival_index = 0

        self.markets = []
        for _ in range(num_assets):
            fundamental = LazyGaussianMeanReverting(mean=mean, final_time=sim_time, r=r, shock_var=shock_var)
            self.markets.append(Market(fundamental=fundamental, time_steps=sim_time))

        self.agents = {}
        for agent_id in range(num_background_agents):
            self.arrivals[self.arrival_times[self.arrival_index].item()].append(agent_id)
            self.arrival_index += 1

            self.agents[agent_id] = (
                ZIAgent(
                    agent_id=agent_id,
                    market=self.markets[0],
                    q_max=q_max,
                    shade=shade,
                    pv_var=pv_var
                ))

    def step(self):
        agents = self.arrivals[self.time]
        if self.time < self.sim_time:
            for market in self.markets:
                market.event_queue.set_time(self.time)
                for agent_id in agents:
                    agent = self.agents[agent_id]
                    market.withdraw_all(agent_id)
                    side = random.choice([BUY, SELL])
                    orders = agent.take_action(side)
                    market.add_orders(orders)

                    if self.arrival_index == self.arrivals_sampled:
                        self.arrival_times = sample_arrivals(self.lam, self.arrivals_sampled)
                        self.arrival_index = 0
                    self.arrivals[self.arrival_times[self.arrival_index].item() + 1 + self.time].append(agent_id)
                    self.arrival_index += 1

                new_orders = market.step()
                for matched_order in new_orders:
                    agent_id = matched_order.order.agent_id
                    quantity = matched_order.order.order_type*matched_order.order.quantity
                    cash = -matched_order.price*matched_order.order.quantity*matched_order.order.order_type
                    self.agents[agent_id].update_position(quantity, cash)

        else:
            self.end_sim()

    def end_sim(self):
        fundamental_val = self.markets[0].get_final_fundamental()
        values = {}
        for agent_id in self.agents:
            agent = self.agents[agent_id]
            values[agent_id] = agent.get_pos_value() + agent.position*fundamental_val + agent.cash
        #print(f'At the end of the simulation we get {values}')
        return values

    def run(self):
        counter = 0
        for t in range(self.sim_time):
            if self.arrivals[t]:
                try:
                    # print(f'It is time {t}')
                    self.step()
                except KeyError:
                    print(self.arrivals[self.time])
                    return self.markets
                counter += 1
            self.time += 1
        self.step()


def sample_arrivals(p, num_samples):
    geometric_dist = dist.Geometric(torch.tensor([p]))
    return geometric_dist.sample((num_samples,)).squeeze()  # Returns a tensor of 1000 sampled time steps
