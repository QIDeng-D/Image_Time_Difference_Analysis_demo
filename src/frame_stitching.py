"""Frame stitching module for vertically combining stereo camera frames."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Callable, Optional
from PIL import Image, ImageDraw, ImageFont
import logging
import cv2
import numpy as np

from src.frame_extraction import ExtractedFrame
from src.error_handling import (
    StitchingError, OutputDirectoryError,
    log_error, log_warning, validate_output_directory
)

logger = logging.getLogger(__name__)


@dataclass
class StitchedFrame:
    """Metadata for a stitched frame.
    
    Attributes:
        global_frame_number: The global frame number across all video segments
        file_path: Path to the saved stitched frame file
    """
    global_frame_number: int
    file_path: Path


class FrameStitcher:
    """Handles vertical stitching of corresponding frames from two cameras.
    
    The stitcher combines frames from cam0 (top) and cam1 (bottom) into a single
    vertically-stacked image. It handles width mismatches by centering narrower
    frames on a white background.
    """
    
    def __init__(self, output_format: str, enable_overlay: bool = True, 
                 overlay_font_size: int = 32, overlay_position: str = "top-left"):
        """Initialize the frame stitcher.
        
        Args:
            output_format: Output image format ('png', 'jpg', or 'jpeg')
            enable_overlay: Enable frame number overlay on stitched images
            overlay_font_size: Font size for frame number overlay text
            overlay_position: Position of overlay ('top-left', 'top-right', 'bottom-left', 'bottom-right')
        """
        self.output_format = output_format.lower()
        if self.output_format not in ['png', 'jpg', 'jpeg']:
            raise ValueError(f"Invalid output format: {output_format}")
        
        self.enable_overlay = enable_overlay
        self.overlay_font_size = overlay_font_size
        self.overlay_position = overlay_position
    
    def find_frame_pairs(
        self,
        cam0_frames: List[ExtractedFrame],
        cam1_frames: List[ExtractedFrame]
    ) -> List[Tuple[ExtractedFrame, ExtractedFrame]]:
        """Find matching frame pairs by global frame number.
        
        Args:
            cam0_frames: List of extracted frames from cam0
            cam1_frames: List of extracted frames from cam1
            
        Returns:
            List of tuples containing matching frame pairs (cam0, cam1)
        """
        # Create mapping of global frame numbers to frames
        cam0_map = {frame.global_frame_number: frame for frame in cam0_frames}
        cam1_map = {frame.global_frame_number: frame for frame in cam1_frames}
        
        # Find intersection of frame numbers
        common_frame_numbers = sorted(set(cam0_map.keys()) & set(cam1_map.keys()))
        
        # Log warnings for unpaired frames
        cam0_only = set(cam0_map.keys()) - set(cam1_map.keys())
        cam1_only = set(cam1_map.keys()) - set(cam0_map.keys())
        
        if cam0_only:
            logger.warning(f"Found {len(cam0_only)} frames in cam0 without matching cam1 frames")
        if cam1_only:
            logger.warning(f"Found {len(cam1_only)} frames in cam1 without matching cam0 frames")
        
        # Create pairs
        pairs = [(cam0_map[num], cam1_map[num]) for num in common_frame_numbers]
        
        return pairs
    
    def add_frame_number_overlay(self, image: Image.Image, frame_number: int) -> Image.Image:
        """Add frame number overlay to the stitched frame image.
        
        Adds a text overlay showing the global frame number in the format "Frame: XXXXX".
        Uses white text with black outline for maximum visibility on any background.
        
        Args:
            image: Input PIL Image
            frame_number: Global frame number to display
            
        Returns:
            Image with overlay applied (new image, original is not modified)
        """
        if not self.enable_overlay:
            return image
        
        # Convert PIL Image to OpenCV format for text rendering
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Format the text
        text = f"Frame: {frame_number:05d}"
        
        # Font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.overlay_font_size / 32.0  # Scale relative to default size 32
        thickness = max(1, int(font_scale * 2))
        outline_thickness = thickness + 2
        
        # Get text size for positioning
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Calculate position based on configuration
        height, width = img_cv.shape[:2]
        margin = 10
        
        if self.overlay_position == "top-left":
            x = margin
            y = text_height + margin
        elif self.overlay_position == "top-right":
            x = width - text_width - margin
            y = text_height + margin
        elif self.overlay_position == "bottom-left":
            x = margin
            y = height - margin
        elif self.overlay_position == "bottom-right":
            x = width - text_width - margin
            y = height - margin
        else:
            # Default to top-left
            x = margin
            y = text_height + margin
        
        # Draw black outline first (for contrast)
        cv2.putText(img_cv, text, (x, y), font, font_scale, 
                   (0, 0, 0), outline_thickness, cv2.LINE_AA)
        
        # Draw white text on top
        cv2.putText(img_cv, text, (x, y), font, font_scale, 
                   (255, 255, 255), thickness, cv2.LINE_AA)
        
        # Convert back to PIL Image
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img_rgb)
    
    def stitch_single_pair(
        self,
        cam0_path: Path,
        cam1_path: Path,
        frame_number: int,
        output_dir: Path
    ) -> Path:
        """Stitch a single frame pair and return the output path.
        
        Args:
            cam0_path: Path to cam0 frame image
            cam1_path: Path to cam1 frame image
            frame_number: Global frame number
            output_dir: Directory to save stitched frame
            
        Returns:
            Path to the saved stitched frame
            
        Raises:
            StitchingError: If frames cannot be stitched
        """
        filename = f"frame_{frame_number:04d}.{self.output_format}"
        output_path = output_dir / filename
        self.stitch_pair(cam0_path, cam1_path, output_path, frame_number)
        return output_path
    
    def stitch_pair(
        self,
        cam0_path: Path,
        cam1_path: Path,
        output_path: Path,
        frame_number: int = 0
    ) -> None:
        """Stitch two frames vertically (cam0 on top, cam1 on bottom).
        
        Handles width mismatches by centering narrower frames on a white background.
        Applies frame number overlay if enabled.
        
        Args:
            cam0_path: Path to cam0 frame image
            cam1_path: Path to cam1 frame image
            output_path: Path where stitched image should be saved
            frame_number: Global frame number for overlay
            
        Raises:
            StitchingError: If frames cannot be loaded or stitched
        """
        try:
            # Load images
            cam0_img = Image.open(cam0_path)
            cam1_img = Image.open(cam1_path)
            
            # Get dimensions
            cam0_width, cam0_height = cam0_img.size
            cam1_width, cam1_height = cam1_img.size
            
            # Determine output width (maximum of the two)
            output_width = max(cam0_width, cam1_width)
            output_height = cam0_height + cam1_height
            
            # Create output image with white background
            stitched = Image.new('RGB', (output_width, output_height), color='white')
            
            # Calculate horizontal offsets for centering
            cam0_x_offset = (output_width - cam0_width) // 2
            cam1_x_offset = (output_width - cam1_width) // 2
            
            # Paste cam0 on top
            stitched.paste(cam0_img, (cam0_x_offset, 0))
            
            # Paste cam1 on bottom
            stitched.paste(cam1_img, (cam1_x_offset, cam0_height))
            
            # Apply frame number overlay if enabled
            if self.enable_overlay and frame_number > 0:
                stitched = self.add_frame_number_overlay(stitched, frame_number)
            
            # Save stitched image
            if self.output_format == 'jpg' or self.output_format == 'jpeg':
                stitched.save(output_path, 'JPEG', quality=95)
            else:
                stitched.save(output_path, 'PNG')
            
            # Close images to free memory
            cam0_img.close()
            cam1_img.close()
            stitched.close()
            
        except FileNotFoundError as e:
            raise StitchingError(
                0,  # Frame number unknown at this level
                cam0_path,
                cam1_path,
                f"Image file not found: {e}"
            )
        except IOError as e:
            raise StitchingError(
                0,
                cam0_path,
                cam1_path,
                f"Failed to read or write image: {e}"
            )
        except Exception as e:
            raise StitchingError(
                0,
                cam0_path,
                cam1_path,
                f"Unexpected error: {e}"
            )
    
    def stitch_frames(
        self,
        cam0_frames: List[ExtractedFrame],
        cam1_frames: List[ExtractedFrame],
        output_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[StitchedFrame]:
        """Stitch corresponding frames from both cameras vertically.
        
        Args:
            cam0_frames: List of extracted frames from cam0
            cam1_frames: List of extracted frames from cam1
            output_dir: Directory to save stitched frames
            progress_callback: Optional function to report progress (current, total)
            
        Returns:
            List of stitched frame metadata
            
        Raises:
            OutputDirectoryError: If output directory cannot be created or accessed
        """
        # Validate and create output directory
        try:
            validate_output_directory(output_dir)
        except OutputDirectoryError as e:
            log_error(e, "Frame stitching")
            raise
        
        # Find matching frame pairs
        frame_pairs = self.find_frame_pairs(cam0_frames, cam1_frames)
        
        logger.info(f"Found {len(frame_pairs)} matching frame pairs to stitch")
        
        stitched_frames = []
        total_pairs = len(frame_pairs)
        
        for idx, (cam0_frame, cam1_frame) in enumerate(frame_pairs):
            # Generate output filename
            frame_num = cam0_frame.global_frame_number
            filename = f"frame_{frame_num:04d}.{self.output_format}"
            output_path = output_dir / filename
            
            try:
                # Stitch the pair
                self.stitch_pair(cam0_frame.file_path, cam1_frame.file_path, output_path, frame_num)
                
                # Record stitched frame
                stitched_frames.append(StitchedFrame(
                    global_frame_number=frame_num,
                    file_path=output_path
                ))
                
                # Report progress
                if progress_callback:
                    progress_callback(idx + 1, total_pairs)
                    
            except StitchingError as e:
                # Update frame number in error
                e.frame_number = frame_num
                log_error(e)
                continue
            except Exception as e:
                error = StitchingError(
                    frame_num,
                    cam0_frame.file_path,
                    cam1_frame.file_path,
                    str(e)
                )
                log_error(error)
                continue
        
        logger.info(f"Successfully stitched {len(stitched_frames)} frames")
        
        return stitched_frames
