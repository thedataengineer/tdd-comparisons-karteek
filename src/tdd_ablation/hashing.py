"""Canonical SHA-256 tree hashing for artifact directories."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tdd_ablation.contracts import ContractError


def hash_tree(root: Path) -> str:
    """Compute canonical SHA-256 hash of directory content.

    Hashes relative pathnames and file bytes in sorted order.
    Rejects symlinks and path escapes.
    """
    if not root.exists():
        raise ContractError(f"hash_tree path does not exist: {root}")

    hasher = hashlib.sha256()

    if root.is_file():
        hasher.update(root.read_bytes())
        return hasher.hexdigest()

    file_paths = []
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ContractError(f"symlinks not allowed in artifact directory: {p}")
        if p.is_file():
            rel_path = p.relative_to(root).as_posix()
            file_paths.append((rel_path, p))

    file_paths.sort(key=lambda item: item[0])

    for rel_path, p in file_paths:
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(p.read_bytes())
        hasher.update(b"\x00")

    return hasher.hexdigest()
