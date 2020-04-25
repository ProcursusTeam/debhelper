import os
import subprocess
import sys

from .dhemulation import (
    package_file as package_file,
    install_as as install_as,
)


TOOL_NAME = os.path.basename(sys.argv[0])
if TOOL_NAME.endswith(".py"):
    TOOL_NAME = TOOL_NAME[:-3]
if TOOL_NAME == "":
    TOOL_NAME = "<cmdline>"


def package_actions(func):
    return func


def parse_rrr(environ):
    rrr = frozenset(x for x in environ.get('DEB_RULES_REQUIRES_ROOT', 'binary-targets').split())
    if len(rrr) > 1:
        # The "no" and "binary-targets" only make sense on their own
        if 'binary-targets' in rrr:
            # "binary-targets" overrule other values
            return frozenset(['binary-targets'])
        if 'no' in rrr:
            # Remove "no" as it does not make sense in combination with others
            rrr = frozenset(rrr - {'no'})
    return rrr


def _parse_kv_pair(raw_value):
    for kv_pair_raw in raw_value.split():
        if '=' not in kv_pair_raw:
            k = kv_pair_raw
            v = None
        else:
            k, v = kv_pair_raw.split('=', 1)
        yield k, v


def parse_key_value_env_var(environ, varname) -> 'ReadonlyDict':
    """Parse a ENV "map" variable into a ReadonlyDict

    This is useful for e.g. DEB_BUILD_OPTIONS and such.  Values without
    any value (no "=" sign) will have a None value)
    """
    try:
        raw_value = environ[varname]
    except KeyError:
        return ReadonlyDict()
    return ReadonlyDict(_parse_kv_pair(raw_value))


class ReadonlyDict(dict):
    """Readonly version of dict

    This tries to stop the most obvious mutations to ensure people do not shoot
    themselves in the foot.  No attempt is made to stop people with sniper rifles
    that insist on firing at their own toes though.
    """

    def __setitem__(self, key, value):
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def __delitem__(self, key):
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def update(self, *args, **kwargs):  # known special case of dict.update
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def pop(self, *args, **kwargs):
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def popitem(self, *args, **kwargs):
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def setdefault(self, *args, **kwargs):
        raise TypeError("%s does not support mutation" % self.__class__.__name__)

    def clear(self) -> None:
        raise TypeError("%s does not support mutation" % self.__class__.__name__)


class AbstractDpkgArchitectureValuesTable:

    def __getitem__(self, item):
        raise NotImplementedError("Subclasses must implement __getitem__")

    def __contains__(self, item):
        raise NotImplementedError("Subclasses must implement __contains__")

    def get(self, item, default_value=None):
        try:
            self[item]
        except KeyError:
            return default_value

    @property
    def current_host_arch(self):
        return self['DEB_HOST_ARCH']


class DpkgArchitectureValuesTable(AbstractDpkgArchitectureValuesTable):
    """Current implementation of deb.debhelper.BuildEnvironment.dpkg_architecture

    Concrete class and implementation is subject to change without notice.
    """

    __slots__ = ['_architecture_cache', '_environ']

    def __init__(self, environ):
        self._environ = environ
        self._architecture_cache = {}

    def __getitem__(self, item):
        # The startswith check is to avoid false lookups for invalid variables that happen
        # to be set in the environment.  It is still possible with the prefix, but at least
        # we make it a lot less likely to happen by mistake.
        if item not in self._architecture_cache and item.startswith(('DEB_HOST_', 'DEB_BUILD_', 'DEB_TARGET_')):
            value = self._environ.get(item)
            if value is not None:
                self._architecture_cache[item] = value
                return value
            self._load_dpkg_architecture_values()
            # Fall through and look it up in the cache
        return self._architecture_cache[item]

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        return True

    def _load_dpkg_architecture_values(self):
        text = subprocess.check_output(['dpkg-architecture']).decode('utf-8')
        for line in text.splitlines():
            k, v = line.strip().split('=', 1)
            # The environment takes precedence
            self._architecture_cache[k] = self._environ.get(k, v)
