# Supabase production operations

The base paid-reading migration creates private data, commerce, delivery, and
privacy controls but deliberately does not enable a retention policy or
schedule a database-owner job.

Production policy `reading-retention-v1-2026-07-31` was approved and activated
by migration `20260731143000_enable_production_reading_retention.sql` with:

- incomplete readings retained for 30 days after last activity;
- delivered readings retained for 365 days after delivery or readiness;
- refunded or revoked readings eligible for deletion immediately;
- a database-owner retention run at minute 7 of every hour.

Because the database requires every duration to be positive, “immediately” is
encoded as one second. The hourly scheduler therefore deletes eligible revoked
content on its next run, normally within one hour.

`reading-retention-cron.sql.example` is the reviewed registration template.
Use it only after all of these are explicit and approved:

- the production Supabase project and backup/PITR plan;
- policy version and positive durations;
- the `reading-retention-anchor-v1` semantics;
- legal-hold placement/release ownership;
- customer-request identity verification;
- provider, log, and backup retention outside reading-content storage;
- the scheduler identity hash and database-owner execution path.

The paid-reading health check stays red until the exact enabled policy has a
fresh successful run, its stored policy snapshot still matches, and no overdue
eligible backlog remains. Each bounded run rechecks due status after acquiring
the reading locks; activity that moves an anchor makes the stale action
`skipped` rather than erasing content. A policy row alone is not enough.
Once a policy is approved or enabled, its version, anchors, durations, cadence,
approval evidence, and creation time are immutable; only its enabled kill
switch can change. Any duration or semantic change requires a newly approved
version.

`billing-email-correction.sql.example` is the DB-owner-only support template
for a verified typo or hard bounce. Use it only after an authorized operator
corrects and revalidates the exact WooCommerce paid order. It atomically
revokes the possibly exposed link, records hashed audit evidence, creates one
replacement grant, and queues recovery to the corrected address. The public
recovery form never accepts a new address.

Recipient suppressions are DB-owner-only too. A complaint must not be cleared
as an ordinary bounce: verify explicit re-consent, pass the expected current
suppression kind, and record the named actor hash plus reason through
`private.valley_clear_email_recipient_suppression`. A corrected address uses a
different hash and leaves the old-address audit history intact.
