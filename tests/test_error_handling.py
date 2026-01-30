"""Unit and property-based tests for error handling components."""

import pytest
from pathlib import Path
import tempfile
import shutil
from hypothesis import given, strategies as st, settings
from src.error_handling import (
    VideoFrameStitcherError,
    InputDirectoryError,
    VideoFileError,
    FrameExtractionError,
    OutputDirectoryError,
    StitchingError,
    validate_input_directory,
    validate_output_directory,
    log_error,
    log_warning
)


class TestCustomExceptions:
    """Test suite for custom exception classes."""
    
    def test_input_directory_error_message(self):
        """Test that InputDirectoryError contains directory and reason."""
        directory = Path("/test/dir")
        reason = "Directory does not exist"
        
        error = InputDirectoryError(directory, reason)
        
        assert str(directory) in str(error)
        assert reason in str(error)
        assert error.directory == directory
        assert error.reason == reason
    
    def test_video_file_error_message(self):
        """Test that VideoFileError contains file path, operation, and reason."""
        file_path = Path("/test/video.mp4")
        operation = "open"
        reason = "File is corrupted"
        
        error = VideoFileError(file_path, operation, reason)
        
        assert str(file_path) in str(error)
        assert operation in str(error)
        assert reason in str(error)
        assert error.file_path == file_path
        assert error.operation == operation
        assert error.reason == reason
    
    def test_frame_extraction_error_message(self):
        """Test that FrameExtractionError contains frame number, file path, and reason."""
        frame_number = 100
        file_path = Path("/test/video.mp4")
        reason = "Frame read failed"
        
        error = FrameExtractionError(frame_number, file_path, reason)
        
        assert str(frame_number) in str(error)
        assert str(file_path) in str(error)
        assert reason in str(error)
        assert error.frame_number == frame_number
        assert error.file_path == file_path
        assert error.reason == reason
    
    def test_output_directory_error_message(self):
        """Test that OutputDirectoryError contains directory, operation, and reason."""
        directory = Path("/test/output")
        operation = "create"
        reason = "Permission denied"
        
        error = OutputDirectoryError(directory, operation, reason)
        
        assert str(directory) in str(error)
        assert operation in str(error)
        assert reason in str(error)
        assert error.directory == directory
        assert error.operation == operation
        assert error.reason == reason
    
    def test_stitching_error_message_with_both_paths(self):
        """Test that StitchingError contains frame number and both file paths."""
        frame_number = 50
        cam0_path = Path("/test/cam0/frame_0050.png")
        cam1_path = Path("/test/cam1/frame_0050.png")
        reason = "Image dimensions mismatch"
        
        error = StitchingError(frame_number, cam0_path, cam1_path, reason)
        
        assert str(frame_number) in str(error)
        assert str(cam0_path) in str(error)
        assert str(cam1_path) in str(error)
        assert reason in str(error)
        assert error.frame_number == frame_number
        assert error.cam0_path == cam0_path
        assert error.cam1_path == cam1_path
        assert error.reason == reason
    
    def test_stitching_error_message_with_missing_paths(self):
        """Test that StitchingError handles missing file paths."""
        frame_number = 50
        reason = "Files not found"
        
        error = StitchingError(frame_number, None, None, reason)
        
        assert str(frame_number) in str(error)
        assert "missing files" in str(error)
        assert reason in str(error)


