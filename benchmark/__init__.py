"""Benchmark matching quality across LLM models."""

from benchmark.compare import compare_matching, summarize_errors, summarize_model_agreement
from benchmark.schema import GoldenUserProfile, PostRecord, load_model_configs, load_posts_jsonl, load_user_profile

__all__ = [
    "PostRecord",
    "GoldenUserProfile",
    "compare_matching",
    "load_posts_jsonl",
    "load_user_profile",
    "load_model_configs",
    "summarize_errors",
    "summarize_model_agreement",
]
