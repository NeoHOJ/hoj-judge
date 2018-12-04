import logging
import math
import os
from os import path
import re
import subprocess
import shlex
import sys
import time

from peewee import *
from colors import color

from google.protobuf.wrappers_pb2 import Int64Value
import hoj_judge.models_hoj as m
from . import protos
from ._hoj_helpers import *


SANDBOX_PATH = '/run/shm/judge'
TESTDATA_PATH = path.relpath(path.join(__package__, '..', 'testdata'))
TMP_RUNLOG_PATH = '/run/shm/sandbox.log'
TMP_USEROUT_PATH = '/tmp/test'
TMP_COMPLOG_PATH = '/run/shm/compile.log'
PROG_EXEC_PATH = './program'
SOURCE_FILENAME = 'test-file.cpp'

# for security reasons, sudo closes fds that are larger some integer (2 by default).
# since we want to keep them in order to keep logs, we need to configure sudo to allow
# exceptions to allow overriding this limitation
cmd_task_tpl = ('sudo -C {fd_close_from} -u nobody '
    '-- ../nsjail -C ../nsjail.cfg -D {cwd} '
    '-t {time} --cgroup_mem_max {mem} --log_fd {log_fd} '
    '-- {exec}')

cmd_compile_tpl = 'g++ -Wall -O2 -fdiagnostics-color=always -o {output} {src}'
cmd_compile_checker_tpl = 'g++ -O2 -fdiagnostics-color=always -o {output} {src}'

logger = logging.getLogger('hoj_judge')


def taskCompile(cmd, logf_compile, verbose=True):
    t = time.perf_counter()
    subp = subprocess.run(
        cmd,
        cwd=SANDBOX_PATH,
        stderr=logf_compile
    )
    t = time.perf_counter() - t

    if verbose:
        logf_compile.seek(0)
        for line in logf_compile.readlines():
            print('>>> {}'.format(line), end='')

    return subp, t

def judgeSingleSubtask(task, paths, checker_args):
    infile, outfile = paths

    log_file = open(TMP_RUNLOG_PATH, 'w+')
    # the file is possibly not owned by the user executing task (via sudo),
    # and latter writing will fail
    os.chmod(TMP_RUNLOG_PATH, 0o666)
    log_file_fd = log_file.fileno()

    cmd_task = cmd_task_tpl.format(
        cwd=shlex.quote(path.realpath(SANDBOX_PATH)),
        time=math.ceil(task.time_limit / 1000),
        mem=math.ceil(task.mem_limit * 1024),
        log_fd=log_file_fd,
        fd_close_from=log_file_fd + 1,
        exec=PROG_EXEC_PATH
    )

    f_in = open(infile, 'r')
    f_out_user = open(TMP_USEROUT_PATH, 'w+')

    time_task = time.perf_counter()

    subp_task = subprocess.run(
        shlex.split(cmd_task),
        cwd=path.dirname(__file__),
        stdin=f_in,
        stdout=f_out_user,
        pass_fds=(log_file_fd,)
    )

    time_task = time.perf_counter() - time_task

    f_in.close()
    f_out_user.close()

    # parse output and filter out the STATs key-value pair

    # get size of the log
    # TODO: interrupt if the log file is empty. the worker probably fails to start up
    log_file.seek(0, 2)
    sz = log_file.tell()

    log_file.seek(0)
    log_dict = {}
    for ln in log_file:
        mat = re.match(r'\[S\]\[\d+?\] __STAT__:0 (?:\d+?:)?([\w]+)\s+=\s+(.*)', ln)
        if mat is None:
            # print('>>> {}'.format(ln), end='')
            continue
        log_dict[mat.group(1)] = mat.group(2)
    log_file.close()

    logger.info(log_dict)

    log_used_keys = [
        'cgroup_memory_failcnt',
        'cgroup_memory_max_usage',
        'time'
    ]

    for k in log_used_keys:
        if k not in log_dict:
            print(color('===== SER =====', fg='white', style='negative') +
                ' Cannot find key "{}" from log'.format(k))
            return HojVerdict.SERR, log_dict

    time_used = int(log_dict['time'])
    mem_used = int(log_dict['cgroup_memory_max_usage'])

    # check if the process ends with error
    # TODO: RF, OLE
    verdict = None
    process_failed = (subp_task.returncode != 0)

    if log_dict['cgroup_memory_failcnt'] != '0':
        verdict = HojVerdict.MLE
    elif time_used > task.time_limit:
        verdict =  HojVerdict.TLE
    elif subp_task.returncode != 0:
        verdict =  HojVerdict.RE

    if process_failed:
        print('Subtask {} after {:.0f}ms'.format(color('failed', fg='yellow'), time_task * 1000))
    else:
        print('Subtask {} after {:.0f}ms'.format('finished', time_task * 1000))

    if verdict is not None:
        print(color('===== {:3} ====='.format(verdict.name), fg='magenta', style='negative'))
        return verdict, log_dict

    cxt = protos.subtask_context_pb2.SubtaskContext(
        # TODO: fill in counter info
        subtask={
            'time_limit': task.time_limit,
            'mem_limit': task.mem_limit,
            'input_path': infile,
            'output_path': outfile,
            'output_user_path': TMP_USEROUT_PATH,
        },
        stat={
            'time_used': time_used,
            'mem_used': mem_used,
        },
        log_dict=log_dict,
    )

    subp_checker = subprocess.run(
        checker_args,
        input=cxt.SerializeToString(),
        stdout=subprocess.PIPE
    )

    resp = protos.subtask_response_pb2.SubtaskResponse()
    if subp_checker.returncode == 0:
        resp.ParseFromString(subp_checker.stdout)
    else:
        resp.verdict = HojVerdict.SERR.value

    # alternative way for a Python file; faster
    # import runpy
    # tolerantDiff = runpy.run_path(checker_path)
    # resp = tolerantDiff['main'](cxt)

    if resp.verdict == HojVerdict.WA.value:
        lineno_wrap = Int64Value()
        # lineno only makes sense in tolerantDiff
        resp.meta['lineno'].Unpack(lineno_wrap)
        print(color('===== WA  =====', fg='red', style='negative') +
              '  @ line {}'.format(lineno_wrap.value))
        return HojVerdict.WA, log_dict
    elif resp.verdict != HojVerdict.AC.value:
        print(color('===== {:3} ====='.format(HojVerdict(resp.verdict).name), fg='blue', style='negative'))
        return HojVerdict(resp.verdict), log_dict

    print(color('===== AC  =====', fg='green', style='negative'))
    return HojVerdict(resp.verdict), log_dict

