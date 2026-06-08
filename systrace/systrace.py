#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ts=4 st=4 sts=4 expandtab syntax=python

import sys, os, time
import signal
import optparse

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SIMPLE = True
if not SIMPLE:
    html_prefix = """<!DOCTYPE HTML>
<html>
<head i18n-values="dir:textdirection;">
<title>Linux System Trace</title>
%s
%s
<script language="javascript">
document.addEventListener('DOMContentLoaded', function() {
  if (!linuxPerfData)
    return;

  var m = new tracing.TimelineModel(linuxPerfData);
  var timelineViewEl = document.querySelector('.view');
  base.ui.decorate(timelineViewEl, tracing.TimelineView);
  timelineViewEl.model = m;
  timelineViewEl.tabIndex = 1;
  timelineViewEl.timeline.focusElement = timelineViewEl;
});
</script>
<style>
  .view {
    overflow: hidden;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
  }
</style>
</head>
<body>
  <div class="view">
  </div>
<!-- BEGIN TRACE -->
  <script>
  var linuxPerfData = "\\
"""

    html_suffix = """\\n";
  </script>
<!-- END TRACE -->
</body>
</html>
"""

    compiled_css_tag = """<style type="text/css">%s</style>"""
    compiled_js_tag = """<script language="javascript">%s</script>"""


    css_path = SCRIPT_DIR + '/style.css'
    script_path = SCRIPT_DIR + '/script.js'



DEBUG_DIR = '/sys/kernel/debug/'
TRACE_DIR = DEBUG_DIR + 'tracing/'

TRACE_CLOCK = TRACE_DIR + 'trace_clock'
TRACE_BUFFER_SIZE = TRACE_DIR + 'buffer_size_kb'
TRACE_OVERWRITE = TRACE_DIR + 'options/overwrite'
TRACE_RECORD_TGID = TRACE_DIR + 'options/record-tgid'

EVENT_DIR = TRACE_DIR + 'events/'
TRACE_SWITCH = EVENT_DIR + 'sched/sched_switch/enable'
TRACE_WAKEUP = EVENT_DIR + 'sched/sched_wakeup/enable'
TRACE_MEMORY_BUS = EVENT_DIR + 'memory_bus/enable'
TRACE_FREQUENCY = EVENT_DIR + 'power/cpu_frequency/enable'
TRACE_CLOCK_SET_RATE = EVENT_DIR + 'power/clock_set_rate/enable'
TRACE_CPU_IDLE = EVENT_DIR + 'power/cpu_idle/enable'
TRACE_GOVERNOR = EVENT_DIR + 'cpufreq_interactive/enable'
TRACE_SYNC = EVENT_DIR + 'sync/enable'
TRACE_WORKQUEUE = EVENT_DIR + 'workqueue/enable'

TRACE_DISK = (EVENT_DIR + 'ext4/ext4_sync_file_enter/enable',
        EVENT_DIR + 'ext4/ext4_sync_file_exit/enable',
        EVENT_DIR + 'block/block_rq_issue/enable',
        EVENT_DIR + 'block/block_rq_complete/enable', )

TRACE_ON = TRACE_DIR + 'tracing_on'
TRACE_PATH = TRACE_DIR + 'trace'
TRACE_MARKER = TRACE_DIR + 'trace_marker'
TRACE_EVENT_PID = TRACE_DIR + 'set_event_pid'
TRACE_SCHED_FILTER = EVENT_DIR + 'sched/filter'

def setEnable(filename, enable):
    if os.access(filename, os.W_OK):
        open(filename, 'w').write(enable and '1' or '0')
        if options.verbose:
            sys.stdout.write('write success: %s %s\n' % (filename, enable))
        return True
    elif options.verbose:
        sys.stdout.write('write failed: %s %s\n' % (filename, enable))
    return False

def setTraceOverwrite(enable):
    return setEnable(TRACE_OVERWRITE, enable)

def setTraceRecordTgid(enable):
    return setEnable(TRACE_RECORD_TGID, enable)

def setSchedSwitch(enable):
    if setEnable(TRACE_SWITCH, enable) and setEnable(TRACE_WAKEUP, enable):
        return True
    return False

