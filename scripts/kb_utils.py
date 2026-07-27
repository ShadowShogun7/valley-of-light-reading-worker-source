from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"
SOURCE_MANIFEST_PATH = ROOT / "docs" / "research" / "sources.yml"

IGNORE_FILENAMES = {"README.md", "ARTICLE_TEMPLATE.md"}

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CLAIM_ID_RE = re.compile(r"^###\s+([a-z0-9]+(?:-[a-z0-9]+)*-\d{3})\s*$", re.MULTILINE)
CLAIM_CITATION_RE = re.compile(r"\(claims:\s*([^)]+)\)")
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
SOURCE_LOCATION_RE = re.compile(r"^(raw/.+?\.txt)(?::(\d+)(?:-(\d+))?)?(?:\s+section=(.+))?$")


@dataclass(frozen=True)
class SourceLocation:
    raw_path: str
    start_line: int | None = None
    end_line: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    article_id: str
    body: str
    claim: str
    source_quote: str
    source_location: str
    confidence: str
    reasoning: str
    product_use: list[str]
    variants_supported: list[str]


@dataclass(frozen=True)
class TypedLink:
    target: str
    type: str
    reason: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")

    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter is not closed with ---")

    raw_yaml = text[4:end]
    body = text[end + 5 :]
    metadata = yaml.safe_load(raw_yaml) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return metadata, body


def get_sections(body: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(body))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()

    return sections


def article_files() -> list[Path]:
    return sorted(
        path
        for path in WIKI_DIR.rglob("*.md")
        if path.name not in IGNORE_FILENAMES
    )


def expected_category(path: Path) -> str:
    return str(path.parent.relative_to(WIKI_DIR))


def claim_blocks(claims_section: str) -> list[tuple[str, str]]:
    matches = list(CLAIM_ID_RE.finditer(claims_section))
    blocks: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        claim_id = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(claims_section)
        blocks.append((claim_id, claims_section[start:end].strip()))

    return blocks


def marker_section(block: str, label: str) -> str:
    marker = f"**{label}:**"
    start = block.find(marker)
    if start == -1:
        return ""

    value_start = start + len(marker)
    next_marker = re.search(r"\n\*\*[^*\n]+:\*\*", block[value_start:])
    value_end = value_start + next_marker.start() if next_marker else len(block)
    return block[value_start:value_end].strip()


def first_line(value: str) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def parse_list_field(value: str) -> list[str]:
    items: list[str] = []
    for line in value.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def parse_claims(sections: dict[str, str], article_id: str) -> dict[str, Claim]:
    parsed: dict[str, Claim] = {}
    for claim_id, block in claim_blocks(sections.get("Claims", "")):
        quote_section = marker_section(block, "Source quote")
        quote_lines = []
        for line in quote_section.splitlines():
            stripped = line.strip()
            if stripped.startswith(">"):
                quote_lines.append(stripped[1:].strip())
        source_quote = "\n".join(line for line in quote_lines if line).strip()

        confidence = first_line(marker_section(block, "Confidence")).split()[0] if marker_section(block, "Confidence") else ""
        parsed[claim_id] = Claim(
            claim_id=claim_id,
            article_id=article_id,
            body=block,
            claim=first_line(marker_section(block, "Claim")),
            source_quote=source_quote,
            source_location=first_line(marker_section(block, "Source location")),
            confidence=confidence,
            reasoning=marker_section(block, "Reasoning").strip(),
            product_use=parse_list_field(marker_section(block, "Product use")),
            variants_supported=parse_list_field(marker_section(block, "Variants supported")),
        )
    return parsed


def parse_claim_citations(text: str) -> list[str]:
    claim_ids: list[str] = []
    for match in CLAIM_CITATION_RE.finditer(text):
        claim_ids.extend(
            claim_id.strip()
            for claim_id in match.group(1).split(",")
            if claim_id.strip()
        )
    return claim_ids


def parse_wiki_links(text: str) -> list[str]:
    targets: list[str] = []
    for match in WIKI_LINK_RE.finditer(text):
        targets.append(match.group(1).split("|", 1)[0].strip())
    return targets


