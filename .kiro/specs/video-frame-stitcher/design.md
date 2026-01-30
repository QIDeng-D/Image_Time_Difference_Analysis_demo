# Design Document: Video Frame Stitcher

## Overview

The Video Frame Stitcher is a Python application that processes segmented stereo camera videos, extracts frames at configurable intervals, and vertically stitches corresponding frames from two cameras. The system maintains continuous frame numbering across video segments and provides real-time progress reporting.

The application follows a modular architecture with clear separation between video processing, frame extraction, frame stitching, configuration management, and progress reporting. It uses OpenCV for video processing and PIL/Pillow for image manipulation.

## Architecture

The system follows a pipeline architecture with the following main components:

```
┌─────────────────┐
│  Configuration  │
│     Manager     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Video       │
│    Discovery    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│     Frame       │─────▶│    Progress     │
│   Extractor     │      │    Reporter     │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│     Frame       │
│    Stitcher     │
└─────────────────┘
```

### Component Responsibilities

1. **Configuration Manager**: Loads and validates configuration from file, provides default values
2. **Video Discovery**: Scans input directory, groups videos by camera, sorts by segment number
3. **Frame Extractor**: Opens video files, extracts frames at specified intervals, maintains global frame numbering
4. **Frame Stitcher**: Combines corresponding frames from both cameras vertically
5. **Progress Reporter**: Displays real-time progress information to the user

## Components and Interfaces

### 1. Configuration Manager

**Purpose**: Manage application configuration with validation and defaults.

**Interface**:
```python
class Config:
    input_dir: Path
    output_dir: Path
    extracted_frames_dir: Path
    sampling_interval: int
    output_format: str  # 'png' or 'jpg'
    cam0_pattern: str
    cam1_pattern: str
    frame_count_threshold: float  # Maximum allowed frame count difference percentage
    enable_frame_overlay: bool  # Enable frame number overlay
    overlay_font_size: int  # Font size for overlay text
    overlay_position: str  # Position: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
    
class ConfigManager:
    def load_config(config_path: Path) -> Config:
        """Load configuration from YAML file, create default if missing"""
        
    def validate_config(config: Config) -> List[str]:
        """Validate configuration values, return list of errors"""
        
    def create_default_config(config_path: Path) -> None:
        """Create a default configuration file"""
```

**Default Configuration**:
- `input_dir`: "./segments"
- `output_dir`: "./stitched_frames"
- `extracted_frames_dir`: "./extracted_frames"
- `sampling_interval`: 100
- `output_format`: "png"
- `cam0_pattern`: "stereo_cam0_sbs_*.mp4"
- `cam1_pattern`: "stereo_cam1_sbs_*.mp4"
- `frame_count_threshold`: 5.0  # Maximum allowed frame count difference percentage
- `enable_frame_overlay`: true  # Enable frame number overlay on images
- `overlay_font_size`: 32  # Font size for frame number overlay
- `overlay_position`: "top-left"  # Position of frame number overlay

### 2. Video Discovery

**Purpose**: Discover and organize video files by camera and segment.

**Interface**:
```python
@dataclass
class VideoSegment:
    camera_id: str  # 'cam0' or 'cam1'
    segment_number: int
    file_path: Path
    frame_count: int  # Total frames in this segment
    
class VideoDiscovery:
    def discover_videos(input_dir: Path, cam0_pattern: str, cam1_pattern: str) -> Dict[str, List[VideoSegment]]:
        """
        Discover video files and return them grouped by camera.
        Returns: {'cam0': [VideoSegment, ...], 'cam1': [VideoSegment, ...]}
        """
        
    def get_frame_count(video_path: Path) -> int:
        """Get total frame count from a video file"""
        
    def calculate_total_frame_counts(segments: Dict[str, List[VideoSegment]]) -> Dict[str, int]:
        """
        Calculate total frame count for each camera by summing all segments.
        Returns: {'cam0': total_frames, 'cam1': total_frames}
        """
        
    def validate_frame_count_difference(cam0_total: int, cam1_total: int, threshold_percent: float) -> Tuple[bool, float]:
        """
        Check if frame count difference exceeds threshold.
        Returns: (exceeds_threshold, difference_percent)
        """
        
    def validate_segment_pairing(cam0_segments: List[VideoSegment], cam1_segments: List[VideoSegment]) -> List[str]:
        """Check for missing segment pairs, return list of warnings"""
```

### 3. Frame Extractor

**Purpose**: Extract frames from video segments at specified intervals with global frame numbering.

