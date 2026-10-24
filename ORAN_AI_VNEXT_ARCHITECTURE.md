# ORAN AI vNext Unified Collector

GitHub Actions runs validated allowlisted adapters. The GitHub artifact is **temporary transfer only**, not a permanent database. The existing new local SQLite will remain the durable queryable data source once approved and backed up. Historical legacy SQLite remains protected.

Two approved sources: OpenFootball 2025-26 EPL and Bundesliga CC0 JSON. The older Collector and other sites are not yet approved for new automatic copying. No quota circumvention.

Source bundle format remains oranai.source.bundle.v1 and compatible with REV7B+ desktop preview. SHA256 confirms integrity, NOT origin authentication. Scores are historical research observations, NOT confirmed prematch odds, timestamps or predictions.

No git commits, DB writes or live FINAL in this staging workflow. Promotion requires a real successful Actions job, artifact verification, controlled Windows SQLite import, durable backup/restore acceptance and the user's gated cutover. Do not delete legacy data or old jobs before this cutover.
