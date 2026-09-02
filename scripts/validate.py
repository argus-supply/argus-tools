#!/usr/bin/env python3
"""Validate immutable tool locks and reviewed recipe companions."""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = {"nuclei", "fscan", "subfinder", "httpx", "katana", "ffuf", "fofax"}


def fail(message: str) -> None:
    raise SystemExit(message)


lock = json.loads((ROOT / "locks/tools.lock.json").read_text())
if lock.get("schemaVersion") != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", lock.get("goVersion", "")):
    fail("invalid tool lock header")
tools = lock.get("tools")
if not isinstance(tools, list) or {item.get("id") for item in tools} != EXPECTED:
    fail("tool lock must contain the exact ARGUS descriptor registry")
for item in tools:
    tool_id = item["id"]
    if not re.fullmatch(r"[0-9a-f]{40}", item.get("commit", "")):
        fail(f"{tool_id}: commit must be a full SHA")
    if item.get("tag") in {"latest", "main", "master", "dev"}:
        fail(f"{tool_id}: mutable tag is forbidden")
    if item.get("redistributable") is not True:
        fail(f"{tool_id}: release cannot include a non-redistributable tool")
    if item.get("license") == "GPL-3.0-only" and item.get("correspondingSource") is not True:
        fail(f"{tool_id}: GPL release requires corresponding source")
    recipe = (ROOT / f"tools/{tool_id}/tool.yaml").read_text()
    required = {f"id: {tool_id}", f"official_upstream: {item['repository']}", f"license_spdx: {item['license']}", f"argus_descriptor: {tool_id}"}
    missing = sorted(value for value in required if value not in recipe)
    if missing:
        fail(f"{tool_id}: recipe diverges from lock: {missing}")
print("validated 7 immutable tool recipes")
