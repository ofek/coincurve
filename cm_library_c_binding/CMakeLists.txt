# create folder for _gen code
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/_gen_c_file)

if (NOT CFFI_C_CODE)
    set(CFFI_C_CODE _cffi_c_code.c)
endif()  

if (NOT CFFI_C_CODE_DIR)
    set(CFFI_C_CODE_DIR "${PROJECT_BINARY_DIR}/_gen_c_file")
endif()

# Copy the build.py file to the build directory
file(COPY ${CMAKE_CURRENT_LIST_DIR}/build.py DESTINATION ${CFFI_C_CODE_DIR})

include(VerifyPythonModule)
VerifyPythonModule(cffi ${Python_EXECUTABLE})

if (VENDORED_HEADERS_DIR)
    set(_static_build 'ON')
else()
    message(STATUS "CFFI C-file is built for a SHARED system library")
    set(_static_build 'OFF')
endif()

# Generate the CFFI source file
add_custom_command(
    OUTPUT                ${CFFI_C_CODE_DIR}/${CFFI_C_CODE}
    COMMAND               ${Python_EXECUTABLE} ${CFFI_C_CODE_DIR}/build.py
                          ${CFFI_HEADERS_DIR}
                          ${CFFI_C_CODE_DIR}/${CFFI_C_CODE} ${_static_build}
    MAIN_DEPENDENCY       ${CMAKE_CURRENT_LIST_DIR}/build.py
    DEPENDS               headers-for-cffi
    WORKING_DIRECTORY     ${CFFI_C_CODE_DIR}
    COMMENT               "Generating CFFI source file"
)

add_custom_target(cffi-c-binding ALL DEPENDS ${CFFI_C_CODE_DIR}/${CFFI_C_CODE})
add_dependencies(cffi-c-binding headers-for-cffi)
