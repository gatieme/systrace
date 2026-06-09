#!/usr/bin/env python3
"""解析 Perfetto .pftrace 文件，按指定间隔导出 GPU/DDR/CPU/Mem/IO 统计到 xlsx。

参考实现：../../smartperf/script/parse_hitrace_stats.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from perfetto.trace_processor import TraceProcessor


def format_interval_label(interval_sec: float) -> str:
    """将 interval_sec 转为可读标签，如 '5s', '10ms', '100ms'。"""
    if interval_sec >= 1.0 and interval_sec == int(interval_sec):
        return f"{int(interval_sec)}s"
    ms = interval_sec * 1000
    if ms >= 1.0 and ms == int(ms):
        return f"{int(ms)}ms"
    return f"{interval_sec:.4g}s"


def get_trace_range(tp: TraceProcessor) -> tuple[int, int]:
    """获取 trace 时间范围（起止时间戳）。

    Perfetto trace 没有 trace_range 表，通过查询 counter 表估算范围。
    """
    sql = """
        SELECT MIN(ts) AS start_ts, MAX(ts) AS end_ts
        FROM counter
    """
    result = tp.query(sql)
    row = result.__iter__().__next__()
    # Perfetto Row 是动态类型，属性名取决于 SQL 列名
    start_ts = getattr(row, "start_ts", 0)
    end_ts = getattr(row, "end_ts", 0)
    return int(start_ts), int(end_ts)


def query_to_dataframe(tp: TraceProcessor, sql: str) -> pd.DataFrame:
    """执行 SQL 查询并返回 Pandas DataFrame。

    Perfetto query() 返回 QueryResultIterator，转换为 DataFrame 方便后续处理。
    """
    result = tp.query(sql)
    return result.as_pandas_dataframe()


def query_gpu_load(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 GPU Load 数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: ts, gpu_load, track_name
    """
    sql = f"""
        SELECT
            ts, value AS gpu_load, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%gpu%load%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return query_to_dataframe(tp, sql)


def query_gpu_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 GPU Frequency 数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: ts, gpu_freq, track_name
    """
    sql = f"""
        SELECT
            ts, value AS gpu_freq, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%gpu_freq%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return query_to_dataframe(tp, sql)


def query_ddr_bandwidth(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 DDR Bandwidth 数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: ts, ddr_bandwidth, track_name
    """
    sql = f"""
        SELECT
            ts, value AS ddr_bandwidth, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%ddr%width%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return query_to_dataframe(tp, sql)


def query_ddr_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 DDR Frequency 数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: ts, ddr_freq, track_name
    """
    sql = f"""
        SELECT
            ts, value AS ddr_freq, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%ddr%freq%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return query_to_dataframe(tp, sql)


def query_cpu_load(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 CPU Load 数据（按 CPU ID）。

    Args:
        tp: TraceProcessor 实例
        start_ns: 赬始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: cpu, ts, cpu_load
    """
    sql = f"""
        SELECT
            t.cpu, c.ts, c.value AS cpu_load
        FROM counter c
        JOIN cpu_counter_track AS t
        ON c.track_id = t.id
        WHERE (t.name = 'cpuload')
        AND (c.ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY t.cpu, c.ts
    """
    return query_to_dataframe(tp, sql)


