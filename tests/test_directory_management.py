"""Tests for directory management utilities."""

import pytest
from pathlib import Path
import tempfile
import shutil
from hypothesis import given, strategies as st, settings

from src.directory_management import (
    create_output_structure,
    ensure_directory_exists,
    setup_extraction_directories,
    setup_stitching_directory,
    validate_directory_writable,
    get_directory_info
)
from src.error_handling import OutputDirectoryError


# Property-based tests

@given(
    depth=st.integers(min_value=1, max_value=5),
    num_parts=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100)
def test_property_automatic_directory_creation(depth, num_parts):
    """Property 14: Automatic Directory Creation
    
    **Validates: Requirements 8.3**
    
    For any configured output path that does not exist, the system should 
    create the directory and all necessary parent directories before 
    attempting to save files.
    """
    # Feature: video-frame-stitcher, Property 14: Automatic Directory Creation
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Generate a random nested path that doesn't exist
        path_parts = [f"dir_{i}" for i in range(num_parts)]
        nested_path = base / Path(*path_parts)
        
        # Verify path doesn't exist initially
        assert not nested_path.exists()
        
        # Call ensure_directory_exists
        ensure_directory_exists(nested_path)
        
        # Verify directory was created
        assert nested_path.exists()
        assert nested_path.is_dir()
        
        # Verify all parent directories were created
        current = nested_path
        for _ in range(num_parts):
            assert current.exists()
            assert current.is_dir()
            current = current.parent


@given(
    num_subdirs=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=100)
def test_property_directory_structure_creation(num_subdirs):
    """Property test for create_output_structure with subdirectories.
    
    Verifies that create_output_structure creates the base directory
    and all specified subdirectories.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "output"
        subdirs = [f"subdir_{i}" for i in range(num_subdirs)]
        
        # Create structure
        create_output_structure(base, subdirs if num_subdirs > 0 else None)
        
        # Verify base directory exists
        assert base.exists()
        assert base.is_dir()
        
        # Verify all subdirectories exist
        for subdir in subdirs:
            subdir_path = base / subdir
            assert subdir_path.exists()
            assert subdir_path.is_dir()


# Unit tests

def test_create_output_structure_basic():
    """Test basic directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "output"
        
        create_output_structure(base)
        
        assert base.exists()
        assert base.is_dir()


def test_create_output_structure_with_subdirs():
    """Test directory creation with subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "output"
        subdirs = ["cam0", "cam1"]
        
        create_output_structure(base, subdirs)
        
        assert base.exists()
        assert (base / "cam0").exists()
        assert (base / "cam1").exists()


def test_create_output_structure_already_exists():
    """Test that existing directories don't cause errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "output"
        base.mkdir()
        
        # Should not raise error
        create_output_structure(base)
        
        assert base.exists()


def test_ensure_directory_exists_creates_parents():
    """Test automatic parent directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir) / "a" / "b" / "c"
        
        ensure_directory_exists(nested)
        
        assert nested.exists()
        assert nested.is_dir()
        assert (Path(tmpdir) / "a").exists()
        assert (Path(tmpdir) / "a" / "b").exists()


def test_ensure_directory_exists_file_conflict():
    """Test error when path exists as file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "file.txt"
        file_path.touch()
        
        with pytest.raises(OutputDirectoryError) as exc_info:
            ensure_directory_exists(file_path)
        
        assert "not a directory" in str(exc_info.value).lower()


def test_setup_extraction_directories():
    """Test extraction directory structure setup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "extracted"
        
        result = setup_extraction_directories(base)
        
        assert result['base'] == base
        assert result['cam0'] == base / 'cam0'
        assert result['cam1'] == base / 'cam1'
        
        assert base.exists()
        assert result['cam0'].exists()
        assert result['cam1'].exists()


def test_setup_stitching_directory():
    """Test stitching directory setup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "stitched"
        
        result = setup_stitching_directory(output)
        
        assert result == output
        assert output.exists()
        assert output.is_dir()