class TestValidationFunctions:
    """Test suite for validation functions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup after test
        shutil.rmtree(temp_path)
    
    def test_validate_input_directory_success(self, temp_dir):
        """Test that validate_input_directory succeeds for valid directory."""
        # Should not raise any exception
        validate_input_directory(temp_dir)
    
    def test_validate_input_directory_not_exists(self):
        """Test that validate_input_directory raises error for non-existent directory."""
        non_existent = Path("/non/existent/directory")
        
        with pytest.raises(InputDirectoryError, match="Directory does not exist"):
            validate_input_directory(non_existent)
    
    def test_validate_input_directory_not_a_directory(self, temp_dir):
        """Test that validate_input_directory raises error for file path."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test")
        
        with pytest.raises(InputDirectoryError, match="Path is not a directory"):
            validate_input_directory(file_path)
    
    def test_validate_output_directory_creates_directory(self, temp_dir):
        """Test that validate_output_directory creates non-existent directory."""
        new_dir = temp_dir / "new_output"
        
        assert not new_dir.exists()
        
        validate_output_directory(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_validate_output_directory_existing_directory(self, temp_dir):
        """Test that validate_output_directory succeeds for existing directory."""
        # Should not raise any exception
        validate_output_directory(temp_dir)
    
    def test_validate_output_directory_creates_parent_directories(self, temp_dir):
        """Test that validate_output_directory creates parent directories."""
        nested_dir = temp_dir / "parent" / "child" / "output"
        
        assert not nested_dir.exists()
        
        validate_output_directory(nested_dir)
        
        assert nested_dir.exists()
        assert nested_dir.is_dir()


# Property-Based Tests

class TestErrorHandlingProperties:
    """Property-based tests for error handling."""
    
    @settings(deadline=None, max_examples=100)
    @given(
        frame_number=st.integers(min_value=1, max_value=100000),
        operation=st.sampled_from(['open', 'read', 'process', 'extract', 'stitch']),
        error_type=st.sampled_from([
            'InputDirectoryError',
            'VideoFileError',
            'FrameExtractionError',
            'OutputDirectoryError',
            'StitchingError'
        ])
    )
    def test_property_error_message_completeness(self, frame_number, operation, error_type):
        """Property 13: Error Message Completeness
        
        **Validates: Requirements 7.6**
        
        For any error that occurs during processing, the error message should 
        contain both the type of operation that failed and the specific file 
        or resource involved.
        """
        # Create appropriate error based on type
        if error_type == 'InputDirectoryError':
            directory = Path(f"/test/input_{frame_number}")
            reason = f"Test error for {operation}"
            error = InputDirectoryError(directory, reason)
            
            # Verify error message contains operation type (implied by reason)
            assert reason in str(error), \
                f"Error message should contain reason: {reason}"
            
            # Verify error message contains specific resource (directory)
            assert str(directory) in str(error), \
                f"Error message should contain directory: {directory}"
        
        elif error_type == 'VideoFileError':
            file_path = Path(f"/test/video_{frame_number}.mp4")
            reason = "Test error reason"
            error = VideoFileError(file_path, operation, reason)
            
            # Verify error message contains operation type
            assert operation in str(error), \
                f"Error message should contain operation: {operation}"
            
            # Verify error message contains specific resource (file path)
            assert str(file_path) in str(error), \
                f"Error message should contain file path: {file_path}"
            
            # Verify error message contains reason
            assert reason in str(error), \
                f"Error message should contain reason: {reason}"
        
        elif error_type == 'FrameExtractionError':
            file_path = Path(f"/test/video_{frame_number}.mp4")
            reason = "Test extraction error"
            error = FrameExtractionError(frame_number, file_path, reason)
            
            # Verify error message contains operation type (implied by "extract")
            assert "extract" in str(error).lower(), \
                "Error message should indicate extraction operation"
            
            # Verify error message contains specific resource (frame number and file)
            assert str(frame_number) in str(error), \
                f"Error message should contain frame number: {frame_number}"
            assert str(file_path) in str(error), \
                f"Error message should contain file path: {file_path}"
            
            # Verify error message contains reason
            assert reason in str(error), \
                f"Error message should contain reason: {reason}"
        
        elif error_type == 'OutputDirectoryError':
            directory = Path(f"/test/output_{frame_number}")
            reason = "Test output error"
            error = OutputDirectoryError(directory, operation, reason)
            
            # Verify error message contains operation type
            assert operation in str(error), \
                f"Error message should contain operation: {operation}"
            
            # Verify error message contains specific resource (directory)
            assert str(directory) in str(error), \
                f"Error message should contain directory: {directory}"
            
            # Verify error message contains reason
            assert reason in str(error), \
                f"Error message should contain reason: {reason}"
        
        elif error_type == 'StitchingError':
            cam0_path = Path(f"/test/cam0/frame_{frame_number:04d}.png")
            cam1_path = Path(f"/test/cam1/frame_{frame_number:04d}.png")
            reason = "Test stitching error"
            error = StitchingError(frame_number, cam0_path, cam1_path, reason)
            
            # Verify error message contains operation type (implied by "stitch")
            assert "stitch" in str(error).lower(), \
                "Error message should indicate stitching operation"
            
            # Verify error message contains specific resources (frame number and files)
            assert str(frame_number) in str(error), \
                f"Error message should contain frame number: {frame_number}"
            assert str(cam0_path) in str(error) or str(cam1_path) in str(error), \
                "Error message should contain at least one file path"
            
            # Verify error message contains reason
            assert reason in str(error), \
                f"Error message should contain reason: {reason}"
        
        # Verify all errors are instances of VideoFrameStitcherError
        assert isinstance(error, VideoFrameStitcherError), \
            f"All custom errors should inherit from VideoFrameStitcherError"
        
        # Verify error message is not empty
        assert len(str(error)) > 0, \
            "Error message should not be empty"
        
        # Verify error message contains some descriptive text
        assert len(str(error).split()) >= 3, \
            "Error message should contain at least 3 words for clarity"
