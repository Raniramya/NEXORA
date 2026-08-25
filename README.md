# NEXORA-CDI

Evidence-Calibrated Causal Decision Intelligence for Business Analytics.

NEXORA-CDI is a full-stack decision-intelligence workspace. It keeps descriptive analytics, predictive modelling, causal inference, counterfactual scenarios, reliability checks, and decision provenance deliberately separate so business conclusions remain evidence-bounded.

## Website experience

The frontend is designed as an analytics command center with an executive overview and a guided workflow:

1. **Assets and telemetry** — register physical machines and record vibration, temperature, current, and RPM observations from the test bench or edge device.
2. **Data foundation** — upload a CSV or Excel source and review its computed quality profile, schema, missingness, and untouched preview.
3. **Analytics** — inspect descriptive aggregations and correlations without representing them as causal evidence.
4. **ML studio and Causal lab** — run distinct predictive and causal workflows.
5. **Decision register** — review recommendations together with confidence, provenance, and abstention state.

The UI uses a responsive light analytics canvas, dark navigation rail, and teal action language. It does not display fabricated example metrics; figures shown after upload are computed from the submitted source.

## Local setup

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start PostgreSQL (optional for health checks): `docker compose up -d postgres`.
3. Backend:
   - `cd backend`
   - `python -m venv .venv`
   - macOS/Linux: `source .venv/bin/activate`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
   - `python -m alembic upgrade head`
   - `uvicorn app.main:app --reload --port 8000`
4. Frontend (separate terminal):
   - `cd frontend`
   - `npm install`
   - `npm run dev`

The backend, Alembic commands, and MQTT bridge all load the same repository-root
`.env` file, regardless of the directory from which they are launched. Check
container readiness with `docker compose ps`; PostgreSQL and Mosquitto include
health checks and restart automatically unless explicitly stopped.

The frontend runs at `http://localhost:3000`; backend health is available at `http://localhost:8000/api/health`.

## Faculty demonstration flow

1. Start PostgreSQL, the backend, and the frontend using the steps above.
2. Open `http://localhost:3000` and introduce the four-stage evidence workflow.
3. Go to **Data foundation**, upload a business CSV, and show the generated quality profile and source preview.
4. Use **Analytics** to explain descriptive results and explicitly note that correlations are not causal claims.
5. Show **ML studio** and **Causal lab** as separate workflows, then finish in the **Decision register** to highlight provenance and abstention.

Uploaded source files are stored only in local `storage/` and are ignored by Git.

## Physical maintenance foundation

The Assets & Telemetry workspace provides the first edge–cloud integration boundary. Machines can be registered with optional coordinates, and timestamped multimodal readings are stored as observed evidence. The API also records fault events and planned or completed maintenance actions, including predicted and observed benefits for later intervention-validation experiments. This layer intentionally does not generate fault probabilities or causal effects; those must come from versioned analytical runs.

## Signal processing

Raw vibration windows can be submitted to `/api/machines/{machine_id}/signal-windows` from an ESP32 client or replayed through Assets & Telemetry. The backend preserves the submitted samples and stores a separate versioned feature set containing time-domain and FFT-derived evidence. Set `NEXORA_EDGE_INGEST_TOKEN` to require the `X-Nexora-Edge-Token` header for ingestion. Signal features are not fault classifications; Phase 3 models will consume them through reproducible labelled datasets.

### ESP32 MQTT integration

The reference firmware is in `hardware/esp32_nexora/`. Copy `config.example.h` to `config.h`, enter Wi-Fi, broker, registered machine UUID, and ADC pin values, then install the Arduino libraries `PubSubClient` and `ArduinoJson`. The firmware publishes to:

```text
nexora/machines/{machine_id}/signal-windows
```

Start the local PostgreSQL and Mosquitto services, backend, and bridge:

```bash
docker compose up -d
cd backend
python -m alembic upgrade head
uvicorn app.main:app --reload
python -m app.edge.mqtt_bridge
```

Each MQTT envelope contains a stable `message_id` and the existing signal-window contract. The bridge forwards it to `/api/edge/signal-windows`; an ingestion receipt makes repeated QoS deliveries idempotent. Set the same `NEXORA_EDGE_INGEST_TOKEN` for the API and bridge. The bundled Mosquitto configuration permits anonymous local development only. Use authenticated TLS, broker ACLs, and a CA file for any networked deployment.

## Physical fault modelling

