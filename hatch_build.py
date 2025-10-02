from __future__ import annotations

import os
import shutil
from functools import cached_property
from importlib.metadata import PackagePath, distribution
from typing import Any

import _cffi_backend  # noqa: PLC2701
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """
    A build hook that copies the `_cffi_backend` extension module into the wheel so that
    the `cffi` package is not required as a runtime dependency.
    """

    LICENSE_NAME = "LICENSE-cffi"

    @cached_property
    def local_cffi_license(self) -> str:
        return os.path.join(self.root, self.LICENSE_NAME)

    @staticmethod
    def get_cffi_distribution_license_files() -> list[PackagePath]:
        license_files = []

        dist_files = distribution("cffi").files or []
        for f in dist_files:
            if f.name != "LICENSE":
                continue

            orig_f = f

            # `cffi-1.17.1.dist-info/licenses/LICENSE`
            if f.parent.name == "licenses":
                f = f.parent

            if f.parent.name.endswith(".dist-info"):
                license_files.append(orig_f)

        return license_files

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        cffi_shared_lib = _cffi_backend.__file__
        relative_path = f"coincurve/{os.path.basename(cffi_shared_lib)}"
        build_data["force_include"][cffi_shared_lib] = relative_path

        license_files = self.get_cffi_distribution_license_files()
        if len(license_files) != 1:
            message = f"Expected exactly one LICENSE file in cffi distribution, got {len(license_files)}"
            raise RuntimeError(message)

        license_file = license_files[0]
        shutil.copy2(license_file.locate(), self.local_cffi_license)
        self.metadata.core.license_files.append(self.LICENSE_NAME)

    def finalize(self, version: str, build_data: dict[str, Any], artifact: str) -> None:  # noqa: ARG002
        os.remove(self.local_cffi_license)
