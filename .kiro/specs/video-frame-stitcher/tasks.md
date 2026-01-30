# Implementation Plan: Video Frame Stitcher

## Overview

This implementation plan breaks down the video frame stitcher into discrete coding tasks. The approach follows a bottom-up strategy: building core components first, then integrating them into the complete pipeline. Each task builds on previous work and includes validation through tests.

## Tasks

- [x] 1. Set up project structure and configuration management
  - Create project directory structure (src/, tests/, config/)
  - Implement Config dataclass with validation
  - Implement ConfigManager for loading/saving YAML configuration
  - Create default config.yaml template
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 1.1 Write unit tests for configuration management
  - Test loading valid configuration
  - Test handling missing configuration file
  - Test handling invalid configuration values
  - Test default configuration creation
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 2. Implement video discovery component
  - [x] 2.1 Create VideoSegment dataclass
    - Implement dataclass with camera_id, segment_number, file_path, frame_count
    - Implement __lt__ for sorting by segment number
    - _Requirements: 1.2, 1.3_

  - [x] 2.2 Implement VideoDiscovery class
    - Implement discover_videos() to scan directory and match patterns
    - Implement get_frame_count() using OpenCV to read video metadata
    - Implement validate_segment_pairing() to check for missing pairs
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.3 Write property test for video discovery
    - **Property 1: Video Discovery Correctness**
    - **Validates: Requirements 1.1, 1.2**
    - Generate random file lists with matching/non-matching patterns
    - Verify only matching files are returned, grouped by camera, sorted by segment

  - [x] 2.4 Write unit tests for video discovery
    - Test discovery with known directory structure
    - Test handling of missing segment pairs (edge case)
    - Test support for MP4 and AVI formats
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [ ] 3. Implement frame extraction component
  - [x] 3.1 Create ExtractedFrame dataclass
    - Implement dataclass with global_frame_number, camera_id, file_path
    - _Requirements: 2.3, 2.4_

  - [x] 3.2 Implement FrameExtractor class
    - Implement __init__ with sampling_interval and output_format
    - Implement should_extract_frame() to determine sampling pattern
    - Implement save_frame() with proper filename formatting
    - Implement extract_frames() with global frame numbering logic
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Write property test for frame sampling pattern
    - **Property 3: Frame Sampling Pattern**
    - **Validates: Requirements 2.1, 2.2**
    - Generate random sampling intervals and frame counts
    - Verify extracted frame numbers follow pattern: 1, 1+N, 1+2N, ...

  - [x] 3.4 Write property test for global frame numbering
    - **Property 4: Global Frame Numbering Continuity**
    - **Validates: Requirements 3.2, 3.3, 3.5**
    - Generate random segment sequences with varying frame counts
    - Verify global frame numbers are continuous across segments

  - [x] 3.5 Write property test for filename format
    - **Property 5: Filename Format Consistency**
    - **Validates: Requirements 2.4, 3.4, 4.4, 8.4**
    - Generate random frame numbers
    - Verify filenames follow "frame_XXXX.ext" with zero-padding

  - [x] 3.6 Write property test for resolution preservation
    - **Property 7: Frame Resolution Preservation**
    - **Validates: Requirements 2.5**
    - Extract frames from videos with various resolutions
    - Verify extracted frame dimensions match original

  - [x] 3.7 Write unit tests for frame extraction
    - Test extraction from single-frame video (edge case)
    - Test extraction with sampling interval of 1
    - Test directory organization for cam0/cam1 subdirectories
    - _Requirements: 2.1, 2.3, 2.5, 3.1_

- [x] 4. Checkpoint - Ensure frame extraction works correctly
  - Run all frame extraction tests
  - Verify extracted frames are saved with correct naming and organization
  - Ask the user if questions arise

