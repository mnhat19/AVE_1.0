from .phase1_001 import apply as apply_001_phase1
from .phase3_001 import apply as apply_001_phase3


def run_migrations(engine) -> None:
    apply_001_phase1(engine)
    apply_001_phase3(engine)
