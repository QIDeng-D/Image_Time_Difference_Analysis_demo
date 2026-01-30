"""Unit tests for frame extraction components."""

import pytest
from pathlib import Path
import tempfile
import shutil
import cv2
import numpy as np
from src.frame_extraction import ExtractedFrame, FrameExtractor
from src.video_discovery import VideoSegment


class TestExtractedFrame:
    """Test suite for ExtractedFrame dataclass."""
    
    def test_extracted_frame_creation(self):
        """Test creating an ExtractedFrame instance with valid data."""
        frame = ExtractedFrame(
            global_frame_number=101,
            camera_id='cam0',
            file_path=Path('extracted_frames/cam0/frame_0101.png')
        )
        
        assert frame.global_frame_number == 101
        assert frame.camera_id == 'cam0'
        assert frame.file_path == Path('extracted_frames/cam0/frame_0101.png')
    
    def test_extracted_frame_with_cam1(self):
        """Test creating an ExtractedFrame for cam1."""
        frame = ExtractedFrame(
            global_frame_number=201,
            camera_id='cam1',
            file_path=Path('extracted_frames/cam1/frame_0201.png')
        )
        
        assert frame.global_frame_number == 201
        assert frame.camera_id == 'cam1'
        assert frame.file_path == Path('extracted_frames/cam1/frame_0201.png')
    
    def test_extracted_frame_equality(self):
        """Test that two ExtractedFrame instances with same data are equal."""
        frame1 = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam0',
            file_path=Path('frame_0001.png')
        )
        frame2 = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam0',
            file_path=Path('frame_0001.png')
        )
        
        assert frame1 == frame2
    
    def test_extracted_frame_inequality(self):
        """Test that ExtractedFrame instances with different data are not equal."""
        frame1 = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam0',
            file_path=Path('frame_0001.png')
        )
        frame2 = ExtractedFrame(
            global_frame_number=2,
            camera_id='cam0',
            file_path=Path('frame_0002.png')
        )
        
        assert frame1 != frame2
    
    def test_extracted_frame_with_different_cameras(self):
        """Test that frames from different cameras are not equal even with same frame number."""
        frame1 = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam0',
            file_path=Path('cam0/frame_0001.png')
        )
        frame2 = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam1',
            file_path=Path('cam1/frame_0001.png')
        )
        
        assert frame1 != frame2
    
    def test_extracted_frame_attributes_are_accessible(self):
        """Test that all attributes can be accessed after creation."""
        frame = ExtractedFrame(
            global_frame_number=500,
            camera_id='cam0',
            file_path=Path('test/path/frame_0500.png')
        )
        
        # Verify all attributes are accessible
        assert isinstance(frame.global_frame_number, int)
        assert isinstance(frame.camera_id, str)
        assert isinstance(frame.file_path, Path)
    
    def test_extracted_frame_repr(self):
        """Test that ExtractedFrame has a useful string representation."""
        frame = ExtractedFrame(
            global_frame_number=1,
            camera_id='cam0',
            file_path=Path('frame_0001.png')
        )
        
        repr_str = repr(frame)
        assert 'ExtractedFrame' in repr_str
        assert '1' in repr_str
        assert 'cam0' in repr_str
        assert 'frame_0001.png' in repr_str


