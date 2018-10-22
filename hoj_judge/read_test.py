import models_hoj as m
from _hoj_helpers import *


m.init(hoj_database)

submissions = (m.Submission.select(m.Submission, m.Problem)
                .where(m.Submission.problem == 102)
                .order_by(m.Submission.submission.desc())
                .limit(1)
                .join(m.Problem))
problems = m.Problem.select()

for subm in submissions:
    # subm.problem.problem_title
    print(subm.__data__)
    print(subm.problem.__data__)
    print(subm.submission_result)

    print(subm.problem.problem_testdata)
    print('desc')
    print(hoj_to_judge_desc(subm.problem.problem_testdata))
