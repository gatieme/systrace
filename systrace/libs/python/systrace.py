#!/usr/bin/env python

import os

__all__ = ["traceBegin", "traceEnd", "Trace", "trace"]

_TRACE_MARKER = '/sys/kernel/debug/tracing/trace_marker'
_USE_TRACE = os.environ.get('ENABLE_SYSTRACE', '0') == '1'

if _USE_TRACE and os.access(_TRACE_MARKER, os.W_OK):
    _TRACE_FD = os.open(_TRACE_MARKER, os.O_WRONLY)
else:
    _USE_TRACE = False

if _USE_TRACE:
    import ctypes
    libc = ctypes.CDLL('libc.so.6')
    _sys_write = libc.write
    def traceBegin(name):
        buf = '|'.join(('B', str(os.getpid()), name))
        _sys_write(_TRACE_FD, buf, len(buf))

    def traceEnd():
        _sys_write(_TRACE_FD, 'E', 1)

    class Trace:
        def __init__(self, name):
            traceBegin(name)
        def __del__(self):
            traceEnd()

else:
    traceBegin = lambda name: None 
    traceEnd = lambda: None
    Trace = lambda name: None

class trace:
    def __init__(self, name = '', enable = lambda: _USE_TRACE):
        self.name = name
        self.enable = enable

    def __call__(self, func):
        if not self.enable():
            return func

        if not self.name:
            self.name = func.__name__
        def wrapper(*args, **kwds):
            traceBegin(self.name)
            r = func(*args, **kwds)
            traceEnd()
            return r
        return wrapper

def main():
    import time

    @trace()
    def sleep(duration):
        time.sleep(duration)

    class Sleep:
        @trace()
        def __init__(self):
            pass

        @trace()
        def sleep(self, duration):
            time.sleep(duration)

    # test manual trace
    traceBegin('Manual_Sleep')
    time.sleep(1)
    traceEnd()

    time.sleep(1)

    # test trace decorator
    sleep(1)

    s = Sleep()
    s.sleep(1)

if __name__ == '__main__':
    main()

# vim: ts=4 st=4 sts=4 expandtab syntax=python
