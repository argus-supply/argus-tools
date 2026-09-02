# ARGUS managed toolchain

This repository aggregates reviewed upstream security tools into one immutable ARGUS toolchain release. It is not a source mirror or long-lived fork.

`locks/tools.lock.json` pins every upstream tag to its resolved commit. `tools/*/tool.yaml` records the human-reviewed recipe and redistribution decision. `scripts/build.sh` builds all seven tools from those commits for one target, and the release workflow publishes Linux and macOS archives for amd64 and arm64 together.

Runtime releases never use branches or GitHub's `latest` alias. Updating a tool starts with the scheduled discovery report or a reviewed lock change; ARGUS still requires Catalog publication and operator activation.

## Local verification

```sh
python3 scripts/validate.py
bash scripts/build.sh --version 2026.09.03.1 --os linux --arch amd64 --output dist
```

Builds require Git, Go 1.26 or newer, Python 3.11+, GNU tar, zstd, and network access to the pinned upstream repositories and Go module proxy. The release workflow supplies these dependencies.
