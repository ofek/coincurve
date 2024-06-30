# Create the shared library from the CFFI binding and the static library from ${CFFI_INPUT_LIBRARY}
if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    Python_add_library(${CFFI_OUTPUT_LIBRARY} MODULE USE_SABI 3.8 "${CFFI_C_CODE_DIR}/${CFFI_C_CODE}")
else()
    set(Python_SOABI ${SKBUILD_SOABI})
    Python_add_library(${CFFI_OUTPUT_LIBRARY} MODULE WITH_SOABI "${CFFI_C_CODE_DIR}/${CFFI_C_CODE}")
    target_compile_definitions(${CFFI_OUTPUT_LIBRARY} PRIVATE Py_LIMITED_API)
endif()

set_source_files_properties("${CFFI_C_CODE_DIR}/${CFFI_C_CODE}" PROPERTIES GENERATED 1)

# Detect whether the vendored library is a system library or not
if (PROJECT_IGNORE_SYSTEM_LIB OR NOT VENDORED_AS_SYSTEM_LIB_FOUND)
    # The build-type seems to be defined as 'MODULE', which creates issues with missing variables
    # for CMake: (This only happens on Windows though ...)
    set(CMAKE_MODULE_LINKER_FLAGS_COVERAGE "")

    add_dependencies(${CFFI_OUTPUT_LIBRARY} ${CFFI_INPUT_LIBRARY})
    add_dependencies(${CFFI_OUTPUT_LIBRARY} cffi-c-binding)
    target_include_directories(${CFFI_OUTPUT_LIBRARY} PUBLIC ${VENDORED_HEADERS_DIR})

    # Link the vendored library to the output library
    # https://docs.python.org/3/c-api/stable.html#limited-c-api
    target_link_libraries(${CFFI_OUTPUT_LIBRARY} PRIVATE ${CFFI_INPUT_LIBRARY})
elseif(VENDORED_AS_SYSTEM_LIB_FOUND)
    message(STATUS "Vendored system library found: ${VENDORED_AS_SYSTEM_LIB_LIBRARIES}")
    target_include_directories(${CFFI_OUTPUT_LIBRARY} PRIVATE ${VENDORED_AS_SYSTEM_LIB_INCLUDE_DIRS})
    add_dependencies(${CFFI_OUTPUT_LIBRARY} cffi-c-binding)
    # On windows, using the LDFLAGS field creates /libpath... secp256k1.lib (correct), but at a later stage
    # /libpath is converted to \libpath and fails to be interpreted as a flag by the linker
    # This may be an issue with libsecp256k1.pc, i.e. wrong slash used that triggers the slash conversion
    target_link_libraries(${CFFI_OUTPUT_LIBRARY} PRIVATE ${VENDORED_AS_SYSTEM_LIB_LIBRARIES})
    string(REPLACE "/libpath:" "" VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS ${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS})
    string(REPLACE "/LIBPATH:" "" VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS ${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS})
    target_link_directories(${CFFI_OUTPUT_LIBRARY} PRIVATE ${VENDORED_AS_SYSTEM_LIB_LIBRARY_DIRS})
else()
    message(FATAL_ERROR "Vendored library not found.")
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
