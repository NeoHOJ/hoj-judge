from enum import Enum
from os import path

import toml
from colors import color
from peewee import *

from .datatypes import TaskDef, TaskSpec

'''
A bridge to operate on managing submissions in HOJ DB.
'''

config = toml.load(path.join(path.dirname(__file__), '../config/config.toml'))
hoj_database = MySQLDatabase('judge', **config['database'])

class HojTaskDef(TaskDef):
    def __init__(self,
                 label=None,
                 time_limit=-1,
                 mem_limit=-1,
                 fallthrough=False):
        self.label = label
        self.time_limit = time_limit
        self.mem_limit = mem_limit
        self.fallthrough = fallthrough

    def __repr__(self):
        return ('<HojTaskDef "{}" time={}ms mem={}KiB>'
            .format(self.label, self.time_limit, self.mem_limit))


class HojVerdict(Enum):
    PENDING = 0
    AC = 1
    RE = 2
    CE = 3
    TLE = 4
    MLE = 5
    WA = 6
    PE = 7
    OLE = 8
    OTHER = 9
    SERR = 10
    RF = 11

    def toPriority(self):
        # SYSERR > Restricted > OTHER > CE > RE > OLE > TLE > MLE > PE > WA > AC
        # in reverse order (increasing priority)
        order = [1, 6, 7, 5, 4, 8, 2, 3, 9, 11, 10, 0]
        return order.index(self.value)


'''
Convert HOJ tabular problem description to compatiable format.
'''
def hoj_to_judge_desc(tabular):
    arr = iter(tabular)

    # <# samples> <# groups>
    header = next(arr)
    num_samples, num_subtasks = header

    genLabel = lambda total: '{0}-{1}' if total > 1 else '{0}'

    desc_samples = []
    for i in range(num_samples):
        label = genLabel(num_samples).format(0, i + 1)
        tl, ml = next(arr)
        desc_samples.append(HojTaskDef(label, tl, ml))

    # a flattened subtask list
    desc_subtasks = []
    desc_task_groups = []
    for i in range(num_subtasks):
        # <# small> <is-ocen?> <score>
        subheader = next(arr)
        num_small, is_ocen, score = subheader

        if is_ocen:
            # Note that isOcen consume an extra row if it is true
            tl, ml = next(arr)
            label = '{}-ocen'.format(i + 1)
            desc_subtasks.append(HojTaskDef(label, tl, ml, fallthrough=True))

        desc_task_groups.append([num_small + is_ocen, score])

        for j in range(num_small):
            label = genLabel(num_small).format(i + 1, j + 1)
            tl, ml = next(arr)
            desc_subtasks.append(HojTaskDef(label, tl, ml))

    return TaskSpec(
        samples=desc_samples,
        subtasks=desc_subtasks,
        task_groups=desc_task_groups
    )

'''
Check whether all testdata paths are valid.

func_tpl l, x:
    l is the label of the lask
    x is either `in` or `out` to produce the file name of either infile or
    outfile.
'''
def hoj_collect_testdata(arr_subtasks, func_tpl, verbose=True):
    exts = ('in', 'out')
    healthy = True
    testdata = []

    for task in arr_subtasks:
        testdata_paths = tuple(func_tpl(task.label, ext) for ext in exts)

        for ext, p in zip(exts, testdata_paths):
            exists = path.isfile(p)

            if verbose:
                if exists:
                    print('.', end='')
                else:
                    print(''.join([
                        '\n',
                        color('X', fg='red', style='bold'),
                        ' ERR: {} is not ready '.format(p)
                    ]), end='')

            if not exists:
                healthy = False

        testdata.append(testdata_paths)

    if verbose:
        print()

    return testdata, healthy
