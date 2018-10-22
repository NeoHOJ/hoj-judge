#!/bin/bash

# should move to config file
CG_USER=nobody
CG_GROUP=nogroup
CG_NAME=sandbox
JUDGE_TMPFS_PATH=/run/shm/judge

echo "Creating memory control group '${CG_NAME}' for ${CG_USER}:${CG_GROUP}..."
sudo cgcreate -t ${CG_USER}:${CG_GROUP} -a ${CG_USER}:${CG_GROUP} -g memory:${CG_NAME}

echo "Creating tmpfs '${JUDGE_TMPFS_PATH}'..."
mkdir -p ${JUDGE_TMPFS_PATH}
