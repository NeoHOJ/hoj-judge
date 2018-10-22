from collections import namedtuple

class TaskDef(object):
    pass

TaskSpec = namedtuple('TaskSpec', [
    'samples', 'subtasks', 'task_groups'
])
