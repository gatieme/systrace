# -*- coding: utf-8 -*-


from perfetto.trace_processor import TraceProcessor
tp = TraceProcessor(trace='trace/traces/[36G0224605012554][System Trace] 2026-06-08-23-16-28.trace.pb')

qr_it = tp.query('SELECT name FROM slice')
for row in qr_it:
      print(row.name)