def setGpu(enable):
    BASE_DIR = EVENT_DIR + 'i915/'
    import glob
    for f in glob.glob(BASE_DIR + '*/enable'):
        setEnable(f, enable)
    setEnable(EVENT_DIR + 'drm/drm_vblank_event/enable', enable)
    return True

def setBusUtilization(enable):
    return setEnable(TRACE_MEMORY_BUS, enable)

def setFrequency(enable):
    if setEnable(TRACE_FREQUENCY, enable) and setEnable(TRACE_CLOCK_SET_RATE, enable):
        return True
    return False

def setCpuIdle(enable):
    return setEnable(TRACE_CPU_IDLE, enable)

def setGovernor(enable):
    return setEnable(TRACE_GOVERNOR, enable)

def setSync(enable):
    return setEnable(TRACE_SYNC, enable)

def setWorkqueue(enable):
    return setEnable(TRACE_WORKQUEUE, enable)

def setDisk(enable):
    for f in TRACE_DISK:
        setEnable(f, enable)
    return True

def setCustomEnable(events, enable):
    if len(events) == 0 or events.isspace():
           return True
    event_list = events.strip().split(',')
    for event in event_list:
        custom_event = EVENT_DIR + event + "/enable"
        if not setEnable(custom_event, enable):
            sys.stderr.write('write failed: %s %s\n' % (custom_event, enable))
            return False
    return True

def setPid(trace_pid, enable):
    if len(trace_pid) == 0 or trace_pid.isspace():
        return True
    if enable:
        pids = trace_pid.strip().split(',')
        for pid in pids:
            open(TRACE_EVENT_PID, "a+").write(pid)
        if options.verbose:
            sys.stdout.write('set-pid success: %s\n' %(pid))
    else:
        open(TRACE_EVENT_PID, "w").write("")
        if options.verbose:
            sys.stdout.write('clr-pid success: %s\n' %(pid))

def setFilter(trace_filter, enable):
    if len(trace_filter) == 0 or trace_filter.isspace():
        return True

    if enable:
        trace_filter = trace_filter.strip()
        open(TRACE_SCHED_FILTER, "w").write(trace_filter)
    else:
        open(TRACE_SCHED_FILTER, "w").write(" ")

    if options.verbose:
        sys.stdout.write('filter success: %s %s\n' % (trace_filter, enable))
    return True

def setTracingEnable(enable):
    return setEnable(TRACE_ON, enable)

def clearTrace():
    if options.verbose:
        sys.stdout.write('=======Clear Tracing=======\n')
    open(TRACE_PATH, 'w').write("")

def setTraceBufferSize(size):
    open(TRACE_BUFFER_SIZE, 'w').write('%d'%size)

def setGlobalClock(enable):
    open(TRACE_CLOCK, 'w').write(enable and 'global' or 'local')

def startTrace(options):
    if options.verbose:
        sys.stdout.write('=======Start Tracing=======\n')
    setTraceOverwrite(True)
    setTraceRecordTgid(True)
    if options.trace_cpu_sched:
       setSchedSwitch(True)
    if options.trace_cpu_freq:
        setFrequency(True)
    if options.trace_cpu_idle:
        setCpuIdle(True)
    setTraceBufferSize(options.trace_buf_size)
    setGlobalClock(True)
    if options.trace_gpu:
        setGpu(True)
    setCustomEnable(options.trace_event, True)
    setPid(options.trace_pid, True)
    setFilter(options.trace_filter, True)

    isRoot = False

    if isRoot:
        setGovernor(True)
        setBusUtilization(True)
        setSync(True)
        if options.trace_workqueue:
            setWorkqueue(True)
        if options.trace_disk:
            setDisk(True)

    setTracingEnable(True)

def stopTrace():
    if options.verbose:
        sys.stdout.write('=======Stop Tracing=======\n')
    setTracingEnable(False)
    setTraceOverwrite(True)
    setTraceRecordTgid(False)

    setSchedSwitch(False)
    setFrequency(False)
    setGlobalClock(False)

    setGpu(False)
    setCustomEnable(options.trace_event, False)
    setPid(options.trace_pid, False)
    setFilter(options.trace_filter, False)

    isRoot = False

    if isRoot:
        setGovernor(False)
        setBusUtilization(False)
        setSync(False)
        setWorkqueue(False)
        setDisk(False)

