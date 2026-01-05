import logging
import os
import re
import sys
import warnings

from .__version__ import __version__

_deprecation_behavior: str = os.environ.get("JINKO_SDK_DEPRECATION", "warn").lower()
_DEPRECATED_OPERATIONS: list[dict] = []
try:
    from .types.deprecated_operations import (
        DEPRECATED_OPERATIONS as _SPEC_DEPRECATED_OPERATIONS,
    )

    _DEPRECATED_OPERATIONS.extend(_SPEC_DEPRECATED_OPERATIONS)
except Exception:
    pass


def _path_matches(template: str, path: str) -> bool:
    if "{" not in template:
        return template == path
    pattern = re.sub(r"\{[^/]+\}", r"[^/]+", template)
    return re.fullmatch(pattern, path) is not None


def _find_spec_deprecation(method: str, path: str) -> dict | None:
    method_upper = method.upper()
    for operation in _DEPRECATED_OPERATIONS:
        if operation.get("http_method", "").upper() != method_upper:
            continue
        template = operation.get("path")
        if not template:
            continue
        if _path_matches(template, path):
            return operation
    return None


def handle_deprecation(
    method: str,
    path: str,
):
    data = _find_spec_deprecation(method, path)
    if not data:
        return
    migration = data.get("migration")
    parts = [f"Deprecated API used: {method.upper()} {path}."]
    message = " ".join(parts)
    if migration:
        message += f" Migration guidance: {migration}"
    logger = logging.getLogger("jinko_helpers.deprecation")
    logger.info(
        "api_deprecated",
        extra={
            "event": "api_deprecated",
            "http_method": method.upper(),
            "path": path,
            "client_version": __version__,
        },
    )
    behavior = _deprecation_behavior.lower().strip()
    if behavior not in {"warn", "error", "silent"}:
        behavior = "warn"
    if behavior == "silent":
        return
    if behavior == "warn":
        print(message, file=sys.stderr)
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        return
    if behavior == "error":
        raise DeprecationWarning(message)