**Interface**:
```python
@dataclass
class ExtractedFrame:
    global_frame_number: int
    camera_id: str
    file_path: Path
    
class FrameExtractor:
    def __init__(self, sampling_interval: int, output_format: str, enable_overlay: bool = True, overlay_font_size: int = 32, overlay_position: str = "top-left"):
        self.sampling_interval = sampling_interval
        self.output_format = output_format
        self.enable_overlay = enable_overlay
        self.overlay_font_size = overlay_font_size
        self.overlay_position = overlay_position
        
    def extract_frames(
        video_segments: List[VideoSegment],
        output_dir: Path,
        camera_id: str,
        progress_callback: Callable[[int, int], None]
    ) -> List[ExtractedFrame]:
        """
        Extract frames from video segments maintaining global frame numbering.
        
        Args:
            video_segments: List of video segments sorted by segment number
            output_dir: Directory to save extracted frames
            camera_id: Camera identifier for subdirectory organization
            progress_callback: Function to report progress (current, total)
            
        Returns:
            List of extracted frame metadata
        """
        
    def should_extract_frame(self, global_frame_number: int) -> bool:
        """Determine if a frame at given global number should be extracted"""
        
    def add_frame_number_overlay(self, frame: np.ndarray, frame_number: int) -> np.ndarray:
        """
        Add frame number overlay to the frame image.
        
        Args:
            frame: Input frame as numpy array
            frame_number: Global frame number to display
            
        Returns:
            Frame with overlay applied
        """
        
    def save_frame(self, frame: np.ndarray, global_frame_number: int, output_dir: Path, camera_id: str) -> Path:
        """Save a frame with proper naming convention"""
```

**Frame Extraction Algorithm**:
1. Initialize global frame counter to 0
2. For each video segment in order:
   - Open video file
   - For each frame in video:
     - Increment global frame counter
     - If global_frame_number matches sampling pattern (1, 101, 201, ...):
       - Extract and save frame with global frame number
   - Close video file
3. Return list of extracted frames

### 4. Frame Stitcher

**Purpose**: Vertically combine corresponding frames from both cameras.

**Interface**:
```python
@dataclass
class StitchedFrame:
    global_frame_number: int
    file_path: Path
    
class FrameStitcher:
    def __init__(self, output_format: str, enable_overlay: bool = True, overlay_font_size: int = 32, overlay_position: str = "top-left"):
        self.output_format = output_format
        self.enable_overlay = enable_overlay
        self.overlay_font_size = overlay_font_size
        self.overlay_position = overlay_position
        
    def stitch_frames(
        cam0_frames: List[ExtractedFrame],
        cam1_frames: List[ExtractedFrame],
        output_dir: Path,
        progress_callback: Callable[[int, int], None]
    ) -> List[StitchedFrame]:
        """
        Stitch corresponding frames from both cameras vertically.
        
        Args:
            cam0_frames: List of extracted frames from cam0
            cam1_frames: List of extracted frames from cam1
            output_dir: Directory to save stitched frames
            progress_callback: Function to report progress
            
        Returns:
            List of stitched frame metadata
        """
        
    def stitch_pair(self, cam0_path: Path, cam1_path: Path, output_path: Path, frame_number: int) -> None:
        """
        Stitch two frames vertically (cam0 on top, cam1 on bottom).
        Handles width mismatches by centering narrower frames.
        Adds frame number overlay if enabled.
        """
        
    def add_frame_number_overlay(self, frame: np.ndarray, frame_number: int) -> np.ndarray:
        """
        Add frame number overlay to the stitched frame image.
        
        Args:
            frame: Input frame as numpy array
            frame_number: Global frame number to display
            
        Returns:
            Frame with overlay applied
        """
        
    def find_frame_pairs(self, cam0_frames: List[ExtractedFrame], cam1_frames: List[ExtractedFrame]) -> List[Tuple[ExtractedFrame, ExtractedFrame]]:
        """Find matching frame pairs by global frame number"""
```

**Stitching Algorithm**:
1. Create a mapping of global frame numbers to frames for both cameras
2. Find intersection of frame numbers (frames that exist in both cameras)
3. For each matching frame number:
   - Load both images
   - Determine maximum width
   - If widths differ, center narrower image on white/black background
   - Vertically concatenate (cam0 top, cam1 bottom)
   - Save stitched image with global frame number

### 5. Progress Reporter

**Purpose**: Provide real-time progress updates to the user.

