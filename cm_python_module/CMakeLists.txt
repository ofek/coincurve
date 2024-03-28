# Create the shared library from the CFFI binding and the static library from ${CFFI_INPUT_LIBRARY}
if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    Python_add_library(${CFFI_OUTPUT_LIBRARY} MODULE USE_SABI 3.8 "${CFFI_C_CODE_DIR}/${CFFI_C_CODE}")
else()
    set(Python_SOABI ${SKBUILD_SOABI})
    Python_add_library(${CFFI_OUTPUT_LIBRARY} MODULE WITH_SOABI "${CFFI_C_CODE_DIR}/${CFFI_C_CODE}")
    target_compile_definitions(${CFFI_OUTPUT_LIBRARY} PRIVATE Py_LIMITED_API)
endif()

set_source_files_properties("${CFFI_C_CODE_DIR}${CFFI_C_CODE}" PROPERTIES GENERATED 1)

# Detect whether the vendored library is a system library or not
if (PROJECT_IGNORE_SYSTEM_LIB OR NOT LOCAL_INPUT_LIBRARY)
    # The build-type seems to be defined as 'MODULE', which creates issues with missing variables
    # for CMake: (This only happens on Windows though ...)
    set(CMAKE_MODULE_LINKER_FLAGS_COVERAGE "")

    add_dependencies(${CFFI_OUTPUT_LIBRARY} ${CFFI_INPUT_LIBRARY})
    add_dependencies(${CFFI_OUTPUT_LIBRARY} cffi-c-binding)
    target_include_directories(${CFFI_OUTPUT_LIBRARY} PUBLIC ${VENDORED_HEADERS_DIR})

    # Link the vendored library to the output library
    # https://docs.python.org/3/c-api/stable.html#limited-c-api
    target_link_libraries(${CFFI_OUTPUT_LIBRARY} PRIVATE ${CFFI_INPUT_LIBRARY})
else()
    target_link_libraries(${CFFI_OUTPUT_LIBRARY} PRIVATE PkgConfig::PKGCONFIG_INPUT_LIB)
endif()


# Add platform-specific definitions
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_compile_definitions(${CFFI_OUTPUT_LIBRARY} PUBLIC "IS_LINUX")
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    target_compile_definitions(${CFFI_OUTPUT_LIBRARY} PUBLIC "IS_MACOS")
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_compile_definitions(${CFFI_OUTPUT_LIBRARY} PUBLIC "IS_WINDOWS")
endif()