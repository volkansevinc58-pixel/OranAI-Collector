# ORAN AI NEXT — Multi-source staging

This branch is an isolated candidate, not production. The previous Collector and historical CSV files remain unchanged on `main`.

## Verified local candidate
- Revision: REV7
- ZIP: `ORAN_AI_REV7_COK_KAYNAKLI_COLLECTOR_VE_MASAUSTU.zip` (distributed independently via ChatGPT conversation)
- SHA-256: `7c6ecc843cd2db2861a780bed9456087563625e2cdc9345806bda8273d7c60ec`
- Offline tests: 29 passed (source adapter and isolated SQLite contract)
- Runtime GitHub Actions: NOT_PROVEN
- User Windows acceptance: NOT_PROVEN
- Production data: NOT_MUTATED

## Candidate design
Allowed OpenFootball CC0 dataset -> bounded HTTPS GET -> validate -> SHA-256 manifest -> staged GitHub Actions artifact -> reviewed import to the separately approved SQLite database. No forced duplicate collector, no automated production writes, no real FINAL / wagering coupon claims.

## Release gate
Do not delete old Collector or any CSV history. Verify candidate source files from the ZIP, run a GitHub Actions staging job, check durable output and acceptance tests, then plan a separate reversible cutover. Only after data preservation and rollback have been proven may legacy collection be retired.
