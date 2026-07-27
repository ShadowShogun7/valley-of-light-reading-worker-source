# Valley of Light source and licence notice

## Covered software

The source code used to operate the Valley of Light paid-reading network
service is released under `AGPL-3.0-or-later`. Each deployed worker must offer
the matching source archive through its unauthenticated `/source` endpoint and
the response `Link` header.

The deployed release must be built from the public AGPL source archive. The
archive SHA-256 recorded in `VALLEY_AGPL_SOURCE_SHA256` must match the archive
available at `VALLEY_AGPL_SOURCE_URL`.

## Excluded material

The following are not relicensed and must never be copied into a public source
release:

- `.env` files, credentials, API keys, signing keys, database contents,
  customer records, order records, logs, or birth data;
- the `raw/` book/source corpus and any other third-party source publication;
- third-party fonts, photography, video, audio, trademarks, and other media
  unless their own licence expressly permits redistribution; and
- local caches, build output other than the exact published runtime KB,
  dependency folders, editor state, and deployment credentials.

The generated, published-only runtime KB shipped in the deployed worker is
included in the matching source release so that the public build does not
require or redistribute the private `raw/` source corpus.

## Release rule

`services/reading-worker/build_agpl_source_release.py` is the only supported
source-release builder. Production must fail closed until:

1. the archive has been generated and reviewed;
2. the archive has been published at a public, no-charge HTTPS URL;
3. its SHA-256 has been independently verified; and
4. those exact URL and digest values have been configured on the worker.

This notice documents the selected operational path and is not legal advice.
