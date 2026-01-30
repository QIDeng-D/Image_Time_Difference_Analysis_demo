# Video Frame Stitcher

A Python application that processes segmented stereo camera videos, extracts frames at configurable intervals, and vertically stitches corresponding frames from two cameras into unified output images.

## Features

- **Automatic Video Discovery**: Scans input directory for video files matching camera naming patterns
- **Parallel Frame Extraction**: Simultaneously extracts frames from cam0 and cam1 for maximum efficiency ⚡
- **Configurable Frame Sampling**: Extract frames at regular intervals (e.g., every 100th frame)
- **Cross-Segment Frame Numbering**: Maintains continuous frame numbering across all video segments
- **Vertical Frame Stitching**: Combines corresponding frames from both cameras (cam0 on top, cam1 on bottom)
- **Width Mismatch Handling**: Automatically handles frames with different widths by centering
- **Real-time Progress Reporting**: Displays progress information during processing
- **Comprehensive Error Handling**: Graceful error handling with clear error messages
- **Flexible Configuration**: YAML-based configuration for easy customization

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

1. **Prepare your video files**: Place your stereo camera video segments in an input directory. Videos should follow the naming pattern:
   - Camera 0: `stereo_cam0_sbs_0001.mp4`, `stereo_cam0_sbs_0002.mp4`, etc.
   - Camera 1: `stereo_cam1_sbs_0001.mp4`, `stereo_cam1_sbs_0002.mp4`, etc.

2. **Run the application**:
   ```bash
   python -m src.main
   ```

   This will use the default `config.yaml` file. If it doesn't exist, a default configuration will be created.

3. **Check the output**: Stitched frames will be saved in the output directory specified in the configuration.

### Using a Custom Configuration File

```bash
python -m src.main --config my_config.yaml
```

### Command-Line Options

```bash
python -m src.main --help
```

Options:
- `--config`, `-c`: Path to configuration file (default: config.yaml)
- `--version`, `-v`: Display version information
- `--help`, `-h`: Show help message

## Configuration

The application uses a YAML configuration file. Here's an example with all available options:

```yaml
# Directory containing input video segments
input_dir: "./segments"

# Directory for stitched output frames
output_dir: "./stitched_frames"

# Directory for intermediate extracted frames
extracted_frames_dir: "./extracted_frames"

# Number of frames between each extracted frame (e.g., 100 means extract every 100th frame)
sampling_interval: 100

# Output image format: 'png' or 'jpg'
output_format: "png"

# Glob pattern for camera 0 video files
cam0_pattern: "stereo_cam0_sbs_*.mp4"

# Glob pattern for camera 1 video files
cam1_pattern: "stereo_cam1_sbs_*.mp4"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `input_dir` | string | `./segments` | Directory containing input video segments |
| `output_dir` | string | `./stitched_frames` | Directory for stitched output frames |
| `extracted_frames_dir` | string | `./extracted_frames` | Directory for intermediate extracted frames |
| `sampling_interval` | integer | `100` | Number of frames between each extracted frame |
| `output_format` | string | `png` | Output image format (`png` or `jpg`) |
| `cam0_pattern` | string | `stereo_cam0_sbs_*.mp4` | Glob pattern for camera 0 video files |
| `cam1_pattern` | string | `stereo_cam1_sbs_*.mp4` | Glob pattern for camera 1 video files |

## Directory Structure

### Input Structure

```
segments/
├── stereo_cam0_sbs_0001.mp4
├── stereo_cam0_sbs_0002.mp4
├── stereo_cam0_sbs_0003.mp4
├── stereo_cam1_sbs_0001.mp4
├── stereo_cam1_sbs_0002.mp4
└── stereo_cam1_sbs_0003.mp4
```

### Output Structure

```
extracted_frames/
├── cam0/
│   ├── frame_0001.png
│   ├── frame_0101.png
│   └── frame_0201.png
└── cam1/
    ├── frame_0001.png
    ├── frame_0101.png
    └── frame_0201.png

stitched_frames/
├── frame_0001.png
├── frame_0101.png
└── frame_0201.png
```

## How It Works

1. **Video Discovery**: The application scans the input directory for video files matching the configured patterns and groups them by camera.

2. **Parallel Frame Extraction**: Frames from cam0 and cam1 are extracted **simultaneously** using multi-threading for maximum efficiency. Frame numbering is continuous across all video segments.

3. **Frame Stitching**: After both cameras complete extraction, corresponding frames (with matching frame numbers) are vertically stitched together, with cam0 on top and cam1 on bottom.

4. **Output**: Stitched frames are saved to the output directory with zero-padded frame numbers for proper sorting.

### Performance Benefits

With parallel processing, the application can process both cameras simultaneously:
- **Sequential processing**: Time(cam0) + Time(cam1) + Time(stitching)
- **Parallel processing**: max(Time(cam0), Time(cam1)) + Time(stitching)
- **Speed improvement**: Up to **2x faster** for frame extraction! 🚀

## Examples

### Example 1: Extract Every 50th Frame

```yaml
sampling_interval: 50
```

With 3 video segments of 100 frames each (300 total frames), this will extract frames at positions: 1, 51, 101, 151, 201, 251.

### Example 2: Extract Every Frame

```yaml
sampling_interval: 1
```

This will extract every single frame from all video segments.

### Example 3: Custom Camera Patterns

```yaml
cam0_pattern: "camera_left_*.avi"
cam1_pattern: "camera_right_*.avi"
```

This allows you to process videos with different naming conventions.

## Error Handling

The application handles various error conditions gracefully:

- **Missing input directory**: Displays error and terminates
- **No video files found**: Displays error and terminates
- **Corrupted video file**: Logs error and skips the segment
- **Missing segment pairs**: Logs warning and continues with available segments
- **Frame extraction failure**: Logs error and continues with next frame
- **Output directory creation failure**: Displays error and terminates

All errors include descriptive messages indicating the operation that failed and the specific file or resource involved.

## Testing

The project includes comprehensive unit tests, property-based tests, and integration tests.

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -k "not property"

# Property-based tests only
pytest tests/ -k "property"

# Integration tests only
pytest tests/test_integration.py
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

## Supported Video Formats

- MP4 (`.mp4`)
- AVI (`.avi`)

## Requirements

- Python 3.8+
- opencv-python >= 4.5.0
- Pillow >= 9.0.0
- PyYAML >= 6.0
- hypothesis >= 6.0.0 (for testing)
- pytest >= 7.0.0 (for testing)

## Troubleshooting

### Issue: "No video files found"

**Solution**: Check that:
- Your video files are in the correct input directory
- The file naming patterns match the configured `cam0_pattern` and `cam1_pattern`
- The video files have the correct extensions (`.mp4` or `.avi`)

### Issue: "Cannot stitch frames: need frames from both cameras"

**Solution**: Ensure that:
- You have video files for both cameras (cam0 and cam1)
- The video files are not corrupted
- The videos contain frames (not empty)

### Issue: Stitched frames have incorrect dimensions

**Solution**: This is expected behavior when frames have different widths. The application automatically handles width mismatches by centering narrower frames on a background. If this is not desired, ensure your source videos have identical dimensions.

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a pull request.

## Version

Current version: 1.0.0

## Contact

For questions or issues, please open an issue on the project repository.
