#!/bin/bash

set -e
set -x

if [ -n "${TOXENV}" ]; then
    case "${TOXENV}" in
        style);;
        ^bench$);;
        *)
            codecov
            ;;
    esac
fi
