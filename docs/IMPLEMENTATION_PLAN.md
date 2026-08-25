# NEXORA-CDI Phased Implementation Plan

## Delivery rule

NEXORA is implemented as verified vertical phases. A phase is complete only when its database schema, backend service, API contract, frontend workflow, provenance, targeted tests, and documentation are integrated. Later phases may consume earlier evidence, but they may not replace observed or computed values with demonstrations or hard-coded results.

## Phase map

| Phase | Scope | Primary output | Exit gate | Status |
|---|---|---|---|---|
| 1 | Platform and physical-evidence foundation | Asset registry; multimodal telemetry; fault and intervention records | Migrated schema, validated API, usable UI, API workflow test | Complete |
| 2 | Edge ingestion and signal processing | ESP32 HTTP contract; raw-window storage; filtering; RMS, FFT and spectral features | Recorded raw window reproducibly generates versioned features | Complete |
| 3 | Fault pattern recognition | Dataset/window labelling; RF, SVM and XGBoost baselines; optional 1D-CNN | Reproducible splits, computed metrics and serialized model versions | Complete |
| 4 | Explainability and anomaly detection | SHAP evidence; Isolation Forest unknown-condition detection | Attributions link to a model run; anomaly output is not called a fault class | Complete |
| 5 | Causal and counterfactual maintenance | Maintenance DAG; identification checks; treatment effects; feasible intervention scenarios | Causal claims expose assumptions and abstain when unidentified | Complete |
| 6 | Uncertainty and selective prediction | Calibration; conformal prediction; OOD checks; ACT/MONITOR/ABSTAIN policy | Coverage and abstention metrics are computed from held-out evidence | Complete |
| 7 | Geospatial asset intelligence | Asset map; Haversine distance; DBSCAN hotspot analysis | Spatial clusters remain distinct from causal explanations | Complete |
| 8 | Multi-objective maintenance optimization | NSGA-II schedule across risk, cost, downtime, travel and causal benefit | Pareto set compared with greedy and conventional baselines | Complete |
| 9 | Integrated decision workflow | Evidence graph from telemetry through decision; investigator explanation | Every recommendation is traceable; weak evidence produces abstention | Complete |
| 10 | Physical validation and research evaluation | Controlled faults/interventions; predicted-versus-observed effects; benchmark and ablations | Reproducible experiment artifacts support every reported result | Complete |

## Phase 1 — platform and physical-evidence foundation

### Implemented

- FastAPI and PostgreSQL application foundation with health/readiness boundaries.
- Machine registry with optional geospatial coordinates.
- Timestamped vibration RMS, temperature, current, RPM, and extensible feature records.
- Fault-event records that distinguish observed/classified events from causal conclusions.
- Maintenance-action records with separate predicted and observed benefit fields.
- Assets & Telemetry workspace for manual test-bench integration.
- Targeted end-to-end API workflow test.

### Acceptance criteria

- A machine can be registered and retrieved.
- At least one measured channel is required for a telemetry record.
- An unknown machine cannot receive telemetry, a fault event, or an action.
- Confidence values are constrained to the interval `[0, 1]`.
- New and existing databases receive the maintenance schema through Alembic.
- The frontend compiles and exposes `/assets` without fabricated readings.

## Phase 2 — edge ingestion and signal processing

### Implemented

- Optional token-protected ESP32 HTTP ingestion using `X-Nexora-Edge-Token` and `NEXORA_EDGE_INGEST_TOKEN`.
- Raw signal-window persistence with sample rate, channel, unit, device, source, and acquisition metadata.
- Deterministic moving-average filtering configuration.
- Mean, RMS, variance, absolute peak, skewness, kurtosis, and crest factor.
- FFT dominant frequency, spectral energy, normalized low/mid/high band energy, and second-harmonic ratio.
- A separately persisted, versioned feature set linked one-to-one with its raw source window.
- Dashboard replay workflow for recorded ESP32/test-bench samples and derived-feature inspection.
- Idempotent MQTT bridge using the same validated signal-window and feature-extraction contract as HTTP replay.
- ESP32 reference firmware with fixed-rate ADC acquisition, NTP timestamps, stable QoS message identifiers, and machine-scoped topics.
- Numerical sine-wave test, API persistence/provenance test, and Alembic migration.

### Delivered work packages

