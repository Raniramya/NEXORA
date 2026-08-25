# Experiment Guide

Run from `backend/` after installing `requirements.txt`:

`python ../experiments/run_all.py --smoke --seed 42`

Use the same command without `--smoke` for the current deterministic benchmark case set. Output is written to `experiments/results/`, which is excluded from source control. Results are generated at execution time; this repository contains no experimental conclusions. The current runner is a smoke scaffold and does not yet execute the complete requested baseline and ablation matrix.
