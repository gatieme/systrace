# Perfetto Trace 解析脚本设计文档

## 1. 需求概述

实现 `parse_perfetto_stats.py` 脚本，解析 Perfetto trace 文件，按指定时间区间和间隔统计 CPU/GPU/DDR/Mem/IO 性能数据，输出到 xlsx 文件。

**参考实现**：`../../smartperf/script/parse_hitrace_stats.py`

---

## 2. 需求澄清结果

### 2.1 输入文件格式

✅ **已确认**：Perfetto 原生 `.pftrace` 格式

**技术方案**：使用 Perfetto TraceProcessor Python API

```python
from perfetto.trace_processor import TraceProcessor

with TraceProcessor(trace='trace.perfetto-trace') as tp:
    result = tp.query('SELECT ... FROM counter ...')
    df = result.as_pandas_dataframe()
```

**依赖**：
```bash
pip install perfetto pandas numpy openpyxl
```

### 2.2 数据类型范围

✅ **已确认**：全部 5 类数据统计

| 类型 | 查询对象 | 输出 Sheet |
|------|---------|-----------|
| GPU | Load + Frequency | `gpu_load`, `gpu_freq`, `chart_gpu` |
| DDR | Bandwidth + Frequency | `ddr_bandwidth`, `ddr_freq`, `chart_ddr` |
| CPU | Load + Frequency | `cpu_load`, `cpu_freq`, `chart_cpu` |
| Mem | MemTotal/MemFree/MemAvailable/Active | `mem`, `chart_mem` |
| IO | diskstat (sda/sdb/sdc...) | `io`, `chart_io` |

### 2.3 已确认的设计细节

#### 时间戳单位

✅ **已确认**：纳秒（ns）

- Perfetto trace 内部 `ts` 字段单位为纳秒
- 用户输入参数 `--start_ns/--end_ns` 单位为纳秒
- 与参考脚本完全一致

#### 图表需求

✅ **已确认**：与参考脚本一致

- 散点折线图（ScatterChart）
- 数据标签（DataLabelList）显示数值
- 每类数据独立 Sheet + 图表 Sheet
- 使用 `openpyxl.chart` 库生成图表

#### 多文件支持

✅ **已确认**：仅支持单文件

- 简化实现逻辑
- 输入为单个 `.pftrace` 文件路径
- 不支持目录输入和多文件合并

#### 默认时间区间

✅ **已确认**：默认全范围

- 用户不指定 `--start_ns/--end_ns` 时，默认分析整个 trace 时间范围
- 通过查询获取 trace 起止时间戳：
  ```sql
  SELECT MIN(ts) AS start_ts, MAX(ts) AS end_ts FROM counter;
  ```
- 或查询 trace metadata bounds

---

## 3. 技术方案

### 3.1 API 方案（已确定）

✅ **方案 A：Perfetto TraceProcessor Python API**

适用于 `.pftrace` 输入文件。

```python
from perfetto.trace_processor import TraceProcessor

def query_perfetto(trace_path: str, sql: str) -> pd.DataFrame:
    """使用 Perfetto API 查询 trace"""
    with TraceProcessor(trace=trace_path) as tp:
        result = tp.query(sql)
        return result.as_pandas_dataframe()
```

**优点**：
- 官方 API，表结构标准化
- 无需手动导出 .db 文件
- SQL 查询与 README 完全一致
- 内置时间戳处理机制

**依赖**：
```bash
pip install perfetto pandas numpy openpyxl
```

---

### 3.2 核心模块设计

#### 模块划分

| 模块 | 功能 | 对应参考脚本 |
|------|------|--------------|
| `parse_perfetto_stats.py` | 主脚本入口 | `main()` |
| 查询模块 | 执行 SQL 查询 | `load_running_intervals()`, `load_gpu_measure_samples()` |
| 计算模块 | 滑动窗口统计 | `compute_cpu_usage()`, `compute_gpu_measure()` |
| 输出模块 | xlsx + 图表导出 | `export_xlsx()` |

#### 关键函数设计

