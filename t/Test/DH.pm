package Test::DH;

use strict;
use warnings;

use Test::More;

use Exporter qw(import);

use File::Basename qw(dirname);

my $ROOT_DIR;

BEGIN {
    $ROOT_DIR = dirname(dirname(dirname(__FILE__)));
};

use lib "$ROOT_DIR/lib";

$ENV{PATH} = "$ROOT_DIR:$ENV{PATH}" if $ENV{PATH} !~ m{\Q$ROOT_DIR\E/?:};
$ENV{PERL5LIB} = join(':', "${ROOT_DIR}/lib", (grep { defined } $ENV{PERL5LIB}))
    if not $ENV{PERL5LIB} or $ENV{PERL5LIB} !~ m{\Q$ROOT_DIR\E(?:/lib)?/?:};

use Debian::Debhelper::Dh_Lib;

our @EXPORT = qw(
    each_compat_up_to_and_incl_subtest each_compat_subtest
    each_compat_from_and_above_subtest run_dh_tool
);

our $TEST_DH_COMPAT;

sub run_dh_tool {
    my (@cmd) = @_;
    my $compat = $TEST_DH_COMPAT;
    my $options = ref($cmd[0]) ? shift(@cmd) : {};
    my $pid = fork() // BAIL_OUT("fork failed: $!");
    if (not $pid) {
        $ENV{DH_COMPAT} = $compat;
        $ENV{DH_INTERNAL_TESTSUITE_SILENT_WARNINGS} = 1;
        if ($options->{quiet}) {
            open(STDOUT, '>', '/dev/null') or error("Reopen stdout: $!");
            open(STDERR, '>', '/dev/null') or error("Reopen stderr: $!");
        } else {
            # If run under prove/TAP, we don't want to confuse the test runner.
            open(STDOUT, '>&', *STDERR) or error("Redirect stdout to stderr: $!");
        }
        exec(@cmd);
    }
    waitpid($pid, 0) == $pid or BAIL_OUT("waitpid($pid) failed: $!");
    return 1 if not $?;
    return 0;
}

sub each_compat_up_to_and_incl_subtest($&) {
    my ($compat, $code) = @_;
    my $low = Debian::Debhelper::Dh_Lib::MIN_COMPAT_LEVEL;
    error("compat $compat is no longer support! Min compat $low")
        if $compat < $low;
    subtest '' => sub {
        while ($low <= $compat) {
            local $TEST_DH_COMPAT = $compat;
            $code->($low);
            ++$low;
        }
    };
    return;
}

sub each_compat_from_and_above_subtest($&) {
    my ($compat, $code) = @_;
    my $lowest = Debian::Debhelper::Dh_Lib::MIN_COMPAT_LEVEL;
    my $end = Debian::Debhelper::Dh_Lib::MAX_COMPAT_LEVEL;
    if ($lowest > $compat) {
        diag("Bumping $compat to $lowest ($compat is no longer supported)");
        $compat = $lowest;
    }
    error("$compat is from the future! Max known is $end")
        if $compat > $end;
    subtest '' => sub {
        while ($compat <= $end) {
            local $TEST_DH_COMPAT = $compat;
            $code->($compat);
            ++$compat;
        }
    };
    return;
}

sub each_compat_subtest(&) {
    unshift(@_, Debian::Debhelper::Dh_Lib::MIN_COMPAT_LEVEL);
    goto \&each_compat_from_and_above_subtest;
}

1;
