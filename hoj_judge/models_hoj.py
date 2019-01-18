import logging
import os

from peewee import *


DATABASE = Proxy()
LOGGER_PEEWEE = logging.getLogger('peewee')
LOGGER_PEEWEE.setLevel(logging.WARNING)

def init(database_):
    DATABASE.initialize(database_)

    if os.environ.get('DEBUG_PEEWEE'):
        LOGGER_PEEWEE.addHandler(logging.StreamHandler())
        LOGGER_PEEWEE.setLevel(logging.DEBUG)

    return DATABASE

def connection_context():
    return DATABASE.connection_context()


class TabularIntgralField(TextField):
    __listToLineStr = lambda x: ' '.join(map(str, x)) + '\n'
    __lineToIntList = lambda l: [int(c) for c in l.strip().split(' ')]

    def db_value(self, value):
        return ''.join(map(TabularIntgralField.__listToLineStr, value))
    def python_value(self, value):
        if value == '' or value is None: return []
        try:
            return list(map(TabularIntgralField.__lineToIntList,
                            value.strip().split('\n')))
        except:
            return list(value.strip().split('\n'))


'''
the model definition below is derived from pwiz with some text substitutions
regarding to foreign keys and default values, and some other tweaks
'''
class BaseModel(Model):
    class Meta:
        database = DATABASE


class Contest(BaseModel):
    contest = AutoField(column_name='contest_id')
    contest_description = TextField(null=True)
    contest_end = DateTimeField()
    contest_feedback = IntegerField(default=0)
    contest_level = IntegerField(default=1)
    contest_mode = IntegerField(default=1)
    contest_oi = IntegerField(default=1)
    contest_open = IntegerField(default=0)
    contest_penalty = IntegerField(default=0)
    contest_score = IntegerField(default=1)
    contest_showscoreboard = IntegerField(default=1)
    contest_start = DateTimeField()
    contest_title = CharField(null=True)

    class Meta:
        table_name = 'contest'


class User(BaseModel):
    user = AutoField(column_name='user_id')
    user_class = CharField(null=True)
    user_email = CharField(null=True)
    user_level = IntegerField(default=1)
    user_name = CharField(null=True)
    user_nick = TextField()
    user_password = CharField()
    user_solved = IntegerField(default=0)
    user_username = CharField()

    class Meta:
        table_name = 'user'


class Problem(BaseModel):
    problem = AutoField(column_name='problem_id')
    problem_check = TextField(null=True)
    problem_description = TextField(null=True)
    problem_hint = TextField(null=True)
    problem_input = TextField(null=True)
    problem_level = IntegerField(default=0)
    problem_output = TextField(null=True)
    problem_samplein = TextField(null=True)
    problem_sampleout = TextField(null=True)
    problem_setter = IntegerField(default=1)
    problem_source = CharField(null=True)
    problem_special = IntegerField(default=0, null=True)
    problem_task = TextField(null=True)
    problem_testdata = TabularIntgralField(null=True)
    problem_title = CharField(null=True)

    class Meta:
        table_name = 'problem'


class Submission(BaseModel):
    submission = AutoField(column_name='submission_id')
    contest = ForeignKeyField(Contest, column_name='contest_id', default=-1)
    problem = ForeignKeyField(Problem, column_name='problem_id', null=True)
    submission_code = TextField(null=True)
    submission_date = DateTimeField(null=True)
    submission_error = TextField(null=True)
    submission_len = IntegerField(default=0)
    submission_mem = IntegerField(default=0)
    submission_mode = IntegerField(default=0)
    submission_result = TabularIntgralField(null=True)
    submission_score = IntegerField(default=0, null=True)
    submission_status = IntegerField(default=0)
    submission_time = IntegerField(default=0)
    user = ForeignKeyField(User, column_name='user_id')

    class Meta:
        table_name = 'submission'