1. Define the ESP32 device identity and authenticated ingestion envelope.
2. Store raw sampled windows separately from derived features.
3. Implement deterministic filtering and time-domain features: mean, RMS, variance, peak, kurtosis, skewness, and crest factor.
4. Implement FFT-derived dominant frequency, spectral energy, band power, and harmonic features with sampling metadata.
5. Version the feature-extraction configuration and connect each feature row to its source window.
6. Add replay fixtures, numerical unit tests, ingestion integration tests, and a replayed signal feature view.

### Phase 2 non-goals

- No fault probability before a trained model exists.
- No causal claim from frequency correlation or feature importance.
- Production broker identity, certificates, and network policy are deployment responsibilities; the included anonymous Mosquitto listener is local-development configuration only.

## Phase 3 — fault pattern recognition

### Implemented

- One-to-one controlled fault labels for raw signal windows, including source, confirmation state, and notes.
- Confirmed-label filtering so provisional labels do not enter the default training set.
- Seeded, stratified train/test separation with minimum sample and per-class coverage checks.
- Random Forest, RBF SVM, and XGBoost candidate comparison without silent estimator substitution.
- Computed accuracy, weighted precision/recall/F1, and fixed-class-order confusion matrices.
- Winner selection by held-out weighted F1 and versioned `joblib` artifact persistence.
- Predictions linked to both the source signal window and model run.
- Prediction probabilities explicitly marked `uncalibrated`; they are not decision confidence.
- ML Lab workflow for labelling, training, metric comparison, and latest-window prediction.

### Acceptance criteria

- Training rejects fewer than eight windows, a single class, or classes with insufficient examples.
- Repeating a run with the same evidence and seed reproduces its split metrics and winner.
- Every model metric originates from held-out predictions.
- Every persisted prediction identifies its exact model run and Phase 2 source window.
- Model incompatibility produces an error rather than fabricated or partially matched features.
- Random Forest, SVM, and XGBoost execute through their real implementations.

### Deferred research extension

A 1D-CNN remains optional until the physical dataset is large enough to justify raw-window deep learning and a leakage-safe validation protocol. It will not be added merely to expand the algorithm list.

## Phase 4 — explainability and anomaly detection

### Implemented

- Deterministic, model-agnostic permutation SHAP for the predicted class.
- Training-background reference persisted inside each Phase 3 model artifact.
- Additive feature contributions, base probability, reconstructed output probability, source feature values, and explanation configuration.
- One explanation persisted per prediction and therefore linked to the model run and raw signal provenance chain.
- Isolation Forest trained exclusively on confirmed `normal` windows.
- Versioned anomaly artifacts with training-envelope decision-score summaries.
- Persisted per-window anomaly scores with `unknown_condition` or `within_learned_normal_envelope` interpretation.
- ML Lab displays signed SHAP contributions and clearly distinguishes unknown-condition detection from named fault classification.

### Acceptance criteria

- SHAP contributions reconstruct the explained model output within numerical tolerance.
- Explanation records cannot exist without a persisted prediction and compatible model artifact.
- Isolation Forest training rejects fewer than eight confirmed normal windows.
- Extreme out-of-envelope numerical fixtures are flagged in deterministic tests.
- An anomaly score never contains or implies a named fault class.
- UI language states that feature attribution explains model behavior, not causal effects.

## Phase 5 — causal and counterfactual maintenance

### Implemented

- Confirmed physical experiment records containing intervention assignment, pre/post outcome, measured covariates, timestamps, and optional source-window identifiers.
- Treatment and control trials represented under the same candidate intervention for comparable effect estimation.
- Maintenance DAG validation, common-cause discovery, adjustment-set validation, descendant-adjustment rejection, minimum coverage, complete-case, and treatment-overlap gates.
- Backdoor-adjusted OLS treatment effect with HC3 robust intervals and explicit identification assumptions.
- Diagnostic unadjusted mean difference kept separate from the causal estimate.
- Persisted causal studies for both identified and abstained outcomes; abstained studies contain no effect value.
- Feasibility-gated counterfactuals with estimated outcome, benefit direction, and transformed confidence interval.
- Causal Lab workflow for recording experiments, running identification, inspecting abstention, and estimating a feasible intervention scenario.

### Acceptance criteria

- A known synthetic data-generating process recovers the intervention effect within tolerance after adjustment.
- Omitting a DAG common cause produces `abstained` with no numerical effect.
- Cyclic DAGs, treatment descendants in the adjustment set, insufficient samples, or inadequate overlap abstain.
- Counterfactuals abstain when their source study is unidentified or the intervention is infeasible.
- Estimated counterfactual outcomes are labelled model-based and remain distinct from observed post-maintenance measurements.

## Phase 6 — uncertainty and selective prediction

### Implemented

