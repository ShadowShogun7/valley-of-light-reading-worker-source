"""Build a deterministic, secret-screened AGPL source release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
INCLUDED_PATHS = (
    Path("LICENSE"),
    Path("LICENSE.md"),
    Path("NOTICE.md"),
    Path("THIRD_PARTY_NOTICES.md"),
    Path("apps/web"),
    Path("calculation"),
    Path("dist/kb"),
    Path("docs/product"),
    Path("docs/tech"),
    Path("front-end-template"),
    Path("infrastructure"),
    Path("kb"),
    Path("scripts"),
    Path("services/reading-worker"),
    Path("supabase/migrations"),
    Path("wiki"),
    Path("wordpress"),
)
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".next",
    ".vercel",
    ".venv",
    ".wrangler",
    "__pycache__",
    "build",
    "node_modules",
    "out",
}
EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "Dockerfile",
    "worker-runtime-manifest.json",
}
EXCLUDED_SUFFIXES = {
    ".db",
    ".gif",
    ".jpeg",
    ".jpg",
    ".key",
    ".log",
    ".mov",
    ".mp3",
    ".mp4",
    ".otf",
    ".p12",
    ".pdf",
    ".pem",
    ".pyc",
    ".png",
    ".rtf",
    ".sqlite",
    ".sqlite3",
    ".svg",
    ".tsbuildinfo",
    ".ttf",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
}
ALLOWED_ENV_EXAMPLES = {
    ".env.example",
    ".env.staging.example",
}
RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
STRONG_SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "OpenAI-style key": re.compile(
        rb"sk-(?:proj-|admin-)?[A-Za-z0-9_-]{24,}"
    ),
    "WooCommerce credential": re.compile(rb"(?:ck|cs)_[A-Za-z0-9]{24,}"),
    "JWT credential": re.compile(
        rb"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}"
    ),
}


class SourceReleaseError(RuntimeError):
    """Raised when a release would be incomplete or unsafe."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_exclude(path: Path, *, entry_root: Path) -> bool:
    relative_to_entry = path.relative_to(entry_root)
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_to_entry.parts[:-1]):
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if path.name.startswith(".env") and path.name not in ALLOWED_ENV_EXAMPLES:
        return True
    return False


def release_files() -> list[Path]:
    selected: set[Path] = set()
    for relative_entry in INCLUDED_PATHS:
        entry = ROOT / relative_entry
        if not entry.exists():
            raise SourceReleaseError(f"Required release path is missing: {relative_entry}")
        if entry.is_file():
            selected.add(entry)
            continue
        for path in entry.rglob("*"):
            if path.is_file() and not should_exclude(path, entry_root=entry):
                selected.add(path)
    files = sorted(selected, key=lambda path: path.relative_to(ROOT).as_posix())
    if not files:
        raise SourceReleaseError("Source release contains no files")
    return files


def scan_for_secrets(path: Path, data: bytes) -> None:
    for label, pattern in STRONG_SECRET_PATTERNS.items():
        if pattern.search(data):
            raise SourceReleaseError(
                f"Possible {label} found in {path.relative_to(ROOT)}"
            )


def validate_source_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise SourceReleaseError(
            "Source URL must be public HTTPS without credentials or a fragment"
        )
    return value


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_release(
    *,
    output_dir: Path,
    release_id: str,
    source_url: str,
) -> tuple[Path, str, int]:
    if not RELEASE_ID_PATTERN.fullmatch(release_id):
        raise SourceReleaseError(
            "Release ID must contain only letters, numbers, dot, underscore, or dash"
        )
    source_url = validate_source_url(source_url)
    files = release_files()
    root_name = f"valley-of-light-agpl-source-{release_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{root_name}.zip"
    if archive.exists():
        raise SourceReleaseError(f"Refusing to overwrite existing archive: {archive}")

    manifest_files: list[dict[str, object]] = []
    file_payloads: list[tuple[Path, bytes]] = []
    for path in files:
        data = path.read_bytes()
        scan_for_secrets(path, data)
        relative = path.relative_to(ROOT).as_posix()
        file_payloads.append((path, data))
        manifest_files.append(
            {
                "path": relative,
                "sha256": sha256_bytes(data),
                "size": len(data),
            }
        )

    manifest = {
        "archiveFormat": "valley-agpl-source-v1",
        "excluded": [
            "credentials, environment values, customer/order/birth data, and logs",
            "raw/ copyrighted source corpus",
            "third-party and non-source media, font, and document assets",
            "dependency, cache, editor, and private deployment state",
        ],
        "files": manifest_files,
        "license": "AGPL-3.0-or-later",
        "releaseId": release_id,
        "sourceUrl": source_url,
    }
    manifest_data = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(archive, mode="x") as handle:
        for path, data in file_payloads:
            relative = path.relative_to(ROOT).as_posix()
            handle.writestr(zip_info(f"{root_name}/{relative}"), data)
        handle.writestr(
            zip_info(f"{root_name}/AGPL-SOURCE-MANIFEST.json"),
            manifest_data,
        )

    return archive, sha256_file(archive), len(file_payloads)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the reviewed AGPL source archive for one deployment"
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    archive, digest, file_count = build_release(
        output_dir=args.output_dir.resolve(),
        release_id=args.release_id,
        source_url=args.source_url,
    )
    print(
        json.dumps(
            {
                "archive": str(archive),
                "fileCount": file_count,
                "sha256": digest,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