- [ ] 5. Implement frame stitching component
  - [x] 5.1 Create StitchedFrame dataclass
    - Implement dataclass with global_frame_number and file_path
    - _Requirements: 4.2, 4.4_

  - [x] 5.2 Implement FrameStitcher class
    - Implement __init__ with output_format
    - Implement find_frame_pairs() to match frames by global frame number
    - Implement stitch_pair() to vertically combine two images
    - Handle width mismatches by centering narrower frames
    - Implement stitch_frames() to process all frame pairs
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 5.3 Write property test for vertical stitching order
    - **Property 8: Vertical Stitching Order**
    - **Validates: Requirements 4.1**
    - Generate random frame pairs
    - Verify top half contains cam0, bottom half contains cam1

  - [x] 5.4 Write property test for frame pair matching
    - **Property 9: Frame Pair Matching**
    - **Validates: Requirements 4.2**
    - Generate random sets of extracted frames with various global frame numbers
    - Verify only frames with matching numbers are stitched

  - [x] 5.5 Write property test for width mismatch handling
    - **Property 10: Width Mismatch Handling**
    - **Validates: Requirements 4.5**
    - Generate random frame pairs with different widths
    - Verify output width equals max(W1, W2) and narrower frame is centered

  - [x] 5.6 Write property test for image quality preservation
    - **Property 11: Image Quality Preservation**
    - **Validates: Requirements 4.6**
    - Extract and stitch frames
    - Verify color depth is maintained and no unexpected artifacts

  - [x] 5.7 Write unit tests for frame stitching
    - Test stitching two frames with identical dimensions
    - Test stitching frames with different widths
    - Test handling missing frame pairs (edge case)
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [ ] 6. Implement progress reporting component
  - [x] 6.1 Create ProgressReporter class
    - Implement start_extraction(), update_extraction(), complete_extraction()
    - Implement start_stitching(), update_stitching(), complete_stitching()
    - Implement report_warning() and report_error()
    - Use clear, formatted console output
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 6.2 Write property test for progress counter accuracy
    - **Property 12: Progress Counter Accuracy**
    - **Validates: Requirements 6.3, 6.4**
    - Run extraction and stitching with random inputs
    - Verify reported counts match actual file counts

  - [x] 6.3 Write unit tests for progress reporting
    - Test progress display during extraction
    - Test progress display during stitching
    - Test summary display at completion
    - _Requirements: 6.1, 6.2, 6.5_

- [ ] 7. Implement error handling and validation
  - [x] 7.1 Add error handling to all components
    - Add input directory validation with clear error messages
    - Add video file opening error handling
    - Add frame extraction error handling
    - Add output directory creation error handling
    - Ensure all error messages include operation and file/resource
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 7.2 Write property test for error message completeness
    - **Property 13: Error Message Completeness**
    - **Validates: Requirements 7.6**
    - Trigger various errors
    - Verify error messages contain operation type and specific resource

  - [x] 7.3 Write unit tests for error handling
    - Test missing input directory (edge case)
    - Test empty input directory (edge case)
    - Test corrupted video file (edge case)
    - Test output directory creation failure (edge case)
    - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ] 8. Implement directory management
  - [x] 8.1 Create directory management utilities
    - Implement function to create output directory structure
    - Implement automatic parent directory creation
    - Add validation for directory paths
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 8.2 Write property test for automatic directory creation
    - **Property 14: Automatic Directory Creation**
    - **Validates: Requirements 8.3**
    - Generate random non-existent paths
    - Verify directories are created before file operations

  - [x] 8.3 Write property test for directory organization
    - **Property 6: Directory Organization**
    - **Validates: Requirements 2.3, 8.1, 8.2, 8.5**
    - Run full pipeline
    - Verify extracted frames in cam0/cam1 subdirectories
    - Verify stitched frames in single output directory

  - [x] 8.4 Write unit tests for directory management
    - Test directory structure creation
    - Test automatic parent directory creation
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 9. Checkpoint - Ensure all components work independently
  - Run all unit and property tests
  - Verify each component handles errors correctly
  - Ask the user if questions arise

- [ ] 10. Integrate components into main pipeline
  - [x] 10.1 Create main application entry point
    - Implement main() function that orchestrates the pipeline
    - Load configuration
    - Discover videos
    - Extract frames from both cameras
    - Stitch corresponding frames
    - Report progress throughout
    - Handle errors gracefully
    - _Requirements: All requirements_

  - [x] 10.2 Add command-line interface
    - Add argument parser for config file path
    - Add --help documentation
    - Add --version flag
    - _Requirements: 5.1_

  - [x] 10.3 Write integration tests
    - Test end-to-end pipeline with sample videos
    - Test pipeline with mismatched segments
    - Test pipeline with various sampling intervals
    - _Requirements: All requirements_

- [ ] 11. Create project documentation and setup
  - [x] 11.1 Create README.md
    - Document installation instructions
    - Document usage examples
    - Document configuration options
    - Include example directory structure

  - [x] 11.2 Create requirements.txt
    - List all dependencies with versions
    - opencv-python, Pillow, PyYAML, hypothesis, pytest

  - [x] 11.3 Create setup.py or pyproject.toml
    - Configure package metadata
    - Define entry points for CLI

- [x] 12. Final checkpoint - End-to-end validation
  - Run complete test suite
  - Test with real video files if available
  - Verify all requirements are met
  - Ask the user if questions arise