- Phase 3 training now uses seeded stratified train, validation, and independent calibration partitions.
- One-vs-rest sigmoid calibration fitted only on the calibration partition.
- Raw and calibrated multiclass Brier score, expected calibration error, accuracy, and calibration-bin evidence.
- Split-conformal classification sets using finite-sample corrected nonconformity quantiles.
- Empirical calibration coverage and mean prediction-set size reporting.
- Persisted reliability models linked to their exact fault-model artifacts.
- Mechanical ACT/MONITOR/ABSTAIN policy using calibrated probability, conformal-set ambiguity, and Phase 4 anomaly/OOD evidence.
- Persisted low-evidence abstention when calibration size or per-class coverage is insufficient.
- ML Lab reliability panel with calibrated probabilities, prediction set, and explicit action interpretation.

### Acceptance criteria

- Model selection and calibration never reuse the same partition.
- Calibration metrics and conformal coverage originate from recorded calibration predictions.
- Too little independent calibration evidence produces no reliability artifact and a persisted abstention.
- Any linked anomaly/OOD flag forces ABSTAIN.
- ACT requires a singleton conformal set and the configured calibrated-probability threshold.
- ACT accepts a classification for downstream review only; it never authorizes a physical maintenance intervention.

## Phase 7 — geospatial asset intelligence

### Implemented

- Coordinate-backed asset registry view that excludes incomplete locations instead of imputing them.
- Haversine great-circle distance calculation from an operator-supplied response origin.
- DBSCAN fault-hotspot analysis using a Haversine metric and a configurable physical radius.
- Unique-asset clustering so repeated events from one machine cannot satisfy the minimum-asset gate.
- Cluster centroids, member assets, source fault-event identifiers, event counts, and explicit noise assets.
- Persisted geospatial runs with calculation configuration, exclusions, method metadata, and results.
- Geo Intelligence workspace for relative asset visualization, response distances, and recent hotspot inspection.
- Explicit warning that spatial clusters are descriptive patterns and not causal explanations.

### Acceptance criteria

- A one-degree equatorial longitude difference agrees with the expected Haversine distance within tolerance.
- Assets lacking either coordinate are omitted and counted as excluded from distance calculations.
- Hotspots require the configured number of distinct located assets, not merely repeated fault events.
- Every hotspot retains its contributing machine and fault-event identifiers.
- No cluster output is presented as fault causation or intervention evidence.
- A clean database upgrades to revision `0008_geospatial_analysis`; backend tests and the frontend production build pass.

## Phase 8 — multi-objective maintenance optimization

### Implemented

- Deterministic binary NSGA-II with seeded initialization, uniform crossover, bit mutation, feasibility repair, non-dominated sorting, and crowding-distance selection.
- Five simultaneously minimized objectives: residual calibrated fault risk, declared maintenance cost, declared downtime, computed Haversine travel distance, and negative identified causal benefit.
- Hard budget, downtime, technician-hour, and maximum-action constraints applied to every generated solution and baseline.
- Candidate eligibility gate requiring a machine-matched ACT selective prediction, positive identified causal counterfactual, and machine distance from a persisted Haversine run.
- Explicit candidate exclusion reasons and run-level abstention when no evidence-backed candidate remains.
- Greedy risk-per-cost and conventional risk-priority baselines evaluated under identical constraints.
- Computed baseline comparison reporting Pareto dominance and Pareto membership.
- Persisted optimization configuration, Pareto front, baseline outputs, exclusions, upstream source identifiers, and operational inputs.
- Review-only maintenance-plan materialization that does not create or authorize physical maintenance actions.
- Maintenance Planner workspace with evidence readiness, operational input collection, constraint configuration, Pareto comparison, and plan preservation.

### Acceptance criteria

- A fixed candidate set and seed reproduce the same Pareto set and baseline results.
- Every returned Pareto or baseline schedule satisfies all configured hard constraints.
- Risk originates from calibrated non-normal probabilities; causal benefit and distance originate from persisted Phase 5 and Phase 7 evidence.
- MONITOR/ABSTAIN, machine mismatches, unidentified or non-positive causal benefit, and missing distance evidence exclude a candidate with recorded reasons.
- No eligible candidates produce a persisted abstained run without numerical schedule recommendations.
- Selected Pareto options remain `review_required` and never create maintenance actions.
- A clean database upgrades to revision `0009_maintenance_optimization`; targeted backend tests and the frontend production build pass.

## Phase 9 — integrated decision workflow

### Implemented

