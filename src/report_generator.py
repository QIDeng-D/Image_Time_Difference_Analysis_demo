"""Enhanced report generation with timestamp analysis."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import json
from src.timestamp_analysis import SyncAnalysis, format_timestamp, format_duration


def load_timestamps_for_frame(segments_dir: Path, camera_id: str, global_frame_number: int, 
                               cam_segments: List) -> Tuple[int, float]:
    """Load timestamp for a specific global frame number.
    
    Args:
        segments_dir: Directory containing timestamp files
        camera_id: 'cam0' or 'cam1'
        global_frame_number: Global frame number (1-indexed)
        cam_segments: List of video segments for this camera
        
    Returns:
        Tuple of (local_frame_index, timestamp_us) or (None, None) if not found
    """
    # Convert 1-indexed to 0-indexed
    frame_idx = global_frame_number - 1
    
    # Find which segment this frame belongs to
    cumulative_frames = 0
    for segment in sorted(cam_segments, key=lambda s: s.segment_number):
        if frame_idx < cumulative_frames + segment.frame_count:
            # This frame is in this segment
            local_idx = frame_idx - cumulative_frames
            
            # Load timestamp file
            timestamp_file = segments_dir / f"stereo_{camera_id}_{segment.segment_number:04d}_timestamps.jsonl"
            
            if not timestamp_file.exists():
                return None, None
            
            try:
                with open(timestamp_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        if data['i'] == local_idx:
                            return local_idx, data['pts_us']
            except Exception:
                return None, None
            
            return None, None
        
        cumulative_frames += segment.frame_count
    
    return None, None


def analyze_stitched_frames_timestamps(
    segments_dir: Path,
    cam0_segments: List,
    cam1_segments: List,
    stitched_frame_numbers: List[int],
    sampling_interval: int
) -> Dict:
    """Analyze timestamps for all stitched frames.
    
    Args:
        segments_dir: Directory containing timestamp files
        cam0_segments: List of cam0 video segments
        cam1_segments: List of cam1 video segments
        stitched_frame_numbers: List of global frame numbers that were stitched
        sampling_interval: Sampling interval used
        
    Returns:
        Dictionary with detailed timestamp analysis
    """
    results = {
        'total_stitched': len(stitched_frame_numbers),
        'comparisons': [],
        'statistics': {
            'avg_drift_ms': 0.0,
            'max_drift_ms': 0.0,
            'min_drift_ms': 0.0,
            'std_drift_ms': 0.0,
            'drift_distribution': {
                '<10ms': 0,
                '10-30ms': 0,
                '30-50ms': 0,
                '>50ms': 0
            }
        }
    }
    
    drifts = []
    
    for frame_num in stitched_frame_numbers:
        # Load timestamps for both cameras
        cam0_idx, cam0_ts = load_timestamps_for_frame(segments_dir, 'cam0', frame_num, cam0_segments)
        cam1_idx, cam1_ts = load_timestamps_for_frame(segments_dir, 'cam1', frame_num, cam1_segments)
        
        if cam0_ts is not None and cam1_ts is not None:
            # Calculate drift in milliseconds
            drift_ms = (cam1_ts - cam0_ts) / 1000.0
            drifts.append(drift_ms)
            
            # Store comparison
            results['comparisons'].append({
                'frame_number': frame_num,
                'cam0_timestamp_us': cam0_ts,
                'cam1_timestamp_us': cam1_ts,
                'drift_ms': drift_ms,
                'cam0_time_s': cam0_ts / 1_000_000.0,
                'cam1_time_s': cam1_ts / 1_000_000.0
            })
            
            # Update distribution
            abs_drift = abs(drift_ms)
            if abs_drift < 10:
                results['statistics']['drift_distribution']['<10ms'] += 1
            elif abs_drift < 30:
                results['statistics']['drift_distribution']['10-30ms'] += 1
            elif abs_drift < 50:
                results['statistics']['drift_distribution']['30-50ms'] += 1
            else:
                results['statistics']['drift_distribution']['>50ms'] += 1
    
    # Calculate statistics
    if drifts:
        import statistics
        results['statistics']['avg_drift_ms'] = statistics.mean(drifts)
        results['statistics']['max_drift_ms'] = max(drifts)
        results['statistics']['min_drift_ms'] = min(drifts)
        results['statistics']['std_drift_ms'] = statistics.stdev(drifts) if len(drifts) > 1 else 0.0
    
    return results


def generate_enhanced_report(
    output_path: Path,
    cam0_total_frames: int,
    cam1_total_frames: int,
    cam0_segments: int,
    cam1_segments: int,
    cam0_extracted: int,
    cam1_extracted: int,
    frames_stitched: int,
    frame_difference: int,
    difference_percent: float,
    sampling_interval: int,
    config,
    sync_analysis: SyncAnalysis = None,
    segments_dir: Path = None,
    cam0_segment_list: List = None,
    cam1_segment_list: List = None,
    stitched_frame_numbers: List[int] = None
) -> None:
    """Generate a detailed processing report with timestamp analysis.
    
    Args:
        output_path: Path where the report should be saved
        cam0_total_frames: Total frames in cam0 videos
        cam1_total_frames: Total frames in cam1 videos
        cam0_segments: Number of cam0 video segments
        cam1_segments: Number of cam1 video segments
        cam0_extracted: Number of frames extracted from cam0
        cam1_extracted: Number of frames extracted from cam1
        frames_stitched: Number of frames successfully stitched
        frame_difference: Absolute difference in total frames
        difference_percent: Percentage difference in total frames
        sampling_interval: Sampling interval used
        config: Configuration object
        sync_analysis: Optional SyncAnalysis object with timestamp analysis
        segments_dir: Directory containing timestamp files
        cam0_segment_list: List of cam0 video segments
        cam1_segment_list: List of cam1 video segments
        stitched_frame_numbers: List of frame numbers that were stitched
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate discarded frames
    cam0_discarded = cam0_extracted - frames_stitched
    cam1_discarded = cam1_extracted - frames_stitched
    total_discarded = cam0_discarded + cam1_discarded
    
    report_content = f"""
{'='*80}
视频帧处理报告 (Video Frame Processing Report)
{'='*80}

生成时间 (Generated): {timestamp}

{'='*80}
1. 输入视频信息 (Input Video Information)
{'='*80}

Camera 0 (cam0):
  - 视频段数量 (Segments): {cam0_segments}
  - 总帧数 (Total Frames): {cam0_total_frames:,}"""

    if sync_analysis:
        report_content += f"""
  - 录制时长 (Duration): {format_duration(sync_analysis.cam0_stats.duration_seconds)}
  - 平均帧率 (Avg FPS): {sync_analysis.cam0_stats.avg_framerate:.2f} fps"""
    
    report_content += f"""
  
Camera 1 (cam1):
  - 视频段数量 (Segments): {cam1_segments}
  - 总帧数 (Total Frames): {cam1_total_frames:,}"""

    if sync_analysis:
        report_content += f"""
  - 录制时长 (Duration): {format_duration(sync_analysis.cam1_stats.duration_seconds)}
  - 平均帧率 (Avg FPS): {sync_analysis.cam1_stats.avg_framerate:.2f} fps"""
    
    report_content += f"""

{'='*80}
2. 同步质量分析 (Synchronization Quality Analysis)
{'='*80}

2.1 帧数对比:
  - 绝对差异 (Absolute): {frame_difference:,} 帧
  - 百分比差异 (Percentage): {difference_percent:.2f}%
  - 验证阈值 (Threshold): {config.frame_count_threshold:.2f}%
  - 评级 (Rating): {'✅ 优秀 (Excellent)' if difference_percent <= 1 else '✅ 良好 (Good)' if difference_percent <= config.frame_count_threshold else '⚠️ 超出阈值 (Exceeded)'}
"""

    if sync_analysis:
        report_content += f"""
2.2 时间对比:
  - 录制时长差异 (Duration Diff): {abs(sync_analysis.duration_diff_seconds):.3f}秒
  - 百分比差异 (Percentage): {abs(sync_analysis.duration_diff_seconds)/sync_analysis.cam0_stats.duration_seconds*100:.3f}%
  - 评级 (Rating): {'✅ 优秀 (Excellent)' if abs(sync_analysis.duration_diff_seconds) < 0.1 else '✅ 良好 (Good)' if abs(sync_analysis.duration_diff_seconds) < 1.0 else '⚠️ 一般 (Fair)'}

2.3 启动同步:
  - Cam0首帧时间: {format_timestamp(sync_analysis.cam0_stats.start_time_us)}
  - Cam1首帧时间: {format_timestamp(sync_analysis.cam1_stats.start_time_us)}
  - 启动延迟 (Start Delay): {abs(sync_analysis.start_delay_ms):.3f}ms {'(Cam0晚启动)' if sync_analysis.start_delay_ms > 0 else '(Cam1晚启动)' if sync_analysis.start_delay_ms < 0 else '(完美同步)'}
  - 评级 (Rating): {'✅ 优秀 (Excellent)' if abs(sync_analysis.start_delay_ms) < 10 else '✅ 良好 (Good)' if abs(sync_analysis.start_delay_ms) < 50 else '⚠️ 一般 (Fair)'}

2.4 时间戳对齐分析:
  - 采样点数 (Sample Points): {len(sync_analysis.sample_drifts)}
  - 平均时间偏差 (Avg Drift): {sync_analysis.avg_time_drift_ms:.2f}ms
  - 最大时间偏差 (Max Drift): {sync_analysis.max_time_drift_ms:.2f}ms
  - 标准差 (Std Dev): {sync_analysis.time_drift_std_ms:.2f}ms
  
  偏差分布 (Drift Distribution):
    <10ms:   {sync_analysis.drift_distribution['<10ms']:3d}帧 ({sync_analysis.drift_distribution['<10ms']/len(sync_analysis.sample_drifts)*100:5.1f}%) {'✅' if sync_analysis.drift_distribution['<10ms']/len(sync_analysis.sample_drifts) > 0.5 else '⚠️'}
    10-30ms: {sync_analysis.drift_distribution['10-30ms']:3d}帧 ({sync_analysis.drift_distribution['10-30ms']/len(sync_analysis.sample_drifts)*100:5.1f}%) ⚠️
    30-50ms: {sync_analysis.drift_distribution['30-50ms']:3d}帧 ({sync_analysis.drift_distribution['30-50ms']/len(sync_analysis.sample_drifts)*100:5.1f}%) ⚠️
    >50ms:   {sync_analysis.drift_distribution['>50ms']:3d}帧 ({sync_analysis.drift_distribution['>50ms']/len(sync_analysis.sample_drifts)*100:5.1f}%) {'❌' if sync_analysis.drift_distribution['>50ms'] > 0 else '✅'}
  
  采样点详细对比 (Sample Point Details):
    {'帧索引':>8s}  {'Cam0时间':>10s}  {'Cam1时间':>10s}  {'时间差':>10s}  状态
    {'-'*60}"""
        
        # Show first 10 sample points
        for idx, cam0_time, cam1_time, drift in sync_analysis.sample_drifts[:10]:
            status = '✅' if abs(drift) < 10 else '⚠️' if abs(drift) < 50 else '❌'
            report_content += f"""
    {idx:8d}  {cam0_time:10.3f}s  {cam1_time:10.3f}s  {drift:+9.2f}ms  {status}"""
        
        if len(sync_analysis.sample_drifts) > 10:
            report_content += f"""
    ... (显示前10个采样点，共{len(sync_analysis.sample_drifts)}个)"""
        
        report_content += f"""
  
  评级 (Rating): {sync_analysis.overall_rating}

2.5 帧率稳定性:
  Cam0:
    - 平均帧间隔 (Avg Interval): {sync_analysis.cam0_stats.avg_frame_interval_ms:.2f}ms
    - 标准差 (Std Dev): {sync_analysis.cam0_stats.frame_interval_std_ms:.2f}ms
    - 范围 (Range): {sync_analysis.cam0_stats.min_interval_ms:.2f}ms ~ {sync_analysis.cam0_stats.max_interval_ms:.2f}ms
    - 稳定性 (Stability): {'✅ 优秀' if sync_analysis.cam0_stats.frame_interval_std_ms < 2 else '✅ 良好' if sync_analysis.cam0_stats.frame_interval_std_ms < 5 else '⚠️ 一般'}
  
  Cam1:
    - 平均帧间隔 (Avg Interval): {sync_analysis.cam1_stats.avg_frame_interval_ms:.2f}ms
    - 标准差 (Std Dev): {sync_analysis.cam1_stats.frame_interval_std_ms:.2f}ms
    - 范围 (Range): {sync_analysis.cam1_stats.min_interval_ms:.2f}ms ~ {sync_analysis.cam1_stats.max_interval_ms:.2f}ms
    - 稳定性 (Stability): {'✅ 优秀' if sync_analysis.cam1_stats.frame_interval_std_ms < 2 else '✅ 良好' if sync_analysis.cam1_stats.frame_interval_std_ms < 5 else '⚠️ 一般'}

2.6 综合评估与建议:
  - 帧数同步: {'✅ 优秀' if difference_percent <= 1 else '✅ 良好' if difference_percent <= config.frame_count_threshold else '⚠️ 一般'}
  - 时间同步: {sync_analysis.overall_rating}
  - 帧率稳定: {'✅ 良好' if sync_analysis.cam0_stats.frame_interval_std_ms < 5 and sync_analysis.cam1_stats.frame_interval_std_ms < 5 else '⚠️ 一般'}
  
  建议 (Recommendations):"""
        
        for rec in sync_analysis.recommendations:
            report_content += f"""
    • {rec}"""
    
    report_content += f"""

{'='*80}
3. 帧提取信息 (Frame Extraction Information)
{'='*80}

采样间隔 (Sampling Interval): 每 {sampling_interval} 帧提取一次
提取模式 (Extraction Pattern): 第 1, {1+sampling_interval}, {1+2*sampling_interval}, ... 帧

Camera 0 (cam0):
  - 提取帧数 (Extracted): {cam0_extracted:,}
  - 提取率 (Extraction Rate): {(cam0_extracted/cam0_total_frames*100):.2f}%
  
Camera 1 (cam1):
  - 提取帧数 (Extracted): {cam1_extracted:,}
  - 提取率 (Extraction Rate): {(cam1_extracted/cam1_total_frames*100):.2f}%

{'='*80}
4. 帧拼接信息 (Frame Stitching Information)
{'='*80}

成功拼接 (Successfully Stitched): {frames_stitched:,} 帧
拼接率 (Stitching Rate): {(frames_stitched/min(cam0_extracted, cam1_extracted)*100):.2f}%

抛弃帧统计 (Discarded Frames):
  - Camera 0: {cam0_discarded:,} 帧 (无匹配的cam1帧)
  - Camera 1: {cam1_discarded:,} 帧 (无匹配的cam0帧)
  - 总计 (Total): {total_discarded:,} 帧

{'='*80}
5. 输出信息 (Output Information)
{'='*80}

输出格式 (Output Format): {config.output_format.upper()}
帧号叠加 (Frame Overlay): {'✅ 启用 (Enabled)' if config.enable_frame_overlay else '❌ 禁用 (Disabled)'}
"""

    if config.enable_frame_overlay:
        report_content += f"""  - 字体大小 (Font Size): {config.overlay_font_size}
  - 位置 (Position): {config.overlay_position}
"""

    report_content += f"""
输出目录 (Output Directories):
  - 提取帧 (Extracted): {config.extracted_frames_dir}
    - cam0: {config.extracted_frames_dir}/cam0/
    - cam1: {config.extracted_frames_dir}/cam1/
  - 拼接帧 (Stitched): {config.output_dir}

{'='*80}
6. 处理总结 (Processing Summary)
{'='*80}

✅ 处理成功完成！

关键指标 (Key Metrics):
  - 输入视频总帧数 (Total Input Frames): {cam0_total_frames + cam1_total_frames:,}
  - 提取帧总数 (Total Extracted Frames): {cam0_extracted + cam1_extracted:,}
  - 成功拼接帧数 (Successfully Stitched): {frames_stitched:,}
  - Cam0利用率 (Cam0 Utilization): {(frames_stitched/cam0_extracted*100) if cam0_extracted > 0 else 0:.2f}%
  - Cam1利用率 (Cam1 Utilization): {(frames_stitched/cam1_extracted*100) if cam1_extracted > 0 else 0:.2f}%

时间同步状态 (Time Synchronization):
  - 帧数差异 (Frame Difference): {frame_difference:,} 帧
  - 同步质量 (Sync Quality): {'✅ 优秀 (Excellent)' if difference_percent < 1 else '✅ 良好 (Good)' if difference_percent < 3 else '⚠️ 一般 (Fair)' if difference_percent < 5 else '❌ 较差 (Poor)'}
"""

    # Add stitched frames timestamp analysis if data is available
    if (segments_dir and cam0_segment_list and cam1_segment_list and 
        stitched_frame_numbers and len(stitched_frame_numbers) > 0):
        
        try:
            stitched_analysis = analyze_stitched_frames_timestamps(
                segments_dir,
                cam0_segment_list,
                cam1_segment_list,
                stitched_frame_numbers,
                sampling_interval
            )
            
            if stitched_analysis['comparisons']:
                stats = stitched_analysis['statistics']
                dist = stats['drift_distribution']
                total_compared = len(stitched_analysis['comparisons'])
                
                report_content += f"""

{'='*80}
7. 拼接帧时间戳详细分析 (Stitched Frames Timestamp Analysis)
{'='*80}

7.1 概览 (Overview):
  - 分析帧数 (Frames Analyzed): {total_compared:,} / {frames_stitched:,}
  - 采样间隔 (Sampling Interval): 每 {sampling_interval} 帧
  - 分析覆盖率 (Coverage): {(total_compared/frames_stitched*100):.1f}%

7.2 时间偏差统计 (Drift Statistics):
  - 平均偏差 (Average Drift): {stats['avg_drift_ms']:.3f}ms
  - 最大偏差 (Maximum Drift): {stats['max_drift_ms']:.3f}ms
  - 最小偏差 (Minimum Drift): {stats['min_drift_ms']:.3f}ms
  - 标准差 (Std Deviation): {stats['std_drift_ms']:.3f}ms
  
  偏差分布 (Drift Distribution):
    <10ms:   {dist['<10ms']:4d}帧 ({dist['<10ms']/total_compared*100:5.1f}%) {'✅ 优秀' if dist['<10ms']/total_compared > 0.8 else '✅ 良好' if dist['<10ms']/total_compared > 0.5 else '⚠️ 一般'}
    10-30ms: {dist['10-30ms']:4d}帧 ({dist['10-30ms']/total_compared*100:5.1f}%) {'✅' if dist['10-30ms']/total_compared < 0.3 else '⚠️'}
    30-50ms: {dist['30-50ms']:4d}帧 ({dist['30-50ms']/total_compared*100:5.1f}%) {'✅' if dist['30-50ms']/total_compared < 0.1 else '⚠️'}
    >50ms:   {dist['>50ms']:4d}帧 ({dist['>50ms']/total_compared*100:5.1f}%) {'✅' if dist['>50ms'] == 0 else '❌'}
  
  评级 (Rating): {'✅ 优秀 (Excellent)' if abs(stats['avg_drift_ms']) < 10 and dist['>50ms']/total_compared < 0.05 else '✅ 良好 (Good)' if abs(stats['avg_drift_ms']) < 30 and dist['>50ms']/total_compared < 0.1 else '⚠️ 一般 (Fair)'}

7.3 每帧详细对比 (Frame-by-Frame Comparison):
  
  说明: 以下列出所有拼接帧的时间戳对比
  - 帧号: 全局帧编号（1-indexed）
  - Cam0时间: Camera 0的时间戳（秒）
  - Cam1时间: Camera 1的时间戳（秒）
  - 时间差: Cam1 - Cam0（毫秒，正值表示Cam1晚于Cam0）
  - 状态: ✅优秀(<10ms) ⚠️一般(10-50ms) ❌较差(>50ms)
  
  {'帧号':>8s}  {'Cam0时间':>18s}  {'Cam1时间':>18s}  {'时间差':>10s}  状态
  {'-'*70}"""
                
                # Show all stitched frames
                for comp in stitched_analysis['comparisons']:
                    status = '✅' if abs(comp['drift_ms']) < 10 else '⚠️' if abs(comp['drift_ms']) < 50 else '❌'
                    # Format timestamps relative to first frame
                    cam0_rel = comp['cam0_time_s'] - stitched_analysis['comparisons'][0]['cam0_time_s']
                    cam1_rel = comp['cam1_time_s'] - stitched_analysis['comparisons'][0]['cam1_time_s']
                    report_content += f"""
  {comp['frame_number']:8d}  {cam0_rel:18.6f}s  {cam1_rel:18.6f}s  {comp['drift_ms']:+9.3f}ms  {status}"""
                
                report_content += f"""

7.4 时间偏差趋势分析 (Drift Trend Analysis):
  
  前10帧平均偏差: {sum(c['drift_ms'] for c in stitched_analysis['comparisons'][:10])/min(10, len(stitched_analysis['comparisons'])):.3f}ms
  中间10帧平均偏差: {sum(c['drift_ms'] for c in stitched_analysis['comparisons'][len(stitched_analysis['comparisons'])//2-5:len(stitched_analysis['comparisons'])//2+5])/min(10, len(stitched_analysis['comparisons'])):.3f}ms
  最后10帧平均偏差: {sum(c['drift_ms'] for c in stitched_analysis['comparisons'][-10:])/min(10, len(stitched_analysis['comparisons'])):.3f}ms
  
  偏差变化趋势: {'✅ 稳定' if stats['std_drift_ms'] < 5 else '⚠️ 有波动' if stats['std_drift_ms'] < 10 else '❌ 波动较大'}
  
7.5 建议 (Recommendations):"""
                
                if abs(stats['avg_drift_ms']) < 10 and dist['>50ms'] == 0:
                    report_content += """
  ✅ 时间同步质量优秀，两个相机的时间戳高度一致
  ✅ 当前按帧号匹配的拼接方式完全适用"""
                elif abs(stats['avg_drift_ms']) < 30:
                    report_content += """
  ✅ 时间同步质量良好，两个相机的时间戳基本一致
  ✅ 当前按帧号匹配的拼接方式适用
  💡 如需更高精度，可考虑基于时间戳的匹配算法"""
                else:
                    report_content += """
  ⚠️ 时间同步存在一定偏差，建议检查相机同步设置
  💡 对于高精度应用，建议使用基于时间戳的匹配算法
  💡 考虑在录制时使用硬件同步触发"""
                
        except Exception as e:
            report_content += f"""

{'='*80}
7. 拼接帧时间戳详细分析 (Stitched Frames Timestamp Analysis)
{'='*80}

⚠️ 无法加载时间戳数据: {str(e)}
"""

    report_content += f"""

{'='*80}
报告结束 (End of Report)
{'='*80}
"""

    # Write report to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
