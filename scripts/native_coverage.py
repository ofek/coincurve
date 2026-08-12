from __future__ import annotations

import importlib.machinery
import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "src" / "coincurve" / "_csrc"
OUTPUT_DIR = PROJECT_ROOT / "build" / "native-coverage"


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        message = f"Required LLVM coverage tool is not on PATH: {name}"
        raise RuntimeError(message)
    return path


def find_extension() -> Path:
    distribution = importlib.metadata.distribution("coincurve")
    candidates = []
    for relative_path in distribution.files or ():
        path = Path(distribution.locate_file(relative_path)).resolve()
        if path.name.startswith("_coincurve.") and any(
            path.name.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES
        ):
            candidates.append(path)

    if len(candidates) != 1:
        message = f"Expected one installed _coincurve extension, found: {candidates}"
        raise RuntimeError(message)
    return candidates[0]


def run_command(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=capture_output, text=True)


def prepare_output_directory() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)


def run_tests(arguments: list[str]) -> None:
    environment = os.environ.copy()
    environment["LLVM_PROFILE_FILE"] = str(OUTPUT_DIR / "coincurve-%p.profraw")
    subprocess.run([sys.executable, "-m", "pytest", *arguments], check=True, env=environment)


def create_reports(llvm_profdata: str, llvm_cov: str) -> None:
    extension = find_extension()
    raw_profiles = sorted(OUTPUT_DIR.glob("*.profraw"))
    if not raw_profiles:
        message = f"No raw profiles were written to {OUTPUT_DIR}"
        raise RuntimeError(message)

    profile = OUTPUT_DIR / "coverage.profdata"
    sources = sorted(SOURCE_DIR.glob("*.c"))
    run_command([llvm_profdata, "merge", "-sparse", *map(str, raw_profiles), "-o", str(profile)])

    common_arguments = [str(extension), f"-instr-profile={profile}", *map(str, sources)]
    run_command([llvm_cov, "report", *common_arguments])

    lcov_report = run_command(
        [llvm_cov, "export", "-format=lcov", *common_arguments],
        capture_output=True,
    )
    (OUTPUT_DIR / "coverage.lcov").write_text(lcov_report.stdout, encoding="utf-8")

    html_directory = OUTPUT_DIR / "html"
    run_command([
        llvm_cov,
        "show",
        "-format=html",
        f"-output-dir={html_directory}",
        "-show-branches=count",
        *common_arguments,
    ])
    print(f"HTML report: {html_directory / 'index.html'}")
    print(f"LCOV report: {OUTPUT_DIR / 'coverage.lcov'}")


def main() -> None:
    llvm_profdata = require_tool("llvm-profdata")
    llvm_cov = require_tool("llvm-cov")
    prepare_output_directory()
    run_tests(sys.argv[1:] or ["tests"])
    create_reports(llvm_profdata, llvm_cov)


if __name__ == "__main__":
    main()
