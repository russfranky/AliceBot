#!/usr/bin/env python3
"""Install the Alice Hermes memory provider into an existing Hermes install."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "docs" / "integrations" / "hermes-memory-provider" / "plugins" / "memory" / "alice"


def _resolve_hermes_memory_plugins_dir() -> Path:
    try:
        import plugins.memory as memory_plugins  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - runtime-dependent
        raise RuntimeError(
            "Could not import Hermes memory plugins package. "
            "Run this script with the Python environment where Hermes is installed."
        ) from exc
    return Path(memory_plugins.__file__).resolve().parent


def _validate_source_tree(path: Path) -> None:
    required = ("__init__.py", "plugin.yaml", "README.md")
    missing = [name for name in required if not (path / name).exists()]
    if missing:
        raise RuntimeError(f"source plugin tree is incomplete: missing {', '.join(missing)}")


def _install(*, destination_root: Path, force: bool, symlink: bool) -> Path:
    destination = destination_root / "alice"

    if destination.exists():
        if not force:
            raise RuntimeError(
                f"destination already exists: {destination}. Re-run with --force to replace it."
            )
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)

    if symlink:
        destination.symlink_to(SOURCE_DIR, target_is_directory=True)
    else:
        shutil.copytree(SOURCE_DIR, destination)

    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="install_hermes_alice_memory_provider.py",
        description="Install Alice as a Hermes external memory provider plugin.",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=None,
        help=(
            "Hermes memory plugin root directory. Defaults to the discovered "
            "<hermes>/plugins/memory path in the active Python environment."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing alice provider directory at the destination.",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Install as a symlink instead of copying files.",
    )

    args = parser.parse_args()

    _validate_source_tree(SOURCE_DIR)

    destination_root = args.destination_root
    if destination_root is None:
        destination_root = _resolve_hermes_memory_plugins_dir()

    destination_root = destination_root.resolve()
    if not destination_root.exists():
        raise RuntimeError(f"destination root does not exist: {destination_root}")

    installed_path = _install(
        destination_root=destination_root,
        force=args.force,
        symlink=args.symlink,
    )

    print("Installed Alice memory provider plugin")
    print(f"  source: {SOURCE_DIR}")
    print(f"  destination: {installed_path}")
    print()
    print("Next steps:")
    print("  1) hermes memory setup      # choose alice")
    print("  2) hermes memory status")
    print("  3) hermes config set memory.provider alice")
    print("  4) ./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py")
    print()
    print("Bridge B2 config keys:")
    print("  - prefetch_recall_limit")
    print("  - prefetch_max_recent_changes")
    print("  - prefetch_max_open_loops")
    print("  - prefetch_include_non_promotable_facts")
    print("  - sync_turn_capture_enabled")
    print("  - memory_write_capture_enabled")
    print("  - bridge_mode")
    print("  - session_end_flush_timeout_seconds")
    print("Legacy compatibility keys still accepted: prefetch_limit, max_recent_changes,")
    print("max_open_loops, include_non_promotable_facts, auto_capture, mirror_memory_writes, capture_mode")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
