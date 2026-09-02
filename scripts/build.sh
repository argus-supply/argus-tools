#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_dir="$(cd -- "$script_dir/.." && pwd -P)"
version=""
target_os=""
target_arch=""
output_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) version="${2:?missing version}"; shift 2 ;;
    --os) target_os="${2:?missing os}"; shift 2 ;;
    --arch) target_arch="${2:?missing arch}"; shift 2 ;;
    --output) output_dir="${2:?missing output}"; shift 2 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ "$version" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]] || { printf 'invalid version\n' >&2; exit 2; }
[[ "$target_os" == "linux" || "$target_os" == "darwin" ]] || { printf 'unsupported os\n' >&2; exit 2; }
[[ "$target_arch" == "amd64" || "$target_arch" == "arm64" ]] || { printf 'unsupported architecture\n' >&2; exit 2; }
[[ -n "$output_dir" ]] || { printf 'output is required\n' >&2; exit 2; }

for command_name in git go python3 tar zstd sha256sum; do
  command -v "$command_name" >/dev/null || { printf 'missing command: %s\n' "$command_name" >&2; exit 1; }
done
python3 "$script_dir/validate.py"
work_dir="$(mktemp -d)"
cleanup() { rm -rf -- "$work_dir"; }
trap cleanup EXIT INT TERM
stage="$work_dir/stage"
mkdir -p "$stage/bin" "$stage/licenses" "$output_dir"

mapfile -t rows < <(python3 - "$repo_dir/locks/tools.lock.json" <<'PY'
import json, sys
for item in sorted(json.load(open(sys.argv[1]))["tools"], key=lambda value: value["id"]):
    print("\t".join([item["id"], item["repository"], item["commit"], item["buildPath"], item["licensePath"], item["version"], "1" if item.get("correspondingSource") else "0"]))
PY
)
for row in "${rows[@]}"; do
  IFS=$'\t' read -r tool_id repository commit build_path license_path upstream_version source_required <<<"$row"
  source_dir="$work_dir/source-$tool_id"
  git init -q "$source_dir"
  git -C "$source_dir" remote add origin "https://github.com/$repository.git"
  git -C "$source_dir" fetch -q --depth 1 origin "$commit"
  git -C "$source_dir" checkout -q --detach FETCH_HEAD
  [[ "$(git -C "$source_dir" rev-parse HEAD)" == "$commit" ]] || { printf '%s commit mismatch\n' "$tool_id" >&2; exit 1; }
  [[ -f "$source_dir/$license_path" ]] || { printf '%s license is missing\n' "$tool_id" >&2; exit 1; }
  mkdir -p "$stage/licenses/$tool_id"
  cp "$source_dir/$license_path" "$stage/licenses/$tool_id/LICENSE"
  (
    cd "$source_dir"
    SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" CGO_ENABLED=0 GOOS="$target_os" GOARCH="$target_arch" \
      go build -mod=readonly -trimpath -buildvcs=false -ldflags='-buildid=' -o "$stage/bin/$tool_id" "$build_path"
  )
  chmod 0555 "$stage/bin/$tool_id"
  if [[ "$source_required" == "1" ]]; then
    source_archive="$output_dir/${tool_id}_source_v${upstream_version}.tar.zst"
    git -C "$source_dir" archive --format=tar --prefix="${tool_id}-${upstream_version}/" HEAD | zstd -19 -T0 -q -o "$source_archive"
  fi
done

cp "$repo_dir/locks/tools.lock.json" "$stage/tools.lock.json"
python3 "$script_dir/make_manifest.py" --root "$stage" --lock "$repo_dir/locks/tools.lock.json" --version "$version" --os "$target_os" --arch "$target_arch"
archive="$output_dir/argus-tools_${version}_${target_os}_${target_arch}.tar.zst"
epoch="$(git -C "$repo_dir" show -s --format=%ct HEAD)"
tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner -C "$stage" -cf - . | zstd -19 -T0 -q -o "$archive"
cp "$stage/manifest.json" "$output_dir/manifest_${target_os}_${target_arch}.json"
cp "$stage/sbom.cdx.json" "$output_dir/sbom_${target_os}_${target_arch}.cdx.json"
cp "$stage/provenance.json" "$output_dir/provenance_${target_os}_${target_arch}.json"
printf 'built %s\n' "$archive"