**Interface**:
```python
class ProgressReporter:
    def start_extraction(self, camera_id: str, total_segments: int) -> None:
        """Report start of extraction phase"""
        
    def update_extraction(self, camera_id: str, segment_number: int, frames_extracted: int) -> None:
        """Update extraction progress"""
        
    def complete_extraction(self, camera_id: str, total_frames: int) -> None:
        """Report completion of extraction phase"""
        
    def report_frame_count_validation(self, cam0_total: int, cam1_total: int, difference_percent: float) -> None:
        """Report frame count validation results"""
        
    def prompt_user_continue(self, message: str) -> bool:
        """
        Prompt user for yes/no confirmation.
        Returns True if user confirms, False otherwise.
        """
        
    def start_stitching(self, total_pairs: int) -> None:
        """Report start of stitching phase"""
        
    def update_stitching(self, frames_stitched: int, total_pairs: int) -> None:
        """Update stitching progress"""
        
    def complete_stitching(self, total_stitched: int) -> None:
        """Report completion of stitching phase"""
        
    def report_warning(self, message: str) -> None:
        """Report a warning message"""
        
    def report_error(self, message: str) -> None:
        """Report an error message"""
```

## Data Models

### Configuration Data Model

```python
@dataclass
class Config:
    """Application configuration"""
    input_dir: Path
    output_dir: Path
    extracted_frames_dir: Path
    sampling_interval: int
    output_format: str
    cam0_pattern: str
    cam1_pattern: str
    frame_count_threshold: float
    enable_frame_overlay: bool
    overlay_font_size: int
    overlay_position: str
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.sampling_interval < 1:
            raise ValueError("sampling_interval must be >= 1")
        if self.output_format not in ['png', 'jpg', 'jpeg']:
            raise ValueError("output_format must be 'png' or 'jpg'")
        if self.frame_count_threshold < 0 or self.frame_count_threshold > 100:
            raise ValueError("frame_count_threshold must be between 0 and 100")
        if self.overlay_position not in ['top-left', 'top-right', 'bottom-left', 'bottom-right']:
            raise ValueError("overlay_position must be one of: top-left, top-right, bottom-left, bottom-right")
```

### Video Segment Data Model

```python
@dataclass
class VideoSegment:
    """Metadata for a single video segment"""
    camera_id: str
    segment_number: int
    file_path: Path
    frame_count: int
    
    def __lt__(self, other):
        """Enable sorting by segment number"""
        return self.segment_number < other.segment_number
```

### Frame Metadata Models

