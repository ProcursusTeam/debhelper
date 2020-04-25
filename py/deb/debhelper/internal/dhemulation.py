import errno
import os


def package_file(binary_package: 'AbstractBinaryPackage',
                 basename,
                 *,
                 always_fallback_to_packageless_variant=False,
                 mandatory=False
                 ):
    """Reduced implementation of debhelper's pkgfile

    Looks up the package specific version of a file in debian as debhelper's pkgfile
    would EXCEPT:
     * There is no support for architecture specific files
     * There is no support for --name

    :param binary_package A BinaryPackage
    :param basename The basename of the package file to look up (e.g. "install" or "docs")
    :param always_fallback_to_packageless_variant If True, always look up the package-less variant of
    the path.  This fallback is otherwise only performed for the "main package".
    :param mandatory If True, this will raise a FileNotFoundError if there is no matching file instead
    of returning None.
    :returns A path to the package file or None if the file could not be located (assuming mandatory=False)
    """

    possible_names = [
        "%s.%s" % (binary_package.package_name, basename)
    ]
    if binary_package.is_main_package or always_fallback_to_packageless_variant:
        possible_names.append(basename)

    for name in possible_names:
        path = "debian/%s" % name
        if os.path.exists(path):
            return path
    if mandatory:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "debian%s" % possible_names[0])
    return None


def install_as(binary_package: 'AbstractBinaryPackage',
               source,
               dest,
               *,
               mode=0o644):
    pass
