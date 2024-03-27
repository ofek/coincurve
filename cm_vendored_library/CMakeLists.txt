# Note that this could also be handled by: ExternalProject_Add
# However, FetchContent is a more modern and simpler way to handle this
# https://cmake.org/cmake/help/latest/module/ExternalProject.html
# https://cmake.org/cmake/help/latest/module/FetchContent.html
include(GNUInstallDirs)
include(FetchContent)
include(UpdateVendoredLibraryOptions)

# Set ULR based upon CMake definitions
if (NOT VENDORED_UPSTREAM_URL)
    set(VENDORED_UPSTREAM_URL "https://github.com/bitcoin-core/secp256k1/archive")
endif()

if (NOT VENDORED_UPSTREAM_REF)
    set(VENDORED_UPSTREAM_REF "1ad5185cd42c0636104129fcc9f6a4bf9c67cc40")
endif()

if (NOT VENDORED_UPSTREAM_SHA)
    set(VENDORED_UPSTREAM_SHA "ba34be4319f505c5766aa80b99cfa696cbb2993bfecf7d7eb8696106c493cb8c")
endif()

if (NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# -fPIC is needed since we will link it from a shared object
if (VENDORED_LIBRARY_STATIC_BUILD)
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)
endif()

UpdateVendoredLibraryOptions("VENDORED_OPTION" ${VENDORED_LIBRARY_OPTION_PREFIX})


FetchContent_Declare(
    vendored_library
    URL "${VENDORED_UPSTREAM_URL}/${VENDORED_UPSTREAM_REF}.tar.gz"
    URL_HASH "SHA256=${VENDORED_UPSTREAM_SHA}"
)
FetchContent_MakeAvailable(vendored_library)

if (NOT IS_DIRECTORY ${vendored_library_SOURCE_DIR}/include)
    message(FATAL_ERROR "The vendored library include files does not exist. Exiting")
else()
    set(VENDORED_HEADERS_DIR "${vendored_library_SOURCE_DIR}/include" CACHE PATH "Path to the vendored headers")

    # Avoid spurious warnings when building the vendored library
    unset(VENDORED_UPSTREAM_URL PARENT_SCOPE)
    unset(VENDORED_UPSTREAM_REF PARENT_SCOPE)
    unset(VENDORED_UPSTREAM_SHA PARENT_SCOPE)
endif()
