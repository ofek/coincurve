# Verify CFFI python module is available
function(VerifyPythonModule module python_executable)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    execute_process(
        COMMAND         ${python_executable} -c "import ${module}"
        ERROR_VARIABLE  _error
        OUTPUT_QUIET
        ERROR_STRIP_TRAILING_WHITESPACE
    )

    if(_error)
        message(FATAL_ERROR "${module} is required to build coincurve")
    endif()
endfunction()
