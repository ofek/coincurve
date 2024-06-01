# create folder for _gen code
file(MAKE_DIRECTORY ${CFFI_HEADERS_DIR})

macro(generate_cffi_header src_header cffi_header cffi_dir)
    add_custom_command(
        OUTPUT              ${cffi_dir}/${cffi_header}
        COMMAND             ${Python_EXECUTABLE} ${CMAKE_CURRENT_LIST_DIR}/compose_cffi_headers.py
                            ${src_header} ${cffi_header} ${cffi_dir}
        MAIN_DEPENDENCY     ${CMAKE_CURRENT_LIST_DIR}/compose_cffi_headers.py
        DEPENDS             ${src_header}
        WORKING_DIRECTORY   ${cffi_dir}
    )
    add_custom_target(${cffi_header} ALL DEPENDS ${cffi_dir}/${cffi_header})
endmacro()

# Extract files from full path of src_headers
if(VENDORED_HEADERS_DIR)
    file(GLOB src_headers ${VENDORED_HEADERS_DIR}/*.h)
elseif(VENDORED_AS_SYSTEM_LIB_FOUND)
    message(WARNING "Using system library ${VENDORED_LIBRARY_CMAKE_TARGET}. The list of headers is set to:"
                    "   <system_include>/*${VENDORED_LIBRARY_CMAKE_TARGET}/*.h")
    file(GLOB src_headers ${VENDORED_AS_SYSTEM_LIB_INCLUDE_DIRS}/*${VENDORED_LIBRARY_CMAKE_TARGET}*.h)
    message(STATUS "   Generating CFFI header for ${src_headers}")
else()
    message(FATAL_ERROR "Headers for CFFI cannot be found. Exiting")
endif()

add_custom_target(headers-for-cffi)

foreach(src_header ${src_headers})
    get_filename_component(cffi_header ${src_header} NAME)
    get_filename_component(src_header_dir ${src_header} DIRECTORY)
    generate_cffi_header(${src_header_dir} ${cffi_header} ${CFFI_HEADERS_DIR})
    add_dependencies(headers-for-cffi ${cffi_header})
endforeach()
