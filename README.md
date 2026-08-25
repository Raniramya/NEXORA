# NEXORA-CDI

Evidence-Calibrated Causal Decision Intelligence for Business Analytics.

NEXORA-CDI is a full-stack decision-intelligence workspace. It keeps descriptive analytics, predictive modelling, causal inference, counterfactual scenarios, reliability checks, and decision provenance deliberately separate so business conclusions remain evidence-bounded.

## Website experience

The frontend is designed as an analytics command center with an executive overview and a guided workflow:

1. **Data foundation** — upload a CSV or Excel source and review its computed quality profile, schema, missingness, and untouched preview.
2. **Analytics** — inspect descriptive aggregations and correlations without representing them as causal evidence.
3. **ML studio and Causal lab** — run distinct predictive and causal workflows.
4. **Decision register** — review recommendations together with confidence, provenance, and abstention state.

The UI uses a responsive light analytics canvas, dark navigation rail, and teal action language. It does not display fabricated example metrics; figures shown after upload are computed from the submitted source.

## Local setup

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start PostgreSQL (optional for health checks): `docker compose up -d postgres`.
3. Backend:
   - `cd backend`
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`
4. Frontend (separate terminal):
   - `cd frontend`
   - `npm install`
   - `npm run dev`

The frontend runs at `http://localhost:3000`; backend health is available at `http://localhost:8000/api/health`.

## Faculty demonstration flow

1. Start PostgreSQL, the backend, and the frontend using the steps above.
2. Open `http://localhost:3000` and introduce the four-stage evidence workflow.
3. Go to **Data foundation**, upload a business CSV, and show the generated quality profile and source preview.
4. Use **Analytics** to explain descriptive results and explicitly note that correlations are not causal claims.
5. Show **ML studio** and **Causal lab** as separate workflows, then finish in the **Decision register** to highlight provenance and abstention.

Uploaded source files are stored only in local `storage/` and are ignored by Git.

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
