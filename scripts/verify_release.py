#!/usr/bin/env python3
"""Verify a complete four-target toolchain release directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=pathlib.Path)
parser.add_argument("--version", required=True)
args = parser.parse_args()
for os_name in ("linux", "darwin"):
    for arch in ("amd64", "arm64"):
        archive = args.directory / f"argus-tools_{args.version}_{os_name}_{arch}.tar.zst"
        manifest = args.directory / f"manifest_{os_name}_{arch}.json"
        if not archive.is_file() or not manifest.is_file():
            raise SystemExit(f"missing release output for {os_name}/{arch}")
        value = json.loads(manifest.read_text())
        if value["version"] != args.version or value["os"] != os_name or value["arch"] != arch:
            raise SystemExit(f"manifest target mismatch for {os_name}/{arch}")
        if {item["id"] for item in value["tools"]} != {"nuclei", "fscan", "subfinder", "httpx", "katana", "ffuf", "fofax"}:
            raise SystemExit(f"descriptor mismatch for {os_name}/{arch}")
files = sorted(path for path in args.directory.iterdir() if path.is_file() and path.name != "SHA256SUMS")
(args.directory / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files))
print(f"verified {len(files)} release assets")
