# NEXORA-CDI Research Specification

## Problem statement

Business analytics systems often produce persuasive recommendations from correlations, incomplete data, or uncalibrated model outputs. NEXORA-CDI investigates an evidence-calibrated decision system that integrates predictive modelling, causal inference, counterfactual analysis, uncertainty calibration, selective abstention, and provenance so that recommendations are reliable, traceable, and appropriately limited.

## Research questions

- **RQ1:** Does combining predictive ML with causal inference improve decision quality over traditional analytics and ML-only systems?
- **RQ2:** Do counterfactual analyses improve the actionability and faithfulness of business recommendations?
- **RQ3:** Does uncertainty calibration improve the reliability of confidence communicated to decision-makers?
- **RQ4:** Does selective abstention reduce harmful or unsupported recommendations under weak evidence?
- **RQ5:** Does evidence provenance improve auditability, trust, and reproducibility of recommendations?
- **RQ6:** How does the integrated system compare with LLM-only analytical workflows on factual grounding and decision reliability?

## Architecture

The monorepo separates a Next.js TypeScript frontend, FastAPI backend, PostgreSQL persistence layer, and future domain modules for ML, causal inference, counterfactuals, reliability, provenance, agents, benchmarking, and experiments. The backend is the boundary for validated analytical evidence; the frontend presents only API-delivered evidence and decision states.

## Major components

- `frontend/`: decision workspace UI and typed API client.
- `backend/`: API, persistence, validation, logging, and error handling.
- `ml/`: predictive modelling and feature-attribution workflows.
- `causal/`: causal graph and treatment-effect workflows, distinct from correlation analysis.
- `counterfactual/`: feasible what-if and recourse analysis.
- `reliability/`: calibration, confidence, and abstention policies.
- `provenance/`: source, computation, and version traceability.
- `agents/`: evidence-bounded explanation and orchestration layer.
- `benchmark/` and `experiments/`: baselines, evaluation protocols, and reproducible results.

## Research constraints

No layer may invent numerical evidence. Analytical, ML, causal, and counterfactual results must be computed, versioned, and traceable. Correlation claims must not be represented as causal effects. LLMs may explain validated artifacts but may not produce unsupported metrics, effect sizes, confidence values, or recommendations.

## Evidence-first rule

Every externally presented numerical statement and recommendation must be linked to validated computed evidence and its provenance. Missing, stale, conflicting, or insufficient evidence must be visible to the decision workflow.

## Abstention requirement

When evidence quality, uncertainty calibration, causal identification, or data coverage does not meet the configured reliability threshold, the system must abstain or request additional evidence rather than issue a definitive decision recommendation.

## Experimental baseline requirements

Experiments must compare the integrated system with at least traditional descriptive analytics, predictive ML-only, and LLM-only baselines. Evaluations must report reproducible datasets/splits, metric definitions, uncertainty treatment, abstention behavior, provenance coverage, and failure cases. Metrics must be computed from recorded experiment outputs, never manually asserted.
