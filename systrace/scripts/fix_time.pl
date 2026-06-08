use warnings;

my $file_name = $ARGV[0] // "systrace.html";
open FH, $file_name;

my $output_name = $ARGV[1] // "mytrace.js";
open OUT, ">$output_name";

my ($time, $start);

while (<FH>) {
	if (1) {
		$_ = <FH>;
		($start) = /(\d+\.\d+): /;
		unless ($start) {
			# try one more line
			$_ = <FH>;
			($start) = /(\d+\.\d+): /;
		}

		die "not get start timestamp" unless $start;

		#print "start is $start\n";
		print OUT "start is $start\n";
		last;
	}
}


while (<FH>) {
	if (1) {
		($time) = /(\d+\.\d+): /;
		next unless time;
		$time = $time - $start;
		$time = $time * 1000;

		my $time_ms_part = $time;
		my $time_us_part = $time;
		$time_ms_part = int($time);
		$time_us_part = int(($time_us_part - $time_ms_part) * 1000);

		#print "$time_ms_part, $time_us_part\n";
		s/\d+\.\d+: /$time_ms_part ms($time_us_part us): /;

		print OUT $_
	}
}
