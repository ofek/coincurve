from __future__ import annotations

import argparse
import re
from fnmatch import fnmatch
from pathlib import Path
from zipfile import ZipFile

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
CALVER_PATTERN = re.compile(r"^\d{4}\.(?:[1-9]|1[0-2])\.\d+(?:(?:a|b|rc)\d+)?$")


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


def classify_wheel(wheel: Path, version: str) -> tuple[str, str]:
    distribution, python_tag, abi_tag, platform = wheel.stem.rsplit("-", 3)
    expected_distribution = f"coincurve-{version}"
    if distribution != expected_distribution:
        message = f"Expected wheel for {expected_distribution}, found: {wheel.name}"
        raise ValueError(message)

    build_tag = abi_tag if abi_tag.endswith("t") else python_tag
    if build_tag.startswith("cp315"):
        message = f"Python 3.15 wheels are source-only for this release: {wheel.name}"
        raise ValueError(message)
    if build_tag not in PYTHON_TAGS:
        message = f"Unexpected Python tag in {wheel.name}: {build_tag}"
        raise ValueError(message)
    return build_tag, classify_platform(platform)


def check_wheel_contents(wheel: Path) -> None:
    with ZipFile(wheel) as archive:
        files = archive.namelist()

    extension_files = [
        name for name in files if name.startswith("coincurve/_coincurve.") and name.endswith((".so", ".pyd"))
    ]
    if len(extension_files) != 1:
        message = f"Expected exactly one native Coincurve extension in {wheel.name}, found: {extension_files}"
        raise RuntimeError(message)

    forbidden_patterns = ["*_cffi_backend*", "*LICENSE-cffi*", "coincurve/_csrc/*"]
    forbidden = [name for name in files if any(fnmatch(name, pattern) for pattern in forbidden_patterns)]
    if forbidden:
        message = f"Found removed CFFI or C source artifacts in {wheel.name}: {forbidden}"
        raise RuntimeError(message)

    shared_libraries = [name for name in files if name.endswith((".dll", ".dylib", ".so")) or ".so." in name]
    undeclared = [name for name in shared_libraries if name not in extension_files and "secp256k1" not in name.lower()]
    if undeclared:
        message = f"Found unexpected shared libraries in {wheel.name}: {undeclared}"
        raise RuntimeError(message)


def check_distribution(directory: Path) -> None:
    sdists = sorted(directory.glob("*.tar.gz"))
    if len(sdists) != 1:
        message = f"Expected exactly one source distribution, found: {[path.name for path in sdists]}"
        raise RuntimeError(message)

    sdist_name = sdists[0].name
    sdist_prefix = "coincurve-"
    sdist_suffix = ".tar.gz"
    if not sdist_name.startswith(sdist_prefix) or not sdist_name.endswith(sdist_suffix):
        message = f"Unexpected source distribution name: {sdist_name}"
        raise RuntimeError(message)
    version = sdist_name[len(sdist_prefix) : -len(sdist_suffix)]
    if CALVER_PATTERN.fullmatch(version) is None:
        message = f"Distribution version is not YYYY.MM.PATCH CalVer: {version}"
        raise RuntimeError(message)

    wheels = sorted(directory.glob("*.whl"))
    for wheel in wheels:
        check_wheel_contents(wheel)
    actual = {classify_wheel(wheel, version) for wheel in wheels}
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
    args = parser.parse_args()
    check_distribution(args.directory)


if __name__ == "__main__":
    main()
