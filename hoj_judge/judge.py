import io
import logging
import math
import os
from os import path
import re
import resource
import subprocess
import shlex
import sys
import time


from peewee import *
from colors import color

from google.protobuf.wrappers_pb2 import Int64Value
import hoj_judge.models_hoj as m
from . import protos
from . import pipes
from .utils import pformat
from ._hoj_helpers import *


SANDBOX_PATH = '/run/shm/judge'
TESTDATA_PATH = path.relpath(path.join(__package__, '..', 'testdata'))
TMP_RUNLOG_PATH = '/run/shm/sandbox.log'
TMP_USEROUT_PATH = '/tmp/test'
TMP_COMPLOG_PATH = '/run/shm/compile.log'
LOG_STDOUT_PATH = '/tmp/judge.stdout.log'
LOG_STDERR_PATH = '/tmp/judge.stderr.log'
PROG_EXEC_PATH = './program'

SOURCE_FILENAME = 'test-file.cpp'
COMPILE_MEM_LIM = 128 * 1024 * 1024
COMPILE_OUT_LIM = 8 * 1024
USER_OUTPUT_LIM = 64 * 1024 * 1024  # 64MB is enough for most cases (?)

# for security reasons, sudo closes fds that are larger by some integer (2 by default).
# since we want to keep them in order to keep logs, we need to configure sudo to allow
# exceptions to allow overriding this limitation
cmd_task_tpl = ('sudo -C {fd_close_from} -u nobody '
    '-- ../nsjail -C ../nsjail.cfg -D {cwd} '
    '-t {time} --cgroup_mem_max {mem} --log_fd {log_fd} '
    '-- {exec}')

cmd_compile_tpl = 'g++ -Wall -O2 -fdiagnostics-color=always -o {output} {src}'
cmd_compile_checker_tpl = 'g++ -O2 -fdiagnostics-color=always -o {output} {src}'

logger = logging.getLogger(__name__)


def taskCompile(cmd, journals):
    logger.debug('Starting subproc for task compiling: %r', cmd)

    def preexec():
        resource.setrlimit(resource.RLIMIT_AS, (COMPILE_MEM_LIM, COMPILE_MEM_LIM))

    t = time.perf_counter()
    subp, ole = pipes.run_with_pipes(
        cmd,
        cwd=SANDBOX_PATH,
        preexec_fn=preexec,
        pipe_stderr=(journals[1], COMPILE_OUT_LIM),
    )
    logger.debug('Ending subproc for task compiling after %.0fms', (time.perf_counter() - t) * 1000)

    msg = journals[1]._read()

    buf = io.StringIO(msg)
    # TODO: remove redundency
    for line in buf.readlines():
        logger.debug('COMPILE >>> %s', line[:-1])

    return subp, ole[0] or ole[1]

def taskCompileChecker(problem, checker_out, checker_exec):
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


