#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)" || {
  echo "Couldn't determine the script's running directory, which probably matters, bailing out" >&2
  exit 2
}

input_source="${1:-https://api.jinko.ai/openapi.json}"
output_file="${2:-${script_dir}/../../jinko_helpers/types/deprecated_operations.py}"

echo "Generating deprecated operations from ${input_source}..." 1>&2

python3 - "${input_source}" "${output_file}" <<'PY'
import json
import sys
import urllib.request

input_source = sys.argv[1]
output_file = sys.argv[2]

if input_source.startswith("http://") or input_source.startswith("https://"):
    with urllib.request.urlopen(input_source) as response:
        data = response.read().decode("utf-8")
else:
    with open(input_source, "r", encoding="utf-8") as handle:
        data = handle.read()

spec = json.loads(data)
paths = spec.get("paths", {})
methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}

operations = []
for path, path_item in paths.items():
    if not isinstance(path_item, dict):
        continue
    for method, operation in path_item.items():
        if method.lower() not in methods or not isinstance(operation, dict):
            continue
        if not operation.get("deprecated", False):
            continue
        entry = {
            "http_method": method.upper(),
            "path": path,
        }
        migration = operation.get("x-jinko-migration")
        if isinstance(migration, str):
            entry["migration"] = migration
        else:
            description = operation.get("description")
            summary = operation.get("summary")
            for candidate in (description, summary):
                if not isinstance(candidate, str):
                    continue
                lower = candidate.lower()
                if "use " in lower or "deprecated" in lower:
                    entry["migration"] = candidate
                    break
        docs_url = operation.get("x-jinko-docs-url")
        if isinstance(docs_url, str):
            entry["docs_url"] = docs_url
        operations.append(entry)

lines = [
    f"# generated from: {input_source}",
    f"# timestamp: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}",
    "",
    "DEPRECATED_OPERATIONS = [",
]
for entry in operations:
    lines.append(f"    {entry!r},")
lines.append("]")
lines.append("")
lines.append("__all__ = [\"DEPRECATED_OPERATIONS\"]")

with open(output_file, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines))
PY

echo "Deprecated operations generated in ${output_file}" 1>&2
