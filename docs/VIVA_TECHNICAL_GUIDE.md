# Viva Technical Guide

NEXORA-CDI separates descriptive analytics, prediction, causal estimation, reliability, and explanation. Datasets are stored unchanged; derived cleaned previews do not overwrite source files. ML uses seeded sklearn train/test pipelines. Causal analysis validates a supplied DAG and reports linear-regression-adjustment assumptions, confidence intervals, p-values, and warnings. Reliability keeps ECDS `UNCALIBRATED` without labeled calibration history. The deterministic investigator respects `ABSTAIN` and cites generated evidence IDs; it is not an external LLM integration.
