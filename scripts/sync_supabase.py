#!/usr/bin/env python3
"""
Sync compiled Valley of Light KB JSON into Supabase.

Default behavior is production-safe:
- validate and compile first
- compile only `status: published` articles
- abort on an empty published set unless `--allow-empty` is passed

Use `--include-drafts` only for private build-phase testing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compile_kb import compile_kb
from kb_utils import ROOT
from validate import main as validate_main


DEFAULT_OUT_DIR = ROOT / "dist" / "kb_supabase"
DEFAULT_SHARED_ENV = Path("/Users/novaos/.openclaw/workspace/.env")
DEFAULT_PLAN_OUT = ROOT / "dist" / "kb_supabase_sync_plan.json"
COUNT_KEYS = (
    "article_count",
    "claim_count",
    "link_count",
    "atom_count",
    "rule_count",
    "question_blueprint_count",
    "guardrail_count",
)
PRIMARY_KEYS = {
    "kb_articles": "id",
    "kb_claims": "claim_id",
    "kb_links": "link_id",
    "kb_atoms": "id",
    "kb_rulesets": "ruleset_id",
    "kb_rules": "id",
    "kb_question_blueprints": "blueprint_id",
    "kb_guardrail_sets": "guardrail_id",
    "kb_guardrails": "id",
}
PRUNE_ORDER = (
    "kb_guardrails",
    "kb_guardrail_sets",
    "kb_rules",
    "kb_rulesets",
    "kb_question_blueprints",
    "kb_atoms",
    "kb_links",
    "kb_claims",
    "kb_articles",
)


class SupabaseError(RuntimeError):
    pass


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    joined = " or ".join(names)
    raise SystemExit(f"Missing required environment variable: {joined}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_records(payload: Any, key: str | None = None) -> list[dict[str, Any]]:
    if key and isinstance(payload, dict):
        payload = payload.get(key)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def as_list(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value if item is not None]


def as_json_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def with_content_hash(row: dict[str, Any]) -> dict[str, Any]:
    row["content_hash"] = canonical_hash(row)
    return row


def article_search_text(article: dict[str, Any]) -> str:
    variants = article.get("variants") or {}
    if not isinstance(variants, dict):
        return ""
    return "\n\n".join(str(value).strip() for value in variants.values() if str(value).strip())


def transform_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for article in articles:
        row = {
            "id": article["id"],
            "path": article["path"],
            "title": article["title"],
            "title_en": article.get("title_en"),
            "category": article["category"],
            "article_type": article["type"],
            "status": article["status"],
            "confidence": article["confidence"],
            "source_primary": article.get("source_primary"),
            "source_primary_id": article.get("source_primary_id"),
            "source_chapter": article.get("source_chapter"),
            "source_secondary": as_list(article.get("source_secondary")),
            "source_secondary_ids": as_list(article.get("source_secondary_ids")),
            "applicable_products": as_list(article.get("applicable_products")),
            "relationship_stage": as_list(article.get("relationship_stage")),
            "question_relevance": as_list(article.get("question_relevance")),
            "related_ids": as_list(article.get("related")),
            "links": article.get("links") or [],
            "variants": article.get("variants") or {},
            "variant_claims": article.get("variant_claims") or {},
            "claim_ids": as_list(article.get("claim_ids")),
            "search_text": article_search_text(article),
            "created_on": article.get("created_at"),
            "updated_on": article.get("updated_at"),
            "last_reviewed_on": article.get("last_reviewed"),
        }
        rows.append(with_content_hash(row))
    return rows


def transform_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim in claims:
        row = {
            "claim_id": claim["claim_id"],
            "article_id": claim["article_id"],
            "article_path": claim["article_path"],
            "claim": claim["claim"],
            "source_quote": claim.get("source_quote"),
            "source_location": claim["source_location"],
            "source_raw_path": claim.get("source_raw_path"),
            "source_id": claim.get("source_id"),
            "source_start_line": claim.get("source_start_line"),
            "source_end_line": claim.get("source_end_line"),
            "confidence": claim["confidence"],
            "reasoning": claim["reasoning"],
            "product_use": as_list(claim.get("product_use")),
            "variants_supported": as_list(claim.get("variants_supported")),
        }
        rows.append(with_content_hash(row))
    return rows


def transform_links(links: list[dict[str, Any]], valid_article_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in links:
        to_id = link.get("to_id")
        synced_to_id = str(to_id) if to_id and str(to_id) in valid_article_ids else None
        row = {
            "from_id": link["from_id"],
            "to_id": synced_to_id,
            "target": link["target"],
            "link_type": link["type"],
            "reason": link.get("reason"),
            "source": link["source"],
            "resolved": bool(link.get("resolved")) and synced_to_id is not None,
        }
        row["link_id"] = canonical_hash(row)[:32]
        rows.append(row)
    return rows


def transform_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for atom in atoms:
        row = {
            "id": atom["id"],
            "system": atom["system"],
            "layer": atom["layer"],
            "category": atom["category"],
            "label": atom["label"],
            "source_article_id": atom["source_article_id"],
            "claim_ids": as_list(atom.get("claim_ids")),
            "applies_to": as_json_object(atom.get("applies_to")),
            "selectors": as_json_object(atom.get("selectors")),
            "interpretation": as_json_object(atom.get("interpretation")),
            "path": atom["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def transform_rulesets(rulesets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ruleset in rulesets:
        row = {
            "ruleset_id": ruleset["ruleset_id"],
            "version": ruleset["version"],
            "applies_to": as_json_object(ruleset.get("applies_to")),
            "rule_ids": as_list(ruleset.get("rule_ids")),
            "path": ruleset["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def transform_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule in rules:
        row = {
            "id": rule["id"],
            "ruleset_id": rule["ruleset_id"],
            "question": rule["question"],
            "priority": int(rule.get("priority") or 0),
            "when_clause": as_json_object(rule.get("when")),
            "rule_output": as_json_object(rule.get("output")),
            "path": rule["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def transform_question_blueprints(blueprints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for blueprint in blueprints:
        row = {
            "blueprint_id": blueprint["blueprint_id"],
            "version": blueprint["version"],
            "applies_to": as_json_object(blueprint.get("applies_to")),
            "title_direction": blueprint["title_direction"],
            "story_arc_template": blueprint["story_arc_template"],
            "chapter_order": as_list(blueprint.get("chapter_order")),
            "global_forbidden_claims": as_list(blueprint.get("global_forbidden_claims")),
            "style_rules": as_list(blueprint.get("style_rules")),
            "paid_unlock": as_list(blueprint.get("paid_unlock")),
            "questions": blueprint.get("questions") if isinstance(blueprint.get("questions"), list) else [],
            "chapters": blueprint.get("chapters") if isinstance(blueprint.get("chapters"), list) else [],
            "path": blueprint["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def transform_guardrail_sets(guardrail_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for guardrail_set in guardrail_sets:
        row = {
            "guardrail_id": guardrail_set["guardrail_id"],
            "version": guardrail_set["version"],
            "applies_to": as_json_object(guardrail_set.get("applies_to")),
            "guardrail_ids": as_list(guardrail_set.get("guardrail_ids")),
            "path": guardrail_set["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def transform_guardrails(guardrails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for guardrail in guardrails:
        row = {
            "id": guardrail["id"],
            "guardrail_id": guardrail["guardrail_id"],
            "system": guardrail["system"],
            "category": guardrail["category"],
            "source_article_id": guardrail["source_article_id"],
            "claim_ids": as_list(guardrail.get("claim_ids")),
            "applies_to": as_list(guardrail.get("applies_to")),
            "points_any": as_list(guardrail.get("points_any")),
            "precision_any": as_list(guardrail.get("precision_any")),
            "blocks": as_list(guardrail.get("blocks")),
            "lowers_confidence": as_list(guardrail.get("lowers_confidence")),
            "display": guardrail["display"],
            "reason": guardrail["reason"],
            "path": guardrail["path"],
        }
        rows.append(with_content_hash(row))
    return rows


def git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def row_identity(row: dict[str, Any]) -> str:
    for key in ("id", "claim_id", "link_id", "ruleset_id", "blueprint_id", "guardrail_id"):
        value = row.get(key)
        if value:
            return str(value)
    return canonical_hash(row)[:12]


def build_sync_plan(
    table_rows: dict[str, list[dict[str, Any]]],
    out_dir: Path,
    published_only: bool,
) -> dict[str, Any]:
    table_plan: dict[str, Any] = {}
    for table, rows in table_rows.items():
        table_plan[table] = {
            "row_count": len(rows),
            "content_hash": canonical_hash(rows),
            "first_ids": [row_identity(row) for row in rows[:5]],
        }

    return {
        "generated_at": now_iso(),
        "git_sha": git_sha(),
        "compiled_artifact_dir": str(out_dir.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else str(out_dir),
        "published_only": published_only,
        "write_order": list(table_rows),
        "overall_content_hash": canonical_hash(table_plan),
        "tables": table_plan,
    }


def write_sync_plan(plan: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SupabaseClient:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.base_url = url.rstrip("/")
        self.service_role_key = service_role_key

    def request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        prefer: str = "return=minimal",
    ) -> Any:
        url = f"{self.base_url}/rest/v1/{path.lstrip('/')}"
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": prefer,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SupabaseError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc

    def upsert(self, table: str, rows: list[dict[str, Any]], conflict_key: str) -> None:
        if not rows:
            return
        query = urllib.parse.urlencode({"on_conflict": conflict_key})
        self.request(
            "POST",
            f"{table}?{query}",
            rows,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def select_ids(self, table: str, key: str) -> list[str]:
        rows = self.request("GET", f"{table}?select={urllib.parse.quote(key)}&limit=10000") or []
        if not isinstance(rows, list):
            return []
        return [str(row[key]) for row in rows if isinstance(row, dict) and row.get(key) is not None]

    def delete_ids(self, table: str, key: str, ids: list[str]) -> None:
        for index in range(0, len(ids), 50):
            chunk = ids[index:index + 50]
            filter_value = "in.(" + ",".join(chunk) + ")"
            query = urllib.parse.urlencode({key: filter_value})
            self.request("DELETE", f"{table}?{query}")


def prune_rows(client: SupabaseClient, table_rows: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    pruned: dict[str, int] = {}
    for table in PRUNE_ORDER:
        key = PRIMARY_KEYS[table]
        keep_ids = {str(row[key]) for row in table_rows[table] if row.get(key) is not None}
        existing_ids = client.select_ids(table, key)
        stale_ids = [existing_id for existing_id in existing_ids if existing_id not in keep_ids]
        if stale_ids:
            client.delete_ids(table, key, stale_ids)
        pruned[table] = len(stale_ids)
    return pruned


def compile_for_sync(out_dir: Path, include_drafts: bool) -> dict[str, int]:
    validation_exit = validate_main()
    if validation_exit != 0:
        raise SystemExit(validation_exit)
    return compile_kb(out_dir=out_dir, published_only=not include_drafts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync compiled KB JSON into Supabase.")
    parser.add_argument("--include-drafts", action="store_true", help="Sync draft/review/published articles for private testing.")
    parser.add_argument("--allow-empty", action="store_true", help="Allow syncing zero articles.")
    parser.add_argument("--dry-run", action="store_true", help="Compile and report counts without contacting Supabase.")
    parser.add_argument("--prune", action="store_true", help="Delete runtime rows that are not present in the current compiled sync set.")
    parser.add_argument("--skip-compile", action="store_true", help="Use existing JSON in --out instead of validating and compiling.")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Compile output directory. Defaults to dist/kb_supabase.")
    parser.add_argument(
        "--plan-out",
        default=None,
        help=f"Optional dry-run JSON plan path. Defaults to {DEFAULT_PLAN_OUT.relative_to(ROOT)} when set to 'default'.",
    )
    parser.add_argument("--env-file", default=None, help="Optional env file containing SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    if args.env_file:
        load_env_file(Path(args.env_file).expanduser())
    load_env_file(ROOT / ".env")
    load_env_file(DEFAULT_SHARED_ENV)

    if args.skip_compile:
        manifest = read_json(out_dir / "manifest.json")
        counts = {key: int(manifest.get(key, 0)) for key in COUNT_KEYS}
    else:
        counts = compile_for_sync(out_dir, include_drafts=args.include_drafts)

    articles = transform_articles(as_records(read_json(out_dir / "kb_articles.json")))
    claims = transform_claims(as_records(read_json(out_dir / "kb_claims.json")))
    synced_article_ids = {str(article["id"]) for article in articles}
    links = transform_links(as_records(read_json(out_dir / "kb_links.json")), synced_article_ids)
    atoms = transform_atoms(as_records(read_json(out_dir / "kb_atoms.json"), "atoms"))

    rules_payload = read_json(out_dir / "kb_rules.json")
    rulesets = transform_rulesets(as_records(rules_payload, "rulesets"))
    rules = transform_rules(as_records(rules_payload, "rules"))

    blueprints = transform_question_blueprints(
        as_records(read_json(out_dir / "kb_question_blueprints.json"), "blueprints")
    )

    guardrails_payload = read_json(out_dir / "kb_guardrails.json")
    guardrail_sets = transform_guardrail_sets(as_records(guardrails_payload, "guardrail_sets"))
    guardrails = transform_guardrails(as_records(guardrails_payload, "guardrails"))

    if not articles and not args.allow_empty:
        mode = "draft-inclusive" if args.include_drafts else "published-only"
        raise SystemExit(
            f"Refusing to sync empty {mode} KB. Publish articles or pass --allow-empty."
        )

    table_rows = {
        "kb_articles": articles,
        "kb_claims": claims,
        "kb_links": links,
        "kb_atoms": atoms,
        "kb_rulesets": rulesets,
        "kb_rules": rules,
        "kb_question_blueprints": blueprints,
        "kb_guardrail_sets": guardrail_sets,
        "kb_guardrails": guardrails,
    }
    plan = build_sync_plan(table_rows, out_dir=out_dir, published_only=not args.include_drafts)

    print(
        "Prepared Supabase sync: "
        f"{len(articles)} article(s), {len(claims)} claim(s), {len(links)} link(s), "
        f"{len(atoms)} atom(s), {len(rules)} rule(s), "
        f"{len(blueprints)} question blueprint(s), {len(guardrails)} guardrail(s)"
    )
    print(f"Sync plan hash: {plan['overall_content_hash']}")
    if args.plan_out:
        plan_out = DEFAULT_PLAN_OUT if args.plan_out == "default" else Path(args.plan_out)
        if not plan_out.is_absolute():
            plan_out = ROOT / plan_out
        write_sync_plan(plan, plan_out)
        print(f"Wrote Supabase sync plan -> {plan_out.relative_to(ROOT) if plan_out.is_relative_to(ROOT) else plan_out}")
    if args.dry_run:
        print("Dry run only; Supabase was not contacted.")
        return 0

    supabase_url = first_env("VALLEY_SUPABASE_URL", "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    service_role_key = first_env("VALLEY_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    client = SupabaseClient(supabase_url, service_role_key)

    run_rows = client.request(
        "POST",
        "kb_sync_runs",
        {
            "git_sha": git_sha(),
            "published_only": not args.include_drafts,
            "article_count": counts["article_count"],
            "claim_count": counts["claim_count"],
            "link_count": counts["link_count"],
            "atom_count": counts["atom_count"],
            "rule_count": counts["rule_count"],
            "question_blueprint_count": counts["question_blueprint_count"],
            "guardrail_count": counts["guardrail_count"],
            "status": "started",
        },
        prefer="return=representation",
    )
    run_id = run_rows[0]["id"] if run_rows else None

    try:
        client.upsert("kb_articles", articles, "id")
        client.upsert("kb_claims", claims, "claim_id")
        client.upsert("kb_links", links, "link_id")
        client.upsert("kb_atoms", atoms, "id")
        client.upsert("kb_rulesets", rulesets, "ruleset_id")
        client.upsert("kb_rules", rules, "id")
        client.upsert("kb_question_blueprints", blueprints, "blueprint_id")
        client.upsert("kb_guardrail_sets", guardrail_sets, "guardrail_id")
        client.upsert("kb_guardrails", guardrails, "id")
        if args.prune:
            pruned = prune_rows(client, table_rows)
            pruned_total = sum(pruned.values())
            if pruned_total:
                print(
                    "Pruned stale Supabase rows: "
                    + ", ".join(f"{table}={count}" for table, count in pruned.items() if count)
                )
        if run_id:
            client.request(
                "PATCH",
                f"kb_sync_runs?id=eq.{urllib.parse.quote(run_id)}",
                {"status": "completed", "completed_at": now_iso()},
            )
    except Exception as exc:
        if run_id:
            client.request(
                "PATCH",
                f"kb_sync_runs?id=eq.{urllib.parse.quote(run_id)}",
                {"status": "failed", "completed_at": now_iso(), "notes": str(exc)[:1000]},
            )
        raise

    print("Supabase sync completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SupabaseError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
