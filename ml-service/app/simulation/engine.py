import simpy
import datetime
from app.simulation.state import TwinState
from app.simulation.core import build_graph

class ScarletSimulation:
    def __init__(self, env: simpy.Environment, db_kwargs: dict, start_date: datetime.datetime):
        self.env = env
        self.db_kwargs = db_kwargs
        self.state = TwinState(current_time=start_date)
        self.graph = build_graph(db_kwargs)
        self.metrics = {"demand_generated": 0, "orders_fulfilled": 0, "shipments_sent": 0}
        
        # Start processes
        self.env.process(self.daily_loop())

    def daily_loop(self):
        while True:
            # 1. Update clock
            self.state.current_time += datetime.timedelta(days=1)
            
            # 2. Simulate Demand
            self.simulate_demand()
            
            # 3. Simulate Shipments & Receiving
            self.simulate_shipments()
            
            yield self.env.timeout(1) # wait 1 day

    def simulate_demand(self):
        # Simplified demand generation
        self.metrics["demand_generated"] += 10
        # Check inventory, fulfill if possible
        # This is deterministic based on the seed
        pass

    def simulate_shipments(self):
        self.metrics["shipments_sent"] += 2
        pass

def run_simulation(db_kwargs: dict, days: int = 7):
    env = simpy.Environment()
    start_date = datetime.datetime.now()
    sim = ScarletSimulation(env, db_kwargs, start_date)
    env.run(until=days)
    return sim.metrics
