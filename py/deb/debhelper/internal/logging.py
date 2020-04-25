import os
import sys

try:

    _MODE = os.environ.get('DH_COLORS')
    if _MODE is None:
        _MODE = os.environ.get('DPKG_COLORS')
    if _MODE is None:
        # Support NO_COLOR (https://no-color.org/)
        _MODE = 'never' if 'NO_COLOR' in os.environ else 'auto'

    if _MODE == 'never':
        raise ImportError()

    # We take DH_COLORS/DPKG_COLORS as an explicit request for color (which is "allowed" by no-color.org)
    # This means we have to ensure NO_COLOR is unset when loading colored
    try:
        del os.environ['NO_COLOR']
    except KeyError:
        pass

    from colored import fg, attr
    import colored

    colored.set_tty_awareness(_MODE == 'auto')
except ImportError:
    def fg(_):
        return ""

    def attr(_):
        return ""

from . import TOOL_NAME


ERROR = 1
WARNING = 2
FIXIT_HINT = 3
NON_QUIET_INFO = 4
VERBOSE = 5

LOG_LEVEL = NON_QUIET_INFO


ATTR_BOLD = attr('bold')
ATTR_RESET = attr("reset")
COLOR_RED = fg('red')
COLOR_YELLOW = fg('yellow')
COLOR_SKY_BLUE = fg('deep_sky_blue_2')


def _color(msg, color="", text_attr=""):
    return color + text_attr + msg + ATTR_RESET


def _msg_prefix(tag, tag_color="", tag_attr=""):
    return _color(TOOL_NAME, text_attr=ATTR_BOLD) + ': ' + _color(tag, color=tag_color, text_attr=tag_attr) + ': '


def set_log_level(level):
    global LOG_LEVEL
    LOG_LEVEL = level


def error(*msg, exit_code=255):
    prefix = _msg_prefix('error', tag_color=COLOR_RED, tag_attr=ATTR_BOLD)
    for m in msg:
        print(prefix + m, file=sys.stderr)
    sys.exit(exit_code)


def warning(*msg):
    prefix = _msg_prefix('warning', tag_color=COLOR_YELLOW, tag_attr=ATTR_BOLD)
    for m in msg:
        print(prefix + m, file=sys.stderr)


def fixit_hint(*msg):
    prefix = _msg_prefix('hint', tag_color=COLOR_SKY_BLUE, tag_attr=ATTR_BOLD)
    for m in msg:
        print(prefix + m)


def non_quiet_print(*msg):
    if LOG_LEVEL >= NON_QUIET_INFO:
        for m in msg:
            print("\t" + m)


def verbose_print(*msg):
    if LOG_LEVEL >= VERBOSE:
        for m in msg:
            print("\t" + m)
