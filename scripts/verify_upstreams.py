#!/usr/bin/env python3
"""Verify every pinned tag resolves to the recorded immutable commit."""

from __future__ import annotations

import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
lock = json.loads((root / "locks/tools.lock.json").read_text())
for item in lock["tools"]:
    tag_ref = f"refs/tags/{item['tag']}"
    result = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{item['repository']}.git", tag_ref, f"{tag_ref}^{{}}"],
        check=True,
        text=True,
        capture_output=True,
    )
    refs = dict(line.split("\t", 1)[::-1] for line in result.stdout.splitlines())
    resolved = refs.get(f"{tag_ref}^{{}}", refs.get(tag_ref))
    if resolved != item["commit"]:
        raise SystemExit(f"{item['id']}: {item['tag']} resolved to {resolved}, expected {item['commit']}")
print("verified 7 upstream tag-to-commit locks")
