function (SetSystemLibIfExists)
    set(_paths "$ENV{PKG_CONFIG_PATH}" "$ENV{CONDA_PREFIX}/Library/lib/pkgconfig" "$ENV{CONDA_PREFIX}/lib/pkgconfig")
    cmake_path(CONVERT "${_paths}" TO_NATIVE_PATH_LIST _paths)
    set(ENV{PKG_CONFIG_PATH} ${_paths})

    pkg_check_modules(VENDORED_AS_SYSTEM_LIB IMPORTED_TARGET GLOBAL ${VENDORED_LIBRARY_PKG_CONFIG}>=${VENDORED_LIBRARY_PKG_CONFIG_VERSION})
endfunction()
