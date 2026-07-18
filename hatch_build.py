from __future__ import annotations

import os
from typing import Any

import _cffi_backend  # noqa: PLC2701
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """
    A build hook that copies the `_cffi_backend` extension module into the wheel so that
    the `cffi` package is not required as a runtime dependency.
    """

    LICENSE_NAME = "LICENSE-cffi"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        if os.environ.get("COINCURVE_VENDOR_CFFI", "1") != "1":
            return

        cffi_shared_lib = _cffi_backend.__file__
        if cffi_shared_lib is None:
            message = "Could not locate the _cffi_backend extension module"
            raise RuntimeError(message)

        relative_path = f"coincurve/{os.path.basename(cffi_shared_lib)}"
        build_data["force_include"][cffi_shared_lib] = relative_path
        self.metadata.core.license_files.append(self.LICENSE_NAME)
