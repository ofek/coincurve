cmake_minimum_required(VERSION 3.26)

project(${SKBUILD_PROJECT_NAME}
    VERSION ${SKBUILD_PROJECT_VERSION}
    LANGUAGES C
)

# Path to custom CMake functions
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake" ${CMAKE_MODULE_PATH})

# Name of the vendored library CMake target
include(SetDefaultVendoredLibrary)
SetDefaultVendoredLibrary()

set(CFFI_INPUT_LIBRARY ${VENDORED_LIBRARY_CMAKE_TARGET})

# Set the output directories for the generated C code and headers
set(CFFI_C_CODE_DIR ${PROJECT_BINARY_DIR}/_gen_c_file)
set(CFFI_C_CODE "${CFFI_INPUT_LIBRARY}_cffi_bindings.c")
set(CFFI_HEADERS_DIR ${PROJECT_BINARY_DIR}/_gen_cffi_headers)

# Shared object that wraps the CFFI binding of the vendored library
set(CFFI_OUTPUT_LIBRARY "_${VENDORED_LIBRARY_PKG_CONFIG}")

# Setting python for the host system (before change in CMAKE_SYSTEM_PROCESSOR)
find_package(Python 3 REQUIRED COMPONENTS Interpreter Development.Module Development.SABIModule)

include(SetCrossCompilerGithubActions)
SetCrossCompilerGithubActions()

# Add the subdirectories. Append CONDA to the PKG_CONFIG_PATH
if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(PKG_CONFIG_ARGN "--dont-define-prefix")
endif()
find_package(PkgConfig REQUIRED)

# Set VENDORED_AS_SYSTEM_LIB to true if the vendored library is installed as a system library
include(SetSystemLibIfExists)
SetSystemLibIfExists()

add_subdirectory(cm_vendored_library)
add_subdirectory(cm_library_cffi_headers)
add_subdirectory(cm_library_c_binding)
add_subdirectory(cm_python_module)

# Configure installation of the shared library ${CFFI_OUTPUT_LIBRARY} in the package
install(TARGETS ${CFFI_OUTPUT_LIBRARY} LIBRARY DESTINATION ${SKBUILD_PLATLIB_DIR}/${SKBUILD_PROJECT_NAME})