def judgeSingleSubtask(task, paths, checker_args):
    infile, outfile = paths

    log_file = open(TMP_RUNLOG_PATH, 'w+')
    # the file is possibly not owned by the user executing task (via sudo),
    # and latter writing will fail
    os.chmod(TMP_RUNLOG_PATH, 0o666)
    log_file_fd = log_file.fileno()

    cmd_task_str = cmd_task_tpl.format(
        cwd=shlex.quote(path.realpath(SANDBOX_PATH)),
        time=math.ceil(task.time_limit / 1000),
        mem=math.ceil(task.mem_limit * 1024),
        log_fd=log_file_fd,
        fd_close_from=log_file_fd + 1,
        exec=PROG_EXEC_PATH
    )
    cmd_task = shlex.split(cmd_task_str)

    f_in = open(infile, 'r')
    # No, you really can't trust the user's output
    f_out_user = open(TMP_USEROUT_PATH, 'w+b')

    time_task = time.perf_counter()

    logger.debug('Starting subproc for subtask: %r', cmd_task)

    subp_task, (is_stdout_ole, _) = pipes.run_with_pipes(
        cmd_task,
        cwd=path.dirname(__file__),
        stdin=f_in,
        pipe_stdout=(f_out_user, USER_OUTPUT_LIM),
        stderr=subprocess.DEVNULL,
        pass_fds=(log_file_fd,)
    )

    logger.debug('Ending subproc for subtask after %.0fms', (time.perf_counter() - time_task) * 1000)

    process_failed = (subp_task.returncode != 0)
    if process_failed:
        logger.debug('Subtask {} with return code %d'.format(color('failed', fg='yellow')), subp_task.returncode)

    f_in.close()
    f_out_user.close()

    # parse output and filter out the STATs key-value pair

    # get size of the log
    # TODO: interrupt if the log file is empty. the worker probably fails to start up
    log_file.seek(0, 2)  # SEEK_END = 2
    sz = log_file.tell()

    log_file.seek(0)
    log_dict = {}
    for ln in log_file:
        mat = re.match(r'\[S\]\[\d+?\] __STAT__:0 (?:\d+?:)?([\w]+)\s+=\s+(.*)', ln)
        if mat is None:
            # TODO: triage the message to separate file
            logger.debug('SANDBOX >>> %s', ln[:-1])
            continue
        log_dict[mat.group(1)] = mat.group(2)
    log_file.close()

    logger.debug('captured stat dict:\n%s', pformat(log_dict))

    log_used_keys = [
        'cgroup_memory_failcnt',
        'cgroup_memory_max_usage',
        'exit_normally',
        'time'
    ]

    for k in log_used_keys:
        if k not in log_dict:
            logger.error('Cannot find key "%s" form log, which is mandatory', k)
            print(color('===== SER =====', fg='white', style='negative') +
                ' MISSING_KEY')
            return HojVerdict.SERR, log_dict

    time_used = int(log_dict['time'])
    mem_used = int(log_dict['cgroup_memory_max_usage'])

    # TODO: RF
    if is_stdout_ole:
        # looks like nsjail ignores SIGPIPE and let children continue to run
        # until TLE, because of the pid-namespace :(
        print(color('===== OLE =====', style='negative'))
        return HojVerdict.OLE, log_dict

    # check if the process ends with error
    verdict = None

    if log_dict['cgroup_memory_failcnt'] != '0':
        verdict = HojVerdict.MLE
    elif (log_dict['exit_normally'] == 'false' and time_used >= task.time_limit):
        verdict =  HojVerdict.TLE
    elif process_failed:
        verdict =  HojVerdict.RE

    if verdict is not None:
        print(color('===== {:3} ====='.format(verdict.name), fg='magenta', style='negative') +
            ' REPORTED_BY_SANDBOX')
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
        # TODO: triage stderr; use alt. way to execute (if possible) to integrate log
    )

    resp = protos.subtask_response_pb2.SubtaskResponse()
    if subp_checker.returncode == 0:
        # the method name is confusing; it is in fact a byte string
        try:
            resp.ParseFromString(subp_checker.stdout)
        except:
            logger.exception('Error occurred when attempting to parse the response from the checker')
            resp.verdict = HojVerdict.SERR.value
    else:
        logger.error('The checker exits abnormally with return code %d', subp_checker.returncode)
        resp.verdict = HojVerdict.SERR.value

    # alternative way for a Python file; faster
    # import runpy
    # tolerantDiff = runpy.run_path(checker_path)
    # resp = tolerantDiff['main'](cxt)

    if resp.verdict == HojVerdict.WA.value:
        lineno_wrap = Int64Value(value=-1)
        # lineno only makes sense in tolerantDiff
        if 'lineno' in resp.meta:
            resp.meta['lineno'].Unpack(lineno_wrap)
        print(color('===== WA  =====', fg='red', style='negative') +
              '  @ line {}'.format(lineno_wrap.value))
        return HojVerdict.WA, log_dict
    elif resp.verdict != HojVerdict.AC.value:
        print(color('===== {:3} ====='.format(HojVerdict(resp.verdict).name), fg='blue', style='negative') +
            ' REPORTED_BY_CHECKER')
        return HojVerdict(resp.verdict), log_dict

    print(color('===== AC  =====', fg='green', style='negative'))
    return HojVerdict(resp.verdict), log_dict