def query_cpu_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 CPU Frequency 数据（按 CPU ID）。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: cpu, ts, cpu_freq
    """
    sql = f"""
        SELECT
            t.cpu, c.ts, c.value AS cpu_freq
        FROM counter c
        JOIN cpu_counter_track AS t
        ON c.track_id = t.id
        WHERE (t.name = 'cpufreq')
        AND (c.ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY t.cpu, c.ts
    """
    return query_to_dataframe(tp, sql)


def query_mem(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 Memory 统计数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: counter_name, value, timestamp
    """
    sql = f"""
        SELECT
            ct.name AS counter_name, c.value, c.ts AS timestamp
        FROM counter c
        JOIN counter_track ct ON c.track_id = ct.id
        WHERE ct.name IN ('MemTotal', 'MemFree', 'MemAvailable', 'Active')
        AND c.ts BETWEEN {start_ns} AND {end_ns}
        ORDER BY c.ts
    """
    return query_to_dataframe(tp, sql)


def query_io(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 I/O 统计数据。

    Args:
        tp: TraceProcessor 实例
        start_ns: 起始时间戳（纳秒）
        end_ns: 结束时间戳（纳秒）

    Returns:
        DataFrame with columns: counter_name, value, timestamp
    """
    sql = f"""
        SELECT
            ct.name AS counter_name, c.value, c.ts AS timestamp
        FROM counter c
        JOIN counter_track ct ON c.track_id = ct.id
        WHERE ct.name LIKE 'diskstat.[sdf].%'
        AND c.ts BETWEEN {start_ns} AND {end_ns}
        ORDER BY c.ts
    """
    return query_to_dataframe(tp, sql)


import bisect


def measure_time_weighted_avg(
    samples: list[dict],
    value_key: str,
    win_start_ns: int,
    win_end_ns: int,
    idx_start: int = 0,
    idx_end: int | None = None,
) -> float:
    """计算时间加权平均值（step function 模型）。

    Perfetto counter 数据是瞬时值，采用 step function 模型：
    每个采样点的值持续到下一个采样点。

    Args:
        samples: 采样点列表，每个元素包含 ts 和 value_key 字段
        value_key: value 字段的键名（如 'gpu_load', 'cpu_freq'）
        win_start_ns: 窗口起始时间戳（纳秒）
        win_end_ns: 窗口结束时间戳（纳秒）
        idx_start: 搜索起始索引（用于 bisect 加速）
        idx_end: 搜索结束索引（用于 bisect 加速）

    Returns:
        时间加权平均值
    """
    window_ns = win_end_ns - win_start_ns
    if window_ns <= 0:
        return 0.0

    end_idx = idx_end if idx_end is not None else len(samples)
    weighted_sum = 0.0

    for i in range(idx_start, end_idx):
        sample = samples[i]
        start = sample["ts"]
        value = sample[value_key]

        # step function: 当前值持续到下一个采样点
        end = samples[i + 1]["ts"] if i + 1 < end_idx else win_end_ns

        # 裁剪到窗口范围
        if end <= win_start_ns or start >= win_end_ns:
            continue
        clip_start = max(start, win_start_ns)
        clip_end = min(end, win_end_ns)

        if clip_end > clip_start:
            weighted_sum += value * (clip_end - clip_start)

    return weighted_sum / window_ns


def compute_metric_windows(
    samples: pd.DataFrame,
    value_key: str,
    interval_sec: float,
    range_start_ns: int | None = None,
    range_end_ns: int | None = None,
) -> pd.DataFrame:
    """按滑动窗口计算时间加权平均值。

    Args:
        samples: 采样点 DataFrame，必须包含 ts 和 value_key 列
        value_key: value 字段的列名（如 'gpu_load', 'cpu_freq'）
        interval_sec: 窗口间隔（秒）
        range_start_ns: 分析区间起始时间戳（纳秒），None 表示数据起始
        range_end_ns: 分析区间结束时间戳（纳秒），None 表示数据结束

    Returns:
        DataFrame with columns: window_start_ns, window_end_ns, elapsed_sec, value_avg
    """
    if samples.empty:
        return pd.DataFrame()

    # pandas Series 转换为 int 需先提取 scalar 值
    timeline_start = int(samples["ts"].min().item())
    timeline_end = int(samples["ts"].max().item())

    win_start_bound = (
        range_start_ns if range_start_ns is not None else timeline_start
    )
    win_end_bound = range_end_ns if range_end_ns is not None else timeline_end

    win_start_bound = max(win_start_bound, timeline_start)
    win_end_bound = min(win_end_bound, timeline_end)

    if win_start_bound >= win_end_bound:
        return pd.DataFrame()

    window_ns = int(interval_sec * 1_000_000_000)

    sample_list = samples.to_dict("records")
    ts_sorted = [s["ts"] for s in sample_list]

    rows = []
    win_start = win_start_bound
    left_idx = 0

    while win_start < win_end_bound:
        win_end = min(win_start + window_ns, win_end_bound)

        # 推进左边界：跳过完全在窗口左侧的样本
        while (
            left_idx < len(sample_list)
            and sample_list[left_idx]["ts"] + (window_ns if left_idx == 0 else 0)
            < win_start
        ):
            # Perfetto counter 是瞬时值，左边界推进逻辑不同
            # 样本结束时间 = 下一个样本开始时间（如果没有下一个，则是窗口结束）
            next_ts = (
                sample_list[left_idx + 1]["ts"]
                if left_idx + 1 < len(sample_list)
                else win_end_bound
            )
            if next_ts <= win_start:
                left_idx += 1
            else:
                break

        # bisect 找右边界
        right_idx = bisect.bisect_left(ts_sorted, win_end)

        avg = measure_time_weighted_avg(
            sample_list,
            value_key,
            win_start,
            win_end,
            idx_start=left_idx,
            idx_end=right_idx,
        )

        row = {
            "window_start_ns": win_start,
            "window_end_ns": win_end,
            "elapsed_sec": round(len(rows) * interval_sec, 4),
            f"{value_key}_avg": round(avg, 2),
        }
        rows.append(row)
        win_start = win_end

    df_result = pd.DataFrame(rows)
    return df_result


def compute_cpu_windows(
    samples: pd.DataFrame,
    interval_sec: float,
    range_start_ns: int | None = None,
    range_end_ns: int | None = None,
) -> pd.DataFrame:
    """按滑动窗口计算 CPU Load/Freq（按 CPU ID 分组）。

    Args:
        samples: CPU采样点 DataFrame，必须包含 cpu, ts, cpu_load/cpu_freq 列
        interval_sec: 窗口间隔（秒）
        range_start_ns: 分析区间起始时间戳（纳秒）
        range_end_ns: 分析区间结束时间戳（纳秒）

    Returns:
        DataFrame with columns: window_start_ns, window_end_ns, elapsed_sec, CPU0, CPU1, ...
    """
    if samples.empty:
        return pd.DataFrame()

    value_key = "cpu_load" if "cpu_load" in samples.columns else "cpu_freq"
    cpu_ids = sorted(samples["cpu"].unique())

    # 按 CPU ID 分组计算
    cpu_results: dict[int, pd.DataFrame] = {}
    for cpu_id in cpu_ids:
        cpu_samples = samples[samples["cpu"] == cpu_id].sort_values(by="ts")  # type: ignore
        cpu_df = compute_metric_windows(
            cpu_samples, value_key, interval_sec, range_start_ns, range_end_ns
        )
        if not cpu_df.empty:
            cpu_results[cpu_id] = cpu_df.rename(
                columns={f"{value_key}_avg": f"CPU{cpu_id}"}
            )

    if not cpu_results:
        return pd.DataFrame()

    # 合合所有 CPU 的结果（按 elapsed_sec 对齐）
    merged_df = cpu_results[cpu_ids[0]][
        ["window_start_ns", "window_end_ns", "elapsed_sec"]
    ].copy()
    for cpu_id in cpu_ids:
        if cpu_id in cpu_results:
            merged_df[f"CPU{cpu_id}"] = cpu_results[cpu_id][f"CPU{cpu_id}"]

    return merged_df.astype(pd.DataFrame)  # type: ignore


def validate_time_range(
    start_ns: int | None,
    end_ns: int | None,
    trace_start: int,
    trace_end: int,
) -> tuple[int, int]:
    """校验用户指定的时间区间，返回实际分析的起止时间戳。

    Args:
        start_ns: 用户指定的起始时间戳（纳秒），None 表示默认 trace_start
        end_ns: 用户指定的结束时间戳（纳秒），None 表示默认 trace_end
        trace_start: trace 内部起始时间戳
        trace_end: trace 内部结束时间戳

    Returns:
        实际分析的起止时间戳 (actual_start, actual_end)
    """
    actual_start = start_ns if start_ns is not None else trace_start
    actual_end = end_ns if end_ns is not None else trace_end

    # 校验范围
    if actual_start < trace_start:
        raise ValueError(
            f"start_ns ({actual_start}) < trace_start ({trace_start}), 超出范围"
        )
    if actual_end > trace_end:
        raise ValueError(
            f"end_ns ({actual_end}) > trace_end ({trace_end}), 超出范围"
        )
    if actual_start >= actual_end:
        raise ValueError(
            f"start_ns ({actual_start}) >= end_ns ({actual_end}), 区间无效"
        )

    return actual_start, actual_end


def main(argv: list[str]) -> int:
    """主函数入口。"""
    parser = argparse.ArgumentParser(
        description="解析 Perfetto .pftrace 文件，按指定间隔导出 GPU/DDR/CPU/Mem/IO 统计到 xlsx",
    )
    parser.add_argument(
        "--trace_file",
        type=Path,
        required=True,
        help="待分析的 .pftrace 文件路径",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="统计窗口间隔，单位 ms（默认 10ms）",
    )
    parser.add_argument(
        "--start_ns",
        type=int,
        default=None,
        help="分析起始时间（trace 内部时间戳，纳秒），默认 trace 起始",
    )
    parser.add_argument(
        "--end_ns",
        type=int,
        default=None,
        help="分析结束时间（trace 内部时间戳，纳秒），默认 trace 结束",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 xlsx 文件路径（默认与 trace 同目录，后缀 .stats.xlsx）",
    )
    args = parser.parse_args(argv[1:])

    trace_path = args.trace_file.resolve()
    if not trace_path.exists():
        print(f"Trace 文件不存在: {trace_path}")
        return 1

    interval_sec = args.interval / 1000.0  # ms → s

    print(f"Loading {trace_path}")
    print(f"Interval: {format_interval_label(interval_sec)}")

    # 加载 trace
    try:
        tp = TraceProcessor(trace=str(trace_path))
    except Exception as e:
        print(f"加载 trace 失败: {e}")
        return 1

    # 获取 trace 时间范围
    trace_start, trace_end = get_trace_range(tp)
    print(f"trace_range: [{trace_start}, {trace_end}]")

    # 校验用户指定的时间区间
    start_ns, end_ns = args.start_ns, args.end_ns
    try:
        actual_start, actual_end = validate_time_range(
            start_ns, end_ns, trace_start, trace_end
        )
    except ValueError as e:
        print(f"时间区间校验失败: {e}")
        return 1

    print(f"analysis_range: [{actual_start}, {actual_end}]")

    # 输出路径
    output_path = (
        args.output.resolve()
        if args.output
        else trace_path.with_suffix(".stats.xlsx")
    )

    print(f"Output: {output_path}")

    # 数据查询
    print("Querying GPU data...")
    gpu_load_df = query_gpu_load(tp, actual_start, actual_end)
    gpu_freq_df = query_gpu_freq(tp, actual_start, actual_end)

    print("Querying DDR data...")
    ddr_bw_df = query_ddr_bandwidth(tp, actual_start, actual_end)
    ddr_freq_df = query_ddr_freq(tp, actual_start, actual_end)

    print("Querying CPU data...")
    cpu_load_df = query_cpu_load(tp, actual_start, actual_end)
    cpu_freq_df = query_cpu_freq(tp, actual_start, actual_end)

    print("Querying Mem data...")
    mem_df = query_mem(tp, actual_start, actual_end)

    print("Querying IO data...")
    io_df = query_io(tp, actual_start, actual_end)

    # 滑动窗口计算
    print("Computing sliding windows...")
    gpu_load_windows = compute_metric_windows(
        gpu_load_df, "gpu_load", interval_sec, actual_start, actual_end
    )
    gpu_freq_windows = compute_metric_windows(
        gpu_freq_df, "gpu_freq", interval_sec, actual_start, actual_end
    )
    ddr_bw_windows = compute_metric_windows(
        ddr_bw_df, "ddr_bandwidth", interval_sec, actual_start, actual_end
    )
    ddr_freq_windows = compute_metric_windows(
        ddr_freq_df, "ddr_freq", interval_sec, actual_start, actual_end
    )
    cpu_load_windows = compute_cpu_windows(
        cpu_load_df, interval_sec, actual_start, actual_end
    )
    cpu_freq_windows = compute_cpu_windows(
        cpu_freq_df, interval_sec, actual_start, actual_end
    )

    # Mem/IO 按counter_name分组计算（简化处理）
    mem_windows_dict: dict[str, pd.DataFrame] = {}
    if not mem_df.empty:
        for counter_name in mem_df["counter_name"].unique():
            mem_subset = mem_df[mem_df["counter_name"] == counter_name].copy()
            mem_windows_dict[counter_name] = compute_metric_windows(
                mem_subset, "value", interval_sec, actual_start, actual_end  # type: ignore
            )

    io_windows_dict: dict[str, pd.DataFrame] = {}
    if not io_df.empty:
        for counter_name in io_df["counter_name"].unique():
            io_subset = io_df[io_df["counter_name"] == counter_name].copy()
            io_windows_dict[counter_name] = compute_metric_windows(
                io_subset, "value", interval_sec, actual_start, actual_end  # type: ignore
            )

    # xlsx 输出（简化版，仅导出数据，图表 TODO）
    print("Exporting to xlsx...")
    il = format_interval_label(interval_sec)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Summary sheet
        summary_data = {
            "trace_file": str(trace_path),
            "trace_start_ns": trace_start,
            "trace_end_ns": trace_end,
            "analysis_start_ns": actual_start,
            "analysis_end_ns": actual_end,
            "interval_sec": interval_sec,
            "interval_label": il,
            "gpu_load_rows": len(gpu_load_windows),
            "gpu_freq_rows": len(gpu_freq_windows),
            "ddr_bandwidth_rows": len(ddr_bw_windows),
            "ddr_freq_rows": len(ddr_freq_windows),
            "cpu_load_rows": len(cpu_load_windows),
            "cpu_freq_rows": len(cpu_freq_windows),
            "mem_counters": len(mem_windows_dict),
            "io_counters": len(io_windows_dict),
        }
        pd.DataFrame([summary_data]).to_excel(
            writer, sheet_name="summary", index=False
        )

        # GPU sheets
        if not gpu_load_windows.empty:
            gpu_load_windows.to_excel(
                writer, sheet_name=f"gpu_load_{il}", index=False
            )
        if not gpu_freq_windows.empty:
            gpu_freq_windows.to_excel(
                writer, sheet_name=f"gpu_freq_{il}", index=False
            )

        # DDR sheets
        if not ddr_bw_windows.empty:
            ddr_bw_windows.to_excel(
                writer, sheet_name=f"ddr_bandwidth_{il}", index=False
            )
        if not ddr_freq_windows.empty:
            ddr_freq_windows.to_excel(
                writer, sheet_name=f"ddr_freq_{il}", index=False
            )

        # CPU sheets
        if not cpu_load_windows.empty:
            cpu_load_windows.to_excel(
                writer, sheet_name=f"cpu_load_{il}", index=False
            )
        if not cpu_freq_windows.empty:
            cpu_freq_windows.to_excel(
                writer, sheet_name=f"cpu_freq_{il}", index=False
            )

        # Mem sheets（按counter_name）
        if mem_windows_dict:
            for counter_name, df in mem_windows_dict.items():
                if not df.empty:
                    safe_name = counter_name.replace("/", "_")
                    df.to_excel(
                        writer, sheet_name=f"mem_{safe_name}_{il}", index=False
                    )

        # IO sheets（按counter_name）
        if io_windows_dict:
            for counter_name, df in io_windows_dict.items():
                if not df.empty:
                    safe_name = counter_name.replace(".", "_")
                    df.to_excel(
                        writer, sheet_name=f"io_{safe_name}_{il}", index=False
                    )

    print(f"Done: {output_path}")
    print(f"  GPU Load rows: {len(gpu_load_windows)}")
    print(f"  GPU Freq rows: {len(gpu_freq_windows)}")
    print(f"  DDR Bandwidth rows: {len(ddr_bw_windows)}")
    print(f"  DDR Freq rows: {len(ddr_freq_windows)}")
    print(f"  CPU Load rows: {len(cpu_load_windows)}")
    print(f"  CPU Freq rows: {len(cpu_freq_windows)}")
    print(f"  Mem counters: {len(mem_windows_dict)}")
    print(f"  IO counters: {len(io_windows_dict)}")

    print("Note: 图表生成功能待后续实现（TODO）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))