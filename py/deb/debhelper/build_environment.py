import os
from typing import List, FrozenSet, Mapping

from deb.debhelper.internal import parse_key_value_env_var, parse_rrr, DpkgArchitectureValuesTable, \
    AbstractDpkgArchitectureValuesTable


class BuildEnvironment:
    """Environment related operations

    Note each instance maintain a cache of variables it has read.  For efficiency
    all parts of the code should use the same instance (except where you deliberately
    fiddle with the underlying environment - e.g. in unit tests).
    """

    __slots__ = ['_active_build_profiles', '_deb_build_options', '_rrr', '_gain_root_cmd', '_dpkg_arch_table',
                 '_environ']

    def __init__(self, *, environ=None):
        """Create an instance with its own environment cache.

        :param environ: If not None, this dict-like object will be used instead of os.environ. Mostly useful
          for testing to ensure the "environment" is exactly as you expect without having to fiddle directly
          with os.environ.
        """
        self._environ = environ if environ is not None else os.environ
        self._active_build_profiles = None
        self._deb_build_options = None
        self._rrr = None
        self._gain_root_cmd = None
        self._dpkg_arch_table = DpkgArchitectureValuesTable(self._environ)

    @property
    def dpkg_architecture(self) -> AbstractDpkgArchitectureValuesTable:
        """A (lazy) read-only mapping of the dpkg-architecture output

        For performance reasons, the table resolves the values from the
        environment where possible to avoid the overhead of
        dpkg-architecture.

        >>> import subprocess
        >>> from deb.debhelper import BuildEnvironment
        >>> # Pretend that os.environ had no relevant variables
        >>> arch_table = BuildEnvironment(environ={}).dpkg_architecture
        >>> # ... and we have the following shorthand to get the value from dpkg-architecture
        >>> def _call_dpkg_architecture(x):
        ...     return subprocess.check_output(['dpkg-architecture', '-q', x]).decode('utf-8').strip()
        >>>
        >>> # Then we can see that arch_table['DEB_HOST_ARCH'] is the same as dpkg-architecture -qDEB_HOST_ARCH
        >>> arch_table['DEB_HOST_ARCH']  == _call_dpkg_architecture('DEB_HOST_ARCH')
        True
        >>> # There is also a nice short hand for those who prefer that.
        >>> arch_table.current_host_arch == _call_dpkg_architecture('DEB_HOST_ARCH')
        True
        >>> # Looking up arbitrary DEB_{HOST,BUILD,TARGET}_* variables are also possible
        >>> # (Reminder, you almost always want DEB_HOST_X over the other options)
        >>> arch_table['DEB_HOST_ARCH_BITS']== _call_dpkg_architecture('DEB_HOST_ARCH_BITS')
        True

        In the unlikely event that you should need it, you can also query if a variable
        is available.
        >>> 'DEB_HOST_ARCH' in arch_table
        True
        >>> 'RANDOM_VALUE' in arch_table
        False
        >>> arch_table['RANDOM_VALUE']
        Traceback (most recent call last):
            ...
        KeyError: 'RANDOM_VALUE'

        As mentioned, environment variables are preferred, when set:
        >>> a_different_environ = {'DEB_HOST_ARCH': 'foo'}
        >>> arch_table = BuildEnvironment(environ=a_different_environ).dpkg_architecture
        >>> arch_table.current_host_arch
        'foo'
        """
        return self._dpkg_arch_table

    def should_use_root(self, *, keyword=None) -> bool:
        """Check whether root should be used for install/binary actions

        Note that dpkg handles parsing the value in debian/control and
        exposing it via an environment variable.

        Example usage:

        >>> from deb.debhelper import BuildEnvironment
        >>> # Pretend that os.environ had Rules-Requires-Root set no
        >>> environ_rrr_no = {'DEB_RULES_REQUIRES_ROOT': 'no'}
        >>> be = BuildEnvironment(environ=environ_rrr_no)
        >>> # Then should_use_root always returns false
        >>> be.should_use_root()
        False
        >>> be.should_use_root(keyword="dpkg/target-subcommand")
        False
        >>>
        >>> # If we pretend that os.environ had Rules-Requires-Root set to "binary-targets"
        >>> environ_rrr_bt = {'DEB_RULES_REQUIRES_ROOT': 'binary-targets'}
        >>> be = BuildEnvironment(environ=environ_rrr_bt)
        >>> # Then should_use_root will always return true
        >>> be.should_use_root()
        True
        >>> be.should_use_root(keyword="dpkg/target-subcommand")
        True
        >>> # If unset, it is behaves the same as "binary-targets"
        >>> environ_rrr_unset = {}
        >>> be = BuildEnvironment(environ=environ_rrr_unset)
        >>> be.should_use_root()
        True
        >>> be.should_use_root(keyword="dpkg/target-subcommand")
        True
        >>>
        >>> # If we pretend that os.environ had Rules-Requires-Root set to a "targeted" value
        >>> environ_rrr_other = {'DEB_RULES_REQUIRES_ROOT': 'dpkg/target-subcommand foo/bar'}
        >>> be = BuildEnvironment(environ=environ_rrr_other)
        >>> # Then should_use_root returns False in the general case
        >>> be.should_use_root()
        False
        >>> # But true for the known keywords
        >>> be.should_use_root(keyword="dpkg/target-subcommand")
        True
        >>> be.should_use_root(keyword="foo/bar")
        True
        >>> # And false for unknown keywords
        >>> be.should_use_root(keyword="random/value")
        False
        >>> be.should_use_root(keyword="foo/baz")
        False

        """
        if self._rrr is None:
            self._rrr = parse_rrr(self._environ)
        if 'binary-targets' in self._rrr:
            return True
        if keyword is None or 'no' in self._rrr:
            return False
        return keyword in self._rrr

    def gain_root_cmd_prefix(self, *args, keyword=None) -> List[str]:
        """Prefix a command (plus arguments with the "gain root command" from dpkg where relevant

        Example usage:

        >>> import os
        >>> from deb.debhelper import BuildEnvironment
        >>> # Considering the following sample environment
        >>> sample_environ = {
        ...   'DEB_RULES_REQUIRES_ROOT': 'foo/bar',
        ...   'DEB_GAIN_ROOT_CMD': 'sudo -nE --',
        ... }
        >>> be = BuildEnvironment(environ=sample_environ)
        >>> # Then gain_root_cmd_prefix will add sudo for known keywords
        >>> be.gain_root_cmd_prefix('some-command', '--that-requires-root-with-foo-bar',
        ...                         keyword="foo/bar")
        ['sudo', '-nE', '--', 'some-command', '--that-requires-root-with-foo-bar']
        >>> # But omit the sudo prefer for unknown keywords
        >>> be.gain_root_cmd_prefix('some-command', '--that-requires-root-with-other-value',
        ...                         keyword="other/value")
        ['some-command', '--that-requires-root-with-other-value']
        >>> # Without any arguments, it returns the gain root command (here, sudo)
        >>> be.gain_root_cmd_prefix()
        ['sudo', '-nE', '--']
        >>> # With a command but no keyword, it raises a ValueError
        >>> be.gain_root_cmd_prefix('miscall')
        Traceback (most recent call last):
            ...
        ValueError: keyword argument must be set when providing a command (positional arguments)
        """
        if self._gain_root_cmd is None:
            self._gain_root_cmd = self._environ.get('DEB_GAIN_ROOT_CMD').split()
        if keyword is None:
            if args:
                raise ValueError("keyword argument must be set when providing a command (positional arguments)")
            return self._gain_root_cmd.copy()
        if keyword is not None and self.should_use_root(keyword=keyword) and not self.should_use_root():
            ret = self._gain_root_cmd.copy()
            ret.extend(args)
            return ret
        return list(args)

    @property
    def active_build_profiles(self) -> FrozenSet[str]:
        """Return the active build profile labels

        Returns a frozenset that enables callers to query parameters in
        DEB_BUILD_PROFILES.  Example usage:

        >>> import os
        >>> from deb.debhelper import BuildEnvironment
        >>> # Pretend that os.environ had DEB_BUILD_PROFILES set to the following value
        >>> environ = {'DEB_BUILD_PROFILES': 'nospam ham'}
        >>> abp = BuildEnvironment(environ=environ).active_build_profiles
        >>> # Then we can see that "nospam" and "ham" are active build profiles
        >>> 'nospam' in abp
        True
        >>> 'ham' in abp
        True
        >>> # Where as unknown values are not
        >>> 'spam' in abp
        False
        >>> 'noham' in abp
        False
        >>> 'other-unknown-key' in abp
        False
        >>> # If needed, you can iterate over the all the active build profiles
        >>> sorted(abp)
        ['ham', 'nospam']
        """
        if self._active_build_profiles is None:
            self._active_build_profiles = frozenset(self._environ.get('DEB_BUILD_PROFILES', '').split())
        return self._active_build_profiles

    @property
    def deb_build_options(self) -> Mapping[str, str]:
        """A view of the DEB_BUILD_OPTIONS variable

        Returns a "read-only" dict that enables callers to query parameters in
        DEB_BUILD_OPTIONS.  Example usage:

        >>> from deb.debhelper import BuildEnvironment
        >>> # Pretend os.environ contained only
        >>> environ = {'DEB_BUILD_OPTIONS': 'nocheck parallel=4'}
        >>> dbo = BuildEnvironment(environ=environ).deb_build_options
        >>> # Then you get the following replies
        >>> 'nocheck' in dbo
        True
        >>> 'parallel' in dbo
        True
        >>> 'nostrip' in dbo
        False

        It is also possible to get the exact value set for e.g. "parallel".  Note
        all values are strings, so conversion to int must be done as well where needed.
        >>> int(dbo.get('parallel', '1'))
        4

        Alternative variant of the above using the "Asking forgiveness" pattern
        >>> try:
        ...    parallel = int(dbo['parallel'])
        ... except KeyError:
        ...    parallel = 1
        >>> parallel
        4

        Be mindful that the value defaults to None for "valueless" parameters.
        >>> dbo['nocheck'] is None
        True

        Like all other dicts, it will raise KeyError for unknown keys
        >>> dbo['nostrip']
        Traceback (most recent call last):
            ...
        KeyError: 'nostrip'

        Being a dict, it also supports iteration
        >>> sorted(dbo)
        ['nocheck', 'parallel']

        No setdefault though...
        >>> dbo.setdefault('foo', "value")
        Traceback (most recent call last):
            ...
        TypeError: ReadonlyDict does not support mutation
        """
        if self._deb_build_options is None:
            self._deb_build_options = parse_key_value_env_var(self._environ, 'DEB_BUILD_OPTIONS')
        return self._deb_build_options
