#!/bin/bash

pushd "$(dirname "${0}")/.." > /dev/null
basedir=$(pwd -L)

protoc -I. --python_out=. hoj_judge/protos/*.proto

popd > /dev/null
