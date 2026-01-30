# Requirements Document

## Introduction

This document specifies the requirements for a Python application that processes segmented stereo camera videos from two cameras (cam0 and cam1). The system extracts frames at regular intervals from video segments, maintains continuous frame numbering across segments, and vertically stitches corresponding frames from both cameras into unified output images.

## Glossary

- **System**: The video frame extraction and stitching application
- **Video_Segment**: A single video file representing a portion of a continuous recording
- **Frame_Extractor**: Component responsible for extracting frames from video files
- **Frame_Stitcher**: Component responsible for vertically combining frames from two cameras
- **Global_Frame_Number**: Continuous frame numbering across all video segments
- **Sampling_Interval**: The number of frames between each extracted frame (default: 100)
- **Stereo_Pair**: Corresponding frames from cam0 and cam1 at the same global frame number

## Requirements

### Requirement 1: Video Segment Discovery and Processing

**User Story:** As a user, I want the system to automatically discover and process all video segments from both cameras, so that I don't need to manually specify each file.

#### Acceptance Criteria

1. WHEN the System starts, THE System SHALL scan the input directory for video files matching the camera naming patterns
2. WHEN video files are discovered, THE System SHALL group them by camera identifier (cam0, cam1) and sort them by segment number
3. WHEN processing video segments, THE System SHALL process them in sequential order by segment number
4. IF a video segment exists for one camera but not the other at the same segment number, THEN THE System SHALL log a warning and continue processing available segments
5. THE System SHALL support MP4 and AVI video formats

### Requirement 2: Frame Extraction with Sampling

**User Story:** As a user, I want to extract frames at regular intervals from video segments, so that I can reduce storage requirements while capturing representative frames.

#### Acceptance Criteria

1. WHEN extracting frames from a video segment, THE Frame_Extractor SHALL extract frames at positions determined by the sampling interval (frame 1, 101, 201, etc.)
2. WHEN the sampling interval is configured, THE System SHALL use that value to determine which frames to extract
3. WHEN a frame is extracted, THE Frame_Extractor SHALL save it to the intermediate directory maintaining camera separation (cam0/cam1 subdirectories)
4. WHEN saving extracted frames, THE Frame_Extractor SHALL use the global frame number in the filename
5. THE Frame_Extractor SHALL preserve the original frame resolution and quality during extraction

### Requirement 3: Cross-Segment Frame Numbering

**User Story:** As a user, I want frame numbers to be continuous across all video segments, so that the output reflects the true temporal sequence of the recording.

#### Acceptance Criteria

1. WHEN processing the first video segment, THE System SHALL start global frame numbering at frame 1
2. WHEN transitioning to a new video segment, THE System SHALL continue global frame numbering from where the previous segment ended
3. WHEN calculating global frame numbers, THE System SHALL account for the total frame count of all previously processed segments
4. WHEN saving extracted frames, THE System SHALL use the global frame number in the filename format (e.g., frame_0001.png, frame_0101.png)
5. THE System SHALL maintain a running count of total frames processed across all segments

### Requirement 4: Frame Stitching

**User Story:** As a user, I want corresponding frames from both cameras to be vertically stitched together, so that I can view synchronized stereo imagery in a single image.

#### Acceptance Criteria

1. WHEN stitching frames, THE Frame_Stitcher SHALL place the cam0 frame on top and the cam1 frame on bottom
2. WHEN corresponding frames exist for both cameras at the same global frame number, THE Frame_Stitcher SHALL combine them into a single output image
3. IF a frame exists for one camera but not the other at a given global frame number, THEN THE Frame_Stitcher SHALL skip that frame and log a warning
4. WHEN saving stitched frames, THE Frame_Stitcher SHALL use the global frame number in the filename
5. WHEN frames have different widths, THE Frame_Stitcher SHALL handle the width mismatch by using the maximum width and centering narrower frames
6. THE Frame_Stitcher SHALL preserve image quality during the stitching process

### Requirement 5: Configuration Management

**User Story:** As a user, I want to configure the system through a configuration file, so that I can easily adjust settings without modifying code.

#### Acceptance Criteria

1. WHEN the System starts, THE System SHALL load configuration from a configuration file
2. THE System SHALL support configuration of input directory path, output directory paths, sampling interval, output image format, and camera naming patterns
3. IF the configuration file is missing, THEN THE System SHALL create a default configuration file with sensible defaults
4. IF a configuration value is invalid, THEN THE System SHALL log an error and use the default value for that setting
5. WHERE the output image format is configurable, THE System SHALL support PNG and JPEG formats

### Requirement 6: Progress Reporting

**User Story:** As a user, I want to see real-time progress information during processing, so that I can monitor the system's status and estimate completion time.

#### Acceptance Criteria

