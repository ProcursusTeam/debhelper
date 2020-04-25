# PROMISE: DH NOOP WITHOUT cron.hourly cron.daily cron.weekly cron.monthly cron.yearly cron.d cli-options()
from deb.debhelper.internal import package_file, package_actions, install_as

BASENAMES = [
    'cron.hourly',
    'cron.daily',
    'cron.weekly',
    'cron.monthly',
    'cron.yearly',
    'cron.d',
]


@package_actions
def configure(package):
    for basename in BASENAMES:
        pkg_conf = package_file(package, basename)
        if not pkg_conf:
            continue
        mode = 0o644 if basename == 'cron.d' else 0o755
        target_path = "etc/" + basename + '/' + package.package_name
        install_as(package, pkg_conf, target_path, mode=mode)
