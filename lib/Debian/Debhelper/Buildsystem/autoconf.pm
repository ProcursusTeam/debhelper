# A debhelper build system class for handling Autoconf based projects
#
# Copyright: © 2008 Joey Hess
#            © 2008-2009 Modestas Vainius
# License: GPL-2+

package Debian::Debhelper::Buildsystem::autoconf;

use strict;
use warnings;
use Debian::Debhelper::Dh_Lib qw(dpkg_architecture_value sourcepackage compat
	get_installation_directory);
use parent qw(Debian::Debhelper::Buildsystem::makefile);

sub DESCRIPTION {
	"GNU Autoconf (configure)"
}

sub check_auto_buildable {
	my $this=shift;
	my ($step)=@_;

	return 0 unless -x $this->get_sourcepath("configure");

	# Handle configure explicitly; inherit the rest
	return 1 if $step eq "configure";
	return $this->SUPER::check_auto_buildable(@_);
}

sub _get_paths {
	my ($this, @paths) = @_;
	return map {
		"--${_}=" . get_installation_directory($_, 'autoconf')
	} @paths;
}

sub configure {
	my $this=shift;

	# Standard set of options for configure.
	my @opts;
	push @opts, "--build=" . dpkg_architecture_value("DEB_BUILD_GNU_TYPE");
	push(@opts, $this->_get_paths(qw(
			prefix
			includedir
			mandir
			infodir
			sysconfdir
			localstatedir
		)));
	if (defined $ENV{DH_QUIET} && $ENV{DH_QUIET} ne "") {
		push @opts, "--enable-silent-rules";
	} else {
		push @opts, "--disable-silent-rules";
	}
	my $multiarch=dpkg_architecture_value("DEB_HOST_MULTIARCH");
	if (! compat(8)) {
		if (defined $multiarch) {
			push @opts, "--libdir=\${prefix}/lib/$multiarch";
			push @opts, "--libexecdir=\${prefix}/lib/$multiarch";
		}
		else {
			push @opts, "--libexecdir=\${prefix}/lib";
		}
	}
	else {
		push @opts, "--libexecdir=\${prefix}/lib/" . sourcepackage();
	}
	push @opts, "--runstatedir=/run" if not compat(10);
	push @opts, "--disable-maintainer-mode";
	push @opts, "--disable-dependency-tracking";
	# Provide --host only if different from --build, as recommended in
	# autotools-dev README.Debian: When provided (even if equal)
	# autoconf 2.52+ switches to cross-compiling mode.
	if (dpkg_architecture_value("DEB_BUILD_GNU_TYPE")
	    ne dpkg_architecture_value("DEB_HOST_GNU_TYPE")) {
		push @opts, "--host=" . dpkg_architecture_value("DEB_HOST_GNU_TYPE");
	}

	$this->mkdir_builddir();
	eval {
		$this->doit_in_builddir($this->get_source_rel2builddir("configure"), @opts, @_);
	};
	if ($@) {
		if (-e $this->get_buildpath("config.log")) {
			$this->doit_in_builddir('tail', '-v', '-n', '+0', 'config.log');
		}
		die $@;
	}
}

sub test {
	my $this=shift;
	$this->make_first_existing_target(['test', 'check'],
		"VERBOSE=1", @_);
}

1
