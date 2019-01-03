import logging
from os import path
import pprint

from ansicolor import strip_escapes
import toml


_pp = pprint.PrettyPrinter(indent=2)
pformat = _pp.pformat
del _pp

_config = None
def loadConfig(path_=None):
    global _config
    if _config is None:
        if path_ is None:
            path_ = path.join(path.dirname(__file__), '../config/config.toml')
        _config = toml.load(path_)
    return _config

class ColoredFormatter(logging.Formatter):
    color_map = {
        logging.CRITICAL: '\x1b[1;7;91m',
        logging.ERROR:    '\x1b[1;31m',
        logging.WARNING:  '\x1b[1;33m',
        logging.INFO:     '\x1b[1;34m',
        logging.DEBUG:    '\x1b[2m',  # dimmed
    }
    ctrl_reset = '\x1b[0m'

    def format(self, record):
        color_str = self.__class__.color_map.get(record.levelno, None)
        has_color = color_str is not None
        color_str_res = self.__class__.ctrl_reset

        record.color_apply = color_str if has_color else ''
        record.color_reset = color_str_res if has_color else ''
        return super().format(record)


class ColorlessFormatter(logging.Formatter):
    def format(self, record):
        rec = super().format(record)
        return strip_escapes(rec)
