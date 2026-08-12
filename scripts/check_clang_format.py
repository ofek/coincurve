from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_source_files(root: Path) -> list[Path]:
    result = subprocess.run(
        [  # noqa: S607
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*.c",
            "*.h",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    paths = (Path(path) for path in result.stdout.decode().split("\0") if path)
    return sorted(path for path in paths if (root / path).is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Check C source formatting and print unified diffs.")
    parser.add_argument("--fix", action="store_true", help="Write formatted output back to source files.")
    args = parser.parse_args()

    source_files = find_source_files(PROJECT_ROOT)
    if not source_files:
        parser.error("No C source or header files were found.")

    changed = 0
    for path in source_files:
        source_path = PROJECT_ROOT / path
        original = source_path.read_bytes()
        result = subprocess.run(
            ["clang-format", f"--assume-filename={source_path}"],  # noqa: S607
            input=original,
            check=False,
            stdout=subprocess.PIPE,
        )
        if result.returncode:
            return result.returncode
        if original == result.stdout:
            continue

        changed += 1
        if args.fix:
            source_path.write_bytes(result.stdout)
            continue

        name = path.as_posix()
        diff = difflib.unified_diff(
            original.decode().splitlines(keepends=True),
            result.stdout.decode().splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
        sys.stdout.writelines(diff)

    if changed and not args.fix:
        return 1
    if changed:
        file_label = "file" if changed == 1 else "files"
        print(f"Formatted {changed} {file_label}")
        return 0

    file_label = "file" if len(source_files) == 1 else "files"
    print(f"{len(source_files)} {file_label} already formatted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
