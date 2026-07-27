# Valley of Light paid-reading worker

This service is the private, one-job-at-a-time generation worker for paid
relationship readings. It does not receive payment details and it does not
serve customer results.

Its flow is:

1. Accept an authenticated `POST /wake` hint, or wake on the polling timer.
2. Claim one locked intake from the app's signed private API.
3. Convert the paid intake to the existing `ReadingInput` contract.
4. Run `calc_western_spike.build_payload` and
   `complete_relationship_result_runtime.build_view_model` inside a fresh,
   killable child process. Birth data moves through an anonymous stdin pipe and
   is never written to a temporary file.
5. While generation runs, renew the exact attempt-fenced database lease from
   the parent process. Kill and reap the child at the hard wall-clock timeout
   or immediately when lease renewal fails.
6. Return the result through the signed, fenced result callback, or return a
   stable error code through the signed failure callback.
7. Independently ask the app to reconcile unsent invitation/result emails on
   a configurable timer.

`GET /healthz` is intentionally unauthenticated for platform health checks and
contains only operational state. `POST /wake` requires the same timestamped
HMAC used by all worker API calls. A wake request is only a hint: the worker
always claims the authoritative queued job from the database.

## Production safety gates

The process refuses to start unless all of these are true:

- `dist/kb/manifest.json` says `published_only: true`.
- All six runtime inputs are present and non-empty:
  `kb_articles.json`, `kb_claims.json`, `kb_atoms.json`, `kb_rules.json`,
  `kb_question_blueprints.json`, and `kb_guardrails.json`.
- Counts in the KB manifest match the actual record counts and are nonzero.
- Every runtime input and the KB manifest match SHA-256 values recorded in
  `worker-runtime-manifest.json`.
- The bundle's job, result-contract, runtime, and schema versions match the
  versions supported by this worker, and the claimed intake version remains
  `relationship-intake-v1`.
- The pinned Immanuel and pyswisseph versions are installed.
- The operator has explicitly selected the AGPL path.
- A matching, no-charge public source archive URL and lowercase SHA-256 digest
  are configured.

The Docker builder runs the repository source/claim validator, creates a fresh
`--published-only` KB under `dist/kb`, and then records the immutable runtime
checksums. Raw source books are available only to that validation build stage;
the final runtime image contains neither raw books nor draft KB source.

Runtime dependencies are installed from `requirements.lock` with
`--require-hashes`. `requirements.txt` is the short, human-reviewed input list;
regenerate and review the lock file whenever that input changes:

```sh
python3.11 -m piptools compile \
  --generate-hashes \
  --output-file services/reading-worker/requirements.lock \
  services/reading-worker/requirements.txt
```

## AGPL deployment path

The pinned runtime currently uses two separately relevant dependencies:

- `immanuel==1.5.4`, whose published package is AGPL-3.0-or-later; and
- `pyswisseph==2.10.3.2`, which wraps Swiss Ephemeris and is published under
  AGPLv3.

On 2026-07-27 the owner selected the AGPL path for this network service. The
worker now fails closed unless the licence decision and exact public source
release metadata are all configured:

```text
VALLEY_ASTROLOGY_LICENSE_DECISION=agpl-3.0
VALLEY_AGPL_SOURCE_URL=https://<public-release-url>
VALLEY_AGPL_SOURCE_SHA256=<lowercase SHA-256 of that exact archive>
```

Every HTTP response carries a `Link: <...>; rel="source"` header and the exact
archive digest. `GET /source` returns the licence, source URL, and digest
without requiring authentication.

The private validation build may read the `raw/` corpus to compile and verify
the published-only KB. The public AGPL build does not contain or require that
copyrighted corpus; it consumes the exact compiled runtime KB included in the
source release. Production must be built from
`services/reading-worker/Dockerfile.agpl`, never from the private validation
Dockerfile.

Build one reviewed source release with:

```sh
python3 services/reading-worker/build_agpl_source_release.py \
  --release-id <immutable-release-id> \
  --source-url https://<public-release-url> \
  --output-dir /path/outside/the/repository
```

The builder uses an allowlist, rejects secret-like material, excludes
environment files/customer data and the `raw/` corpus, and writes a
file-by-file checksum manifest into the deterministic archive. Publish the
archive at the configured URL before deploying the matching worker.

## Required environment

```text
VALLEY_APP_API_BASE_URL=https://app.valeoflight.com
VALLEY_WORKER_SIGNING_SECRET=<same high-entropy secret as the app>
VALLEY_ASTROLOGY_LICENSE_DECISION=agpl-3.0
VALLEY_AGPL_SOURCE_URL=https://<public-release-url>
VALLEY_AGPL_SOURCE_SHA256=<lowercase SHA-256 of that exact archive>
```

