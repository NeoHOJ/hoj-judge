#!/usr/bin/env python3
import errno
import logging
import os
import subprocess
import sys
from os import path

cwd = path.dirname(path.realpath(__file__))
sys.path.append(path.join(cwd, '..'))

from hoj_judge.protos import subtask_context_pb2
from hoj_judge.protos import subtask_response_pb2
from hoj_judge._hoj_helpers import *


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('__utils/hoj_special_judge')

rtncode_map = {
    1: HojVerdict.AC,
    6: HojVerdict.WA,
    7: HojVerdict.PE
}


def symlink_force(*args):
    src, dest, *_ = args
    try:
        os.symlink(*args)
    except OSError as err:
        if err.errno == errno.EEXIST:
            os.remove(dest)
            os.symlink(*args)
        else:
            raise e

def main(cxt):
    pathIn = cxt.subtask.input_path
    pathOut = cxt.subtask.output_path
    pathOut_user = cxt.subtask.output_user_path

    pShmIn = '/run/shm/in.txt'
    pShmOut = '/run/shm/out.txt'
    pShmAns = '/run/shm/ans.txt'

    # link to "in.txt", "out.txt", "ans.txt"
    # because some dumb checkers hardcode these filenames :(

    symlink_force(path.realpath(pathIn), pShmIn)
    symlink_force(path.realpath(pathOut_user), pShmOut)
    symlink_force(path.realpath(pathOut), pShmAns)

    subp = None
    try:
        subp = subprocess.run([
            './checker',
            pShmIn,
            pShmOut,
            pShmAns,
            # 'special-report'
        ], cwd='/run/shm')
    except Exception as err:
        logger.error(err)

    if subp is not None:
        rtncode = subp.returncode
        logger.info('Result: {}'.format(rtncode))
    else:
        rtncode = -1
        logger.error('Cannot determine return code of subprocess')

    resp = subtask_response_pb2.SubtaskResponse()

    verdict = rtncode_map.get(rtncode, None)

    if verdict is not None:
        resp.verdict = verdict.value
    else:
        logger.error('Unknown return code from testlib checker: {}'.format(rtncode))
        resp.verdict = HojVerdict.SERR.value

    return resp


if __name__ == '__main__':
    # read a protobuf from stdin
    cxtInpBin = sys.stdin.buffer.read()

    cxt = subtask_context_pb2.SubtaskContext()
    cxt.ParseFromString(cxtInpBin)

    cxtOut = main(cxt)
    sys.stdout.buffer.write(cxtOut.SerializeToString())
