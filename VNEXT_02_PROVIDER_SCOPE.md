# ORAN AI — GATE VNEXT-02 Independent provider adapter

Purpose: validate one **different provider** in the established staged workflow, without advancing or altering official task order.

**OpenFootball** CC0: 2025/26 Premier League + Bundesliga (686 source records, previously verified).
**StatsBomb Open Data**: a single historical La Liga 2020/21 competition 11 season 90 JSON, pinned to upstream Git commit 4b73468fc5b0f1950f9f66fada70ad3a4f9327cb.

StatsBomb's public README permits public research use and requests attribution and logo for published analysis; a full license PDF is present and **not yet legally reviewed**. Therefore ingestion here is **research-only staging**, NOT a licensed production/trading data feed, and deliberately uses schema oranai.statsbomb.research.v1 so the existing OpenFootball-only SQLite importer cannot silently accept it. No commercial/automated production use permission is inferred.

- OpenFootball provider scoped fixture SHA identity
- StatsBomb provider scoped match_id: NEVER treated as universal EventID.
- No match kickoff UTC inferred from local kick_off times.
- Published scores are retrospective only, not a pre-match model feature.
- All source files + cross-provider manifest get SHA-256 integrity checks (not publisher signatures).
- Actions uploads a temporary artifact. No SQLite/GitHub CSV writes, no main updates, no live prediction FINAL.
- Future gate: confirm StatsBomb precise rights and permitted automation; design provider-specific quarantined SQLite import, team identity/time mapping, persistent backup/restore, then controlled production acceptance.