1. **时间区间查询**
   - 获取 trace 起止时间戳（类似参考脚本的 `trace_range` 表）
   - Perfetto 可通过 `SELECT MIN(ts), MAX(ts) FROM counter` 估算范围
   - 或查询 `trace_bounds` / `trace_duration` 等内置表

2. **滑动窗口计算**
   - 复用参考脚本的 `cpu_usage_for_window()` 和 `measure_time_weighted_avg()` 逻辑
   - 使用 `bisect` 加速区间查找

3. **数据查询适配**
   - GPU Load/Freq：README SQL 查询直接可用
   - DDR Bandwidth/Freq：README SQL 查询直接可用
   - CPU Load/Freq：需适配 `cpu_counter_track` 表
   - Mem/IO：README SQL 查询直接可用

---

### 3.3 命令行参数设计

```bash
python3 ./parse_perfetto_stats.py \
    --trace_file trace.perfetto-trace \
    --interval 10 \
    --start_ns 5527910967813126 \
    --end_ns 5527920967813126 \
    --output output.xlsx
```

**参数说明**：
- `--trace_file`：输入文件路径（`.pftrace` 或 `.db`，待澄清）
- `--interval`：统计窗口间隔（ms）
- `--start_ns`：起始时间戳（可选）
- `--end_ns`：结束时间戳（可选）
- `--output`：输出 xlsx 文件路径（可选）

---

### 3.4 输出格式设计

#### xlsx Sheet 结构（参考 hitrace 脚本）

| Sheet 名称 | 内容 |
|-----------|------|
| `summary` | 源文件信息、时间范围、统计概览 |
| `gpu_load` | GPU Load 滑动窗口统计 |
| `gpu_freq` | GPU Frequency 滑动窗口统计 |
| `ddr_bandwidth` | DDR Bandwidth 滑动窗口统计 |
| `ddr_freq` | DDR Frequency 滑动窗口统计 |
| `cpu_load` | CPU Load 滑动窗口统计（按 CPU ID） |
| `cpu_freq` | CPU Frequency 滑动窗口统计（按 CPU ID） |
| `mem` | Memory 统计 |
| `io` | I/O 统计 |
| `chart_gpu` | GPU Load/Freq 图表 |
| `chart_cpu` | CPU Load/Freq 图表 |
| `chart_merged` | CPU+GPU 合并图表 |

---

## 4. 实现步骤

### Phase 1：基础框架搭建
1. 命令行参数解析
2. API 选择与验证（根据输入文件格式）
3. 时间范围查询

### Phase 2：数据查询实现
1. GPU Load/Freq 查询
2. DDR Bandwidth/Freq 查询
3. CPU Load/Freq 查询
4. Mem/IO 查询

### Phase 3：滑动窗口计算
1. 时间加权平均算法
2. bisect 加速实现
3. 多类数据并行计算

### Phase 4：输出与图表
1. xlsx 导出（openpyxl）
2. 散点折线图生成
3. 多 sheet 合并输出

---

## 5. 依赖清单

```bash
# 方案 A（Perfetto API）
pip install perfetto pandas numpy openpyxl

# 方案 B（sqlite3）
pip install pandas numpy openpyxl  # perfetto 不必需
```

---

## 6. 测试计划

1. **输入文件格式验证**
   - 测试 `.pftrace` 文件加载
   - 测试 `.db` 文件加载（如可用）

2. **SQL 查询验证**
   - 分别测试 GPU/DDR/CPU/Mem/IO 查询
   - 验证时间区间过滤正确性

3. **滑动窗口计算验证**
   - 对比手动计算结果
   - 验证时间加权平均算法

4. **输出验证**
   - xlsx 文件格式正确性
   - 图表渲染正确性

---

## 7. 风险与注意事项

### 7.1 Perfetto 版本兼容性
- 不同 Perfetto 版本的表结构可能有差异
- 需验证 `counter`, `counter_track`, `cpu_counter_track` 表名是否存在

### 7.2 时间戳精度
- Perfetto 内部时间戳精度可能因平台不同
- 需验证纳秒单位假设

