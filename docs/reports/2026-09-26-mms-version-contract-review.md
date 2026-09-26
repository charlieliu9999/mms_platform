# MMS version contract: local engineering acceptance

Task t424; branch `codex/mms-standard-version-contract`.
Original source baseline `cf8eead7615389c1f843a1fc178f1258fddb7c79`.
Local commit identity is recorded in `outputs/t424/local-delivery-identity.json`.

## Final local HTTP/cache acceptance

The final implementation passes local engineering acceptance: 3919/4555
automatic matches (86.0373%), 23 review, 613 none. The archived original
engine and final engine were rerun with the same current local rule data,
fingerprint `v15030-a0c140d8a1ce`, frozen manifest and evaluation harness.
Baseline is 2495 matches; net gain is 1424; zero baseline matched items
became review/none. Final evaluator and actual HTTP results agree for all
4555 codes, source names, actual versions and tiers.

Real HTTP used a temporary localhost service at `127.0.0.1:19124` and the
existing API routes, real engine, real CacheService and real feedback upsert.
Rule loading and fingerprint queries connected to local `acrac_db` with
`default_transaction_read_only=on`. All writable API sessions connected only
to the explicitly created `codex_t424_mms_acceptance_20260926` database, with
two dedicated cache/feedback tables. No existing cache, source table or service
on port 9100 was changed. The test database is retained as acceptance evidence.

Cold/warm full-cohort HTTP calls produced 1001 and 3509 cache hits (cold can
hit repeated names within the batch). Every non-cache response field is
identical across both calls. The first real-cache run exposed four routing
flag differences. The dispatcher now records engine routing separately and
combines it with the current caller's source/effective-modality routing.
Old algorithm cache rows lacking that distinction are recomputed; confirmed
rows are retained. The evaluator uses the same combined routing rule.

Real cache probes also passed: missing-version algorithm output is recomputed,
the second call hits the new cache, selectors have separate actual hash rows,
an expired historical manual mapping remains byte-for-byte unchanged after
lookup and an automatic overwrite attempt, missing manual provenance requires
review, and the feedback record is actually persisted in the isolated database.

The current rule fingerprint differs from the earlier `v15030-7edcd98ac491`.
This fingerprint contains five rule/standard database tables only; it contains
no source code. Current US standard names include their `US` display prefix.
Active exact-name US aliases now tolerate this prefix while preserving the
source standard name/code/version; alias collisions require review. This
restores specific active finger-joint, large-bowel-enema and cervix codes.
Compared with the earlier accepted ASGI snapshot, all 4555 codes/versions and
tiers are unchanged; 1242 source standard names now contain the current source
prefix. The final source fingerprint was checked again after acceptance and
remained stable. No source data was modified to accomplish this compatibility.

Final tests: **247 passed, 2 skipped, 4 warnings**. Defect ruff and
`git diff --check` pass. Final source SHA-256 is
`5768813182f11234f1d7edd9066cfc10281fb45e83f500e230f7be24fd43fadb`.
Final evaluation-harness SHA-256 is
`b7e024a85c63e78d5a715bf0a1249c7f3f838e431cd77f776dc1e8b07d4a909c`.
Tracked-diff SHA-256 is
`6d6386f5255b611bc97fe0f1e07ba079171feb4d926b8d29f71f1f920e864892`.

Authoritative evidence under `outputs/t424/`:

- `final-http-acceptance-summary.json`
- `baseline-http-final-4555.json` / `after-http-final-4555.json`
- `http-4555-cold.json` / `http-4555-warm.json`
- `http-cache-scenarios.json` / `rules-end-verification.json`
- `full-tests-http-final-readonly.log`

This is engineering acceptance, not complete clinical correctness or a
production release. PR0070's generic myocardial SPECT to acute-infarct
standard and PR0075's unspecified lower-limb Doppler to artery standard
remain pending business review. They were not expanded into new clinical
rules in this task. Downstream ACR persistence is accepted separately by its
owning task. A local scoped commit is authorized after these checks. No push, merge or
production deployment is included.
