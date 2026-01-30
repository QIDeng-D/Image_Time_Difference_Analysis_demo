"""Unit tests for VideoSegment dataclass."""

import pytest
from pathlib import Path
from src.video_discovery import VideoSegment


class TestVideoSegment:
    """Test suite for VideoSegment dataclass."""
    
    def test_video_segment_creation(self):
        """Test creating a VideoSegment instance with valid data."""
        segment = VideoSegment(
            camera_id='cam0',
            segment_number=1,
            file_path=Path('test.mp4'),
            frame_count=100
        )
        
        assert segment.camera_id == 'cam0'
        assert segment.segment_number == 1
        assert segment.file_path == Path('test.mp4')
        assert segment.frame_count == 100
    
    def test_video_segment_sorting_ascending(self):
        """Test sorting VideoSegments by segment number in ascending order."""
        segment1 = VideoSegment('cam0', 3, Path('seg3.mp4'), 100)
        segment2 = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        segment3 = VideoSegment('cam0', 2, Path('seg2.mp4'), 100)
        
        segments = [segment1, segment2, segment3]
        sorted_segments = sorted(segments)
        
        assert sorted_segments[0].segment_number == 1
        assert sorted_segments[1].segment_number == 2
        assert sorted_segments[2].segment_number == 3
    
    def test_video_segment_sorting_with_same_numbers(self):
        """Test sorting VideoSegments when some have the same segment number."""
        segment1 = VideoSegment('cam0', 2, Path('seg2a.mp4'), 100)
        segment2 = VideoSegment('cam1', 2, Path('seg2b.mp4'), 100)
        segment3 = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        
        segments = [segment1, segment2, segment3]
        sorted_segments = sorted(segments)
        
        # First should be segment 1
        assert sorted_segments[0].segment_number == 1
        # Next two should both be segment 2 (order between them is stable)
        assert sorted_segments[1].segment_number == 2
        assert sorted_segments[2].segment_number == 2
    
    def test_video_segment_less_than_comparison(self):
        """Test direct less-than comparison between VideoSegments."""
        segment1 = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        segment2 = VideoSegment('cam0', 2, Path('seg2.mp4'), 100)
        
        assert segment1 < segment2
        assert not segment2 < segment1
        assert not segment1 < segment1  # Not less than itself
    
    def test_video_segment_comparison_with_different_cameras(self):
        """Test comparison works regardless of camera_id."""
        segment_cam0 = VideoSegment('cam0', 2, Path('cam0_seg2.mp4'), 100)
        segment_cam1 = VideoSegment('cam1', 1, Path('cam1_seg1.mp4'), 100)
        
        # Comparison should be based on segment_number only
        assert segment_cam1 < segment_cam0
        assert not segment_cam0 < segment_cam1
    
    def test_video_segment_comparison_with_non_segment(self):
        """Test that comparison with non-VideoSegment returns NotImplemented."""
        segment = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        
        # Comparing with non-VideoSegment should return NotImplemented
        # which Python will handle appropriately
        result = segment.__lt__("not a segment")
        assert result == NotImplemented
        
        # This should raise TypeError when Python tries to compare
        with pytest.raises(TypeError):
            _ = segment < "not a segment"
    
    def test_video_segment_equality(self):
        """Test equality comparison between VideoSegments."""
        segment1 = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        segment2 = VideoSegment('cam0', 1, Path('seg1.mp4'), 100)
        segment3 = VideoSegment('cam0', 2, Path('seg2.mp4'), 100)
        
        # Dataclasses provide automatic equality
        assert segment1 == segment2
        assert segment1 != segment3
    
    def test_video_segment_with_different_frame_counts(self):
        """Test VideoSegments with different frame counts sort correctly."""
        segment1 = VideoSegment('cam0', 1, Path('seg1.mp4'), 50)
        segment2 = VideoSegment('cam0', 2, Path('seg2.mp4'), 200)
        segment3 = VideoSegment('cam0', 3, Path('seg3.mp4'), 100)
        
        segments = [segment2, segment3, segment1]
        sorted_segments = sorted(segments)
        
        # Should sort by segment_number, not frame_count
        assert sorted_segments[0].segment_number == 1
        assert sorted_segments[0].frame_count == 50
        assert sorted_segments[1].segment_number == 2
        assert sorted_segments[1].frame_count == 200
        assert sorted_segments[2].segment_number == 3
        assert sorted_segments[2].frame_count == 100