def judgeSubmission(submission, judge_desc):
    problem = submission.problem
    print('Sandbox path is set to {}'.format(color(SANDBOX_PATH, style='bold')))
    print()

    print(color('--- Judge Description', style='bold'))
    print(judge_desc)
    print()

    samples = judge_desc.samples
    subtasks = judge_desc.subtasks
    all_tasks = samples + subtasks

    print(color('--- Checking test data', style='bold'))
    testdata_path_tpl = lambda label, ext: path.join(TESTDATA_PATH, '{}/{}.{}'.format(problem.problem, label, ext))
    _testdata, testdata_healthy = hoj_collect_testdata(all_tasks, testdata_path_tpl)
    if not testdata_healthy:
        print(color('Failed to collect test data, refusing to continue', fg='red', style='bold'))
        return None, -1
    print()

    print(color('Writing code to disk...', style='bold'))
    with open(path.join(SANDBOX_PATH, SOURCE_FILENAME), 'w') as f:
        f.write(submission.submission_code)

    print(color('Compiling...', style='bold'))

    cmd_compile = cmd_compile_tpl.format(
        src=shlex.quote(SOURCE_FILENAME),
        output=PROG_EXEC_PATH
    )

    with open(TMP_COMPLOG_PATH, 'w+') as logf_compile:
        subp_compile, t = taskCompile(shlex.split(cmd_compile), logf_compile)

    if subp_compile.returncode == 0:
        print(color('Compilation success after {:.0f}ms'.format(t * 1000), fg='green', style='bold'))
    else:
        print(color('Compilation failed after {:.0f}ms'.format(t * 1000), fg='red', style='bold+negative'))

        # fill all fields with CE
        # TODO: wiring out the error message (how?)
        return [[HojVerdict.CE, 0, 0] for _ in all_tasks], 0

    print()

    if problem.problem_special:
        print(color('Special judge. Compiling checker...', style='bold'))

        checker_out = '/tmp/special.cpp'
        checker_exec = '/run/shm/checker'

        with open(checker_out, 'w') as f:
            f.write(problem.problem_check)

        cmd_compile_special = cmd_compile_checker_tpl.format(
            src=shlex.quote(checker_out),
            output=checker_exec
        )

        subp = subprocess.run(
            shlex.split(cmd_compile_special) + ['-I' + path.realpath('include')],
            cwd=SANDBOX_PATH  # should be JUDGE_ROOT
        )
        if subp.returncode != 0:
            raise Exception('Failed to compile checker')

        checker_args = [
            path.join(__package__, '..', 'utils', 'hoj_special_judge.py'),
            checker_exec
        ]
    else:
        checker_args = [path.join(__package__, '..', 'utils', 'tolerant_diff.py')]

    print(color('--- Sample judging tasks', style='bold'))

    testdata_iter = iter(_testdata)
    judge_results = []
    pretest_fail = False

    for task in samples:
        print(color('Judging sample:', fg='blue', style='bold'), task)
        verdict, info = judgeSingleSubtask(task, next(testdata_iter), checker_args)

        judge_results.append([
            verdict,
            int(info.get('time', -1)),
            int(info.get('cgroup_memory_max_usage', -1))
        ])

        if verdict == HojVerdict.SERR:
            pretest_fail = True

    print()

    if pretest_fail:
        print('Error occurred when running samples -- halting')
        results = judge_results + [[HojVerdict.OTHER, -1, -1] for _ in subtasks]
        return results, 0

    print(color('--- Real judging tasks', style='bold'))

    score_total = 0

    group_num = 0
    task_group_iter = iter(judge_desc.task_groups)

    cur_group_no = 0
    cur_group_count, cur_group_score = None, 0
    cur_group_accepted = True

    for task in subtasks:
        if cur_group_count is None:
            cur_group_count, cur_group_score = next(task_group_iter)
            group_num += 1
            cur_group_no = 0
            cur_group_accepted = True

        msg = 'Judging subtask group #{}, {}/{}:'.format(group_num, cur_group_no + 1, cur_group_count)
        print(color(msg, fg='blue', style='bold'), task)

        verdict, info = judgeSingleSubtask(task, next(testdata_iter), checker_args)
        if verdict != HojVerdict.AC and not task.fallthrough:
            cur_group_accepted = False

        judge_results.append([
            verdict,
            int(info.get('time', -1)),
            int(info.get('cgroup_memory_max_usage', -1))
        ])

        cur_group_no += 1
        if cur_group_no >= cur_group_count:
            score = cur_group_score if cur_group_accepted else 0
            score_total += score
            cur_group_count = None
            print(color('End of group, giving score {}/{}'.format(score, cur_group_score), fg='blue', style='bold'))
            print()

    return judge_results, score_total