- Integrated decision creation from a persisted review-required Phase 8 maintenance plan.
- Mechanical reconstruction of the machine, raw signal, feature set, model, prediction, explanation, calibration model, optional anomaly gate, selective prediction, causal study, counterfactual, distance run, optimization run, and selected-plan evidence chain.
- Explicit identity checks across prediction/window, reliability/prediction/model, counterfactual/machine, and distance/machine references.
- Separate predictive/reliability and causal provenance branches that converge only at the optimization candidate.
- Persisted resource-level provenance nodes and typed edges plus a frontend-readable evidence graph.
- Deterministic plan-derived recommendation text; no LLM-generated metrics, action selection, or confidence values.
- Persisted ABSTAIN decision with exact missing-link reasons when any required evidence is absent or inconsistent.
- Named, one-time approve/reject review audit with notes and created-action identifiers.
- Approval creates `planned` maintenance actions only; predicted causal benefit remains separate from later observed benefit.
- Decision-scoped Investigator responses grounded in persisted decision evidence identifiers.
- Rebuilt Decision Register and AI Investigator workspaces for plan intake, graph inspection, review, and grounded explanation.

### Acceptance criteria

- A complete selected plan produces REVIEW and exposes every source identifier in its evidence graph.
- Missing explanation, calibration, causal, spatial, optimization, or plan evidence produces ABSTAIN with no recommendation.
- Predictive evidence is never represented as a causal derivation, and causal evidence is never represented as prediction calibration.
- Investigator responses cite persisted evidence-record IDs and preserve the decision’s REVIEW, RECOMMEND, or ABSTAIN status.
- An ABSTAIN decision cannot be approved; an integrated decision can be reviewed only once.
- Rejection creates no maintenance action; approval creates only planned actions with observed benefit unset.
- A clean database upgrades to revision `0010_integrated_decisions`; targeted backend tests and the frontend production build pass.

## Phase 10 — physical validation and research evaluation

### Implemented

- Confirmed physical-validation trials linked to an approved maintenance action and time-ordered pre/post sensor readings from the same machine.
- Server-side extraction of vibration RMS, temperature, current, or RPM outcomes; observed benefit cannot be manually supplied.
- Computed predicted-versus-observed benefit, signed error, absolute error, MAE, RMSE, mean bias, and normal-approximation bias interval.
- Maintenance-action completion update that preserves predicted and observed benefits in separate fields.
- Case-level recorded benchmark outputs for the integrated system, traditional analytics, predictive-ML-only, LLM-only, and predefined ablation variants.
- Aligned-case design gate requiring all four authoritative baseline variants and a configurable minimum number of shared cases.
- Computed coverage, abstention rate, selective accuracy, overall correct rate, harmful-recommendation rate, provenance coverage, uncertainty-handling rate, Wilson intervals, and failure-case identifiers.
- Integrated-minus-baseline and integrated-minus-ablation differences derived from the same aligned cases.
- Persisted completed or abstained research-evaluation runs with exact input record identifiers.
- Canonical JSON research artifacts with deterministic SHA-256 digests for result reproducibility.
- Research Evaluation workspace for physical trial registration, benchmark/ablation output recording, evaluation execution, abstention inspection, and report verification.

### Acceptance criteria

- Physical benefit is computed only from linked measured values occurring before and after the intervention.
- A reading from another machine, reversed time order, missing channel, unconfirmed trial, or action without predicted benefit is rejected.
- Too few confirmed physical trials produce a persisted abstained evaluation rather than aggregate claims.
- Comparative evaluation requires integrated, traditional analytics, predictive-ML-only, and LLM-only outputs over aligned cases.
- Every displayed metric is computed from persisted observation rows; no example or manually entered metric is presented as a result.
- Repeating an identical report payload produces the same SHA-256 digest.
- A clean database upgrades to revision `0011_research_evaluation`; targeted backend tests and the frontend production build pass.

### Experimental boundary

The evaluation system is complete, but publication claims remain intentionally unavailable until the team records real controlled motor interventions and adjudicated comparison outputs. The platform persists abstention for insufficient evidence and does not ship synthetic headline results.

## Cross-phase integration contract

The authoritative chain is:

`machine → raw sensor window → computed feature set → model run → explanation → causal analysis → reliability evaluation → optimized plan → maintenance action → observed outcome`

Every link carries source identifiers, timestamps, configuration/model versions, and computation provenance. A missing required link results in review or abstention, not an inferred value.

## Verification policy

Each phase must add targeted unit and API tests, pass backend import/compilation, pass frontend type checking and linting, and update this plan. Research claims are produced only by versioned experiment runners from stored outputs.
