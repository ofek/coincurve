from __future__ import annotations

import argparse
from pathlib import Path

PYTHON_TAGS = {"cp310", "cp311", "cp312", "cp313", "cp314", "cp314t"}
PLATFORM_TAGS = {
    "macos-arm64",
    "macos-x86_64",
    "manylinux-aarch64",
    "manylinux-x86_64",
    "musllinux-aarch64",
    "musllinux-x86_64",
    "windows-amd64",
    "windows-arm64",
}


def classify_platform(platform: str) -> str:
    if platform.startswith("macosx_"):
        family = "macos"
    elif "manylinux" in platform:
        family = "manylinux"
    elif "musllinux" in platform:
        family = "musllinux"
    elif platform == "win_amd64":
        return "windows-amd64"
    elif platform == "win_arm64":
        return "windows-arm64"
    else:
        message = f"Unsupported wheel platform tag: {platform}"
        raise ValueError(message)

    for architecture in ("aarch64", "arm64", "x86_64"):
        if platform.endswith(f"_{architecture}"):
            return f"{family}-{architecture}"

    message = f"Unsupported wheel architecture: {platform}"
    raise ValueError(message)


def classify_wheel(wheel: Path) -> tuple[str, str]:
    _, python_tag, abi_tag, platform = wheel.stem.rsplit("-", 3)
    build_tag = abi_tag if abi_tag.endswith("t") else python_tag
    if build_tag.startswith("cp315"):
        message = f"Python 3.15 wheels are source-only for this release: {wheel.name}"
        raise ValueError(message)
    if build_tag not in PYTHON_TAGS:
        message = f"Unexpected Python tag in {wheel.name}: {build_tag}"
        raise ValueError(message)
    return build_tag, classify_platform(platform)


def check_distribution(directory: Path, version: str) -> None:
    expected_sdist = directory / f"coincurve-{version}.tar.gz"
    sdists = sorted(directory.glob("*.tar.gz"))
    if sdists != [expected_sdist]:
        message = f"Expected only {expected_sdist.name}, found: {[path.name for path in sdists]}"
        raise RuntimeError(message)

    wheels = sorted(directory.glob("*.whl"))
    actual = {classify_wheel(wheel) for wheel in wheels}
    expected = {(python, platform) for python in PYTHON_TAGS for platform in PLATFORM_TAGS}

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected or len(wheels) != len(expected):
        message = (
            f"Invalid wheel set: expected {len(expected)}, found {len(wheels)}; "
            f"missing={missing}; unexpected={unexpected}"
        )
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify coincurve release artifacts")
    parser.add_argument("directory", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    check_distribution(args.directory, args.version)


if __name__ == "__main__":
    main()
