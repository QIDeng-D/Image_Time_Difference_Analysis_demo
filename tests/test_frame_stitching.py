"""Tests for frame stitching functionality."""

import pytest
from pathlib import Path
from PIL import Image
import tempfile
import shutil
from hypothesis import given, strategies as st, settings

from src.frame_stitching import FrameStitcher, StitchedFrame
from src.frame_extraction import ExtractedFrame


# Feature: video-frame-stitcher, Property 8: Vertical Stitching Order
@settings(max_examples=100)
@given(
    cam0_color=st.tuples(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
    cam1_color=st.tuples(st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
    width=st.integers(100, 500),
    height=st.integers(100, 500)
)
def test_property_vertical_stitching_order(cam0_color, cam1_color, width, height):
    """
    **Property 8: Vertical Stitching Order**
    **Validates: Requirements 4.1**
    
    For any pair of stitched frames, when the output image is divided horizontally 
    at the midpoint, the top half should contain the cam0 frame and the bottom half 
    should contain the cam1 frame.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test images with distinct colors
        cam0_img = Image.new('RGB', (width, height), color=cam0_color)
        cam1_img = Image.new('RGB', (width, height), color=cam1_color)
        
        cam0_path = tmpdir / "cam0_frame.png"
        cam1_path = tmpdir / "cam1_frame.png"
        output_path = tmpdir / "stitched.png"
        
        cam0_img.save(cam0_path)
        cam1_img.save(cam1_path)
        
        # Stitch the frames
        stitcher = FrameStitcher('png')
        stitcher.stitch_pair(cam0_path, cam1_path, output_path)
        
        # Load stitched image
        stitched = Image.open(output_path)
        stitched_width, stitched_height = stitched.size
        
        # Verify dimensions
        assert stitched_height == height * 2, "Stitched height should be sum of both frames"
        
        # Sample pixels from top half (cam0 region)
        top_center_y = height // 2
        top_pixel = stitched.getpixel((stitched_width // 2, top_center_y))
        
        # Sample pixels from bottom half (cam1 region)
        bottom_center_y = height + (height // 2)
        bottom_pixel = stitched.getpixel((stitched_width // 2, bottom_center_y))
        
        # Verify cam0 is on top and cam1 is on bottom
        assert top_pixel == cam0_color, f"Top half should contain cam0 color {cam0_color}, got {top_pixel}"
        assert bottom_pixel == cam1_color, f"Bottom half should contain cam1 color {cam1_color}, got {bottom_pixel}"
        
        # Clean up
        stitched.close()
        cam0_img.close()
        cam1_img.close()



# Feature: video-frame-stitcher, Property 9: Frame Pair Matching
@settings(max_examples=100)
@given(
    cam0_frame_numbers=st.lists(st.integers(1, 1000), min_size=1, max_size=20, unique=True),
    cam1_frame_numbers=st.lists(st.integers(1, 1000), min_size=1, max_size=20, unique=True)
)
def test_property_frame_pair_matching(cam0_frame_numbers, cam1_frame_numbers):
    """
    **Property 9: Frame Pair Matching**
    **Validates: Requirements 4.2**
    
    For any set of extracted frames from cam0 and cam1, only frames with matching 
    global frame numbers should be stitched together.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock extracted frames
        cam0_frames = []
        cam1_frames = []
        
        # Create cam0 frames
        for frame_num in cam0_frame_numbers:
            frame_path = tmpdir / f"cam0_frame_{frame_num:04d}.png"
            img = Image.new('RGB', (100, 100), color='red')
            img.save(frame_path)
            img.close()
            cam0_frames.append(ExtractedFrame(
                global_frame_number=frame_num,
                camera_id='cam0',
                file_path=frame_path
            ))
        
        # Create cam1 frames
        for frame_num in cam1_frame_numbers:
            frame_path = tmpdir / f"cam1_frame_{frame_num:04d}.png"
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(frame_path)
            img.close()
            cam1_frames.append(ExtractedFrame(
                global_frame_number=frame_num,
                camera_id='cam1',
                file_path=frame_path
            ))
        
        # Find frame pairs
        stitcher = FrameStitcher('png')
        pairs = stitcher.find_frame_pairs(cam0_frames, cam1_frames)
        
        # Calculate expected matching frame numbers
        expected_matches = set(cam0_frame_numbers) & set(cam1_frame_numbers)
        
        # Verify that only matching frames are paired
        assert len(pairs) == len(expected_matches), \
            f"Expected {len(expected_matches)} pairs, got {len(pairs)}"
        
        # Verify all pairs have matching frame numbers
        for cam0_frame, cam1_frame in pairs:
            assert cam0_frame.global_frame_number == cam1_frame.global_frame_number, \
                "Frame pair should have matching global frame numbers"
            assert cam0_frame.global_frame_number in expected_matches, \
                "Paired frame number should be in expected matches"
        
        # Verify all expected matches are present
        paired_frame_numbers = {cam0.global_frame_number for cam0, cam1 in pairs}
        assert paired_frame_numbers == expected_matches, \
            "All and only matching frame numbers should be paired"



# Feature: video-frame-stitcher, Property 10: Width Mismatch Handling
@settings(max_examples=100)
@given(
    cam0_width=st.integers(100, 500),
    cam1_width=st.integers(100, 500),
    height=st.integers(100, 300)
)
def test_property_width_mismatch_handling(cam0_width, cam1_width, height):
    """
    **Property 10: Width Mismatch Handling**
    **Validates: Requirements 4.5**
    
    For any pair of frames with different widths W1 and W2, the stitched output 
    width should equal max(W1, W2), and the narrower frame should be centered 
    horizontally.
    """
    # Skip if widths are equal (not testing mismatch case)
    if cam0_width == cam1_width:
        return
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test images with different widths and distinct colors
        cam0_color = (255, 0, 0)  # Red
        cam1_color = (0, 0, 255)  # Blue
        
        cam0_img = Image.new('RGB', (cam0_width, height), color=cam0_color)
        cam1_img = Image.new('RGB', (cam1_width, height), color=cam1_color)
        
        cam0_path = tmpdir / "cam0_frame.png"
        cam1_path = tmpdir / "cam1_frame.png"
        output_path = tmpdir / "stitched.png"
        
        cam0_img.save(cam0_path)
        cam1_img.save(cam1_path)
        
        # Stitch the frames
        stitcher = FrameStitcher('png')
        stitcher.stitch_pair(cam0_path, cam1_path, output_path)
        
        # Load stitched image
        stitched = Image.open(output_path)
        stitched_width, stitched_height = stitched.size
        
        # Verify output width equals max of input widths
        expected_width = max(cam0_width, cam1_width)
        assert stitched_width == expected_width, \
            f"Stitched width should be {expected_width}, got {stitched_width}"
        
        # Verify output height is sum of input heights
        assert stitched_height == height * 2, \
            f"Stitched height should be {height * 2}, got {stitched_height}"
        
        # Verify narrower frame is centered
        # Check the center pixel of each frame region
        center_y_cam0 = height // 2
        center_y_cam1 = height + (height // 2)
        center_x = stitched_width // 2
        
        # Center pixels should have the correct colors
        cam0_center_pixel = stitched.getpixel((center_x, center_y_cam0))
        cam1_center_pixel = stitched.getpixel((center_x, center_y_cam1))
        
        assert cam0_center_pixel == cam0_color, \
            f"Cam0 center should be {cam0_color}, got {cam0_center_pixel}"
        assert cam1_center_pixel == cam1_color, \
            f"Cam1 center should be {cam1_color}, got {cam1_center_pixel}"
        
        # If cam0 is narrower, check that edges have white background
        if cam0_width < cam1_width:
            left_edge_pixel = stitched.getpixel((0, center_y_cam0))
            right_edge_pixel = stitched.getpixel((stitched_width - 1, center_y_cam0))
            white = (255, 255, 255)
            assert left_edge_pixel == white or right_edge_pixel == white, \
                "Narrower cam0 frame should have white background on edges"
        
        # If cam1 is narrower, check that edges have white background
        if cam1_width < cam0_width:
            left_edge_pixel = stitched.getpixel((0, center_y_cam1))
            right_edge_pixel = stitched.getpixel((stitched_width - 1, center_y_cam1))
            white = (255, 255, 255)
            assert left_edge_pixel == white or right_edge_pixel == white, \
                "Narrower cam1 frame should have white background on edges"
        
        # Clean up
        stitched.close()
        cam0_img.close()
        cam1_img.close()



# Feature: video-frame-stitcher, Property 11: Image Quality Preservation
@settings(max_examples=100, deadline=None)
@given(
    width=st.integers(100, 400),
    height=st.integers(100, 300),
    output_format=st.sampled_from(['png', 'jpg'])
)
def test_property_image_quality_preservation(width, height, output_format):
    """
    **Property 11: Image Quality Preservation**
    **Validates: Requirements 4.6**
    
    For any frame that undergoes extraction and stitching, the output image should 
    maintain the same color depth and should not introduce compression artifacts 
    beyond those specified by the output format.
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test images with specific patterns to detect quality loss
        # Use a gradient pattern to detect compression artifacts
        cam0_img = Image.new('RGB', (width, height))
        cam1_img = Image.new('RGB', (width, height))
        
        # Create gradient patterns
        for y in range(height):
            for x in range(width):
                # Cam0: Red gradient
                r = int((x / width) * 255)
                cam0_img.putpixel((x, y), (r, 0, 0))
                
                # Cam1: Blue gradient
                b = int((x / width) * 255)
                cam1_img.putpixel((x, y), (0, 0, b))
        
        cam0_path = tmpdir / "cam0_frame.png"
        cam1_path = tmpdir / "cam1_frame.png"
        output_path = tmpdir / f"stitched.{output_format}"
        
        # Save with high quality to preserve original
        cam0_img.save(cam0_path, 'PNG')
        cam1_img.save(cam1_path, 'PNG')
        
        # Stitch the frames
        stitcher = FrameStitcher(output_format)
        stitcher.stitch_pair(cam0_path, cam1_path, output_path)
        
        # Load stitched image
        stitched = Image.open(output_path)
        
        # Verify color mode (should be RGB)
        assert stitched.mode == 'RGB', \
            f"Output should be RGB mode, got {stitched.mode}"
        
        # Verify dimensions
        assert stitched.size == (width, height * 2), \
            f"Output dimensions should be ({width}, {height * 2}), got {stitched.size}"
        
        # Sample some pixels from the stitched image and verify they're reasonable
        # For PNG, we expect exact or very close matches
        # For JPEG, we allow some tolerance due to compression
        
        tolerance = 5 if output_format == 'jpg' else 2
        
        # Check cam0 region (top half)
        cam0_sample_y = height // 2
        for x in [width // 4, width // 2, 3 * width // 4]:
            if x < width:
                expected_r = int((x / width) * 255)
                actual_pixel = stitched.getpixel((x, cam0_sample_y))
                actual_r = actual_pixel[0]
                
                # Allow some tolerance for compression
                assert abs(actual_r - expected_r) <= tolerance, \
                    f"Cam0 red channel at x={x} should be ~{expected_r}, got {actual_r}"
                
                # Green and blue should be close to 0
                assert actual_pixel[1] <= tolerance, \
                    f"Cam0 green channel should be ~0, got {actual_pixel[1]}"
                assert actual_pixel[2] <= tolerance, \
                    f"Cam0 blue channel should be ~0, got {actual_pixel[2]}"
        
        # Check cam1 region (bottom half)
        cam1_sample_y = height + (height // 2)
        for x in [width // 4, width // 2, 3 * width // 4]:
            if x < width:
                expected_b = int((x / width) * 255)
                actual_pixel = stitched.getpixel((x, cam1_sample_y))
                actual_b = actual_pixel[2]
                
                # Allow some tolerance for compression
                assert abs(actual_b - expected_b) <= tolerance, \
                    f"Cam1 blue channel at x={x} should be ~{expected_b}, got {actual_b}"
                
                # Red and green should be close to 0
                assert actual_pixel[0] <= tolerance, \
                    f"Cam1 red channel should be ~0, got {actual_pixel[0]}"
                assert actual_pixel[1] <= tolerance, \
                    f"Cam1 green channel should be ~0, got {actual_pixel[1]}"
        
        # Clean up
        stitched.close()
        cam0_img.close()
        cam1_img.close()



# ============================================================================
# Unit Tests
# ============================================================================

def test_stitch_two_frames_identical_dimensions():
    """Test stitching two frames with identical dimensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create two test images with same dimensions
        width, height = 200, 150
        cam0_img = Image.new('RGB', (width, height), color=(255, 0, 0))  # Red
        cam1_img = Image.new('RGB', (width, height), color=(0, 0, 255))  # Blue
        
        cam0_path = tmpdir / "cam0.png"
        cam1_path = tmpdir / "cam1.png"
        output_path = tmpdir / "stitched.png"
        
        cam0_img.save(cam0_path)
        cam1_img.save(cam1_path)
        
        # Stitch frames
        stitcher = FrameStitcher('png')
        stitcher.stitch_pair(cam0_path, cam1_path, output_path)
        
        # Verify output exists
        assert output_path.exists(), "Stitched image should be created"
        
        # Load and verify stitched image
        stitched = Image.open(output_path)
        assert stitched.size == (width, height * 2), \
            f"Expected size ({width}, {height * 2}), got {stitched.size}"
        
        # Verify colors in top and bottom halves
        top_pixel = stitched.getpixel((width // 2, height // 2))
        bottom_pixel = stitched.getpixel((width // 2, height + height // 2))
        
        assert top_pixel == (255, 0, 0), "Top half should be red (cam0)"
        assert bottom_pixel == (0, 0, 255), "Bottom half should be blue (cam1)"
        
        stitched.close()
        cam0_img.close()
        cam1_img.close()


def test_stitch_frames_different_widths():
    """Test stitching frames with different widths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create two test images with different widths
        cam0_width, cam0_height = 300, 150
        cam1_width, cam1_height = 200, 150
        
        cam0_img = Image.new('RGB', (cam0_width, cam0_height), color=(255, 0, 0))
        cam1_img = Image.new('RGB', (cam1_width, cam1_height), color=(0, 0, 255))
        
        cam0_path = tmpdir / "cam0.png"
        cam1_path = tmpdir / "cam1.png"
        output_path = tmpdir / "stitched.png"
        
        cam0_img.save(cam0_path)
        cam1_img.save(cam1_path)
        
        # Stitch frames
        stitcher = FrameStitcher('png')
        stitcher.stitch_pair(cam0_path, cam1_path, output_path)
        
        # Verify output
        stitched = Image.open(output_path)
        
        # Width should be max of the two
        expected_width = max(cam0_width, cam1_width)
        expected_height = cam0_height + cam1_height
        
        assert stitched.size == (expected_width, expected_height), \
            f"Expected size ({expected_width}, {expected_height}), got {stitched.size}"
        
        # Verify cam0 (wider) fills the top
        top_left = stitched.getpixel((0, cam0_height // 2))
        assert top_left == (255, 0, 0), "Top left should be red (cam0)"
        
        # Verify cam1 (narrower) is centered in bottom with white edges
        bottom_center = stitched.getpixel((expected_width // 2, cam0_height + cam1_height // 2))
        assert bottom_center == (0, 0, 255), "Bottom center should be blue (cam1)"
        
        # Check white background on edges of narrower frame
        bottom_left = stitched.getpixel((0, cam0_height + cam1_height // 2))
        assert bottom_left == (255, 255, 255), "Bottom left should be white (background)"
        
        stitched.close()
        cam0_img.close()
        cam1_img.close()


def test_find_frame_pairs_matching():
    """Test finding matching frame pairs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock frames
        cam0_frames = [
            ExtractedFrame(1, 'cam0', tmpdir / 'cam0_0001.png'),
            ExtractedFrame(101, 'cam0', tmpdir / 'cam0_0101.png'),
            ExtractedFrame(201, 'cam0', tmpdir / 'cam0_0201.png'),
        ]
        
        cam1_frames = [
            ExtractedFrame(1, 'cam1', tmpdir / 'cam1_0001.png'),
            ExtractedFrame(101, 'cam1', tmpdir / 'cam1_0101.png'),
            ExtractedFrame(301, 'cam1', tmpdir / 'cam1_0301.png'),  # No match
        ]
        
        stitcher = FrameStitcher('png')
        pairs = stitcher.find_frame_pairs(cam0_frames, cam1_frames)
        
        # Should find 2 matching pairs (1 and 101)
        assert len(pairs) == 2, f"Expected 2 pairs, got {len(pairs)}"
        
        # Verify pairs
        assert pairs[0][0].global_frame_number == 1
        assert pairs[0][1].global_frame_number == 1
        assert pairs[1][0].global_frame_number == 101
        assert pairs[1][1].global_frame_number == 101


def test_find_frame_pairs_no_matches():
    """Test finding frame pairs when there are no matches (edge case)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create mock frames with no overlapping frame numbers
        cam0_frames = [
            ExtractedFrame(1, 'cam0', tmpdir / 'cam0_0001.png'),
            ExtractedFrame(101, 'cam0', tmpdir / 'cam0_0101.png'),
        ]
        
        cam1_frames = [
            ExtractedFrame(201, 'cam1', tmpdir / 'cam1_0201.png'),
            ExtractedFrame(301, 'cam1', tmpdir / 'cam1_0301.png'),
        ]
        
        stitcher = FrameStitcher('png')
        pairs = stitcher.find_frame_pairs(cam0_frames, cam1_frames)
        
        # Should find no matching pairs
        assert len(pairs) == 0, f"Expected 0 pairs, got {len(pairs)}"


def test_stitch_frames_end_to_end():
    """Test the complete stitch_frames workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create actual image files
        cam0_frames = []
        cam1_frames = []
        
        for frame_num in [1, 101, 201]:
            # Create cam0 frame
            cam0_path = tmpdir / f"cam0_{frame_num:04d}.png"
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            img.save(cam0_path)
            img.close()
            cam0_frames.append(ExtractedFrame(frame_num, 'cam0', cam0_path))
            
            # Create cam1 frame
            cam1_path = tmpdir / f"cam1_{frame_num:04d}.png"
            img = Image.new('RGB', (100, 100), color=(0, 0, 255))
            img.save(cam1_path)
            img.close()
            cam1_frames.append(ExtractedFrame(frame_num, 'cam1', cam1_path))
        
        # Create output directory
        output_dir = tmpdir / "stitched"
        
        # Stitch frames
        stitcher = FrameStitcher('png')
        stitched_frames = stitcher.stitch_frames(cam0_frames, cam1_frames, output_dir)
        
        # Verify results
        assert len(stitched_frames) == 3, f"Expected 3 stitched frames, got {len(stitched_frames)}"
        
        # Verify all output files exist
        for stitched in stitched_frames:
            assert stitched.file_path.exists(), f"Stitched frame {stitched.file_path} should exist"
            
            # Verify it's a valid image
            img = Image.open(stitched.file_path)
            assert img.size == (100, 200), "Stitched image should be 100x200"
            img.close()


def test_invalid_output_format():
    """Test that invalid output format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid output format"):
        FrameStitcher('bmp')
