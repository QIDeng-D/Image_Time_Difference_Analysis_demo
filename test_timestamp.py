"""Quick test for timestamp analysis."""

from pathlib import Path
from src.timestamp_analysis import TimestampAnalyzer
from src.video_discovery import VideoDiscovery

# Discover videos
input_dir = Path("segments")
discovery = VideoDiscovery()
videos = discovery.discover_videos(
    input_dir,
    "stereo_cam0_sbs_*.mp4",
    "stereo_cam1_sbs_*.mp4"
)

cam0_segments = videos.get('cam0', [])
cam1_segments = videos.get('cam1', [])

print(f"Found {len(cam0_segments)} cam0 segments and {len(cam1_segments)} cam1 segments")

# Analyze timestamps
analyzer = TimestampAnalyzer(sync_threshold_ms=50.0, sample_points=20)
print("Starting timestamp analysis...")

try:
    sync_analysis = analyzer.analyze_all_segments(input_dir, cam0_segments, cam1_segments)
    
    print("\n" + "="*80)
    print("Timestamp Analysis Results")
    print("="*80)
    print(f"Cam0 total frames: {sync_analysis.cam0_stats.total_frames}")
    print(f"Cam1 total frames: {sync_analysis.cam1_stats.total_frames}")
    print(f"Cam0 duration: {sync_analysis.cam0_stats.duration_seconds:.2f}s")
    print(f"Cam1 duration: {sync_analysis.cam1_stats.duration_seconds:.2f}s")
    print(f"Start delay: {sync_analysis.start_delay_ms:.3f}ms")
    print(f"Avg time drift: {sync_analysis.avg_time_drift_ms:.2f}ms")
    print(f"Max time drift: {sync_analysis.max_time_drift_ms:.2f}ms")
    print(f"Overall rating: {sync_analysis.overall_rating}")
    print("\nRecommendations:")
    for rec in sync_analysis.recommendations:
        print(f"  • {rec}")
    print("="*80)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
