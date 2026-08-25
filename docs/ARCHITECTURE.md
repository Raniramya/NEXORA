# Architecture

Next.js provides Data, Analytics, ML Lab, and Causal Lab route shells. FastAPI exposes dataset ingestion/profile/analytics, synchronous ML runs, and causal/intervention endpoints. PostgreSQL stores dataset and ML-run metadata; uploaded files and model artifacts use local storage boundaries. Reliability, investigator, provenance-like evidence IDs, and benchmark tooling currently exist as service modules. Correlation diagnostics are explicitly labelled non-causal; causal effects originate from the linear adjustment estimator.

Known integration boundary: persisted causal runs, scenarios, decision evidence records, provenance graph tables, and AI Investigator API/UI are not yet wired into the production request flow.