1. WHEN processing begins, THE System SHALL display the total number of video segments to be processed
2. WHILE processing a video segment, THE System SHALL display the current segment being processed and the camera identifier
3. WHEN frames are extracted, THE System SHALL periodically update the count of frames extracted
4. WHEN stitching frames, THE System SHALL display the count of frames stitched
5. WHEN processing completes, THE System SHALL display a summary including total frames extracted and total frames stitched

### Requirement 7: Error Handling and Validation

**User Story:** As a user, I want the system to handle errors gracefully and provide clear error messages, so that I can understand and resolve issues.

#### Acceptance Criteria

1. IF the input directory does not exist, THEN THE System SHALL display an error message and terminate
2. IF no video files are found in the input directory, THEN THE System SHALL display an error message and terminate
3. IF a video file cannot be opened, THEN THE System SHALL log an error and skip that video segment
4. IF frame extraction fails for a specific frame, THEN THE System SHALL log the error and continue with the next frame
5. IF output directories cannot be created, THEN THE System SHALL display an error message and terminate
6. WHEN errors occur, THE System SHALL provide descriptive error messages including the file or operation that failed

### Requirement 8: Output Organization

**User Story:** As a user, I want extracted and stitched frames to be organized in a clear directory structure, so that I can easily locate and use the output files.

#### Acceptance Criteria

1. THE System SHALL create an intermediate directory structure with subdirectories for cam0 and cam1 extracted frames
2. THE System SHALL create an output directory for stitched frames
3. WHEN output directories do not exist, THE System SHALL create them automatically
4. WHEN saving files, THE System SHALL use zero-padded frame numbers in filenames to ensure proper sorting (e.g., frame_0001.png)
5. THE System SHALL organize all final stitched frames in a single output directory with sequential global frame numbers

### Requirement 9: Frame Count Validation

**User Story:** As a user, I want the system to validate that cam0 and cam1 have similar total frame counts before extraction, so that I can detect synchronization issues early and decide whether to proceed.

#### Acceptance Criteria

1. WHEN video segments are discovered, THE System SHALL calculate the total frame count for cam0 and cam1 by summing frames across all segments
2. WHEN total frame counts are calculated, THE System SHALL compute the absolute difference between cam0 and cam1 frame counts
3. IF the frame count difference exceeds a configurable threshold percentage (default: 5%), THEN THE System SHALL display a warning message showing both frame counts and the difference
4. WHEN a frame count difference warning is displayed, THE System SHALL prompt the user to confirm whether to continue processing
5. IF the user chooses not to continue, THEN THE System SHALL terminate gracefully without processing
6. IF the user chooses to continue OR the frame count difference is within the threshold, THEN THE System SHALL proceed with frame extraction
7. THE System SHALL support configuration of the frame count difference threshold percentage

### Requirement 10: Frame Number Overlay

**User Story:** As a user, I want each extracted frame to display its global frame number as a visual overlay, so that I can easily identify which frame I'm viewing without checking the filename.

#### Acceptance Criteria

1. WHEN a frame is extracted, THE System SHALL overlay the global frame number as text on the frame image
2. THE frame number overlay SHALL be positioned in a configurable location (default: top-left corner)
3. THE frame number overlay SHALL use a configurable font size (default: 32 pixels)
4. THE frame number overlay SHALL use a contrasting color (white text with black outline) to ensure visibility on any background
5. THE frame number overlay SHALL display the format "Frame: XXXXX" where XXXXX is the zero-padded global frame number
6. THE System SHALL support configuration to enable or disable the frame number overlay (default: enabled)
7. THE frame number overlay SHALL be applied to both extracted frames (cam0/cam1) and stitched frames

### Requirement 11: Streaming Pipeline with Progress Bar

**User Story:** As a user, I want the system to stitch frames as soon as they are extracted (streaming pipeline) and show a detailed progress bar, so that processing is faster and I can see real-time completion percentage.

#### Acceptance Criteria

1. WHEN frame extraction begins, THE System SHALL use a producer-consumer pattern where extraction and stitching happen concurrently
2. WHEN a matching pair of frames (cam0 and cam1 with same global frame number) is extracted, THE System SHALL immediately queue them for stitching without waiting for all extractions to complete
3. THE System SHALL use a thread-safe queue to pass extracted frame pairs from the extraction threads to the stitching thread
4. WHEN displaying progress, THE System SHALL show a visual progress bar with percentage completion for both extraction and stitching phases
5. THE progress bar SHALL update in real-time as frames are processed
6. THE System SHALL ensure frame number correspondence - only frames with matching global frame numbers from both cameras SHALL be stitched
7. WHEN extraction completes, THE System SHALL signal the stitching thread to finish processing remaining queued frames
8. THE System SHALL display separate progress indicators for: cam0 extraction, cam1 extraction, and frame stitching
9. THE progress display SHALL show current/total counts and percentage for each operation
