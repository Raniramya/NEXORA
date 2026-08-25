import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[2]))
from benchmark.BIDecisionBench.generator import cases,generate
def test_benchmark_determinism():
 assert generate(1,10).equals(generate(1,10)); assert len(cases(1,180))==180