### 7.3 大文件性能
- 大 trace 文件可能导致内存占用高
- 考虑分批查询或流式处理

---

---

### 3.3 SQL 查询设计

根据 README 提供的 SQL 查询模板，设计各类型数据的查询接口。

#### GPU 查询

```python
def query_gpu_load(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 GPU Load"""
    sql = f"""
        SELECT
            ts, value AS gpu_load, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%gpu%load%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return tp.query(sql).as_pandas_dataframe()

def query_gpu_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 GPU Frequency"""
    sql = f"""
        SELECT
            ts, value AS gpu_freq, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%gpu_freq%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return tp.query(sql).as_pandas_dataframe()
```

#### DDR 查询

```python
def query_ddr_bandwidth(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 DDR Bandwidth"""
    sql = f"""
        SELECT
            ts, value AS ddr_bandwidth, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%ddr%width%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return tp.query(sql).as_pandas_dataframe()

def query_ddr_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 DDR Frequency"""
    sql = f"""
        SELECT
            ts, value AS ddr_freq, track.name AS track_name
        FROM counter
        JOIN counter_track AS track ON counter.track_id = track.id
        WHERE (track.name LIKE '%ddr%freq%')
        AND (ts BETWEEN {start_ns} AND {end_ns})
        ORDER BY ts
    """
    return tp.query(sql).as_pandas_dataframe()
```

#### CPU 查询

```python
def query_cpu_load(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 CPU Load"""
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
    return tp.query(sql).as_pandas_dataframe()

def query_cpu_freq(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 CPU Frequency"""
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
    return tp.query(sql).as_pandas_dataframe()
```

#### Mem 查询

```python
def query_mem(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 Memory 统计"""
    sql = f"""
        SELECT
            ct.name AS counter_name, c.value, c.ts AS timestamp
        FROM counter c
        JOIN counter_track ct ON c.track_id = ct.id
        WHERE ct.name IN ('MemTotal', 'MemFree', 'MemAvailable', 'Active')
        AND c.ts BETWEEN {start_ns} AND {end_ns}
        ORDER BY c.ts
    """
    return tp.query(sql).as_pandas_dataframe()
```

#### IO 查询

```python
def query_io(tp: TraceProcessor, start_ns: int, end_ns: int) -> pd.DataFrame:
    """查询 I/O 统计"""
    sql = f"""
        SELECT
            ct.name AS counter_name, c.value, c.ts AS timestamp
        FROM counter c
        JOIN counter_track ct ON c.track_id = ct.id
        WHERE ct.name LIKE 'diskstat.[sdf].%'
        AND c.ts BETWEEN {start_ns} AND {end_ns}
        ORDER BY c.ts
    """
    return tp.query(sql).as_pandas_dataframe()
```

---

### 3.4 滑动窗口计算设计

复用参考脚本的时间加权平均算法。

#### 核心算法：时间加权平均

```python
import bisect

def measure_time_weighted_avg(
    samples: list[dict],
    win_start_ns: int,
    win_end_ns: int,
    idx_start: int = 0,
    idx_end: int | None = None,
) -> float:
    """Time-weighted average of piecewise-constant samples in a window."""
    window_ns = win_end_ns - win_start_ns
    if window_ns <= 0:
        return 0.0

    end_idx = idx_end if idx_end is not None else len(samples)
    weighted_sum = 0.0
    for i in range(idx_start, end_idx):
        sample = samples[i]
        start = sample["ts"]
        # Perfetto counter 数据是瞬时值，无 dur 字段
        # 采用 step function 模型：前一个值持续到下一个采样点
        end = samples[i + 1]["ts"] if i + 1 < end_idx else win_end_ns
        if end <= win_start_ns or start >= win_end_ns:
            continue
        clip_start = max(start, win_start_ns)
        clip_end = min(end, win_end_ns)
        if clip_end > clip_start:
            weighted_sum += sample["value"] * (clip_end - clip_start)
    return weighted_sum / window_ns
```

#### 滑动窗口遍历

