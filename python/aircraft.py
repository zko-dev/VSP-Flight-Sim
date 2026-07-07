from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class SolverConfig:
    root: Path
    case_name: str

    omp_threads: int = 8
    wake_nodes: int = 16
    wake_iters: int = 8
    convergence_target: float = 1e3 #this is obsurdly high 

def load_aircraft_config(config_path):   #Load from YAML
    config_path = Path(config_path)
    with open(config_path, 'r') as f:
        aircraft = yaml.safe_load(f)
    return aircraft