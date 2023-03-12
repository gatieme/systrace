#!/bin/bash

TRACING_PATH=/sys/kernel/debug/tracing

trace_clean()
{
	echo 0 > $TRACING_PATH/tracing_on
	echo 0 > $TRACING_PATH/events/enable

	echo 0 > $TRACING_PATH/options/record-tgid

	echo > $TRACING_PATH/trace
}


get_systrace()
{
	local sleepTime=$1

	rm -rf trace.html
	echo > $TRACING_PATH/trace

	echo 1 > $TRACING_PATH/options/record-tgid

	# sched
	echo 1 > $TRACING_PATH/events/sched/sched_wakeup/enable
	echo 1 > $TRACING_PATH/events/sched/sched_wakeup_new/enable
	echo 1 > $TRACING_PATH/events/sched/sched_switch/enable

	# irq and ipi
	echo 1 > $TRACING_PATH/events/irq/enable
	echo 1 > $TRACING_PATH/events/ipi/enable

	# cpu idle and frequency
	echo 1 > $TRACING_PATH/events/power/cpu_idle/enable
	echo 1 > $TRACING_PATH/events/power/cpu_frequency/enable
	echo 1 > $TRACING_PATH/events/power/cpu_frequency_limits/enable

	echo 1 > $TRACING_PATH/tracing_on

	eval $CMDLINE

	echo 0 > $TRACING_PATH/tracing_on
	echo 0 > $TRACING_PATH/events/enable

	cat $TRACING_PATH/trace > trace.html
	echo > $TRACING_PATH/trace
}

get_cmd()
{
	# -t time
	# -r cmdline
	while getopts "t:r:" OPT
	do
		case $OPT in
			t)
				CMDLINE="sleep $OPTARG"
				;;
			r)
				shift $((OPTIND-2))
				CMDLINE=$* #$OPTARG
				;;
			?)
				echo "unkonw argument"
				#exit 1
				;;
		esac
	done
}

trap "trace_clean" 1 2 3 9 15

trace_clean
get_cmd $*
get_systrace
trace_clean