```python
def compute_metric_windows(
    samples: pd.DataFrame,
    interval_sec: float,
    range_start_ns: int | None = None,
    range_end_ns: int | None = None,
) -> pd.DataFrame:
    """按滑动窗口计算时间加权平均值"""
    if samples.empty:
        return pd.DataFrame()

    timeline_start = int(samples["ts"].min())
    timeline_end = int(samples["ts"].max())

    win_start_bound = range_start_ns if range_start_ns is not None else timeline_start
    win_end_bound = range_end_ns if range_end_ns is not None else timeline_end

    win_start_bound = max(win_start_bound, timeline_start)
    win_end_bound = min(win_end_bound, timeline_end)

    if win_start_bound >= win_end_bound:
        return pd.DataFrame()

    window_ns = int(interval_sec * 1_000_000_000)
    
    # 转换为字典列表以便 bisect 加速
    sample_list = samples.to_dict('records')
    ts_sorted = [s["ts"] for s in sample_list]

    rows = []
    win_start = win_start_bound
    left_idx = 0
    while win_start < win_end_bound:
        win_end = min(win_start + window_ns, win_end_bound)
        # 推进左边界
        while left_idx < len(sample_list) and sample_list[left_idx]["ts"] < win_start:
            left_idx += 1
        # 找右边界
        right_idx = bisect.bisect_left(ts_sorted, win_end)
        
        avg = measure_time_weighted_avg(
            sample_list, win_start, win_end,
            idx_start=left_idx, idx_end=right_idx,
        )
        
        row = {
            "window_start_ns": win_start,
            "window_end_ns": win_end,
            "elapsed_sec": round(len(rows) * interval_sec, 4),
            "value_avg": round(avg, 2),
        }
        rows.append(row)
        win_start = win_end

    return pd.DataFrame(rows)
```

---

### 3.5 输出格式设计

#### xlsx Sheet 结构

| Sheet 名称 | 内容 | 图表 Sheet |
|-----------|------|-----------|
| `summary` | trace 元信息、时间范围、统计概览 | - |
| `gpu_load` | GPU Load 滑动窗口统计 | `chart_gpu_load` |
| `gpu_freq` | GPU Frequency 滑动窗口统计 | `chart_gpu_freq` |
| `ddr_bandwidth` | DDR Bandwidth 滑动窗口统计 | `chart_ddr_bandwidth` |
| `ddr_freq` | DDR Frequency 滑动窗口统计 | `chart_ddr_freq` |
| `cpu_load` | CPU Load 滑动窗口统计（按 CPU ID） | `chart_cpu_load` |
| `cpu_freq` | CPU Frequency 滑动窗口统计（按 CPU ID） | `chart_cpu_freq` |
| `mem` | Memory 统计（按 counter_name） | `chart_mem` |
| `io` | I/O 统计（按 counter_name） | `chart_io` |

#### 图表配置

- **类型**：散点折线图（ScatterChart）
- **样式**：`chart.scatterStyle = 'line'`
- **尺寸**：`chart.height = 14`, `chart.width = 28`
- **数据标签**：显示数值，格式 `"0.0"`
- **颜色**：复用参考脚本的 LINE_COLORS 调色板

---

### 3.6 命令行参数设计（最终版本）

```bash
python3 ./parse_perfetto_stats.py \
    --trace_file trace.perfetto-trace \
    --interval 10 \
    --start_ns 5527910967813126 \
    --end_ns 5527920967813126 \
    --output output.xlsx
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--trace_file` | `Path` | 必需 | 输入 `.pftrace` 文件路径 |
| `--interval` | `float` | `10.0` | 统计窗口间隔，单位 ms |
| `--start_ns` | `int` | `None` | 起始时间戳（纳秒），默认 trace 起始 |
| `--end_ns` | `int` | `None` | 结束时间戳（纳秒），默认 trace 结束 |
| `--output` | `Path` | `None` | 输出 xlsx 文件路径，默认与 trace 同目录 |

---

## 待确认事项（已全部确认）

✅ 所有设计细节已确认，可直接进入实现阶段。