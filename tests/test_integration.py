"""Integration tests for the complete video frame stitcher pipeline."""

import pytest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from src.main import main
from src.config import Config, ConfigManager


def create_test_video(path: Path, num_frames: int, width: int = 640, height: int = 480, color=(0, 0, 255)):
    """Create a test video file with specified parameters."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
    
    for i in range(num_frames):
        # Create a frame with the specified color and frame number text
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        cv2.putText(frame, f"Frame {i+1}", (50, height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    
    out.release()


class TestEndToEndPipeline:
    """Test the complete pipeline from video discovery to frame stitching."""
    
    def test_pipeline_with_single_segment(self):
        """Test end-to-end pipeline with single video segment per camera."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Setup directories
            input_dir = base / "input"
            output_dir = base / "output"
            extracted_dir = base / "extracted"
            input_dir.mkdir()
            
            # Create test videos
            cam0_video = input_dir / "stereo_cam0_sbs_0001.mp4"
            cam1_video = input_dir / "stereo_cam1_sbs_0001.mp4"
            
            create_test_video(cam0_video, 150, color=(255, 0, 0))  # Red
            create_test_video(cam1_video, 150, color=(0, 0, 255))  # Blue
            
            # Create config
            config = Config(
                input_dir=input_dir,
                output_dir=output_dir,
                extracted_frames_dir=extracted_dir,
                sampling_interval=50,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline
            exit_code = main(config_path)
            
            # Verify success
            assert exit_code == 0
            
            # Verify output directories exist
            assert extracted_dir.exists()
            assert output_dir.exists()
            
            # Verify stitched frames exist
            stitched_files = list(output_dir.glob("frame_*.png"))
            assert len(stitched_files) > 0, "No stitched frames were created"
            
            # Verify stitched frame dimensions (check first frame)
            if stitched_files:
                with Image.open(stitched_files[0]) as img:
                    # Height should be double (two frames stacked)
                    assert img.height == 480 * 2
                    assert img.width == 640
            
            # Give Windows time to release file handles
            import time
            time.sleep(0.1)
    
    def test_pipeline_with_multiple_segments(self):
        """Test end-to-end pipeline with multiple video segments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Setup directories
            input_dir = base / "input"
            output_dir = base / "output"
            extracted_dir = base / "extracted"
            input_dir.mkdir()
            
            # Create multiple test video segments
            segments = [1, 2, 3]
            frames_per_segment = 100
            
            for seg in segments:
                cam0_video = input_dir / f"stereo_cam0_sbs_{seg:04d}.mp4"
                cam1_video = input_dir / f"stereo_cam1_sbs_{seg:04d}.mp4"
                
                create_test_video(cam0_video, frames_per_segment, color=(255, 0, 0))
                create_test_video(cam1_video, frames_per_segment, color=(0, 0, 255))
            
            # Create config with sampling interval of 100
            config = Config(
                input_dir=input_dir,
                output_dir=output_dir,
                extracted_frames_dir=extracted_dir,
                sampling_interval=100,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline
            exit_code = main(config_path)
            
            # Verify success
            assert exit_code == 0
            
            # Verify stitched frames
            # With 3 segments of 100 frames each and sampling interval 100:
            # Total frames: 300
            # Frames extracted at positions: 1, 101, 201
            # Check that we have the expected number of frames
            stitched_files = list(output_dir.glob("frame_*.png"))
            assert len(stitched_files) == 3, f"Expected 3 stitched frames, got {len(stitched_files)}"
    
    def test_pipeline_with_mismatched_segments(self):
        """Test pipeline behavior with missing segment pairs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Setup directories
            input_dir = base / "input"
            output_dir = base / "output"
            extracted_dir = base / "extracted"
            input_dir.mkdir()
            
            # Create videos with missing cam1 segment 2
            cam0_seg1 = input_dir / "stereo_cam0_sbs_0001.mp4"
            cam0_seg2 = input_dir / "stereo_cam0_sbs_0002.mp4"
            cam1_seg1 = input_dir / "stereo_cam1_sbs_0001.mp4"
            # cam1_seg2 is missing
            
            create_test_video(cam0_seg1, 100, color=(255, 0, 0))
            create_test_video(cam0_seg2, 100, color=(255, 0, 0))
            create_test_video(cam1_seg1, 100, color=(0, 0, 255))
            
            # Create config
            config = Config(
                input_dir=input_dir,
                output_dir=output_dir,
                extracted_frames_dir=extracted_dir,
                sampling_interval=50,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline - should still succeed but with warnings
            exit_code = main(config_path)
            
            # Should succeed (processes available segments)
            assert exit_code == 0
            
            # Should have stitched frames from segment 1 only
            assert output_dir.exists()
            stitched_files = list(output_dir.glob("frame_*.png"))
            assert len(stitched_files) > 0
    
    def test_pipeline_with_different_sampling_intervals(self):
        """Test pipeline with various sampling intervals."""
        sampling_intervals = [1, 10, 50]
        
        for interval in sampling_intervals:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir)
                
                # Setup directories
                input_dir = base / "input"
                output_dir = base / "output"
                extracted_dir = base / "extracted"
                input_dir.mkdir()
                
                # Create test videos
                cam0_video = input_dir / "stereo_cam0_sbs_0001.mp4"
                cam1_video = input_dir / "stereo_cam1_sbs_0001.mp4"
                
                num_frames = 100
                create_test_video(cam0_video, num_frames, color=(255, 0, 0))
                create_test_video(cam1_video, num_frames, color=(0, 0, 255))
                
                # Create config
                config = Config(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    extracted_frames_dir=extracted_dir,
                    sampling_interval=interval,
                    output_format='png',
                    cam0_pattern='stereo_cam0_sbs_*.mp4',
                    cam1_pattern='stereo_cam1_sbs_*.mp4'
                )
                
                config_path = base / "config.yaml"
                config_manager = ConfigManager()
                config_manager.save_config(config, config_path)
                
                # Run main pipeline
                exit_code = main(config_path)
                
                # Verify success
                assert exit_code == 0
                
                # Calculate expected number of frames
                # Frames at positions: 1, 1+interval, 1+2*interval, ...
                expected_count = len([i for i in range(1, num_frames + 1, interval)])
                
                stitched_files = list(output_dir.glob("frame_*.png"))
                assert len(stitched_files) == expected_count, \
                    f"Expected {expected_count} frames with interval {interval}, got {len(stitched_files)}"


class TestErrorHandling:
    """Test error handling in the integration pipeline."""
    
    def test_missing_input_directory(self):
        """Test error handling when input directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Create config with non-existent input directory
            config = Config(
                input_dir=base / "nonexistent",
                output_dir=base / "output",
                extracted_frames_dir=base / "extracted",
                sampling_interval=100,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline - should fail
            exit_code = main(config_path)
            
            assert exit_code != 0
    
    def test_no_video_files_found(self):
        """Test error handling when no video files are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Setup directories
            input_dir = base / "input"
            output_dir = base / "output"
            extracted_dir = base / "extracted"
            input_dir.mkdir()
            
            # Don't create any video files
            
            # Create config
            config = Config(
                input_dir=input_dir,
                output_dir=output_dir,
                extracted_frames_dir=extracted_dir,
                sampling_interval=100,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline - should fail
            exit_code = main(config_path)
            
            assert exit_code != 0
    
    def test_only_one_camera_videos(self):
        """Test error handling when only one camera has videos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            # Setup directories
            input_dir = base / "input"
            output_dir = base / "output"
            extracted_dir = base / "extracted"
            input_dir.mkdir()
            
            # Create only cam0 video
            cam0_video = input_dir / "stereo_cam0_sbs_0001.mp4"
            create_test_video(cam0_video, 100, color=(255, 0, 0))
            
            # Create config
            config = Config(
                input_dir=input_dir,
                output_dir=output_dir,
                extracted_frames_dir=extracted_dir,
                sampling_interval=50,
                output_format='png',
                cam0_pattern='stereo_cam0_sbs_*.mp4',
                cam1_pattern='stereo_cam1_sbs_*.mp4'
            )
            
            config_path = base / "config.yaml"
            config_manager = ConfigManager()
            config_manager.save_config(config, config_path)
            
            # Run main pipeline - should fail (can't stitch without both cameras)
            exit_code = main(config_path)
            
            assert exit_code != 0
