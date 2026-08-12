cmake_minimum_required(VERSION 3.26)

project(${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES C
)

# Add the directory containing custom CMake functions.
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})

# Configure the name of the vendored library CMake target.
include(SetDefaultVendoredLibrary)
SetDefaultVendoredLibrary()

set(COINCURVE_EXTENSION_TARGET "_coincurve")

# Find the host Python before cross-compilation changes CMAKE_SYSTEM_PROCESSOR.
find_package(Python 3 REQUIRED COMPONENTS Interpreter Development.Module)

include(SetCrossCompilerGithubActions)
SetCrossCompilerGithubActions()

# Configure pkg-config before adding the build subdirectories.
if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(PKG_CONFIG_ARGN "--dont-define-prefix")
endif()
find_package(PkgConfig REQUIRED)

# Detect whether libsecp256k1 is installed as a compatible system library.
include(SetSystemLibIfExists)
SetSystemLibIfExists()

add_subdirectory(cm_vendored_library)
add_subdirectory(src/coincurve/_csrc)

# Configure installation of the extension in the package.
set(PROJECT_PACKAGE_DIR ${SKBUILD_PLATLIB_DIR}/${SKBUILD_PROJECT_NAME})
install(TARGETS ${COINCURVE_EXTENSION_TARGET} LIBRARY DESTINATION ${PROJECT_PACKAGE_DIR})

# A dynamically linked vendored libsecp256k1 must survive the temporary build
# directory so wheel repair tools can find it. Keep it beside the extension and
# use a loader-relative runtime path; Windows already searches the module's
# directory for dependent DLLs.
if ((PROJECT_IGNORE_SYSTEM_LIB OR NOT VENDORED_AS_SYSTEM_LIB_FOUND) AND NOT VENDORED_LIBRARY_STATIC_BUILD)
    if (APPLE)
        set_target_properties(${COINCURVE_EXTENSION_TARGET} PROPERTIES INSTALL_RPATH "@loader_path")
    elseif (UNIX)
        set_target_properties(${COINCURVE_EXTENSION_TARGET} PROPERTIES INSTALL_RPATH "$ORIGIN")
    endif()

    # Linux otherwise creates a fully versioned library and two symlinks, which
    # wheel archives store as three copies. Make the SONAME the real file and
    # omit the development-only linker namelink from the installed package.
    if (CMAKE_SYSTEM_NAME STREQUAL "Linux")
        get_target_property(VENDORED_LIBRARY_SOVERSION ${VENDORED_LIBRARY_CMAKE_TARGET} SOVERSION)
        if (VENDORED_LIBRARY_SOVERSION)
            set_target_properties(${VENDORED_LIBRARY_CMAKE_TARGET} PROPERTIES VERSION ${VENDORED_LIBRARY_SOVERSION})
        endif()
        unset(VENDORED_LIBRARY_SOVERSION)
    endif()

    install(
        TARGETS ${VENDORED_LIBRARY_CMAKE_TARGET}
        LIBRARY DESTINATION ${PROJECT_PACKAGE_DIR} NAMELINK_SKIP
        RUNTIME DESTINATION ${PROJECT_PACKAGE_DIR}
    )
endif()
