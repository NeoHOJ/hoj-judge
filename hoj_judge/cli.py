import sys

from ._hoj_helpers import *
import hoj_judge.models_hoj as m
import hoj_judge.judge


def main(as_module=False):
    if len(sys.argv) != 2:
        print('Usage: {} <submission-id>'.format(sys.argv[0]))
        sys.exit(1)

    submission_id = int(sys.argv[1])

    m.init(hoj_database)

    try:
        submission = m.Submission.get(m.Submission.submission == submission_id)
    except m.OperationalError as err:
        print('OperationalError:', err)
        sys.exit(1)
    except m.DoesNotExist:
        print('Cannot find the submission with id {}.\n'.format(submission_id))
        sys.exit(1)

    problem = submission.problem
    judge_desc = hoj_to_judge_desc(problem.problem_testdata)
    the_result, the_score = hoj_judge.judge.judgeSubmission(submission, judge_desc)

    if the_score < 0:
        print('Fatal error occurred')
        sys.exit(1)

    print('--- Results')
    all_tasks = judge_desc.samples + judge_desc.subtasks
    for d, r in zip(all_tasks, the_result):
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

    print('Submission verdict: {!r}'.format(the_verdict))
    print('           score  : {}'.format(the_score))
    print('   (total) time   : {}'.format(the_time))
    print('     (max) memory : {}'.format(the_mem))

    if submission.submission_status != 0:
        print('Submission is already judged, skip updating.')
    else:
        submission.__data__.update(
            submission_status=the_verdict.value,
            submission_score=the_score,
            submission_mem=the_mem,
            submission_time=the_time,
            submission_result=the_result,
            submission_len=len(submission.submission_code)
        )
        submission.save()

        print('Updated submission in database.')

if __name__ == '__main__':
    main(as_module=True)