- [ ] 13. Implement frame count validation feature
  - [ ] 13.1 Update Config dataclass
    - Add frame_count_threshold field (float, default 5.0)
    - Add validation for threshold range (0-100)
    - Update default configuration template
    - _Requirements: 9.7_

  - [ ] 13.2 Extend VideoDiscovery class
    - Implement calculate_total_frame_counts() to sum frames across all segments
    - Implement validate_frame_count_difference() to check threshold
    - Return tuple of (exceeds_threshold, difference_percent)
    - _Requirements: 9.1, 9.2_

  - [ ] 13.3 Extend ProgressReporter class
    - Implement report_frame_count_validation() to display warning
    - Implement prompt_user_continue() for yes/no confirmation
    - Format output with frame counts and difference percentage
    - _Requirements: 9.3, 9.4_

  - [ ] 13.4 Integrate frame count validation into main pipeline
    - After video discovery, calculate total frame counts
    - Check if difference exceeds threshold
    - If yes, display warning and prompt user
    - If user declines, terminate gracefully
    - If user accepts or within threshold, proceed
    - _Requirements: 9.3, 9.4, 9.5, 9.6_

  - [ ] 13.5 Write property test for frame count validation
    - **Property 15: Frame Count Validation**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    - Generate random segment sets with varying total frame counts
    - Verify validation triggers when difference exceeds threshold
    - Verify validation passes when difference is within threshold

  - [ ] 13.6 Write unit tests for frame count validation
    - Test calculation of total frame counts
    - Test threshold comparison logic
    - Test user prompt functionality
    - Test graceful termination when user declines
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 14. Implement frame number overlay feature
  - [ ] 14.1 Update Config dataclass
    - Add enable_frame_overlay field (bool, default True)
    - Add overlay_font_size field (int, default 32)
    - Add overlay_position field (str, default "top-left")
    - Add validation for overlay_position values
    - Update default configuration template
    - _Requirements: 10.6_

  - [ ] 14.2 Extend FrameExtractor class
    - Update __init__ to accept overlay parameters
    - Implement add_frame_number_overlay() method
    - Use cv2.putText() with white text and black outline
    - Calculate position based on overlay_position config
    - Apply overlay before saving frame
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 14.3 Extend FrameStitcher class
    - Update __init__ to accept overlay parameters
    - Implement add_frame_number_overlay() method
    - Apply overlay to stitched frames
    - Use same text format and styling as FrameExtractor
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.7_

  - [ ] 14.4 Write property test for frame overlay presence
    - **Property 16: Frame Number Overlay Presence**
    - **Validates: Requirements 10.1, 10.5**
    - Extract and stitch frames with overlay enabled
    - Verify output images contain text overlay
    - Use OCR or pixel analysis to detect text presence

  - [ ] 14.5 Write property test for frame overlay position
    - **Property 17: Frame Number Overlay Position**
    - **Validates: Requirements 10.2**
    - Generate frames with different overlay positions
    - Verify text appears in correct corner/position
    - Test all four position options

  - [ ] 14.6 Write property test for frame overlay visibility
    - **Property 18: Frame Number Overlay Visibility**
    - **Validates: Requirements 10.4**
    - Generate frames with various backgrounds (light/dark)
    - Verify text has contrasting outline for visibility
    - Check white text with black outline is present

  - [ ] 14.7 Write unit tests for frame overlay
    - Test overlay with different font sizes
    - Test overlay at different positions
    - Test overlay enable/disable functionality
    - Test overlay text format "Frame: XXXXX"
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 15. Update integration tests for new features
  - [ ] 15.1 Test frame count validation in integration
    - Create test videos with mismatched frame counts
    - Verify validation warning is displayed
    - Test both user acceptance and rejection paths
    - _Requirements: 9.1-9.6_

  - [ ] 15.2 Test frame overlay in integration
    - Run full pipeline with overlay enabled
    - Verify all extracted and stitched frames have overlays
    - Test with overlay disabled
    - Verify frames without overlays when disabled
    - _Requirements: 10.1-10.7_

  - [ ] 15.3 Test combined features
    - Run pipeline with both frame count validation and overlay
    - Verify both features work together correctly
    - Test various configuration combinations

- [ ] 16. Update documentation for new features
  - [ ] 16.1 Update README.md
    - Document frame count validation feature
    - Document frame overlay feature
    - Add new configuration options
    - Include examples and screenshots if possible

  - [ ] 16.2 Update configuration examples
    - Add frame_count_threshold to config.yaml
    - Add enable_frame_overlay to config.yaml
    - Add overlay_font_size to config.yaml
    - Add overlay_position to config.yaml
    - Document all new options

  - [ ] 16.3 Create user guide for new features
    - Explain when frame count validation triggers
    - Explain how to interpret validation warnings
    - Explain frame overlay customization options
    - Provide troubleshooting tips

- [ ] 17. Final validation of new features
  - Run complete test suite including new tests
  - Test with real video files
  - Verify frame count validation works correctly
  - Verify frame overlays are visible and positioned correctly
  - Ask the user if questions arise

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Property tests use Hypothesis library with minimum 100 iterations
- Checkpoints ensure incremental validation and user feedback
- The implementation follows a bottom-up approach: components first, then integration
- Tasks 13-17 implement the new frame count validation and frame overlay features