class TestFrameExtractor:
    """Test suite for FrameExtractor class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup after test
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_video(self):
        """Create a sample video file for testing."""
        def _create_video(path: Path, frame_count: int = 10, width: int = 640, height: int = 480):
            """Create a simple test video with specified frame count."""
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
            
            for i in range(frame_count):
                # Create a simple frame with a different color for each frame
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
                out.write(frame)
            
            out.release()
        
        return _create_video
    
    # Test __init__
    
    def test_frame_extractor_init_with_valid_params(self):
        """Test creating FrameExtractor with valid parameters."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        assert extractor.sampling_interval == 100
        assert extractor.output_format == 'png'
    
    def test_frame_extractor_init_with_jpg_format(self):
        """Test creating FrameExtractor with jpg format."""
        extractor = FrameExtractor(sampling_interval=50, output_format='jpg')
        
        assert extractor.sampling_interval == 50
        assert extractor.output_format == 'jpg'
    
    def test_frame_extractor_init_with_jpeg_format(self):
        """Test creating FrameExtractor with jpeg format (normalized to jpg)."""
        extractor = FrameExtractor(sampling_interval=50, output_format='jpeg')
        
        assert extractor.output_format == 'jpeg'
    
    def test_frame_extractor_init_with_invalid_sampling_interval(self):
        """Test that ValueError is raised for sampling_interval < 1."""
        with pytest.raises(ValueError, match="sampling_interval must be >= 1"):
            FrameExtractor(sampling_interval=0, output_format='png')
        
        with pytest.raises(ValueError, match="sampling_interval must be >= 1"):
            FrameExtractor(sampling_interval=-1, output_format='png')
    
    def test_frame_extractor_init_with_invalid_output_format(self):
        """Test that ValueError is raised for invalid output format."""
        with pytest.raises(ValueError, match="output_format must be"):
            FrameExtractor(sampling_interval=100, output_format='bmp')
        
        with pytest.raises(ValueError, match="output_format must be"):
            FrameExtractor(sampling_interval=100, output_format='gif')
    
    # Test should_extract_frame
    
    def test_should_extract_frame_with_interval_100(self):
        """Test frame extraction pattern with sampling interval 100."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        # Should extract frames: 1, 101, 201, 301, ...
        assert extractor.should_extract_frame(1) is True
        assert extractor.should_extract_frame(101) is True
        assert extractor.should_extract_frame(201) is True
        assert extractor.should_extract_frame(301) is True
        
        # Should not extract these frames
        assert extractor.should_extract_frame(2) is False
        assert extractor.should_extract_frame(50) is False
        assert extractor.should_extract_frame(100) is False
        assert extractor.should_extract_frame(102) is False
        assert extractor.should_extract_frame(200) is False
    
    def test_should_extract_frame_with_interval_1(self):
        """Test frame extraction pattern with sampling interval 1 (every frame)."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Should extract all frames
        assert extractor.should_extract_frame(1) is True
        assert extractor.should_extract_frame(2) is True
        assert extractor.should_extract_frame(3) is True
        assert extractor.should_extract_frame(100) is True
    
    def test_should_extract_frame_with_interval_10(self):
        """Test frame extraction pattern with sampling interval 10."""
        extractor = FrameExtractor(sampling_interval=10, output_format='png')
        
        # Should extract frames: 1, 11, 21, 31, ...
        assert extractor.should_extract_frame(1) is True
        assert extractor.should_extract_frame(11) is True
        assert extractor.should_extract_frame(21) is True
        assert extractor.should_extract_frame(31) is True
        
        # Should not extract these frames
        assert extractor.should_extract_frame(2) is False
        assert extractor.should_extract_frame(10) is False
        assert extractor.should_extract_frame(12) is False
        assert extractor.should_extract_frame(20) is False
    
    def test_should_extract_frame_with_zero_or_negative(self):
        """Test that frames with number <= 0 are not extracted."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        assert extractor.should_extract_frame(0) is False
        assert extractor.should_extract_frame(-1) is False
        assert extractor.should_extract_frame(-100) is False
    
    # Test save_frame
    
    def test_save_frame_creates_camera_subdirectory(self, temp_dir):
        """Test that save_frame creates camera subdirectory if it doesn't exist."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        # Create a simple frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (100, 150, 200)
        
        # Save frame
        file_path = extractor.save_frame(frame, 1, temp_dir, 'cam0')
        
        # Verify subdirectory was created
        assert (temp_dir / 'cam0').exists()
        assert (temp_dir / 'cam0').is_dir()
        
        # Verify file was saved
        assert file_path.exists()
        assert file_path.parent == temp_dir / 'cam0'
    
    def test_save_frame_with_correct_filename_format(self, temp_dir):
        """Test that save_frame uses correct filename format with zero-padding."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test various frame numbers
        file_path_1 = extractor.save_frame(frame, 1, temp_dir, 'cam0')
        assert file_path_1.name == 'frame_0001.png'
        
        file_path_101 = extractor.save_frame(frame, 101, temp_dir, 'cam0')
        assert file_path_101.name == 'frame_0101.png'
        
        file_path_9999 = extractor.save_frame(frame, 9999, temp_dir, 'cam0')
        assert file_path_9999.name == 'frame_9999.png'
        
        file_path_10000 = extractor.save_frame(frame, 10000, temp_dir, 'cam0')
        assert file_path_10000.name == 'frame_10000.png'
    
    def test_save_frame_with_jpg_format(self, temp_dir):
        """Test that save_frame uses correct file extension for jpg format."""
        extractor = FrameExtractor(sampling_interval=100, output_format='jpg')
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        file_path = extractor.save_frame(frame, 1, temp_dir, 'cam0')
        
        assert file_path.name == 'frame_0001.jpg'
        assert file_path.suffix == '.jpg'
    
    def test_save_frame_with_none_frame(self, temp_dir):
        """Test that ValueError is raised when frame is None."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        with pytest.raises(ValueError, match="Frame is None or empty"):
            extractor.save_frame(None, 1, temp_dir, 'cam0')
    
    def test_save_frame_with_empty_frame(self, temp_dir):
        """Test that ValueError is raised when frame is empty."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        empty_frame = np.array([])
        
        with pytest.raises(ValueError, match="Frame is None or empty"):
            extractor.save_frame(empty_frame, 1, temp_dir, 'cam0')
    
    def test_save_frame_preserves_frame_content(self, temp_dir):
        """Test that saved frame preserves the original frame content."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        # Create a frame with specific colors
        original_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        original_frame[:, :] = (50, 100, 150)
        
        # Save frame
        file_path = extractor.save_frame(original_frame, 1, temp_dir, 'cam0')
        
        # Load saved frame
        loaded_frame = cv2.imread(str(file_path))
        
        # Verify content is preserved
        assert loaded_frame.shape == original_frame.shape
        np.testing.assert_array_equal(loaded_frame, original_frame)
    
    # Test extract_frames
    
    def test_extract_frames_from_single_frame_video(self, temp_dir, sample_video):
        """Test extracting frames from a single-frame video (edge case)."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create a video with only 1 frame
        video_path = temp_dir / 'single_frame.mp4'
        sample_video(video_path, frame_count=1)
        
        # Create video segment
        segment = VideoSegment(
            camera_id='cam0',
            segment_number=1,
            file_path=video_path,
            frame_count=1
        )
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Verify exactly one frame was extracted
        assert len(extracted) == 1
        assert extracted[0].global_frame_number == 1
        
        # Verify file exists
        assert extracted[0].file_path.exists()
        assert extracted[0].camera_id == 'cam0'
        
        # Verify the frame can be loaded
        loaded_frame = cv2.imread(str(extracted[0].file_path))
        assert loaded_frame is not None
    
    def test_extract_frames_from_single_segment(self, temp_dir, sample_video):
        """Test extracting frames from a single video segment."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create a video with 3 frames
        video_path = temp_dir / 'test_video.mp4'
        sample_video(video_path, frame_count=3)
        
        # Create video segment
        segment = VideoSegment(
            camera_id='cam0',
            segment_number=1,
            file_path=video_path,
            frame_count=3
        )
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Verify all frames were extracted
        assert len(extracted) == 3
        assert extracted[0].global_frame_number == 1
        assert extracted[1].global_frame_number == 2
        assert extracted[2].global_frame_number == 3
        
        # Verify files exist
        for frame in extracted:
            assert frame.file_path.exists()
            assert frame.camera_id == 'cam0'
    
    def test_extract_frames_with_sampling_interval(self, temp_dir, sample_video):
        """Test extracting frames with sampling interval > 1."""
        extractor = FrameExtractor(sampling_interval=3, output_format='png')
        
        # Create a video with 10 frames
        video_path = temp_dir / 'test_video.mp4'
        sample_video(video_path, frame_count=10)
        
        segment = VideoSegment(
            camera_id='cam0',
            segment_number=1,
            file_path=video_path,
            frame_count=10
        )
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Should extract frames: 1, 4, 7, 10
        assert len(extracted) == 4
        assert extracted[0].global_frame_number == 1
        assert extracted[1].global_frame_number == 4
        assert extracted[2].global_frame_number == 7
        assert extracted[3].global_frame_number == 10
    
    def test_extract_frames_from_multiple_segments(self, temp_dir, sample_video):
        """Test extracting frames from multiple video segments with continuous numbering."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create two video segments
        video1_path = temp_dir / 'video1.mp4'
        video2_path = temp_dir / 'video2.mp4'
        sample_video(video1_path, frame_count=5)
        sample_video(video2_path, frame_count=3)
        
        segments = [
            VideoSegment('cam0', 1, video1_path, 5),
            VideoSegment('cam0', 2, video2_path, 3)
        ]
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames(segments, output_dir, 'cam0')
        
        # Verify continuous global frame numbering
        assert len(extracted) == 8
        assert extracted[0].global_frame_number == 1
        assert extracted[4].global_frame_number == 5
        assert extracted[5].global_frame_number == 6  # First frame of second segment
        assert extracted[7].global_frame_number == 8  # Last frame
    
    def test_extract_frames_directory_organization(self, temp_dir, sample_video):
        """Test that extracted frames are organized in camera subdirectories."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        video_path = temp_dir / 'test_video.mp4'
        sample_video(video_path, frame_count=3)
        
        segment = VideoSegment('cam0', 1, video_path, 3)
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Verify all frames are in cam0 subdirectory
        for frame in extracted:
            assert frame.file_path.parent == output_dir / 'cam0'
    
    def test_extract_frames_with_empty_segment_list(self, temp_dir):
        """Test that ValueError is raised when segment list is empty."""
        extractor = FrameExtractor(sampling_interval=100, output_format='png')
        
        with pytest.raises(ValueError, match="video_segments list is empty"):
            extractor.extract_frames([], temp_dir, 'cam0')
    
    def test_extract_frames_with_progress_callback(self, temp_dir, sample_video):
        """Test that progress callback is called during extraction."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        video_path = temp_dir / 'test_video.mp4'
        sample_video(video_path, frame_count=5)
        
        segment = VideoSegment('cam0', 1, video_path, 5)
        
        # Track progress callback calls
        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extractor.extract_frames([segment], output_dir, 'cam0', progress_callback)
        
        # Verify callback was called
        assert len(progress_calls) == 5
        assert progress_calls[0] == (1, 5)
        assert progress_calls[4] == (5, 5)
    
    def test_extract_frames_handles_corrupted_video(self, temp_dir):
        """Test that extraction continues when a video file cannot be opened."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create a fake video file (not a real video)
        fake_video = temp_dir / 'fake_video.mp4'
        fake_video.write_text("This is not a video")
        
        segment = VideoSegment('cam0', 1, fake_video, 10)
        
        # Extract frames (should handle error gracefully)
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Should return empty list since video couldn't be opened
        assert len(extracted) == 0
    
    def test_extract_frames_preserves_resolution(self, temp_dir, sample_video):
        """Test that extracted frames preserve the original video resolution."""
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create video with specific resolution
        video_path = temp_dir / 'test_video.mp4'
        sample_video(video_path, frame_count=2, width=320, height=240)
        
        segment = VideoSegment('cam0', 1, video_path, 2)
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames([segment], output_dir, 'cam0')
        
        # Load first extracted frame and check resolution
        loaded_frame = cv2.imread(str(extracted[0].file_path))
        assert loaded_frame.shape[0] == 240  # height
        assert loaded_frame.shape[1] == 320  # width


