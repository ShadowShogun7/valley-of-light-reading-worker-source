#!/usr/bin/env python3
"""Legacy compatibility wrapper for build_relationship_result_view_models.py."""

from build_relationship_result_view_models import build_view_model, main, ordered_calculation_paths
from complete_relationship_result_runtime import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CALCULATION_DIR,
    DEFAULT_CLAIMS_PATH,
    DEFAULT_OUTPUT_PATH,
    SCENARIO_ORDER,
    build_complete_relationship_result_view_model,
    build_view_model as build_complete_view_model,
    build_western_free_result_view_model,
    load_articles,
    load_claims_by_article,
    read_json,
)

__all__ = [
    "DEFAULT_ARTICLES_PATH",
    "DEFAULT_CALCULATION_DIR",
    "DEFAULT_CLAIMS_PATH",
    "DEFAULT_OUTPUT_PATH",
    "SCENARIO_ORDER",
    "build_complete_relationship_result_view_model",
    "build_complete_view_model",
    "build_view_model",
    "build_western_free_result_view_model",
    "load_articles",
    "load_claims_by_article",
    "main",
    "ordered_calculation_paths",
    "read_json",
]


if __name__ == "__main__":
    raise SystemExit(main())
