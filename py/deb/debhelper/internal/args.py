import argparse
import os
import sys

from . import TOOL_NAME
from .logging import warning


# TODO: Add annotation for injecting arguments.

def parse_args(argv=None, environ=None):
    if argv is None:
        argv = sys.argv[1:]
    if environ is None:
        environ = os.environ

    # TODO: Check if -a/-i optimization from Dh_Lib.pm is worth it
    parser = define_arg_parser()

    internal_options = environ.get('DH_INTERNAL_OPTIONS')
    maint_options = environ.get('DH_OPTIONS')

    parsed_options = None

    if internal_options:
        parsed_options, _ = parser.parse_known_args(internal_options.split('\x1e'), namespace=parsed_options)
        # FIXME: excluded packages

    if maint_options:
        parsed_options, remainder = parser.parse_known_args(maint_options.split(), namespace=parsed_options)
        if remainder:
            warning("ignored unknown options in DH_OPTIONS")

    try:
        i = argv.index('--')
        upstream_args = argv[i + 1:]
        argv = argv[:i]
    except IndexError:
        upstream_args = []

    parsed_options = parser.parse_args(args=argv)
    parser.parse_known_intermixed_args(args=parsed_options.o_options, namespace=parsed_options)
    parsed_options.upstream_args.extend(upstream_args)

    # if parsed_options.verbose:
    #     set_log_level(VERBOSE)
    # elif parsed_options.quiet:
    #     set_log_level(FIXIT_HINT)
    # else:
    #     set_log_level(NON_QUIET_INFO)

    if parsed_options.arch_any_same:
        warning("--same/-s is deprecated.  Please use --arch/-a instead")
        setattr(parsed_options, 'arch_any', True)
        delattr(parsed_options, 'arch_any_same')

    return parsed_options

# 	my %options=(
# 		"v" => \$dh{VERBOSE},
# 		"verbose" => \$dh{VERBOSE},
#
# 		"no-act" => \$dh{NO_ACT},

# 		"remaining-packages" => \$dh{EXCLUDE_LOGGED},
#
# 		"dbg-package=s" => \&SetDebugPackage,
#
# 		"d" => \$dh{D_FLAG},
#
# 		"P=s" => \$dh{TMPDIR},
# 		"tmpdir=s" => \$dh{TMPDIR},
#
# 		"u=s", => \$dh{U_PARAMS},
#
# 		"V:s", => \$dh{V_FLAG},x
#
# 		"O=s" => sub { push @test, $_[1] },
#
# 		(ref $params{options} ? %{$params{options}} : ()) ,
#
# 		"<>" => \&NonOption,
# 	);

def define_arg_parser():
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description='debhelper-like tool.')
    parser.add_argument('-p', '--package', dest='selected_packages',
                        action='append',
                        default=[],
                        help='Act on the package named package. This option may'
                             ' be specified multiple times to make the tool'
                             ' operate on a given set of packages.')

    parser.add_argument('-N', '--no-package', dest='excluded_packages',
                        action='append',
                        default=[],
                        help='Do not act on the specified package even if an'
                             ' -a, -i, or -p option lists the package as one'
                             ' that should be acted on.')

    parser.add_argument('-i', '--indep', dest='arch_all', default=False,
                        action='store_true',
                        help='Act on all architecture independent packages')

    parser.add_argument('-a', '--arch', dest='arch_any', default=False,
                        action='store_true',
                        help='Act on architecture dependent packages that should'
                             ' be built for the DEB_HOST_ARCH architecture.')

    parser.add_argument('-s', '--same-arch', dest='arch_any_same', action='store_true', default=False,
                        help='[Deprecated] Act on architecture dependent packages that should'
                             ' be built for the DEB_HOST_ARCH architecture. (Use -a/--arch instead)')

    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true')
    parser.add_argument('--no-act', dest='dry_run', default=False, action='store_true')
    parser.add_argument('--remaining-packages', dest='remaining_packages_only', action='store_true', default=False)

    parser.add_argument('-n', '--noscripts', '--no-scripts', dest='no_scripts', action='store_true', default=False)
    parser.add_argument('-o', '--onlyscripts', '--only-scripts', dest='only_scripts', action='store_true',
                        default=False)

    parser.add_argument('-X', '--exclude', dest='excludes', action='append', default=[])
    parser.add_argument('-A', '--all', dest='all_flag', action='store_true', default=False)

    parser.add_argument('--mainpackage', dest='main_package', action='store', default=None)
    parser.add_argument('--name', dest='name', action='store', default=None)
    parser.add_argument('--error-handler', dest='error_handler', action='store')

    parser.add_argument('-O', dest='o_options', action='append', default=[])
    parser.add_argument('-U', action='append', dest='upstream_args', default=[])
    # Added for "help only" - you cannot trigger this option in practice
    parser.add_argument('--', metavar='UPSTREAM_ARGS', action='extend', nargs='+', dest='unused')
    return parser
