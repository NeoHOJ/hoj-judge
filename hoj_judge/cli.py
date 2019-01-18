import argparse
import logging
import logging.config
import sys

logging.Formatter.default_msec_format = '%s.%03d'
logger = logging.getLogger(__name__)

from ._hoj_helpers import *
from hoj_judge.utils import loadConfig
import hoj_judge.models_hoj as m
import hoj_judge.judge


def judgeSubmissionModel(submission):
    problem = submission.problem
    judge_desc = hoj_to_judge_desc(problem.problem_testdata)
    the_result, the_score, log_msg = hoj_judge.judge.judgeSubmission(submission, judge_desc)

    if the_score < 0:
        logger.warning('Fatal error occurred as the score (%d) < 0', the_score)
        sys.exit(1)

    print('Results:')
    all_tasks = judge_desc.samples + judge_desc.subtasks
    for d, r in zip(all_tasks, the_result):
        print(' - ', end='')
        print(d, *r)
    print()

    the_verdict = HojVerdict.AC
    the_time = 0
    the_mem = 0
    for rec in the_result:
        ve, t, mem = rec
        rec[0] = ve.value
        if ve.toPriority() > the_verdict.toPriority():
            the_verdict = ve
        if t < 0:
            the_time = -1
        elif the_time >= 0:
            the_time += t
        the_mem = max(the_mem, mem)

    return {
        'verdict': the_verdict,
        'update': {
            'submission_status': the_verdict.value,
            'submission_score': the_score,
            'submission_mem': the_mem,
            'submission_time': the_time,
            'submission_result': the_result,
            'submission_len': len(submission.submission_code),
            'submission_error': log_msg,
        }
    }

def judgeSubmissionById(id):
    try:
        with m.connection_context():
            submission = m.Submission.get(m.Submission.submission == id)
            is_already_judged = (submission.submission_status != 0)
    except m.OperationalError as err:
        logger.exception('OperationalError:')
        sys.exit(1)
    except m.DoesNotExist:
        logger.critical('Cannot find the submission with id %d.', id)
        sys.exit(1)

    if is_already_judged:
        logger.warning('Submission is already judged, the record is not updated unless --force is specified.')

    logging.info('Start judging submission of ID %d...', id)
    ret = judgeSubmissionModel(submission)
    outp = ret['update']

    print('Submission verdict: {!r}'.format(ret['verdict']))
    print('           score  : {}'.format(outp['submission_score']))
    print('   (total) time   : {}'.format(outp['submission_time']))
    print('     (max) memory : {}'.format(outp['submission_mem']))

    if not is_already_judged:
        submission.__data__.update(**outp)
        with m.connection_context():
            submission.save()
        logger.info('Updated submission in database.')

def exec(args):
        submission_id = args.submission_id
        m.init(hoj_database)
        return judgeSubmissionById(submission_id)

def main(as_module=False):
    config = loadConfig()
    logging.config.dictConfig(config['logging'])

    parser = argparse.ArgumentParser(
        prog='hoj_judge',
        description='The CLI of HOJ judge backend.')
    parser.set_defaults(func=lambda _: (parser.print_help(), parser.exit(1)))

    subparsers = parser.add_subparsers(
        dest='action',
        metavar='<action>',
        help='The action to take')

    parser_exec = subparsers.add_parser('exec',
        help='Run judge of the specified submission ID.',
        description='Run judge of specified submission ID.')
    parser_exec.add_argument('submission_id', type=int, help='submission ID.')
    parser_exec.set_defaults(func=exec)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    main(as_module=True)