# Property-Based Tests

from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck


class TestFrameExtractionProperties:
    """Property-based tests for frame extraction components."""
    
    @given(
        sampling_interval=st.integers(min_value=1, max_value=1000),
        total_frames=st.integers(min_value=1, max_value=10000)
    )
    def test_property_frame_sampling_pattern(self, sampling_interval, total_frames):
        """Property 3: Frame Sampling Pattern
        
        **Validates: Requirements 2.1, 2.2**
        
        For any sampling interval N and video with total frames F, the extracted 
        frame numbers should follow the pattern: 1, 1+N, 1+2N, 1+3N, ... up to 
        the largest value ≤ F.
        """
        extractor = FrameExtractor(sampling_interval=sampling_interval, output_format='png')
        
        # Generate the expected frame numbers based on the sampling pattern
        expected_frames = []
        frame_num = 1
        while frame_num <= total_frames:
            expected_frames.append(frame_num)
            frame_num += sampling_interval
        
        # Test which frames should be extracted
        actual_frames = []
        for frame_num in range(1, total_frames + 1):
            if extractor.should_extract_frame(frame_num):
                actual_frames.append(frame_num)
        
        # Verify the pattern matches
        assert actual_frames == expected_frames, \
            f"Sampling interval {sampling_interval}, total frames {total_frames}: " \
            f"Expected {expected_frames}, got {actual_frames}"
        
        # Verify the pattern properties:
        # 1. First frame should always be 1
        if len(actual_frames) > 0:
            assert actual_frames[0] == 1, "First extracted frame should be frame 1"
        
        # 2. Consecutive frames should differ by exactly sampling_interval
        for i in range(1, len(actual_frames)):
            diff = actual_frames[i] - actual_frames[i-1]
            assert diff == sampling_interval, \
                f"Frames {actual_frames[i-1]} and {actual_frames[i]} differ by {diff}, expected {sampling_interval}"
        
        # 3. All extracted frames should be <= total_frames
        for frame_num in actual_frames:
            assert frame_num <= total_frames, \
                f"Frame {frame_num} exceeds total frames {total_frames}"
        
        # 4. The last extracted frame should be the largest frame matching the pattern that is <= total_frames
        if len(actual_frames) > 0:
            last_frame = actual_frames[-1]
            # The next frame in the pattern would exceed total_frames
            next_frame = last_frame + sampling_interval
            assert next_frame > total_frames, \
                f"Next frame {next_frame} should exceed total frames {total_frames}"

    
    @settings(deadline=None, max_examples=50)
    @given(
        segment_frame_counts=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=5
        ),
        sampling_interval=st.integers(min_value=1, max_value=50)
    )
    def test_property_global_frame_numbering(self, segment_frame_counts, sampling_interval):
        """Property 4: Global Frame Numbering Continuity
        
        **Validates: Requirements 3.2, 3.3, 3.5**
        
        For any sequence of video segments with frame counts [F1, F2, F3, ...], 
        when extracting frames, the global frame number for frame i in segment j 
        should equal (sum of all frame counts in segments 0 to j-1) + i.
        """
        extractor = FrameExtractor(sampling_interval=sampling_interval, output_format='png')
        
        # Create temporary directory for this test
        temp_dir = Path(tempfile.mkdtemp())
        
        # Helper function to create test videos
        def create_test_video(path: Path, frame_count: int):
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(path), fourcc, 30.0, (320, 240))
            for i in range(frame_count):
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
                out.write(frame)
            out.release()
        
        # Create video segments
        segments = []
        for idx, frame_count in enumerate(segment_frame_counts):
            video_path = temp_dir / f'segment_{idx}.mp4'
            create_test_video(video_path, frame_count)
            
            segment = VideoSegment(
                camera_id='cam0',
                segment_number=idx,
                file_path=video_path,
                frame_count=frame_count
            )
            segments.append(segment)
        
        # Extract frames
        output_dir = temp_dir / 'output'
        extracted = extractor.extract_frames(segments, output_dir, 'cam0')
        
        # Verify global frame numbering continuity
        # Calculate expected global frame numbers
        expected_global_frames = []
        cumulative_frames = 0
        
        for segment_idx, frame_count in enumerate(segment_frame_counts):
            for local_frame in range(1, frame_count + 1):
                global_frame = cumulative_frames + local_frame
                if extractor.should_extract_frame(global_frame):
                    expected_global_frames.append(global_frame)
            cumulative_frames += frame_count
        
        # Extract actual global frame numbers from results
        actual_global_frames = [frame.global_frame_number for frame in extracted]
        
        # Verify they match
        assert actual_global_frames == expected_global_frames, \
            f"Segment frame counts {segment_frame_counts}, sampling {sampling_interval}: " \
            f"Expected {expected_global_frames}, got {actual_global_frames}"
        
        # Verify continuity properties:
        # 1. Frame numbers should be strictly increasing
        for i in range(1, len(actual_global_frames)):
            assert actual_global_frames[i] > actual_global_frames[i-1], \
                f"Frame numbers not strictly increasing: {actual_global_frames[i-1]} >= {actual_global_frames[i]}"
        
        # 2. All frame numbers should be within valid range
        total_frames = sum(segment_frame_counts)
        for frame_num in actual_global_frames:
            assert 1 <= frame_num <= total_frames, \
                f"Frame number {frame_num} out of range [1, {total_frames}]"
        
        # 3. Frame numbers should follow the sampling pattern
        if len(actual_global_frames) > 0:
            assert actual_global_frames[0] == 1 or actual_global_frames[0] > 1, \
                "First frame number should be positive"
            
            # Check spacing between consecutive frames
            for i in range(1, len(actual_global_frames)):
                spacing = actual_global_frames[i] - actual_global_frames[i-1]
                assert spacing == sampling_interval, \
                    f"Spacing between frames {actual_global_frames[i-1]} and {actual_global_frames[i]} " \
                    f"is {spacing}, expected {sampling_interval}"
        
        # Cleanup
        shutil.rmtree(temp_dir)

    
    @given(
        global_frame_number=st.integers(min_value=1, max_value=999999),
        output_format=st.sampled_from(['png', 'jpg', 'jpeg'])
    )
    def test_property_filename_format(self, global_frame_number, output_format):
        """Property 5: Filename Format Consistency
        
        **Validates: Requirements 2.4, 3.4, 4.4, 8.4**
        
        For any extracted or stitched frame with global frame number N, the filename 
        should follow the pattern "frame_XXXX.{ext}" where XXXX is N zero-padded to 
        at least 4 digits.
        """
        extractor = FrameExtractor(sampling_interval=100, output_format=output_format)
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create a test frame
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[:, :] = (100, 150, 200)
            
            # Save the frame
            file_path = extractor.save_frame(frame, global_frame_number, temp_dir, 'cam0')
            
            # Extract filename
            filename = file_path.name
            
            # Verify filename pattern
            # Pattern: frame_XXXX.ext where XXXX is zero-padded to at least 4 digits
            import re
            
            # Normalize output format for comparison
            expected_ext = output_format.lower()
            
            # Check pattern
            pattern = r'^frame_(\d{4,})\.(png|jpg|jpeg)$'
            match = re.match(pattern, filename)
            
            assert match is not None, \
                f"Filename '{filename}' does not match pattern 'frame_XXXX.ext'"
            
            # Extract the number part
            number_str = match.group(1)
            file_ext = match.group(2)
            
            # Verify the number matches the global frame number
            extracted_number = int(number_str)
            assert extracted_number == global_frame_number, \
                f"Filename contains {extracted_number}, expected {global_frame_number}"
            
            # Verify zero-padding (at least 4 digits)
            assert len(number_str) >= 4, \
                f"Frame number '{number_str}' should be zero-padded to at least 4 digits"
            
            # Verify correct zero-padding
            expected_padding = max(4, len(str(global_frame_number)))
            assert len(number_str) == expected_padding, \
                f"Frame number '{number_str}' has incorrect padding length"
            
            # Verify file extension matches output format
            assert file_ext == expected_ext, \
                f"File extension '{file_ext}' does not match expected '{expected_ext}'"
            
            # Verify the file actually exists
            assert file_path.exists(), f"File {file_path} does not exist"
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)

    
    @settings(deadline=None, max_examples=30)
    @given(
        width=st.integers(min_value=160, max_value=1920),
        height=st.integers(min_value=120, max_value=1080),
        frame_count=st.integers(min_value=1, max_value=10)
    )
    def test_property_resolution_preservation(self, width, height, frame_count):
        """Property 7: Frame Resolution Preservation
        
        **Validates: Requirements 2.5**
        
        For any frame extracted from a video, the extracted frame's dimensions 
        should match the original video's frame dimensions.
        """
        # Ensure width and height are even (required by some video codecs)
        width = width if width % 2 == 0 else width + 1
        height = height if height % 2 == 0 else height + 1
        
        extractor = FrameExtractor(sampling_interval=1, output_format='png')
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create a test video with specific resolution
            video_path = temp_dir / 'test_video.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (width, height))
            
            for i in range(frame_count):
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                # Create a pattern to verify it's the right frame
                frame[:, :] = (i * 10 % 256, (i * 20) % 256, (i * 30) % 256)
                out.write(frame)
            
            out.release()
            
            # Create video segment
            segment = VideoSegment(
                camera_id='cam0',
                segment_number=1,
                file_path=video_path,
                frame_count=frame_count
            )
            
            # Extract frames
            output_dir = temp_dir / 'output'
            extracted = extractor.extract_frames([segment], output_dir, 'cam0')
            
            # Verify all extracted frames have the correct resolution
            assert len(extracted) == frame_count, \
                f"Expected {frame_count} frames, got {len(extracted)}"
            
            for frame_info in extracted:
                # Load the extracted frame
                loaded_frame = cv2.imread(str(frame_info.file_path))
                
                assert loaded_frame is not None, \
                    f"Failed to load frame {frame_info.file_path}"
                
                # Check dimensions
                actual_height, actual_width = loaded_frame.shape[:2]
                
                assert actual_width == width, \
                    f"Frame {frame_info.global_frame_number}: width {actual_width} != expected {width}"
                
                assert actual_height == height, \
                    f"Frame {frame_info.global_frame_number}: height {actual_height} != expected {height}"
                
                # Verify it's a color image (3 channels)
                assert loaded_frame.shape[2] == 3, \
                    f"Frame {frame_info.global_frame_number}: expected 3 channels, got {loaded_frame.shape[2]}"
        
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
