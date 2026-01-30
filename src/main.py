"""Main application entry point for Video Frame Stitcher with streaming pipeline."""

import sys
import logging
import argparse
import signal
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime
from queue import Queue
from tqdm import tqdm

from src.config import ConfigManager
from src.video_discovery import VideoDiscovery
from src.frame_extraction import FrameExtractor
from src.frame_stitching import FrameStitcher
from src.progress_reporter import ProgressReporter
from src.timestamp_analysis import TimestampAnalyzer, SyncAnalysis
from src.report_generator import generate_enhanced_report
from src.multiprocess_extraction import MultiprocessExtractor
from src.directory_management import (
    setup_extraction_directories,
    setup_stitching_directory
)
from src.error_handling import (
    InputDirectoryError,
    VideoFileError,
    FrameExtractionError,
    OutputDirectoryError,
    StitchingError,
    validate_input_directory,
    validate_output_directory
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    global _shutdown_requested
    if not _shutdown_requested:
        _shutdown_requested = True
        logger.info("\n⚠️ 收到中断信号，正在清理资源... (Interrupt received, cleaning up...)")
        logger.info("请稍候... (Please wait...)")
    else:
        logger.warning("\n强制退出 (Force exit)")
        sys.exit(1)


def streaming_extraction_worker(
    camera_id: str,
    segments: list,
    output_dir: Path,
    extractor: FrameExtractor,
    extracted_frames_dict: Dict[str, dict],
    stitch_queue: Queue,
    lock: threading.Lock,
    pbar: tqdm
):
    """Worker function for extracting frames with streaming to stitcher.
    
    Args:
        camera_id: Camera identifier ('cam0' or 'cam1')
        segments: List of video segments to process
        output_dir: Output directory for extracted frames
        extractor: FrameExtractor instance
        extracted_frames_dict: Shared dict to store extracted frame metadata
        stitch_queue: Queue to send frame pairs to stitcher
        lock: Thread lock for synchronization
        pbar: Progress bar for this camera
    """
    try:
        frames = []
        
        for segment in segments:
            try:
                cap = extractor._open_video(segment.file_path)
                if cap is None:
                    continue
                
                global_frame_number = sum(s.frame_count for s in segments[:segments.index(segment)])
                local_frame_number = 0
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    local_frame_number += 1
                    global_frame_number += 1
                    
                    if extractor.should_extract_frame(global_frame_number):
                        try:
                            file_path = extractor.save_frame(
                                frame, global_frame_number, output_dir, camera_id
                            )
                            
                            frame_metadata = {
                                'global_frame_number': global_frame_number,
                                'camera_id': camera_id,
                                'file_path': file_path
                            }
                            frames.append(frame_metadata)
                            
                            # Store in shared dict
                            with lock:
                                extracted_frames_dict[camera_id][global_frame_number] = frame_metadata
                                
                                # Check if matching frame exists from other camera
                                other_camera = 'cam1' if camera_id == 'cam0' else 'cam0'
                                if global_frame_number in extracted_frames_dict[other_camera]:
                                    # Found a matching pair, queue for stitching
                                    pair = {
                                        'cam0': extracted_frames_dict['cam0'][global_frame_number],
                                        'cam1': extracted_frames_dict['cam1'][global_frame_number],
                                        'frame_number': global_frame_number
                                    }
                                    stitch_queue.put(pair)
                            
                            pbar.update(1)
                            
                        except Exception as e:
                            logger.error(f"Error saving frame {global_frame_number} from {camera_id}: {e}")
                            continue
                
                cap.release()
                
            except Exception as e:
                logger.error(f"Error processing segment {segment.file_path}: {e}")
                continue
        
        return frames
        
    except Exception as e:
        logger.error(f"Error in extraction worker for {camera_id}: {e}")
        return []


def streaming_stitcher_worker(
    stitch_queue: Queue,
    stitching_dir: Path,
    stitcher: FrameStitcher,
    pbar: tqdm,
    stop_event: threading.Event
):
    """Worker function for stitching frames from queue.
    
    Args:
        stitch_queue: Queue containing frame pairs to stitch
        stitching_dir: Output directory for stitched frames
        stitcher: FrameStitcher instance
        pbar: Progress bar for stitching
        stop_event: Event to signal when to stop
    """
    stitched_count = 0
    
    try:
        while not stop_event.is_set() or not stitch_queue.empty():
            try:
                # Get frame pair from queue with timeout
                pair = stitch_queue.get(timeout=0.5)
                
                try:
                    # Stitch the frame pair
                    output_path = stitcher.stitch_single_pair(
                        pair['cam0']['file_path'],
                        pair['cam1']['file_path'],
                        pair['frame_number'],
                        stitching_dir
                    )
                    
                    stitched_count += 1
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error stitching frame {pair['frame_number']}: {e}")
                
                stitch_queue.task_done()
                
            except:
                # Timeout or empty queue
                continue
    
    except Exception as e:
        logger.error(f"Error in stitcher worker: {e}")
    
    return stitched_count


def main(config_path: Optional[Path] = None) -> int:
    """Main application function with streaming pipeline.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Exit code: 0 for success, non-zero for failure
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    progress = ProgressReporter()
    
    try:
        # Load configuration
        if config_path is None:
            config_path = Path('config.yaml')
        
        logger.info("Loading configuration...")
        config_manager = ConfigManager()
        config = config_manager.load_config(config_path)
        
        logger.info(f"Configuration loaded:")
        logger.info(f"  Input directory: {config.input_dir}")
        logger.info(f"  Sampling interval: {config.sampling_interval}")
        
        # Validate input directory
        validate_input_directory(config.input_dir)
        
        # Discover video files
        logger.info("Discovering video files...")
        discovery = VideoDiscovery()
        videos = discovery.discover_videos(
            config.input_dir,
            config.cam0_pattern,
            config.cam1_pattern
        )
        
        cam0_segments = videos.get('cam0', [])
        cam1_segments = videos.get('cam1', [])
        
        if not cam0_segments or not cam1_segments:
            logger.error("Need video segments from both cameras")
            return 1
        
        logger.info(f"Found {len(cam0_segments)} cam0 segments and {len(cam1_segments)} cam1 segments")
        
        # Validate frame count difference
        frame_counts = discovery.calculate_total_frame_counts(videos)
        cam0_total = frame_counts.get('cam0', 0)
        cam1_total = frame_counts.get('cam1', 0)
        
        exceeds_threshold, diff_percent, abs_diff = discovery.validate_frame_count_difference(
            cam0_total, cam1_total, config.frame_count_threshold
        )
        
        if exceeds_threshold:
            progress.report_frame_count_validation(
                cam0_total, cam1_total, diff_percent, abs_diff, config.frame_count_threshold
            )
            
            if not progress.prompt_user_continue():
                logger.info("User chose not to continue. Exiting.")
                return 0
        
        logger.info(f"Frame count validation: cam0={cam0_total}, cam1={cam1_total}, diff={diff_percent:.2f}%")
        
        # Analyze timestamp synchronization
        sync_analysis = None
        if config.timestamp_analysis_enabled:
            try:
                logger.info("Analyzing timestamp synchronization...")
                analyzer = TimestampAnalyzer(
                    sync_threshold_ms=config.timestamp_sync_threshold_ms,
                    sample_points=config.timestamp_sample_points
                )
                sync_analysis = analyzer.analyze_all_segments(
                    config.input_dir,
                    cam0_segments,
                    cam1_segments
                )
                logger.info(f"Timestamp analysis complete: avg_drift={sync_analysis.avg_time_drift_ms:.2f}ms, "
                           f"max_drift={sync_analysis.max_time_drift_ms:.2f}ms")
                logger.info(f"Sync quality rating: {sync_analysis.overall_rating}")
            except Exception as e:
                logger.warning(f"Timestamp analysis failed: {e}")
                sync_analysis = None
        
        # Setup output directories
        extraction_dirs = setup_extraction_directories(config.extracted_frames_dir)
        stitching_dir = setup_stitching_directory(config.output_dir)
        
        # Initialize components
        extractor = FrameExtractor(
            sampling_interval=config.sampling_interval,
            output_format=config.output_format,
            enable_overlay=config.enable_frame_overlay,
            overlay_font_size=config.overlay_font_size,
            overlay_position=config.overlay_position
        )
        
        stitcher = FrameStitcher(
            output_format=config.output_format,
            enable_overlay=config.enable_frame_overlay,
            overlay_font_size=config.overlay_font_size,
            overlay_position=config.overlay_position
        )
        
        # Calculate expected frame counts
        expected_cam0 = sum(1 for i in range(1, cam0_total + 1) if extractor.should_extract_frame(i))
        expected_cam1 = sum(1 for i in range(1, cam1_total + 1) if extractor.should_extract_frame(i))
        expected_stitched = min(expected_cam0, expected_cam1)
        
        logger.info(f"Expected to extract: cam0={expected_cam0}, cam1={expected_cam1}")
        logger.info(f"Expected to stitch: {expected_stitched} frames")
        
        # Use multiprocess extraction
        mp_extractor = MultiprocessExtractor(max_workers=len(cam0_segments) + len(cam1_segments))
        
        extractor_config = {
            'sampling_interval': config.sampling_interval,
            'output_format': config.output_format,
            'enable_overlay': config.enable_frame_overlay,
            'overlay_font_size': config.overlay_font_size,
            'overlay_position': config.overlay_position
        }
        
        logger.info("🚀 Starting multiprocess frame extraction...")
        cam0_frames, cam1_frames = mp_extractor.extract_all_frames(
            cam0_segments,
            cam1_segments,
            extraction_dirs,
            extractor_config
        )
        
        # Check for shutdown request
        if _shutdown_requested:
            logger.info("⚠️ 处理被中断 (Processing interrupted)")
            return 1
        
        logger.info(f"✅ Extraction complete: cam0={len(cam0_frames)}, cam1={len(cam1_frames)}")
        
        # Batch stitching
        print("\n" + "="*80)
        print("🔗 批量拼接 (Batch Stitching)")
        print("="*80)
        
        logger.info("🔗 Starting batch stitching...")
        
        # Convert frame metadata to ExtractedFrame objects
        from src.frame_extraction import ExtractedFrame
        cam0_extracted_frames = [
            ExtractedFrame(
                global_frame_number=f['global_frame_number'],
                camera_id=f['camera_id'],
                file_path=Path(f['file_path'])
            )
            for f in cam0_frames
        ]
        
        cam1_extracted_frames = [
            ExtractedFrame(
                global_frame_number=f['global_frame_number'],
                camera_id=f['camera_id'],
                file_path=Path(f['file_path'])
            )
            for f in cam1_frames
        ]
        
        # Find matching pairs first
        frame_pairs = stitcher.find_frame_pairs(cam0_extracted_frames, cam1_extracted_frames)
        
        print(f"找到 {len(frame_pairs)} 对匹配帧\n")
        
        # Stitch frames with progress bar
        with tqdm(total=len(frame_pairs), desc="🔗 拼接帧",
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%] {elapsed}<{remaining}',
                  ncols=100) as pbar:
            
            def progress_callback(current, total):
                pbar.n = current
                pbar.refresh()
            
            stitched_frames = stitcher.stitch_frames(
                cam0_extracted_frames,
                cam1_extracted_frames,
                stitching_dir,
                progress_callback=progress_callback
            )
        
        print("\n" + "="*80)
        print(f"✅ 拼接完成: {len(stitched_frames)}帧")
        print("="*80 + "\n")
        
        logger.info(f"✅ Stitching complete: {len(stitched_frames)} frames")
        
        # Get final counts
        cam0_extracted = len(cam0_frames)
        cam1_extracted = len(cam1_frames)
        frames_stitched = len(stitched_frames)
        
        # Display summary
        print("\n" + "="*80)
        print("✅ 处理完成！(Processing Complete!)")
        print("="*80)
        print(f"Cam0 提取帧数: {cam0_extracted:,}")
        print(f"Cam1 提取帧数: {cam1_extracted:,}")
        print(f"成功拼接帧数: {frames_stitched:,}")
        print(f"输出目录: {stitching_dir}")
        print("="*80 + "\n")
        
        # Generate processing report
        report_path = Path("processing_report.txt")
        try:
            # Get list of stitched frame numbers
            stitched_frame_numbers = [sf.global_frame_number for sf in stitched_frames]
            
            generate_enhanced_report(
                output_path=report_path,
                cam0_total_frames=cam0_total,
                cam1_total_frames=cam1_total,
                cam0_segments=len(cam0_segments),
                cam1_segments=len(cam1_segments),
                cam0_extracted=cam0_extracted,
                cam1_extracted=cam1_extracted,
                frames_stitched=frames_stitched,
                frame_difference=abs_diff,
                difference_percent=diff_percent,
                sampling_interval=config.sampling_interval,
                config=config,
                sync_analysis=sync_analysis,
                segments_dir=config.input_dir,
                cam0_segment_list=cam0_segments,
                cam1_segment_list=cam1_segments,
                stitched_frame_numbers=stitched_frame_numbers
            )
            logger.info(f"✅ Processing report generated: {report_path}")
        except Exception as e:
            logger.warning(f"Failed to generate processing report: {e}")
            import traceback
            logger.warning(traceback.format_exc())
        
        logger.info("🎉 所有处理完成，程序正常退出 (All processing complete, exiting normally)")
        
        # Force cleanup and exit
        import gc
        gc.collect()
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Video Frame Stitcher - Extract and stitch frames with streaming pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Video Frame Stitcher v1.4.0 (Multiprocess CPU)'
    )
    
    args = parser.parse_args()
    config_path = Path(args.config) if args.config else None
    sys.exit(main(config_path))