def judgeSubmission(submission, judge_desc):
    problem = submission.problem
    logger.debug('Sandbox path is set to {}'.format(SANDBOX_PATH))

    logger.debug('--- Judge Description ---\n%s', pformat(dict(judge_desc._asdict())))

    samples = judge_desc.samples
    subtasks = judge_desc.subtasks
    all_tasks = samples + subtasks

    print(color('--- Initializing...', style='bold'))
    logger.info(color('Checking test data...', style='bold'))
    testdata_path_tpl = lambda label, ext: path.join(TESTDATA_PATH, '{}/{}.{}'.format(problem.problem, label, ext))
    _testdata, testdata_healthy = hoj_collect_testdata(all_tasks, testdata_path_tpl)
    if not testdata_healthy:
        logger.error(color('Failed to collect test data, refusing to continue', fg='red', style='bold'))
        return None, -1, None

    logger.info(color('Writing code to disk...', style='bold'))

    path_src = path.join(SANDBOX_PATH, SOURCE_FILENAME)

    with open(path_src, 'w') as f:
        nwrt = f.write(submission.submission_code)
    logger.debug('Written %d byte(s) to %s', nwrt, path_src)

    # prepare piping threads
    logfile_stdout = open(LOG_STDOUT_PATH, 'w+')
    logfile_stderr = open(LOG_STDERR_PATH, 'w+')

    logger.info(color('Compiling...', style='bold'))


    journals = pipes.Journals(logfile_stdout, logfile_stderr)

    # with 1:
    cmd_compile = cmd_compile_tpl.format(
        src=shlex.quote(SOURCE_FILENAME),
        output=PROG_EXEC_PATH
    )

    with journals.start(None, 'COMPILE'):
        subp_compile, is_ole = taskCompile(shlex.split(cmd_compile), journals)

    _comp_stderr = journals[1].dump('COMPILE')
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    log_msg = ansi_escape.sub('', _comp_stderr)

    if is_ole:
        log_msg += f'@<< Truncated at {COMPILE_OUT_LIM} chars. The message above may be incomplete. >>'

    if subp_compile.returncode == 0:
        logger.debug('Compile task succeeds')
    else:
        logger.debug('Compile task failed with return code %d', subp_compile.returncode)
        print(color('Failed to compile source', fg='red', style='bold'))

        # fill all fields with CE
        logger.debug('Filling all fields with CE')
        # TODO: wiring out the error message (how?)
        return [[HojVerdict.CE, 0, 0] for _ in all_tasks], 0, log_msg

    if problem.problem_special:
        logger.debug('Special judge is on')
        print(color('Special judge. Compiling checker...', style='bold'))

        checker_out = '/tmp/special.cpp'
        checker_exec = '/run/shm/checker'

        taskCompileChecker(problem, checker_out, checker_exec)

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
        logger.info('------ Start judge sample: %r ------', task)
        verdict, info = judgeSingleSubtask(task, next(testdata_iter), checker_args)

        judge_results.append([
            verdict,
            int(info.get('time', -1)),
            int(info.get('cgroup_memory_max_usage', -1))
        ])

        if verdict == HojVerdict.SERR:
            pretest_fail = True

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

        logger.info('------ Start judge subtask (%s, %s/%s): %r ------',
            group_num, cur_group_no + 1, cur_group_count, task)

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
            logger.info('End of group, giving score {}/{}'.format(score, cur_group_score))

    # note that the log is sent back even if the compilation succeeds
    return judge_results, score_total, log_msg
