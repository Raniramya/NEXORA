# NEXORA-CDI Contribution Rules

- Read `docs/PROJECT_SPEC.md` before architectural changes.
- Preserve the existing architecture and make the smallest correct change.
- Never invent experimental metrics or hard-code fake ML results.
- Numerical statements exposed to an LLM must originate from computed evidence.
- Keep causal inference separate from correlation analysis.
- All recommendations require provenance.
- Low-confidence decisions must support abstention.
- Do not modify unrelated modules.
- Prefer targeted tests.
- Never scan generated or dependency directories unnecessarily.
- Do not create duplicate implementations when one already exists.