The ML Lab labels controlled test-bench windows and trains Random Forest, RBF SVM, and XGBoost candidates on a seeded stratified split. Accuracy, weighted precision/recall/F1, and confusion matrices are computed from the held-out partition. The winning artifact and every prediction retain their model-run and source-window identifiers. Probabilities are shown as uncalibrated predictive outputs until the uncertainty phase evaluates calibration and abstention.

## Explainability and unknown conditions

Predictions can be explained with deterministic permutation SHAP. Contributions are stored with the prediction, explained class, model output, feature values, seed, and training-background reference. SHAP describes how the classifier produced an output; it is not causal evidence. A separate Isolation Forest learns only from confirmed normal windows and reports whether a window lies outside that envelope. Anomalies remain `unknown_condition` and are never silently converted into fault labels.

## Causal maintenance experiments

The Causal Lab records confirmed treatment and control trials with measured pre/post outcomes and covariates. A declared DAG and adjustment set must pass identification, coverage, and overlap gates before NEXORA reports a robust regression-adjusted treatment effect. Failed gates produce a persisted abstention with no effect. Counterfactuals inherit the study assumptions and additionally require intervention feasibility; their outputs are model-based estimates, not observed repair results.

## Calibrated selective prediction

Fault-model training reserves independent train, validation, and calibration partitions. Phase 6 fits sigmoid probability calibration, computes Brier/ECE evidence, and constructs split-conformal prediction sets from the calibration partition. The selective policy combines set ambiguity, calibrated thresholds, and Isolation Forest OOD evidence to return ACT, MONITOR, or ABSTAIN. ACT means the classification may proceed to downstream review; it is not authorization to perform maintenance.

## Geospatial asset intelligence

The Geo Intelligence workspace maps only assets with complete recorded coordinates. It persists Haversine distance runs from a supplied response origin and DBSCAN hotspot runs over recent fault events. Hotspots require distinct nearby assets, retain their machine and fault-event provenance, and are labelled as descriptive spatial patterns rather than causal explanations.

## Multi-objective maintenance optimization

The Maintenance Planner accepts candidates only when they have machine-matched ACT reliability evidence, a positive identified causal counterfactual, and a computed Haversine distance. Binary NSGA-II minimizes residual calibrated fault risk, cost, downtime, travel, and negative causal benefit under budget, technician-hour, downtime, and action-count constraints. Greedy risk-per-cost and conventional risk-priority baselines are computed under the same constraints. Persisted Pareto selections remain `review_required` and do not create or authorize maintenance actions.

## Integrated decision and review workflow

The Decision Register converts a selected maintenance plan into a recommendation only after reconstructing its complete persisted evidence graph. Predictive/reliability and causal branches remain separate until they support the same optimization candidate. Missing or inconsistent links produce ABSTAIN. The AI Investigator answers against attached evidence-record IDs, and a named one-time approval is required before the system creates planned maintenance actions. Approval does not mark work as executed and does not populate observed benefit.

## Physical validation and research evaluation

The Experiments workspace links approved actions to physical pre/post readings and computes predicted-versus-observed benefit errors without accepting manually typed outcome metrics. Comparative studies preserve case-level outputs for the integrated system, traditional analytics, predictive-ML-only, LLM-only, and ablations, then evaluate only aligned cases. Completed and abstained runs are persisted with input provenance, metric definitions, uncertainty intervals, failure cases, canonical JSON reports, and SHA-256 digests. Real results appear only after real experiment records exist.

## Phase 2 data foundation

Upload CSV or XLSX files from the Data page. Original files are stored locally in `storage/`; metadata and computed profiles are stored in PostgreSQL. The Analytics page provides descriptive aggregations and correlation display only; it makes no causal claims.

## Phase 3 ML intelligence

ML Lab runs seeded sklearn pipelines with train/test separation and persists computed run metadata, metrics, and serialized model artifacts. Supported models are linear/logistic regression, random forest, K-Means, and Isolation Forest; forecasting currently uses the regression baseline pipeline.

## Phase 4 causal analysis

The causal endpoint implements DAG-validated linear regression adjustment for binary or continuous treatments, reporting its identification assumptions, interval, p-value, and a non-causal raw-association diagnostic. DoWhy and EconML are declared optional advanced estimators; unavailable or unsuitable estimators are not substituted with fabricated effects. Intervention scenarios are explicitly labelled model-based causal estimates.

## Validation

- Backend: `cd backend; python -c "from app.main import app; print(app.title)"`
- Frontend: `cd frontend; npm run typecheck` and `npm run lint`

## Schema migrations

From `backend/`: `alembic upgrade head`; `alembic downgrade -1`; `alembic revision --autogenerate -m "description"`.