def dumpTrace(out):
    if options.verbose:
        sys.stdout.write('=======Dump Tracing=======\n')

    time.sleep(options.trace_time)

    f = open(TRACE_PATH)
    while True:
        d = f.read(64 * 1024 * 1024)
        if not d: break
        out.write(d)

def sig_handler(sig, frame):
    if sig in (signal.SIGTERM, signal.SIGQUIT, signal.SIGINT):
        stopTrace()
        clearTrace()
        setTraceBufferSize(1)
        sys.exit(0)

def check_environment():
    if not os.access(TRACE_DIR, os.X_OK):
        sys.stderr.write('Your system configuration is not acceptable for systrace\n')
        sys.stderr.write('Please check these items\n')
        sys.stderr.write('  1. mount debugfs on /sys/kernel/debug\n')
        sys.stderr.write('  2. turn on CONFIG_FTRACE and their family in your kernel feature\n')
        sys.exit(1)

def main(options):
    for sig in (signal.SIGTERM, signal.SIGQUIT, signal.SIGINT):
        signal.signal(sig, sig_handler)

    if not SIMPLE:
        css = compiled_css_tag % (open(css_path).read())
        js = compiled_js_tag % (open(script_path).read())

    filename = os.path.abspath(options.output_file)
    out = open(filename, 'w')
    if not SIMPLE:
        out.write(html_prefix%(css, js))

    clearTrace()
    startTrace(options)
    dumpTrace(out)
    stopTrace()
    if not SIMPLE:
        out.write(html_suffix)
    del out

    clearTrace()
    setTraceBufferSize(1)

    sys.stdout.write('wrote output file://' + filename + '\n')
    sys.stdout.flush()


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-o', dest='output_file', help='write HTML to FILE',
                    default='trace.html', metavar='FILE')
    parser.add_option('-t', '--time', dest='trace_time', type='int',
                    default=5, help='trace for N seconds', metavar='N')
    parser.add_option('-b', '--buf-size', dest='trace_buf_size', type='int',
                    default=2048, help='use a trace buffer size of N KB', metavar='N')
    parser.add_option('-d', '--disk', dest='trace_disk', default=False,
                    action='store_true', help='trace disk I/O (requires root)')
    parser.add_option('-F', '--cpu-freq', dest='trace_cpu_freq', default=False,
                    action='store_true', help='trace CPU frequency changes')
    parser.add_option('-i', '--cpu-idle', dest='trace_cpu_idle', default=False,
                    action='store_true', help='trace CPU idle events')
    parser.add_option('-l', '--cpu-load', dest='trace_cpu_load', default=False,
                    action='store_true', help='trace CPU load')
    parser.add_option('-s', '--no-cpu-sched', dest='trace_cpu_sched', default=True,
                    action='store_false', help='inhibit tracing CPU ' +
                    'scheduler (allows longer trace times by reducing data ' +
                    'rate into buffer)')
    parser.add_option('-w', '--workqueue', dest='trace_workqueue', default=False,
                    action='store_true', help='trace the kernel workqueues ' +
                    '(requires root)')
    parser.add_option('-g', '--gpu', dest='trace_gpu', default=False,
                    action='store_true', help='trace GPU events')
    parser.add_option('-e', '--trace-event', dest='trace_event', type='str',
                    default="", help='trace Custom events')
    parser.add_option('-v', '--verbose', dest='verbose', default=False,
                    action='store_true', help='be more verbose')
    parser.add_option('-p', '--pid', dest='trace_pid', type="str", default='',
                    help='Record events pn existing process ID')
    parser.add_option('-f', '--filter', dest='trace_filter', type="str", default='',
                    help='trace event filter')

    options, args = parser.parse_args()

    if os.getuid() != 0:
        cmd = ['sudo', sys.executable, SCRIPT_PATH] + sys.argv[1:]
        os.execlp(cmd[0], *cmd)

    check_environment()
    main(options)
