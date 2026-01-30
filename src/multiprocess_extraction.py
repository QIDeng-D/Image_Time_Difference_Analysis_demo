"""Multiprocess frame extraction for improved performance."""

import logging
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import multiprocessing as mp
from tqdm import tqdm

from src.frame_extraction import FrameExtractor

logger = logging.getLogger(__name__)


@dataclass
class SegmentExtractionTask:
    """Task for extracting frames from a single segment."""
    segment: 'VideoSegment'
    camera_id: str
    output_dir: Path
    sampling_interval: int
    output_format: str
    enable_overlay: bool
    overlay_font_size: int
    overlay_position: str
    global_frame_offset: int  # Frames before this segment


def extract_segment_frames(task: SegmentExtractionTask) -> List[Dict]:
    """Extract frames from a single video segment (runs in separate process).
    
    Args:
        task: SegmentExtractionTask with all necessary parameters
        
    Returns:
        List of extracted frame metadata dictionaries
    """
    cap = None
    try:
        # Create extractor
        extractor = FrameExtractor(
            sampling_interval=task.sampling_interval,
            output_format=task.output_format,
            enable_overlay=task.enable_overlay,
            overlay_font_size=task.overlay_font_size,
            overlay_position=task.overlay_position
        )
        
        # Open video
        cap = extractor._open_video(task.segment.file_path)
        if cap is None:
            logger.error(f"Failed to open {task.segment.file_path}")
            return []
        
        extracted_frames = []
        local_frame_number = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            local_frame_number += 1
            global_frame_number = task.global_frame_offset + local_frame_number
            
            # Check if this frame should be extracted
            if extractor.should_extract_frame(global_frame_number):
                try:
                    # Save the frame
                    file_path = extractor.save_frame(
                        frame, global_frame_number, 
                        task.output_dir, task.camera_id
                    )
                    
                    # Create metadata
                    frame_metadata = {
                        'global_frame_number': global_frame_number,
                        'camera_id': task.camera_id,
                        'file_path': str(file_path)
                    }
                    extracted_frames.append(frame_metadata)
                    
                except Exception as e:
                    logger.error(f"Error saving frame {global_frame_number}: {e}")
                    continue
        
        logger.info(f"✅ {task.camera_id} segment {task.segment.segment_number}: "
                   f"extracted {len(extracted_frames)} frames")
        
        return extracted_frames
        
    except Exception as e:
        logger.error(f"Error processing segment {task.segment.file_path}: {e}")
        return []
    
    finally:
        # Ensure video capture is released
        if cap is not None:
            try:
                cap.release()
            except:
                pass


class MultiprocessExtractor:
    """Manages multiprocess frame extraction."""
    
    def __init__(self, max_workers: int = None):
        """Initialize multiprocess extractor.
        
        Args:
            max_workers: Maximum number of worker processes (default: CPU count)
        """
        if max_workers is None:
            max_workers = mp.cpu_count()
        self.max_workers = max_workers
        logger.info(f"Multiprocess extractor initialized with {max_workers} workers")
    
    def extract_all_frames(
        self,
        cam0_segments: List,
        cam1_segments: List,
        extraction_dirs: Dict[str, Path],
        extractor_config: Dict
    ) -> tuple:
        """Extract frames from all segments using multiprocessing with progress bar.
        
        Args:
            cam0_segments: List of cam0 video segments
            cam1_segments: List of cam1 video segments
            extraction_dirs: Dictionary with output directories
            extractor_config: Configuration for FrameExtractor
            
        Returns:
            Tuple of (cam0_frames, cam1_frames) - lists of frame metadata
        """
        # Create tasks for all segments
        tasks = []
        
        # Calculate global frame offsets for cam0
        cam0_offset = 0
        for segment in sorted(cam0_segments, key=lambda s: s.segment_number):
            task = SegmentExtractionTask(
                segment=segment,
                camera_id='cam0',
                output_dir=extraction_dirs['cam0'],
                global_frame_offset=cam0_offset,
                **extractor_config
            )
            tasks.append(task)
            cam0_offset += segment.frame_count
        
        # Calculate global frame offsets for cam1
        cam1_offset = 0
        for segment in sorted(cam1_segments, key=lambda s: s.segment_number):
            task = SegmentExtractionTask(
                segment=segment,
                camera_id='cam1',
                output_dir=extraction_dirs['cam1'],
                global_frame_offset=cam1_offset,
                **extractor_config
            )
            tasks.append(task)
            cam1_offset += segment.frame_count
        
        logger.info(f"Starting multiprocess extraction: {len(tasks)} tasks, "
                   f"{self.max_workers} workers")
        
        # Process all tasks in parallel with progress bar
        cam0_results = []
        cam1_results = []
        
        # Create progress bar
        print("\n" + "="*80)
        print("🚀 多进程并行提取 (Multiprocess Parallel Extraction)")
        print("="*80)
        
        executor = None
        try:
            with tqdm(total=len(tasks), desc="📦 处理视频段", 
                      bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%] {elapsed}<{remaining}',
                      ncols=100) as pbar:
                
                executor = ProcessPoolExecutor(max_workers=self.max_workers)
                
                # Submit all tasks
                future_to_task = {
                    executor.submit(extract_segment_frames, task): task 
                    for task in tasks
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        frames = future.result(timeout=300)  # 5 minute timeout per task
                        if task.camera_id == 'cam0':
                            cam0_results.extend(frames)
                        else:
                            cam1_results.extend(frames)
                        
                        # Update progress bar with detailed info
                        pbar.set_postfix({
                            'cam': task.camera_id,
                            'seg': task.segment.segment_number,
                            'frames': len(frames)
                        })
                        pbar.update(1)
                        
                    except Exception as e:
                        logger.error(f"Task failed for {task.camera_id} "
                                   f"segment {task.segment.segment_number}: {e}")
                        pbar.update(1)
        
        finally:
            # Explicitly shutdown the executor
            if executor is not None:
                logger.info("Shutting down process pool...")
                executor.shutdown(wait=True, cancel_futures=False)
                logger.info("Process pool shutdown complete")
        
        # Sort by frame number
        cam0_results.sort(key=lambda x: x['global_frame_number'])
        cam1_results.sort(key=lambda x: x['global_frame_number'])
        
        print("\n" + "="*80)
        print(f"✅ 提取完成: cam0={len(cam0_results)}帧, cam1={len(cam1_results)}帧")
        print("="*80 + "\n")
        
        logger.info(f"Multiprocess extraction complete: "
                   f"cam0={len(cam0_results)}, cam1={len(cam1_results)}")
        
        return cam0_results, cam1_results
