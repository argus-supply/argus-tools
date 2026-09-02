#!/usr/bin/env python3
"""Create deterministic release manifests, SBOM data, and provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True, type=pathlib.Path)
parser.add_argument("--lock", required=True, type=pathlib.Path)
parser.add_argument("--version", required=True)
parser.add_argument("--os", required=True)
parser.add_argument("--arch", required=True)
args = parser.parse_args()
lock = json.loads(args.lock.read_text())


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


tools = []
files = []
for item in lock["tools"]:
    binary = args.root / "bin" / item["id"]
    if not binary.is_file():
        raise SystemExit(f"missing built tool: {item['id']}")
    file_digest = digest(binary)
    tools.append({key: item[key] for key in ("id", "repository", "tag", "version", "commit", "license")})
    files.append({"path": f"bin/{item['id']}", "size": binary.stat().st_size, "sha256": file_digest, "executable": True})
manifest = {"schemaVersion": 1, "component": "tools", "version": args.version, "os": args.os, "arch": args.arch, "tools": tools, "files": files}
(args.root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
(args.root / "SHA256SUMS").write_text("".join(f"{item['sha256']}  {item['path']}\n" for item in files))
components = [{"type": "application", "name": item["id"], "version": item["version"], "licenses": [{"license": {"id": item["license"]}}], "properties": [{"name": "argus:upstream-commit", "value": item["commit"]}]} for item in tools]
sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "metadata": {"component": {"type": "application", "name": "argus-tools", "version": args.version}}, "components": components}
(args.root / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")
provenance = {"schemaVersion": 1, "builder": "argus-supply/argus-tools", "buildType": "pinned-go-source", "version": args.version, "target": {"os": args.os, "arch": args.arch}, "materials": [{"uri": f"https://github.com/{item['repository']}", "digest": {"gitCommit": item["commit"]}} for item in tools]}
(args.root / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