def test_validate_directory_writable():
    """Test directory writability check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        writable_dir = Path(tmpdir)
        
        assert validate_directory_writable(writable_dir) is True


def test_validate_directory_writable_nonexistent():
    """Test writability check on non-existent directory."""
    nonexistent = Path("/nonexistent/path/that/does/not/exist")
    
    assert validate_directory_writable(nonexistent) is False


def test_get_directory_info_exists():
    """Test getting info for existing directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        
        # Create some test files
        (dir_path / "file1.txt").touch()
        (dir_path / "file2.txt").touch()
        (dir_path / "subdir").mkdir()
        
        info = get_directory_info(dir_path)
        
        assert info['exists'] is True
        assert info['is_directory'] is True
        assert info['is_writable'] is True
        assert info['file_count'] == 2  # Only files, not subdirectories


def test_get_directory_info_nonexistent():
    """Test getting info for non-existent directory."""
    nonexistent = Path("/nonexistent/path")
    
    info = get_directory_info(nonexistent)
    
    assert info['exists'] is False
    assert info['is_directory'] is False
    assert info['is_writable'] is False
    assert info['file_count'] == 0


# Property 6: Directory Organization test
@given(
    num_frames=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50, deadline=None)
def test_property_directory_organization(num_frames):
    """Property 6: Directory Organization
    
    **Validates: Requirements 2.3, 8.1, 8.2, 8.5**
    
    For any execution of the system, extracted frames should be organized 
    in subdirectories by camera (cam0/cam1), and all stitched frames should 
    be in a single output directory.
    """
    # Feature: video-frame-stitcher, Property 6: Directory Organization
    
    import numpy as np
    from PIL import Image
    from src.frame_extraction import FrameExtractor, ExtractedFrame
    from src.frame_stitching import FrameStitcher
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Setup directories
        extracted_base = base / "extracted"
        stitched_dir = base / "stitched"
        
        extraction_dirs = setup_extraction_directories(extracted_base)
        setup_stitching_directory(stitched_dir)
        
        # Create some test frames for both cameras
        cam0_frames = []
        cam1_frames = []
        
        for i in range(1, num_frames + 1):
            frame_num = i * 100 + 1  # Simulate sampling pattern
            
            # Create cam0 frame
            img = Image.new('RGB', (100, 100), color='red')
            cam0_path = extraction_dirs['cam0'] / f"frame_{frame_num:04d}.png"
            img.save(cam0_path)
            cam0_frames.append(ExtractedFrame(frame_num, 'cam0', cam0_path))
            
            # Create cam1 frame
            img = Image.new('RGB', (100, 100), color='blue')
            cam1_path = extraction_dirs['cam1'] / f"frame_{frame_num:04d}.png"
            img.save(cam1_path)
            cam1_frames.append(ExtractedFrame(frame_num, 'cam1', cam1_path))
        
        # Verify extracted frames are in camera subdirectories
        for frame in cam0_frames:
            assert frame.file_path.parent == extraction_dirs['cam0']
            assert frame.file_path.exists()
        
        for frame in cam1_frames:
            assert frame.file_path.parent == extraction_dirs['cam1']
            assert frame.file_path.exists()
        
        # Stitch frames
        stitcher = FrameStitcher('png')
        stitched_frames = stitcher.stitch_frames(
            cam0_frames, 
            cam1_frames, 
            stitched_dir,
            lambda x, y: None  # No-op progress callback
        )
        
        # Verify all stitched frames are in single output directory
        for stitched in stitched_frames:
            assert stitched.file_path.parent == stitched_dir
            assert stitched.file_path.exists()
        
        # Verify directory structure
        assert extraction_dirs['cam0'].exists()
        assert extraction_dirs['cam1'].exists()
        assert stitched_dir.exists()
        
        # Verify no stitched frames in extraction directories
        cam0_files = list(extraction_dirs['cam0'].glob('*.png'))
        cam1_files = list(extraction_dirs['cam1'].glob('*.png'))
        stitched_files = list(stitched_dir.glob('*.png'))
        
        assert len(cam0_files) == num_frames
        assert len(cam1_files) == num_frames
        assert len(stitched_files) == num_frames
