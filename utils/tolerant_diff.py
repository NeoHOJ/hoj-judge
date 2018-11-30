#!/usr/bin/env python3
import logging
import os
import re
import sys
from os import path

from google.protobuf.wrappers_pb2 import Int64Value

cwd = path.dirname(path.realpath(__file__))
sys.path.append(path.join(cwd, '..'))

from hoj_judge.protos import subtask_context_pb2
from hoj_judge.protos import subtask_response_pb2
from hoj_judge._hoj_helpers import *


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('__utils/tolerant_diff')

def rstrip(s):
    while s and (s[-1] == '\r' or s[-1] == '\n'):
        s = s[:-1]
    return s


def tolerantDiffAt(fa, fb):
    line = 0
    while True:
        la, lb = fa.readline(), fb.readline()
        if la:
            if not lb or rstrip(la.strip()) != rstrip(lb.strip()): return line
        elif lb:
            return line
        else:
            break
        line += 1
    return -1

def main(cxt):
    pathOut = cxt.subtask.output_path
    pathOut_user = cxt.subtask.output_user_path

    fOut_user = open(pathOut_user, 'r')
    fOut = open(pathOut, 'r')
    diffResult = tolerantDiffAt(fOut_user, fOut)
    fOut_user.close()
    fOut.close()

    logger.info('diff result: {}'.format(diffResult))

    resp = subtask_response_pb2.SubtaskResponse()
    resp.meta['lineno'].Pack(Int64Value(value=diffResult + 1))

    if diffResult >= 0:
        resp.verdict = HojVerdict.WA.value
    else:
        resp.verdict = HojVerdict.AC.value
    return resp


if __name__ == '__main__':
    # read a protobuf from stdin
    cxtInpBin = sys.stdin.buffer.read()

    cxt = subtask_context_pb2.SubtaskContext()
    cxt.ParseFromString(cxtInpBin)

    # logger.info('--- Context from stdin')
    # logger.info(cxt)

    cxtOut = main(cxt)
    sys.stdout.buffer.write(cxtOut.SerializeToString())
