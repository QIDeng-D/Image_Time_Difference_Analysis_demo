"""Timestamp analysis module for video synchronization quality assessment."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class TimestampStats:
    """Statistics for a single camera's timestamps."""
    total_frames: int
    start_time_us: int
    end_time_us: int
    duration_seconds: float
    avg_framerate: float
    avg_frame_interval_ms: float
    frame_interval_std_ms: float
    min_interval_ms: float
    max_interval_ms: float


@dataclass
class SyncAnalysis:
    """Synchronization analysis results between two cameras."""
    cam0_stats: TimestampStats
    cam1_stats: TimestampStats
    start_delay_ms: float
    duration_diff_seconds: float
    avg_time_drift_ms: float
    max_time_drift_ms: float
    time_drift_std_ms: float
    drift_distribution: Dict[str, int]  # <10ms, 10-30ms, 30-50ms, >50ms
    sample_drifts: List[Tuple[int, float, float, float]]  # (frame_idx, cam0_time, cam1_time, drift)
    overall_rating: str
    recommendations: List[str]


class TimestampAnalyzer:
    """Analyzes video timestamp synchronization quality."""
    
    def __init__(self, sync_threshold_ms: float = 50.0, sample_points: int = 20):
        """Initialize the analyzer.
        
        Args:
            sync_threshold_ms: Threshold for acceptable time drift in milliseconds
            sample_points: Number of sample points to analyze for drift
        """
        self.sync_threshold_ms = sync_threshold_ms
        self.sample_points = sample_points
    
    @staticmethod
    def load_timestamps(jsonl_path: Path) -> List[Dict]:
        """Load timestamps from JSONL file.
        
        Args:
            jsonl_path: Path to the timestamps JSONL file
            
        Returns:
            List of timestamp dictionaries with keys: i, pts_us, pts_ms
        """
        timestamps = []
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        timestamps.append(data)
            logger.info(f"Loaded {len(timestamps)} timestamps from {jsonl_path}")
            return timestamps
        except Exception as e:
            logger.error(f"Error loading timestamps from {jsonl_path}: {e}")
            return []
    
    @staticmethod
    def calculate_timestamp_stats(timestamps: List[Dict]) -> TimestampStats:
        """Calculate statistics for a camera's timestamps.
        
        Args:
            timestamps: List of timestamp dictionaries
            
        Returns:
            TimestampStats object with calculated statistics
        """
        if not timestamps or len(timestamps) < 2:
            raise ValueError("Need at least 2 timestamps for analysis")
        
        total_frames = len(timestamps)
        start_time_us = timestamps[0]['pts_us']
        end_time_us = timestamps[-1]['pts_us']
        duration_us = end_time_us - start_time_us
        duration_seconds = duration_us / 1_000_000
        
        # Calculate frame intervals
        intervals_ms = []
        for i in range(1, len(timestamps)):
            interval_us = timestamps[i]['pts_us'] - timestamps[i-1]['pts_us']
            intervals_ms.append(interval_us / 1000)
        
        avg_interval_ms = statistics.mean(intervals_ms)
        interval_std_ms = statistics.stdev(intervals_ms) if len(intervals_ms) > 1 else 0
        min_interval_ms = min(intervals_ms)
        max_interval_ms = max(intervals_ms)
        
        # Calculate average framerate
        avg_framerate = total_frames / duration_seconds if duration_seconds > 0 else 0
        
        return TimestampStats(
            total_frames=total_frames,
            start_time_us=start_time_us,
            end_time_us=end_time_us,
            duration_seconds=duration_seconds,
            avg_framerate=avg_framerate,
            avg_frame_interval_ms=avg_interval_ms,
            frame_interval_std_ms=interval_std_ms,
            min_interval_ms=min_interval_ms,
            max_interval_ms=max_interval_ms
        )
    
    def analyze_time_drift(
        self, 
        cam0_timestamps: List[Dict], 
        cam1_timestamps: List[Dict]
    ) -> Tuple[float, float, float, Dict[str, int], List[Tuple[int, float, float, float]]]:
        """Analyze time drift between two cameras.
        
        Args:
            cam0_timestamps: Timestamps from camera 0
            cam1_timestamps: Timestamps from camera 1
            
        Returns:
            Tuple of (avg_drift_ms, max_drift_ms, std_drift_ms, distribution, sample_drifts)
        """
        min_frames = min(len(cam0_timestamps), len(cam1_timestamps))
        
        # Sample evenly distributed points
        if min_frames <= self.sample_points:
            sample_indices = list(range(min_frames))
        else:
            step = min_frames // self.sample_points
            sample_indices = [i * step for i in range(self.sample_points)]
        
        drifts = []
        sample_drifts = []
        
        for idx in sample_indices:
            cam0_time_us = cam0_timestamps[idx]['pts_us']
            cam1_time_us = cam1_timestamps[idx]['pts_us']
            drift_us = cam0_time_us - cam1_time_us
            drift_ms = drift_us / 1000
            drifts.append(abs(drift_ms))
            
            # Store sample for detailed report
            cam0_time_s = (cam0_time_us - cam0_timestamps[0]['pts_us']) / 1_000_000
            cam1_time_s = (cam1_time_us - cam1_timestamps[0]['pts_us']) / 1_000_000
            sample_drifts.append((idx, cam0_time_s, cam1_time_s, drift_ms))
        
        avg_drift_ms = statistics.mean(drifts)
        max_drift_ms = max(drifts)
        std_drift_ms = statistics.stdev(drifts) if len(drifts) > 1 else 0
        
        # Calculate distribution
        distribution = {
            '<10ms': sum(1 for d in drifts if d < 10),
            '10-30ms': sum(1 for d in drifts if 10 <= d < 30),
            '30-50ms': sum(1 for d in drifts if 30 <= d < 50),
            '>50ms': sum(1 for d in drifts if d >= 50)
        }
        
        return avg_drift_ms, max_drift_ms, std_drift_ms, distribution, sample_drifts
    
    def analyze_sync_quality(
        self, 
        cam0_timestamps: List[Dict], 
        cam1_timestamps: List[Dict]
    ) -> SyncAnalysis:
        """Analyze synchronization quality between two cameras.
        
        Args:
            cam0_timestamps: Timestamps from camera 0
            cam1_timestamps: Timestamps from camera 1
            
        Returns:
            SyncAnalysis object with comprehensive analysis results
        """
        # Calculate individual camera statistics
        cam0_stats = self.calculate_timestamp_stats(cam0_timestamps)
        cam1_stats = self.calculate_timestamp_stats(cam1_timestamps)
        
        # Calculate start delay
        start_delay_us = cam0_stats.start_time_us - cam1_stats.start_time_us
        start_delay_ms = start_delay_us / 1000
        
        # Calculate duration difference
        duration_diff_seconds = cam0_stats.duration_seconds - cam1_stats.duration_seconds
        
        # Analyze time drift
        avg_drift, max_drift, std_drift, distribution, sample_drifts = self.analyze_time_drift(
            cam0_timestamps, cam1_timestamps
        )
        
        # Determine overall rating
        rating, recommendations = self._calculate_rating(
            start_delay_ms, avg_drift, max_drift, distribution, len(sample_drifts)
        )
        
        return SyncAnalysis(
            cam0_stats=cam0_stats,
            cam1_stats=cam1_stats,
            start_delay_ms=start_delay_ms,
            duration_diff_seconds=duration_diff_seconds,
            avg_time_drift_ms=avg_drift,
            max_time_drift_ms=max_drift,
            time_drift_std_ms=std_drift,
            drift_distribution=distribution,
            sample_drifts=sample_drifts,
            overall_rating=rating,
            recommendations=recommendations
        )
    
    def _calculate_rating(
        self, 
        start_delay_ms: float, 
        avg_drift_ms: float, 
        max_drift_ms: float,
        distribution: Dict[str, int],
        total_samples: int
    ) -> Tuple[str, List[str]]:
        """Calculate overall synchronization rating and recommendations.
        
        Returns:
            Tuple of (rating, recommendations)
        """
        recommendations = []
        
        # Check start delay
        start_quality = "优秀" if abs(start_delay_ms) < 10 else "良好" if abs(start_delay_ms) < 50 else "一般"
        
        # Check average drift
        if avg_drift_ms < 10:
            drift_quality = "优秀"
        elif avg_drift_ms < 30:
            drift_quality = "良好"
            recommendations.append("平均时间偏差在10-30ms范围，建议使用时间戳匹配以获得更精确的同步")
        elif avg_drift_ms < 50:
            drift_quality = "一般"
            recommendations.append("平均时间偏差较大(30-50ms)，强烈建议使用时间戳匹配")
        else:
            drift_quality = "较差"
            recommendations.append("平均时间偏差过大(>50ms)，必须使用时间戳匹配")
        
        # Check max drift
        if max_drift_ms > 100:
            recommendations.append(f"检测到最大偏差{max_drift_ms:.1f}ms，可能存在帧丢失或时间戳跳变")
        
        # Check distribution
        good_ratio = distribution['<10ms'] / total_samples if total_samples > 0 else 0
        if good_ratio < 0.5:
            recommendations.append(f"仅{good_ratio*100:.1f}%的帧偏差<10ms，同步质量需要改善")
        
        # Overall rating
        if drift_quality == "优秀" and start_quality == "优秀":
            overall = "✅ 优秀"
        elif drift_quality in ["优秀", "良好"] and start_quality in ["优秀", "良好"]:
            overall = "✅ 良好"
        elif drift_quality == "一般":
            overall = "⚠️ 一般"
        else:
            overall = "❌ 较差"
        
        if not recommendations:
            recommendations.append("当前同步质量良好，按帧号匹配即可满足需求")
        
        return overall, recommendations
    
    def analyze_all_segments(
        self,
        input_dir: Path,
        cam0_segments: List,
        cam1_segments: List
    ) -> SyncAnalysis:
        """Analyze all video segments and combine timestamps using parallel processing.
        
        Args:
            input_dir: Directory containing timestamp files
            cam0_segments: List of cam0 video segments
            cam1_segments: List of cam1 video segments
            
        Returns:
            SyncAnalysis for combined timestamps
        """
        def load_segment_timestamps(segment, camera_id):
            """Load timestamps for a single segment."""
            video_name = segment.file_path.stem
            ts_name = video_name.replace('_sbs', '') + '_timestamps.jsonl'
            ts_path = input_dir / ts_name
            
            if ts_path.exists():
                timestamps = self.load_timestamps(ts_path)
                return (camera_id, segment.segment_number, timestamps)
            else:
                logger.warning(f"Timestamp file not found: {ts_path}")
                return (camera_id, segment.segment_number, [])
        
        # Parallel load all timestamp files
        all_cam0_timestamps = []
        all_cam1_timestamps = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all loading tasks
            futures = []
            
            for segment in cam0_segments:
                future = executor.submit(load_segment_timestamps, segment, 'cam0')
                futures.append(future)
            
            for segment in cam1_segments:
                future = executor.submit(load_segment_timestamps, segment, 'cam1')
                futures.append(future)
            
            # Collect results
            cam0_results = {}
            cam1_results = {}
            
            for future in as_completed(futures):
                camera_id, segment_num, timestamps = future.result()
                if camera_id == 'cam0':
                    cam0_results[segment_num] = timestamps
                else:
                    cam1_results[segment_num] = timestamps
        
        # Sort by segment number and combine
        for seg_num in sorted(cam0_results.keys()):
            all_cam0_timestamps.extend(cam0_results[seg_num])
        
        for seg_num in sorted(cam1_results.keys()):
            all_cam1_timestamps.extend(cam1_results[seg_num])
        
        if not all_cam0_timestamps or not all_cam1_timestamps:
            raise ValueError("No timestamps loaded for analysis")
        
        logger.info(f"Analyzing {len(all_cam0_timestamps)} cam0 and {len(all_cam1_timestamps)} cam1 timestamps")
        
        return self.analyze_sync_quality(all_cam0_timestamps, all_cam1_timestamps)


def format_timestamp(timestamp_us: int) -> str:
    """Format microsecond timestamp to readable string.
    
    Args:
        timestamp_us: Timestamp in microseconds since epoch
        
    Returns:
        Formatted string like "2024-01-07 10:30:18.836"
    """
    timestamp_s = timestamp_us / 1_000_000
    dt = datetime.fromtimestamp(timestamp_s)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Trim to milliseconds


def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "5分23.320秒" or "1时15分30.500秒"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}时{minutes}分{secs:.3f}秒"
    elif minutes > 0:
        return f"{minutes}分{secs:.3f}秒"
    else:
        return f"{secs:.3f}秒"
