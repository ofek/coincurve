cmake_minimum_required(VERSION 3.26)

project(${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES C
)


# Path to custom CMake functions
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})

# Name of the vendored library recognized by pkg-config
set(CFFI_INPUT_LIBRARY ${VENDORED_LIBRARY_PKG_CONFIG})

# Set the output directories for the generated C code and headers
set(CFFI_C_CODE_DIR ${PROJECT_BINARY_DIR}/_gen_c_file)
set(CFFI_C_CODE "${CFFI_INPUT_LIBRARY}_cffi_bindings.c")
set(CFFI_HEADERS_DIR ${PROJECT_BINARY_DIR}/_gen_cffi_headers)

# Shared object that wraps the CFFI binding and the vendored library
set(CFFI_OUTPUT_LIBRARY "_lib${CFFI_INPUT_LIBRARY}")


# Setting python for the host system (before change in CMAKE_SYSTEM_PROCESSOR)
find_package(Python 3 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)

# Cross-compilation options: This is setup for Github/Actions runners
# For Linux, we use cibuildwheel to build the wheels, which uses Docker
if (PROJECT_CROSS_COMPILE_TARGET AND CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(AUTOMATIC_OSX_TARGETS "armv7" "armv7s" "arm64" "arm64e" "x86_64")

    if ("${PROJECT_CROSS_COMPILE_TARGET}" IN_LIST AUTOMATIC_OSX_TARGETS)
        set(CMAKE_OSX_ARCHITECTURES ${PROJECT_CROSS_COMPILE_TARGET})
    else()
        message(FATAL_ERROR "Cross-compilation target not supported: >${PROJECT_CROSS_COMPILE_TARGET}< (${AUTOMATIC_OSX_TARGETS})")
    endif()

elseif (PROJECT_CROSS_COMPILE_TARGET AND CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(AUTOMATIC_WINDOWS_TARGETS "AMD64" "x86" "arm64")

    if ("${PROJECT_CROSS_COMPILE_TARGET}" IN_LIST AUTOMATIC_WINDOWS_TARGETS)
        # Cross-compilation for Windows host system:
        set(CMAKE_SYSTEM_PROCESSOR ${PROJECT_CROSS_COMPILE_TARGET})
        set(CMAKE_LIBRARY_ARCHITECTURE  ${PROJECT_CROSS_COMPILE_TARGET})
    else()
        message(FATAL_ERROR "Cross-compilation target not supported: >${PROJECT_CROSS_COMPILE_TARGET}< (${AUTOMATIC_WINDOWS_TARGETS})")
    endif()
endif()

# Add the subdirectories. Append CONDA to the PKG_CONFIG_PATH
list(APPEND ENV{PKG_CONFIG_PATH} "$ENV{CONDA_PREFIX}/lib/pkgconfig")
find_package(PkgConfig REQUIRED)
pkg_check_modules(PKGCONFIG_INPUT_LIB IMPORTED_TARGET ${CFFI_INPUT_LIBRARY}>=2)


# Try to find the library in the system
find_library(LOCAL_INPUT_LIBRARY ${CFFI_INPUT_LIBRARY})
if (COINCURVE_IGNORE_SYSTEM_LIB OR NOT LOCAL_INPUT_LIBRARY)
    add_subdirectory(cm_vendored_library)
    if (NOT VENDORED_HEADERS_DIR)
        message(FATAL_ERROR "Vendored library headers not found")
    endif()
    message(STATUS "The vendored library include located at: ${VENDORED_HEADERS_DIR}")
endif()
add_subdirectory(cm_library_cffi_headers)
add_subdirectory(cm_library_c_binding)
add_subdirectory(cm_python_module)

# Configure installation of the shared library ${CFFI_OUTPUT_LIBRARY} in the package
install(TARGETS ${CFFI_OUTPUT_LIBRARY} LIBRARY DESTINATION ${SKBUILD_PLATLIB_DIR}/${SKBUILD_PROJECT_NAME})
