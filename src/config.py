"""Configuration management for Video Frame Stitcher."""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml


@dataclass
class Config:
    """Application configuration with validation.
    
    Attributes:
        input_dir: Directory containing input video segments
        output_dir: Directory for stitched output frames
        extracted_frames_dir: Directory for intermediate extracted frames
        sampling_interval: Number of frames between each extracted frame
        output_format: Image format for output files ('png' or 'jpg')
        cam0_pattern: Glob pattern for camera 0 video files
        cam1_pattern: Glob pattern for camera 1 video files
        frame_count_threshold: Maximum allowed frame count difference percentage (0-100)
        enable_frame_overlay: Enable frame number overlay on images
        overlay_font_size: Font size for frame number overlay text
        overlay_position: Position of overlay ('top-left', 'top-right', 'bottom-left', 'bottom-right')
    """
    input_dir: Path
    output_dir: Path
    extracted_frames_dir: Path
    sampling_interval: int
    output_format: str
    cam0_pattern: str
    cam1_pattern: str
    frame_count_threshold: float = 5.0
    enable_frame_overlay: bool = True
    overlay_font_size: int = 32
    overlay_position: str = "top-left"
    timestamp_analysis_enabled: bool = True
    timestamp_sync_threshold_ms: float = 50.0
    timestamp_sample_points: int = 20
    
    def __post_init__(self):
        """Validate configuration after initialization.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        # Convert string paths to Path objects
        if isinstance(self.input_dir, str):
            self.input_dir = Path(self.input_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.extracted_frames_dir, str):
            self.extracted_frames_dir = Path(self.extracted_frames_dir)
        
        # Validate sampling interval
        if self.sampling_interval < 1:
            raise ValueError("sampling_interval must be >= 1")
        
        # Validate output format
        valid_formats = ['png', 'jpg', 'jpeg']
        if self.output_format.lower() not in valid_formats:
            raise ValueError(f"output_format must be one of {valid_formats}")
        
        # Normalize output format
        if self.output_format.lower() == 'jpeg':
            self.output_format = 'jpg'
        else:
            self.output_format = self.output_format.lower()
        
        # Validate frame count threshold
        if self.frame_count_threshold < 0 or self.frame_count_threshold > 100:
            raise ValueError("frame_count_threshold must be between 0 and 100")
        
        # Validate overlay position
        valid_positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        if self.overlay_position not in valid_positions:
            raise ValueError(f"overlay_position must be one of {valid_positions}")
        
        # Validate overlay font size
        if self.overlay_font_size < 1:
            raise ValueError("overlay_font_size must be >= 1")


class ConfigManager:
    """Manager for loading, validating, and creating configuration files."""
    
    @staticmethod
    def get_default_config() -> dict:
        """Get default configuration values.
        
        Returns:
            Dictionary containing default configuration
        """
        return {
            'input_dir': './segments',
            'output_dir': './stitched_frames',
            'extracted_frames_dir': './extracted_frames',
            'sampling_interval': 100,
            'output_format': 'png',
            'cam0_pattern': 'stereo_cam0_sbs_*.mp4',
            'cam1_pattern': 'stereo_cam1_sbs_*.mp4',
            'frame_count_threshold': 5.0,
            'enable_frame_overlay': True,
            'overlay_font_size': 32,
            'overlay_position': 'top-left',
            'timestamp_analysis_enabled': True,
            'timestamp_sync_threshold_ms': 50.0,
            'timestamp_sample_points': 20
        }
    
    @staticmethod
    def create_default_config(config_path: Path) -> None:
        """Create a default configuration file.
        
        Args:
            config_path: Path where the configuration file should be created
            
        Raises:
            IOError: If the file cannot be created
        """
        default_config = ConfigManager.get_default_config()
        
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration file with comments
        with open(config_path, 'w') as f:
            f.write("# Video Frame Stitcher Configuration\n\n")
            f.write("# Directory containing input video segments\n")
            f.write(f"input_dir: \"{default_config['input_dir']}\"\n\n")
            f.write("# Directory for stitched output frames\n")
            f.write(f"output_dir: \"{default_config['output_dir']}\"\n\n")
            f.write("# Directory for intermediate extracted frames\n")
            f.write(f"extracted_frames_dir: \"{default_config['extracted_frames_dir']}\"\n\n")
            f.write("# Number of frames between each extracted frame (e.g., 100 means extract every 100th frame)\n")
            f.write(f"sampling_interval: {default_config['sampling_interval']}\n\n")
            f.write("# Output image format: 'png' or 'jpg'\n")
            f.write(f"output_format: \"{default_config['output_format']}\"\n\n")
            f.write("# Glob pattern for camera 0 video files\n")
            f.write(f"cam0_pattern: \"{default_config['cam0_pattern']}\"\n\n")
            f.write("# Glob pattern for camera 1 video files\n")
            f.write(f"cam1_pattern: \"{default_config['cam1_pattern']}\"\n\n")
            f.write("# Maximum allowed frame count difference percentage (0-100)\n")
            f.write(f"frame_count_threshold: {default_config['frame_count_threshold']}\n\n")
            f.write("# Enable frame number overlay on images\n")
            f.write(f"enable_frame_overlay: {str(default_config['enable_frame_overlay']).lower()}\n\n")
            f.write("# Font size for frame number overlay text\n")
            f.write(f"overlay_font_size: {default_config['overlay_font_size']}\n\n")
            f.write("# Position of overlay: 'top-left', 'top-right', 'bottom-left', 'bottom-right'\n")
            f.write(f"overlay_position: \"{default_config['overlay_position']}\"\n")
    
    @staticmethod
    def load_config(config_path: Path) -> Config:
        """Load configuration from YAML file, create default if missing.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Config object with loaded or default configuration
            
        Raises:
            ValueError: If configuration values are invalid
            yaml.YAMLError: If the YAML file is malformed
        """
        # If config file doesn't exist, create default
        if not config_path.exists():
            ConfigManager.create_default_config(config_path)
            print(f"Created default configuration file at: {config_path}")
        
        # Load configuration from file
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Merge with defaults for any missing keys
        default_config = ConfigManager.get_default_config()
        for key, value in default_config.items():
            if key not in config_dict:
                config_dict[key] = value
                print(f"Warning: Missing configuration key '{key}', using default: {value}")
        
        # Create and return Config object
        try:
            return Config(**config_dict)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    @staticmethod
    def validate_config(config: Config) -> List[str]:
        """Validate configuration values and return list of errors.
        
        Args:
            config: Configuration object to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate sampling interval
        if config.sampling_interval < 1:
            errors.append("sampling_interval must be >= 1")
        
        # Validate output format
        if config.output_format not in ['png', 'jpg']:
            errors.append(f"output_format must be 'png' or 'jpg', got '{config.output_format}'")
        
        # Validate patterns are not empty
        if not config.cam0_pattern or not config.cam0_pattern.strip():
            errors.append("cam0_pattern cannot be empty")
        
        if not config.cam1_pattern or not config.cam1_pattern.strip():
            errors.append("cam1_pattern cannot be empty")
        
        return errors
    
    @staticmethod
    def save_config(config: Config, config_path: Path) -> None:
        """Save configuration to YAML file.
        
        Args:
            config: Configuration object to save
            config_path: Path where the configuration file should be saved
            
        Raises:
            IOError: If the file cannot be written
        """
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert Config to dictionary
        config_dict = {
            'input_dir': str(config.input_dir),
            'output_dir': str(config.output_dir),
            'extracted_frames_dir': str(config.extracted_frames_dir),
            'sampling_interval': config.sampling_interval,
            'output_format': config.output_format,
            'cam0_pattern': config.cam0_pattern,
            'cam1_pattern': config.cam1_pattern,
            'frame_count_threshold': config.frame_count_threshold,
            'enable_frame_overlay': config.enable_frame_overlay,
            'overlay_font_size': config.overlay_font_size,
            'overlay_position': config.overlay_position
        }
        
        # Write configuration file
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
