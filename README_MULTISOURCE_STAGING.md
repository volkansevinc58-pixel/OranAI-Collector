# ORAN AI — Multi-Source Collector (REV7 staging branch)

This branch is a **non-production, review-only** successor candidate to the legacy single-source collector. The existing `main` branch and all historical CSV data are intentionally preserved.

## Design contract
- Data sources: explicit allowlist and license/terms approval. Initial OpenFootball JSON (CC0) adapter; other sources default deny until accepted.
- Collectors stage source bundles with SHA-256, UTC retrieval time, source-scoped fixture identity, schema checks and rejection counts.
- GitHub Actions is a **runner and short-lived artifact distributor**, not the main production SQL database or an unbounded CSV commit store.
- The local ORAN AI desktop application owns the separately initialized **new** SQLite store; prior `C:\OranAI\data\oranai.db` is not imported or modified by default.
- Import requires user acceptance; no automatic model promotion, no production FINAL, no gambling-profit guarantee.
- Source data freshness, odds types, kickoff time, and provenance are independent fields; never infer them from a fixture score.
- Failure handling is fail-closed; no repeated HTTP requests after access denial/429.

## Current gate
Local candidate package: `ORAN_AI_REV7_COK_KAYNAKLI_COLLECTOR_VE_MASAUSTU.zip` delivered separately to the user.
Offline tests: 29 desktop/data tests and 5 isolated collector tests passed in the supplied environment. Production GitHub workflow and Windows runtime not yet proven.
**Source files from that reviewed ZIP are not uploaded to this branch yet**; this initial commit records staging policy and protects `main` from premature migration.

## Migration sequence
1. Audit and review the complete REV7 code candidate.
2. Upload the matching candidate sources and tests to this branch.
3. Run explicit artifact-only validation and independently check the source time/license/provenance.
4. Verify data bundle import into a separate test SQLite and Windows UI.
5. Promote approved workflows and schedule in a controlled change. Preserve legacy history and provide a rollback checkpoint.
6. Only then decide whether to deprecate, archive, or delete any legacy workflows. Never delete historical data without a verified backup.

No old production files have been deleted.