```python
@dataclass
class ExtractedFrame:
    """Metadata for an extracted frame"""
    global_frame_number: int
    camera_id: str
    file_path: Path

@dataclass
class StitchedFrame:
    """Metadata for a stitched frame"""
    global_frame_number: int
    file_path: Path
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing the acceptance criteria, I identified several areas where properties can be consolidated:

**Redundancies Identified:**
1. Properties 2.4 and 3.4 both test filename format with global frame numbers - can be combined
2. Properties 3.3 and 3.5 both test frame counting across segments - 3.3 subsumes 3.5
3. Properties 2.3 and 8.1 both test directory organization for extracted frames - can be combined
4. Properties 4.4 and 8.4 both test zero-padded filenames - can be combined with 2.4/3.4
5. Properties 2.2 is redundant with 2.1 - if frames are extracted at correct positions (2.1), then the sampling interval is being used correctly

**Consolidated Properties:**
- Filename format property will cover all filename requirements (zero-padding, global frame numbers)
- Frame counting property will cover continuous numbering across segments
- Directory organization property will cover both extraction and stitching output structure

### Core Properties

**Property 1: Video Discovery Correctness**
*For any* directory containing video files with various naming patterns, the video discovery process should only return files that match the specified camera patterns, grouped by camera ID, and sorted by segment number in ascending order.
**Validates: Requirements 1.1, 1.2**

**Property 2: Sequential Processing Order**
*For any* list of video segments, when processed by the frame extractor, the segments should be processed in ascending order by segment number.
**Validates: Requirements 1.3**

**Property 3: Frame Sampling Pattern**
*For any* sampling interval N and video with total frames F, the extracted frame numbers should follow the pattern: 1, 1+N, 1+2N, 1+3N, ... up to the largest value ≤ F.
**Validates: Requirements 2.1, 2.2**

**Property 4: Global Frame Numbering Continuity**
*For any* sequence of video segments with frame counts [F1, F2, F3, ...], when extracting frames, the global frame number for frame i in segment j should equal (sum of all frame counts in segments 0 to j-1) + i.
**Validates: Requirements 3.2, 3.3, 3.5**

**Property 5: Filename Format Consistency**
*For any* extracted or stitched frame with global frame number N, the filename should follow the pattern "frame_XXXX.{ext}" where XXXX is N zero-padded to at least 4 digits.
**Validates: Requirements 2.4, 3.4, 4.4, 8.4**

**Property 6: Directory Organization**
*For any* execution of the system, extracted frames should be organized in subdirectories by camera (cam0/cam1), and all stitched frames should be in a single output directory.
**Validates: Requirements 2.3, 8.1, 8.2, 8.5**

**Property 7: Frame Resolution Preservation**
*For any* frame extracted from a video, the extracted frame's dimensions should match the original video's frame dimensions.
**Validates: Requirements 2.5**

**Property 8: Vertical Stitching Order**
*For any* pair of stitched frames, when the output image is divided horizontally at the midpoint, the top half should contain the cam0 frame and the bottom half should contain the cam1 frame.
**Validates: Requirements 4.1**

**Property 9: Frame Pair Matching**
*For any* set of extracted frames from cam0 and cam1, only frames with matching global frame numbers should be stitched together.
**Validates: Requirements 4.2**

**Property 10: Width Mismatch Handling**
*For any* pair of frames with different widths W1 and W2, the stitched output width should equal max(W1, W2), and the narrower frame should be centered horizontally.
**Validates: Requirements 4.5**

**Property 11: Image Quality Preservation**
*For any* frame that undergoes extraction and stitching, the output image should maintain the same color depth and should not introduce compression artifacts beyond those specified by the output format.
**Validates: Requirements 4.6**

**Property 12: Progress Counter Accuracy**
*For any* execution of the system, the reported count of frames extracted should equal the actual number of frame files created, and the reported count of frames stitched should equal the actual number of stitched files created.
**Validates: Requirements 6.3, 6.4**

**Property 13: Error Message Completeness**
*For any* error that occurs during processing, the error message should contain both the type of operation that failed and the specific file or resource involved.
**Validates: Requirements 7.6**

**Property 14: Automatic Directory Creation**
*For any* configured output path that does not exist, the system should create the directory and all necessary parent directories before attempting to save files.
**Validates: Requirements 8.3**

**Property 15: Frame Count Validation**
*For any* two sets of video segments (cam0 and cam1), when the absolute difference in total frame counts exceeds the configured threshold percentage, the system should prompt the user for confirmation before proceeding with extraction.
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

**Property 16: Frame Number Overlay Presence**
*For any* extracted or stitched frame when overlay is enabled, the output image should contain visible text displaying the global frame number in the format "Frame: XXXXX".
**Validates: Requirements 10.1, 10.5**

**Property 17: Frame Number Overlay Position**
*For any* frame with overlay enabled, the frame number text should be positioned according to the configured position (top-left, top-right, bottom-left, or bottom-right).
**Validates: Requirements 10.2**

**Property 18: Frame Number Overlay Visibility**
*For any* frame with overlay enabled, the frame number text should use contrasting colors (white text with black outline or shadow) to ensure readability against any background.
**Validates: Requirements 10.4**

## Error Handling

The system implements comprehensive error handling at multiple levels:

### Input Validation Errors
- **Missing input directory**: Terminate with clear error message
- **No video files found**: Terminate with clear error message
- **Invalid configuration**: Log error, use default value, continue

### Processing Errors
- **Video file cannot be opened**: Log error with filename, skip segment, continue
- **Frame extraction failure**: Log error with frame number, skip frame, continue
- **Missing frame pairs**: Log warning, skip unpaired frames, continue
- **Output directory creation failure**: Terminate with clear error message

### Error Message Format
All error messages should include:
1. Error type/category
2. Specific file or resource involved
3. Suggested action (if applicable)

Example: "ERROR: Failed to open video file 'stereo_cam0_sbs_0003.mp4'. File may be corrupted. Skipping segment 3."

## Testing Strategy

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage.

### Unit Testing Approach

Unit tests focus on:
- **Specific examples**: Test with known video files and expected outputs
- **Edge cases**: Empty directories, single-frame videos, mismatched segments
- **Error conditions**: Missing files, corrupted videos, invalid configurations
- **Integration points**: Configuration loading, directory creation, file I/O

Example unit tests:
- Test configuration loading with valid YAML file
- Test video discovery with known directory structure
- Test frame extraction from a 3-frame video with sampling interval 1
- Test stitching two frames with identical dimensions
- Test error handling when input directory doesn't exist

### Property-Based Testing Approach

Property-based tests verify universal properties across randomized inputs using a Python PBT library (Hypothesis recommended).

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: video-frame-stitcher, Property N: [property text]`

