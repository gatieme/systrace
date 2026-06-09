实现一套解析 perfetto trace 文件的脚本
python3 ./parse_perfetto_stats.py --db_file ../hitrace/record_trace_20260604112216@5527909-979956408.db  --interval 10

参考 ../../smartperf/script/parse_hitrace_stats.py 实现了一套解析 hitrace DB 文件的脚本，实现分析 perfetto db 文件的类似脚本。
1. 通过如下命令可以完成 hitrace 分析指定区间 [5527910967813126, 5527920967813126] 每 10ms 的 CPU/GPU 负载信息.
python3 ./parse_hitrace_stats.py --db_file ../hitrace/record_trace_20260604112216@5527909-979956408.db --start_ns 5527910967813126 --end_ns 5527920967813126 --interval 10 
2. Perfetto 源代码位于: /home/chengjian/Work/GitHub/Tools/perfetto/perfetto
3. Perfetto 相关资料
Trace Processor (Python): https://perfetto.dev/docs/analysis/trace-processor-python
Trace Processor (C++):  https://perfetto.dev/docs/analysis/trace-processor#shell

SQL 命令
1 GPU 相关
1.1 查询 GPU Load 可以通过
SELECT
ts, value AS gpu_load, track.name AS track_name
FROM counter
JOIN counter_track AS track ON counter.track_id = track.id
WHERE (track.name LIKE '%gpu%load%')
AND (ts BETWEEN start_ns AND end_ns)
ORDER BY ts

1.2 查询 GPU Freq 可以通过

SELECT
ts, value AS gpu_freq, track.name AS track_name
FROM counter
JOIN counter_track AS track ON counter.track_id = track.id
WHERE (track.name LIKE '%gpu_freq%')
AND (ts BETWEEN start_ns AND end_ns)
ORDER BY ts

2 DDR 相关
2.1 查询 DDR Bandwidth

SELECT
ts, value AS ddr_bandwidth, track.name AS track_name
FROM counter
JOIN counter_track AS track ON counter.track_id = track.id
WHERE (track.name LIKE '%ddr%width%')
AND (ts BETWEEN start_ns AND end_ns)
ORDER BY ts

2.2 查询 DDR Freq

SELECT
ts, value AS ddr_freq, track.name AS track_name
FROM counter
JOIN counter_track AS track ON counter.track_id = track.id
WHERE (track.name LIKE '%ddr%freq%')
AND (ts BETWEEN start_ns AND end_ns)
ORDER BY ts

3. CPU 相关

3.1 查询 CPU Load

SELECT
t.cpu, c.ts, c.value AS cpu_freq
FROM counter c
JOIN cpu_counter_track AS t
ON c.track_id = t.id
WHERE (t.name = 'cpuload')
AND (c.ts BETWEEN start_ns AND end_ns)
ORDER BY t.cpu, c.ts

3.2 查询 CPU Freq

SELECT
t.cpu, c.ts, c.value AS cpu_freq
FROM counter c
JOIN cpu_counter_track AS t
ON c.track_id = t.id
WHERE (t.name = 'cpufreq')
AND (c.ts BETWEEN start_ns AND end_ns)
ORDER BY t.cpu, c.ts

4. 查询 Mem 相关

SELECT ct.name AS counter_name, c.value, c.ts AS timestamp
FROM counter c
JOIN counter_tracker ct ON c.track_id = ct.id
WHERE ct.name IN ('MemTotal', 'MemFree', 'MemAvailable', 'Active')
AND c.ts BETWEEN start_ns AND end_ns
ORDER BY c.ts

5. IO  相关

SELECT ct.name AS counter_name, c.value, c.ts AS timestamp
FROM counter c
JOIN counter_track ct ON c.track_id = ct.id
WHERE ct.name LIKE 'diskstat.[sdf].%'
AND c.ts BETWEEN start_ns AND end_ns
ORDER BY c.ts
