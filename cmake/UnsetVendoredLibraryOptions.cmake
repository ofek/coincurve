function (UnsetVendoredLibraryOptions _prefix)
    get_cmake_property(_vars VARIABLES)
    string (REGEX MATCHALL "(^|;)${_prefix}[A-Za-z0-9_]*" _matchedVars "${_vars}")
    foreach (_var ${_matchedVars})
        unset (${_var} PARENT_SCOPE)
    endforeach()
endfunction()