**Test Generators**:
- Random video segment lists with varying segment numbers
- Random frame counts for video segments
- Random sampling intervals (1-1000)
- Random image dimensions
- Random directory structures

Example property tests:
- **Property 1**: Generate random file lists, verify discovery returns only matching patterns
- **Property 3**: Generate random sampling intervals and frame counts, verify extraction pattern
- **Property 4**: Generate random segment sequences, verify global frame numbering
- **Property 5**: Generate random frame numbers, verify filename format
- **Property 8**: Generate random frame pairs, verify stitching order
- **Property 10**: Generate random frame dimensions, verify width handling

### Test Coverage Goals

- **Unit tests**: 80%+ code coverage
- **Property tests**: All 14 correctness properties implemented
- **Integration tests**: End-to-end pipeline with sample videos
- **Error handling**: All error paths tested

### Testing Tools

- **pytest**: Test framework
- **Hypothesis**: Property-based testing library
- **pytest-cov**: Coverage reporting
- **OpenCV**: Video file creation for test fixtures
- **Pillow**: Image comparison and validation

## Implementation Notes

### Dependencies
- **opencv-python**: Video processing and frame extraction
- **Pillow (PIL)**: Image manipulation and stitching
- **PyYAML**: Configuration file parsing
- **pathlib**: Cross-platform path handling
- **hypothesis**: Property-based testing

### Performance Considerations
- Process videos sequentially to manage memory usage
- Release video file handles promptly after processing each segment
- Use efficient image formats (PNG for quality, JPEG for size)
- Consider parallel processing for frame stitching (future enhancement)

### Cross-Platform Compatibility
- Use `pathlib.Path` for all file operations
- Avoid platform-specific path separators
- Test on Windows, macOS, and Linux

### Configuration File Format (YAML)
```yaml
input_dir: "./segments"
output_dir: "./stitched_frames"
extracted_frames_dir: "./extracted_frames"
sampling_interval: 100
output_format: "png"
cam0_pattern: "stereo_cam0_sbs_*.mp4"
cam1_pattern: "stereo_cam1_sbs_*.mp4"
frame_count_threshold: 5.0  # Maximum allowed frame count difference percentage
enable_frame_overlay: true  # Enable frame number overlay on images
overlay_font_size: 32  # Font size for frame number text
overlay_position: "top-left"  # Position: top-left, top-right, bottom-left, bottom-right
```

### Frame Number Overlay Implementation

The frame number overlay feature adds visual text to each frame showing its global frame number. This is implemented using OpenCV's `cv2.putText()` function with the following specifications:

**Text Format**: "Frame: XXXXX" where XXXXX is the zero-padded global frame number

**Visual Style**:
- Font: `cv2.FONT_HERSHEY_SIMPLEX`
- Color: White (255, 255, 255) for main text
- Outline: Black (0, 0, 0) with thickness 2 for contrast
- Font scale: Calculated based on `overlay_font_size` configuration

**Position Calculation**:
- `top-left`: (10, overlay_font_size + 10)
- `top-right`: (width - text_width - 10, overlay_font_size + 10)
- `bottom-left`: (10, height - 10)
- `bottom-right`: (width - text_width - 10, height - 10)

**Implementation Notes**:
- Overlay is applied after frame extraction but before saving
- For stitched frames, overlay is applied to the final stitched image
- Text size is automatically calculated using `cv2.getTextSize()`
- Black outline is drawn first (thicker), then white text on top for maximum contrast

### Frame Count Validation Workflow

The frame count validation feature ensures that cam0 and cam1 have similar total frame counts before extraction begins:

**Validation Steps**:
1. After video discovery, calculate total frames for each camera
2. Compute absolute difference: `|cam0_total - cam1_total|`
3. Calculate difference percentage: `(difference / max(cam0_total, cam1_total)) * 100`
4. If percentage > threshold:
   - Display warning with both frame counts and difference
   - Prompt user: "Frame count difference detected. Continue? (y/n): "
   - If user enters 'n' or 'N', terminate gracefully
   - If user enters 'y' or 'Y', proceed with extraction
5. If percentage <= threshold, proceed automatically

**Example Output**:
```
WARNING: Frame count difference detected!
  cam0 total frames: 15000
  cam1 total frames: 14200
  Difference: 800 frames (5.33%)
  Threshold: 5.00%

This may indicate synchronization issues between cameras.
Continue with frame extraction? (y/n):
```
