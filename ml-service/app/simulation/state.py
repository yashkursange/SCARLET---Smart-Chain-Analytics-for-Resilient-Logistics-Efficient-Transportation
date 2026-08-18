from dataclasses import dataclass, field
from typing import Dict, List, Any
import datetime

@dataclass
class TwinState:
    current_time: datetime.datetime
    nodes: Dict[str, Any] = field(default_factory=dict)
    inventory: Dict[str, Dict[str, float]] = field(default_factory=dict) # node_id -> product_id -> available_quantity
    orders: Dict[str, Any] = field(default_factory=dict)
    shipments: Dict[str, Any] = field(default_factory=dict)
    vehicles: Dict[str, Any] = field(default_factory=dict)
    demand: Dict[str, Any] = field(default_factory=dict)
    
    def copy(self):
        # Implement a deep enough copy for logging state
        import copy
        return copy.deepcopy(self)
