use strict; use warnings;
print "LANG=Perl\n";
my ($x,$s,$b,$n) = (42,"hi",1,undef);
print "LITERALS=$x,$s,$b,\n";
print "OPS=", 7*6 + length("abc"), "\n";
my $acc=0; $acc += $_ for (1..5);
print "CONTROL=$acc\n";
sub fact { my $k=shift; return $k<=1 ? 1 : $k*fact($k-1); }
print "FUNC=", fact(5), "\n";
my @arr=(1,2,3); my %d=(a=>1);
print "DATA=", scalar(@arr), ",$d{a}\n";
open(my $f, ">", "/tmp/plang_pl.txt") or die; print $f "io"; close $f;
open(my $g, "<", "/tmp/plang_pl.txt") or die; close $g; unlink "/tmp/plang_pl.txt";
print "IO=ok\n";
eval { die "x\n" }; print "ERROR=die\n" if $@;
print "CONCURRENCY=n/a(核心无原生线程)\n";
