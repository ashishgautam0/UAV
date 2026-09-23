"""Deterministic draft checks; semantic grounding still requires review."""
import re


def validate_outreach_draft(kind, content):
    if kind in {"cold_dm", "cold-dm"}:
        if len(content.encode("utf-16-le")) // 2 > 300:
            return "Connection note exceeds 300 characters; rewrite, do not truncate."
        if re.search(r"(?im)^\s*(?:variant\s*\d|subject\s*:|to\s*:|```)", content):
            return "Save one connection note only, without variants, headers or code fences."
        if re.search(r"(?i)(?:resume|cv|pdf).{0,30}attach|attach.{0,30}(?:resume|cv|pdf)", content):
            return "Connection notes cannot attach a resume."
    return None
