from __future__ import annotations

import os
import shutil
from functools import cached_property
from importlib.metadata import PackagePath, distribution
from typing import Any, ClassVar

import _cffi_backend  # noqa: PLC2701
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """
    A build hook that copies the `_cffi_backend` extension module into the wheel so that
    the `cffi` package is not required as a runtime dependency.
    """

    LICENSE_NAME = "LICENSE-cffi"
    FALLBACK_LICENSES: ClassVar[dict[str, str]] = {
        "1": "LICENSE-cffi-1",
        "2": "LICENSE-cffi-2",
    }

    @cached_property
    def local_cffi_license(self) -> str:
        return os.path.join(self.root, self.LICENSE_NAME)

    @staticmethod
    def get_cffi_distribution_license_files() -> list[PackagePath]:
        return [
            file
            for file in distribution("cffi").files or []
            if file.name == "LICENSE" and file.parts[0].endswith(".dist-info")
        ]

    def locate_cffi_license(self) -> str:
        cffi_distribution = distribution("cffi")
        license_files = self.get_cffi_distribution_license_files()
        if len(license_files) == 1:
            return str(license_files[0].locate())

        major_version = cffi_distribution.version.partition(".")[0]
        fallback_name = self.FALLBACK_LICENSES.get(major_version)
        if fallback_name is None:
            message = (
                f"Could not locate the CFFI license for version {cffi_distribution.version}, "
                "and no matching fallback is available"
            )
            raise RuntimeError(message)
        return os.path.join(self.root, fallback_name)

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        if os.environ.get("COINCURVE_VENDOR_CFFI", "1") != "1":
            return

        cffi_shared_lib = _cffi_backend.__file__
        if cffi_shared_lib is None:
            message = "Could not locate the _cffi_backend extension module"
            raise RuntimeError(message)

        relative_path = f"coincurve/{os.path.basename(cffi_shared_lib)}"
        build_data["force_include"][cffi_shared_lib] = relative_path
        shutil.copy2(self.locate_cffi_license(), self.local_cffi_license)
        self.metadata.core.license_files.append(self.LICENSE_NAME)

    def finalize(self, version: str, build_data: dict[str, Any], artifact: str) -> None:  # noqa: ARG002
        if os.path.isfile(self.local_cffi_license):
            os.remove(self.local_cffi_license)
