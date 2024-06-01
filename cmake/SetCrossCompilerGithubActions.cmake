function(SetCrossCompilerGithubActions)
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
endfunction()