Optional configuration:

```text
PORT=8080
VALLEY_WORKER_ID=<unique live-replica id; generated per process if omitted>
VALLEY_WORKER_POLL_SECONDS=15
VALLEY_WORKER_LEASE_SECONDS=300
VALLEY_WORKER_LEASE_HEARTBEAT_SECONDS=60
VALLEY_WORKER_JOB_TIMEOUT_SECONDS=900
VALLEY_WORKER_HTTP_TIMEOUT_SECONDS=20
VALLEY_WORKER_MAX_RESULT_BYTES=3500000
VALLEY_EMAIL_RECONCILIATION_SECONDS=60
VALLEY_EMAIL_RECONCILIATION_LIMIT=5
VALLEY_EXPECTED_INTAKE_VERSION=relationship-intake-v1
VALLEY_EXPECTED_JOB_VERSION=paid-reading-job-v1
VALLEY_EXPECTED_RESULT_CONTRACT_VERSION=complete-relationship-result-v1
VALLEY_EXPECTED_RUNTIME_VERSION=valley-paid-reading-runtime-v1
```

The email reconciliation loop runs in its own thread, so a slow email retry
request does not block claim processing. Thirty seconds is the minimum allowed
reconciliation interval. The health endpoint returns a non-200 response if an
idle polling loop stops, an active job exceeds its hard timeout, its lease
heartbeat becomes stale, or email reconciliation has not completed
successfully within its bounded startup/staleness window. A loop that keeps
ticking while the app returns errors is not considered healthy.

The app must separately point its dispatch hook at this service's authenticated
wake endpoint:

```text
VALLEY_WORKER_URL=https://<worker-host>/wake
VALLEY_WORKER_SIGNING_SECRET=<the same secret>
```

## Build and run

The private source-validation build uses the repository root as its context:

```sh
docker build \
  -f services/reading-worker/Dockerfile \
  -t valley-reading-worker:local \
  .
```

It is not the public deployment artifact. Build deployed staging and
production workers from the generated public source release instead:

```sh
docker build \
  -f services/reading-worker/Dockerfile.agpl \
  -t valley-reading-worker:agpl \
  .
```

Then inject environment values through the hosting platform's secret manager:

```sh
docker run --rm -p 8080:8080 \
  --env-file /path/to/worker.env \
  valley-reading-worker:local
```

Do not bake `.env` files or secrets into the image.

## Render staging blueprint

The repository-root `render.yaml` prepares one paid Render Docker web service
named `valley-reading-worker-staging`. A web service is used instead of a
Render background worker because this process exposes `/healthz` and the
authenticated `/wake` endpoint required by the Vercel app.

The blueprint:

- uses the repository root as Docker build context;
- builds `services/reading-worker/Dockerfile`;
- uses Singapore for the staging region;
- disables automatic deploys;
- configures `/healthz` as the platform health check;
- allows up to five minutes for graceful shutdown; and
- prompts for the staging app URL, signing secret, and recorded licensing
  decision instead of storing them in Git.

Creating the Render service incurs the selected paid instance cost. Do not
create it until the owner approves the provider/budget, the staging app URL
exists, and the dependency licensing path has been reviewed. Production must
use a separate service and secrets; do not rename or reuse the staging service.

## Intake/location launch boundary

The current calculation adapter has exact coordinates only for its existing
small known-place list. The worker resolves overlapping aliases by exact or
longest match before calculation (so `new taipei` cannot resolve as `taipei`).
When the place is blank, the worker deliberately drops the entered clock time
and forces date-only precision because the timezone is unknown. An entered but
unsupported place fails the job closed with `UNSUPPORTED_BIRTH_PLACE`; the
worker will not silently deliver a paid result with a missing or incorrectly
timed natal chart.

A production launch that accepts arbitrary city text still needs a reviewed
normalization step that persists latitude, longitude, and an IANA timezone, or
the form must be restricted to the adapter's supported place list. The worker
does not pretend that this product-level requirement is solved.

## Tests

The focused suite uses the standard library and does not call live services:

```sh
PYTHONPATH=services/reading-worker \
  python3 -m unittest discover \
  -s services/reading-worker/tests \
  -v
```

The tests cover HMAC compatibility, stable analysis-time mapping, fail-closed
bundle integrity, result/failure behavior, independent email reconciliation,
lease heartbeats, child-process timeout/termination, and fail-closed health.