def parse_typed_links(metadata: dict[str, Any]) -> list[TypedLink]:
    links: list[TypedLink] = []
    for item in metadata.get("links") or []:
        if not isinstance(item, dict):
            continue
        links.append(
            TypedLink(
                target=str(item.get("target", "")).strip(),
                type=str(item.get("type", "")).strip(),
                reason=str(item.get("reason", "")).strip(),
            )
        )
    return links


def parse_source_location(value: str) -> SourceLocation | None:
    match = SOURCE_LOCATION_RE.match(value.strip())
    if not match:
        return None

    start_line = int(match.group(2)) if match.group(2) else None
    end_line = int(match.group(3)) if match.group(3) else start_line
    section = match.group(4)
    if section:
        section = section.strip().strip("\"'")

    return SourceLocation(
        raw_path=match.group(1),
        start_line=start_line,
        end_line=end_line,
        section=section,
    )


def load_source_manifest() -> dict[str, Any]:
    if not SOURCE_MANIFEST_PATH.exists():
        return {"sources": []}
    data = yaml.safe_load(read_text(SOURCE_MANIFEST_PATH)) or {}
    if not isinstance(data, dict):
        return {"sources": []}
    sources = data.get("sources")
    if not isinstance(sources, list):
        data["sources"] = []
    return data


def source_maps(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, str]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_alias: dict[str, str] = {}
    by_path: dict[str, str] = {}

    for source in manifest.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id", "")).strip()
        if not source_id:
            continue
        by_id[source_id] = source

        raw_path = str(source.get("raw_path", "")).strip()
        if raw_path:
            by_path[raw_path] = source_id

        alias_values = [
            source.get("title"),
            source.get("title_original"),
            source.get("author"),
            *source.get("aliases", []),
        ]
        for value in alias_values:
            if value:
                by_alias[str(value).strip()] = source_id

    return by_id, by_alias, by_path


QUOTE_VARIANT_MAP = str.maketrans(
    {
        "為": "为",
        "謂": "谓",
        "燈": "灯",
        "燭": "烛",
        "較": "较",
        "雖": "虽",
        "內": "内",
        "與": "与",
        "捨": "舍",
        "後": "后",
        "發": "发",
        "闡": "阐",
        "註": "注",
        "詮": "诠",
        "淵": "渊",
        "論": "论",
        "婦": "妇",
        "財": "财",
        "親": "亲",
    }
)


def normalize_quote_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(QUOTE_VARIANT_MAP).lower()
    return re.sub(r"[\s`'\"“”‘’「」『』《》〈〉\[\]（）()，,。.:：;；、!?！？\-—]+", "", normalized)


def quote_payloads(source_quote: str) -> list[str]:
    payloads: list[str] = []
    for line in source_quote.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("引自") or stripped.startswith("From "):
            continue
        if stripped.endswith(":") and ("《" in stripped or "`" in stripped):
            continue
        stripped = stripped.strip("「」\"'")
        if stripped:
            payloads.append(stripped)
    return payloads


def raw_text_for_location(location: SourceLocation) -> tuple[str, str | None]:
    raw_path = ROOT / location.raw_path
    if not raw_path.exists():
        return "", f"raw path does not exist: {location.raw_path}"

    text = read_text(raw_path)
    if location.start_line is None:
        return text, None

    # Use only LF as the line boundary so citations match `nl`, `sed`, and editor
    # line numbers. Some OCR files contain form-feed page breaks that Python
    # `splitlines()` would otherwise count as extra lines.
    lines = text.split("\n")
    if location.start_line < 1 or location.start_line > len(lines):
        return "", f"line {location.start_line} outside file range 1-{len(lines)}"
    if location.end_line is None or location.end_line < location.start_line:
        return "", "source line range is invalid"
    if location.end_line > len(lines):
        return "", f"line {location.end_line} outside file range 1-{len(lines)}"

    return "\n".join(lines[location.start_line - 1 : location.end_line]), None


def serializable_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in metadata.items():
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
        elif isinstance(value, list):
            serialized[key] = [serializable_value(item) for item in value]
        else:
            serialized[key] = serializable_value(value)
    return serialized


def serializable_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serializable_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serializable_value(item) for item in value]
    return value
