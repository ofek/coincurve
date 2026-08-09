# Create an interpreter-specific CPython extension linked directly to libsecp256k1.
set(Python_SOABI ${SKBUILD_SOABI})
set(COINCURVE_C_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
Python_add_library(
    ${COINCURVE_EXTENSION_TARGET}
    MODULE
    WITH_SOABI
    "${COINCURVE_C_SOURCE_DIR}/module.c"
    "${COINCURVE_C_SOURCE_DIR}/private_key.c"
    "${COINCURVE_C_SOURCE_DIR}/public_key.c"
    "${COINCURVE_C_SOURCE_DIR}/xonly_key.c"
    "${COINCURVE_C_SOURCE_DIR}/signatures.c"
    "${COINCURVE_C_SOURCE_DIR}/batch.c"
)
target_compile_features(${COINCURVE_EXTENSION_TARGET} PRIVATE c_std_11)
set_target_properties(
    ${COINCURVE_EXTENSION_TARGET}
    PROPERTIES
    C_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

option(COINCURVE_STRICT_WARNINGS "Treat warnings in Coincurve-owned C sources as errors." OFF)
if (COINCURVE_STRICT_WARNINGS)
    if (MSVC)
        target_compile_options(${COINCURVE_EXTENSION_TARGET} PRIVATE /W4 /WX /wd4152)
    else()
        target_compile_options(${COINCURVE_EXTENSION_TARGET} PRIVATE -Wall -Wextra -Werror)
    endif()
endif()

option(COINCURVE_SANITIZE "Instrument Coincurve-owned C sources with address and undefined-behavior sanitizers." OFF)
if (COINCURVE_SANITIZE AND NOT MSVC)
    target_compile_options(${COINCURVE_EXTENSION_TARGET} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(${COINCURVE_EXTENSION_TARGET} PRIVATE -fsanitize=address,undefined)
endif()

option(COINCURVE_COVERAGE "Instrument Coincurve-owned C sources for LLVM source-based coverage." OFF)
if (COINCURVE_COVERAGE)
    if (NOT CMAKE_C_COMPILER_ID MATCHES "Clang")
        message(FATAL_ERROR "COINCURVE_COVERAGE requires Clang, llvm-profdata, and llvm-cov.")
    endif()
    if (CMAKE_C_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC")
        target_compile_options(
            ${COINCURVE_EXTENSION_TARGET}
            PRIVATE
            /clang:-fprofile-instr-generate
            /clang:-fcoverage-mapping
        )
        if (CMAKE_SYSTEM_PROCESSOR MATCHES "^(AMD64|amd64|x86_64)$")
            set(COINCURVE_PROFILE_RUNTIME_ARCH "x86_64")
        elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(ARM64|arm64|aarch64)$")
            set(COINCURVE_PROFILE_RUNTIME_ARCH "aarch64")
        elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(X86|x86|i.86)$")
            set(COINCURVE_PROFILE_RUNTIME_ARCH "i386")
        else()
            message(FATAL_ERROR "LLVM coverage is unsupported for Windows architecture ${CMAKE_SYSTEM_PROCESSOR}.")
        endif()
        execute_process(
            COMMAND ${CMAKE_C_COMPILER} "--print-file-name=clang_rt.profile-${COINCURVE_PROFILE_RUNTIME_ARCH}.lib"
            OUTPUT_VARIABLE COINCURVE_PROFILE_RUNTIME
            OUTPUT_STRIP_TRAILING_WHITESPACE
            COMMAND_ERROR_IS_FATAL ANY
        )
        if (NOT EXISTS "${COINCURVE_PROFILE_RUNTIME}")
            message(FATAL_ERROR "Clang profile runtime not found: ${COINCURVE_PROFILE_RUNTIME}")
        endif()
        target_link_libraries(${COINCURVE_EXTENSION_TARGET} PRIVATE "${COINCURVE_PROFILE_RUNTIME}")
    else()
        target_compile_options(
            ${COINCURVE_EXTENSION_TARGET}
            PRIVATE
            -fprofile-instr-generate
            -fcoverage-mapping
        )
        target_link_options(${COINCURVE_EXTENSION_TARGET} PRIVATE -fprofile-instr-generate)
    endif()
endif()

if (NOT COINCURVE_COVERAGE)
    include(CheckIPOSupported)
    check_ipo_supported(RESULT COINCURVE_IPO_SUPPORTED OUTPUT COINCURVE_IPO_ERROR LANGUAGES C)
    if (COINCURVE_IPO_SUPPORTED)
        set_property(TARGET ${COINCURVE_EXTENSION_TARGET} PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
        if (TARGET ${VENDORED_LIBRARY_CMAKE_TARGET})
            set_property(TARGET ${VENDORED_LIBRARY_CMAKE_TARGET} PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
        endif()
    else()
        message(STATUS "Interprocedural optimization is unavailable: ${COINCURVE_IPO_ERROR}")
    endif()
endif()

# Link either the vendored target or a compatible system library.
if (PROJECT_IGNORE_SYSTEM_LIB OR NOT VENDORED_AS_SYSTEM_LIB_FOUND)
    add_dependencies(${COINCURVE_EXTENSION_TARGET} ${VENDORED_LIBRARY_CMAKE_TARGET})
    target_include_directories(
        ${COINCURVE_EXTENSION_TARGET}
        PRIVATE
        "${COINCURVE_C_SOURCE_DIR}"
        "${VENDORED_HEADERS_DIR}"
    )

    # Link the vendored library to the extension.
    target_link_libraries(${COINCURVE_EXTENSION_TARGET} PRIVATE ${VENDORED_LIBRARY_CMAKE_TARGET})
elseif(VENDORED_AS_SYSTEM_LIB_FOUND)
    message(STATUS "Vendored system library found: ${VENDORED_AS_SYSTEM_LIB_LIBRARIES}")
    target_include_directories(
        ${COINCURVE_EXTENSION_TARGET}
        PRIVATE
        "${COINCURVE_C_SOURCE_DIR}"
        ${VENDORED_AS_SYSTEM_LIB_INCLUDE_DIRS}
    )
    target_link_libraries(${COINCURVE_EXTENSION_TARGET} PRIVATE ${VENDORED_AS_SYSTEM_LIB_LIBRARIES})
    if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
        # Normalize pkg-config library directories because later Windows processing corrupts `/libpath` flags.
        string(REPLACE "/libpath:" "" VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS "${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS}")
        string(REPLACE "/LIBPATH:" "" VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS "${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS}")
    endif()
    target_link_directories(${COINCURVE_EXTENSION_TARGET} PRIVATE ${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS})

    include(CheckCSourceCompiles)
    set(CMAKE_REQUIRED_LIBRARIES PkgConfig::VENDORED_AS_SYSTEM_LIB)
    check_c_source_compiles(
        [=[
#include <stddef.h>
#include <secp256k1.h>
#include <secp256k1_ecdh.h>
#include <secp256k1_extrakeys.h>
#include <secp256k1_recovery.h>
#include <secp256k1_schnorrsig.h>

/* Volatile reads preserve symbol relocations through compiler optimization. */
typedef void (*required_symbol)(void);

static required_symbol volatile required_symbols[] = {
    (required_symbol)secp256k1_ecdh,
    (required_symbol)secp256k1_ecdsa_recover,
    (required_symbol)secp256k1_keypair_create,
    (required_symbol)secp256k1_schnorrsig_sign32,
};

int main(void)
{
    int missing = 0;
    size_t index;

    for (index = 0; index < sizeof(required_symbols) / sizeof(required_symbols[0]); ++index) {
        missing |= required_symbols[index] == NULL;
    }

    return missing;
}
]=]
        COINCURVE_SYSTEM_SECP256K1_COMPLETE
    )
    unset(CMAKE_REQUIRED_LIBRARIES)
    if (NOT COINCURVE_SYSTEM_SECP256K1_COMPLETE)
        message(FATAL_ERROR "The system libsecp256k1 must provide the ECDH, recovery, extrakeys, and Schnorr modules.")
    endif()
else()
    message(FATAL_ERROR "Vendored library not found.")
endif()

# Windows links against a static libsecp256k1 without dllimport decorations.
if(CMAKE_SYSTEM_NAME STREQUAL "Windows" AND VENDORED_LIBRARY_STATIC_BUILD)
    target_compile_definitions(${COINCURVE_EXTENSION_TARGET} PRIVATE SECP256K1_STATIC)
endif()
