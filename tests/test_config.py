"""Unit tests for configuration management."""

import pytest
import tempfile
from pathlib import Path
import yaml

from src.config import Config, ConfigManager


class TestConfig:
    """Test cases for Config dataclass."""
    
    def test_config_creation_with_valid_values(self):
        """Test creating a Config object with valid values."""
        config = Config(
            input_dir=Path("./segments"),
            output_dir=Path("./stitched_frames"),
            extracted_frames_dir=Path("./extracted_frames"),
            sampling_interval=100,
            output_format="png",
            cam0_pattern="stereo_cam0_sbs_*.mp4",
            cam1_pattern="stereo_cam1_sbs_*.mp4"
        )
        
        assert config.input_dir == Path("./segments")
        assert config.output_dir == Path("./stitched_frames")
        assert config.extracted_frames_dir == Path("./extracted_frames")
        assert config.sampling_interval == 100
        assert config.output_format == "png"
        assert config.cam0_pattern == "stereo_cam0_sbs_*.mp4"
        assert config.cam1_pattern == "stereo_cam1_sbs_*.mp4"
    
    def test_config_converts_string_paths_to_path_objects(self):
        """Test that string paths are converted to Path objects."""
        config = Config(
            input_dir="./segments",
            output_dir="./stitched_frames",
            extracted_frames_dir="./extracted_frames",
            sampling_interval=100,
            output_format="png",
            cam0_pattern="stereo_cam0_sbs_*.mp4",
            cam1_pattern="stereo_cam1_sbs_*.mp4"
        )
        
        assert isinstance(config.input_dir, Path)
        assert isinstance(config.output_dir, Path)
        assert isinstance(config.extracted_frames_dir, Path)
    
    def test_config_validates_sampling_interval(self):
        """Test that invalid sampling interval raises ValueError."""
        with pytest.raises(ValueError, match="sampling_interval must be >= 1"):
            Config(
                input_dir=Path("./segments"),
                output_dir=Path("./stitched_frames"),
                extracted_frames_dir=Path("./extracted_frames"),
                sampling_interval=0,
                output_format="png",
                cam0_pattern="stereo_cam0_sbs_*.mp4",
                cam1_pattern="stereo_cam1_sbs_*.mp4"
            )
    
    def test_config_validates_output_format(self):
        """Test that invalid output format raises ValueError."""
        with pytest.raises(ValueError, match="output_format must be one of"):
            Config(
                input_dir=Path("./segments"),
                output_dir=Path("./stitched_frames"),
                extracted_frames_dir=Path("./extracted_frames"),
                sampling_interval=100,
                output_format="bmp",
                cam0_pattern="stereo_cam0_sbs_*.mp4",
                cam1_pattern="stereo_cam1_sbs_*.mp4"
            )
    
    def test_config_normalizes_jpeg_to_jpg(self):
        """Test that 'jpeg' format is normalized to 'jpg'."""
        config = Config(
            input_dir=Path("./segments"),
            output_dir=Path("./stitched_frames"),
            extracted_frames_dir=Path("./extracted_frames"),
            sampling_interval=100,
            output_format="jpeg",
            cam0_pattern="stereo_cam0_sbs_*.mp4",
            cam1_pattern="stereo_cam1_sbs_*.mp4"
        )
        
        assert config.output_format == "jpg"


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_get_default_config(self):
        """Test getting default configuration values."""
        defaults = ConfigManager.get_default_config()
        
        assert defaults['input_dir'] == './segments'
        assert defaults['output_dir'] == './stitched_frames'
        assert defaults['extracted_frames_dir'] == './extracted_frames'
        assert defaults['sampling_interval'] == 100
        assert defaults['output_format'] == 'png'
        assert defaults['cam0_pattern'] == 'stereo_cam0_sbs_*.mp4'
        assert defaults['cam1_pattern'] == 'stereo_cam1_sbs_*.mp4'
    
    def test_create_default_config(self):
        """Test creating a default configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            ConfigManager.create_default_config(config_path)
            
            assert config_path.exists()
            
            # Verify content
            with open(config_path, 'r') as f:
                content = f.read()
                assert 'input_dir' in content
                assert 'sampling_interval' in content
                assert 'cam0_pattern' in content
    
    def test_load_config_creates_default_if_missing(self):
        """Test that load_config creates default file if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Config file doesn't exist yet
            assert not config_path.exists()
            
            # Load config should create it
            config = ConfigManager.load_config(config_path)
            
            assert config_path.exists()
            assert config.sampling_interval == 100
            assert config.output_format == "png"
    
    def test_load_config_with_valid_file(self):
        """Test loading configuration from a valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Create a custom config file
            config_data = {
                'input_dir': './my_segments',
                'output_dir': './my_output',
                'extracted_frames_dir': './my_extracted',
                'sampling_interval': 50,
                'output_format': 'jpg',
                'cam0_pattern': 'cam0_*.mp4',
                'cam1_pattern': 'cam1_*.mp4'
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Load the config
            config = ConfigManager.load_config(config_path)
            
            assert config.input_dir == Path('./my_segments')
            assert config.output_dir == Path('./my_output')
            assert config.extracted_frames_dir == Path('./my_extracted')
            assert config.sampling_interval == 50
            assert config.output_format == 'jpg'
            assert config.cam0_pattern == 'cam0_*.mp4'
            assert config.cam1_pattern == 'cam1_*.mp4'
    
    def test_load_config_with_missing_keys_uses_defaults(self):
        """Test that missing configuration keys use default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Create a partial config file
            config_data = {
                'input_dir': './my_segments',
                'output_dir': './my_output',
                'extracted_frames_dir': './my_extracted'
                # Missing: sampling_interval, output_format, patterns
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Load the config
            config = ConfigManager.load_config(config_path)
            
            # Custom values
            assert config.input_dir == Path('./my_segments')
            
            # Default values for missing keys
            assert config.sampling_interval == 100
            assert config.output_format == 'png'
            assert config.cam0_pattern == 'stereo_cam0_sbs_*.mp4'
    
    def test_load_config_with_invalid_values_raises_error(self):
        """Test that invalid configuration values raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            
            # Create config with invalid sampling_interval
            config_data = {
                'input_dir': './segments',
                'output_dir': './output',
                'extracted_frames_dir': './extracted',
                'sampling_interval': -5,
                'output_format': 'png',
                'cam0_pattern': 'cam0_*.mp4',
                'cam1_pattern': 'cam1_*.mp4'
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="Invalid configuration"):
                ConfigManager.load_config(config_path)
    
    def test_validate_config_with_valid_config(self):
        """Test validating a valid configuration returns no errors."""
        config = Config(
            input_dir=Path("./segments"),
            output_dir=Path("./stitched_frames"),
            extracted_frames_dir=Path("./extracted_frames"),
            sampling_interval=100,
            output_format="png",
            cam0_pattern="stereo_cam0_sbs_*.mp4",
            cam1_pattern="stereo_cam1_sbs_*.mp4"
        )
        
        errors = ConfigManager.validate_config(config)
        assert len(errors) == 0
    
    def test_validate_config_with_invalid_sampling_interval(self):
        """Test validating config with invalid sampling interval."""
        # Create config with invalid value (bypassing __post_init__)
        config = Config.__new__(Config)
        config.input_dir = Path("./segments")
        config.output_dir = Path("./stitched_frames")
        config.extracted_frames_dir = Path("./extracted_frames")
        config.sampling_interval = 0
        config.output_format = "png"
        config.cam0_pattern = "stereo_cam0_sbs_*.mp4"
        config.cam1_pattern = "stereo_cam1_sbs_*.mp4"
        
        errors = ConfigManager.validate_config(config)
        assert len(errors) > 0
        assert any("sampling_interval" in error for error in errors)
    
    def test_validate_config_with_empty_patterns(self):
        """Test validating config with empty camera patterns."""
        config = Config.__new__(Config)
        config.input_dir = Path("./segments")
        config.output_dir = Path("./stitched_frames")
        config.extracted_frames_dir = Path("./extracted_frames")
        config.sampling_interval = 100
        config.output_format = "png"
        config.cam0_pattern = ""
        config.cam1_pattern = "  "
        
        errors = ConfigManager.validate_config(config)
        assert len(errors) >= 2
        assert any("cam0_pattern" in error for error in errors)
        assert any("cam1_pattern" in error for error in errors)
