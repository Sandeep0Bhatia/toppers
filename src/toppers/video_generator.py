"""
Video Generator - Creates videos from images and scripts
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Generates videos from slides for Top 10 content"""

    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        duration_per_slide: float = 6.0
    ):
        """
        Initialize video generator.

        Args:
            width: Video width (portrait mode)
            height: Video height (portrait mode)
            fps: Frames per second
            duration_per_slide: Seconds per slide
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.duration_per_slide = duration_per_slide

        logger.info(f"Initialized VideoGenerator: {width}x{height} @ {fps}fps")

    def create_title_slide(
        self,
        title: str,
        output_path: Path,
        background_color: tuple = (20, 20, 30),
        text_color: tuple = (255, 255, 255)
    ) -> Path:
        """Create title slide image"""
        try:
            import textwrap

            img = Image.new('RGB', (self.width, self.height), color=background_color)
            draw = ImageDraw.Draw(img)

            # Try to use a nice font
            try:
                font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
            except:
                font_large = ImageFont.load_default()

            # Wrap title text
            wrapped_title = textwrap.fill(title, width=20)

            # Draw title
            bbox = draw.textbbox((0, 0), wrapped_title, font=font_large)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (self.width - text_width) // 2
            y = (self.height - text_height) // 2

            draw.text((x, y), wrapped_title, fill=text_color, font=font_large)

            # Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            logger.info(f"Created title slide: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create title slide: {e}")
            raise

    def add_rank_overlay(
        self,
        image_path: Path,
        rank: int,
        output_path: Path
    ) -> Path:
        """Add rank number overlay to image"""
        try:
            img = Image.open(image_path)

            # Resize to target size if needed
            if img.size != (self.width, self.height):
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(img)

            # Draw rank badge (top left)
            badge_size = 150
            badge_margin = 40

            # Draw circle background
            draw.ellipse(
                [badge_margin, badge_margin, badge_margin + badge_size, badge_margin + badge_size],
                fill=(255, 69, 0),  # Orange-red
                outline=(255, 255, 255),
                width=5
            )

            # Draw rank number
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 70)
            except:
                font = ImageFont.load_default()

            rank_text = f"#{rank}"
            bbox = draw.textbbox((0, 0), rank_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = badge_margin + (badge_size - text_width) // 2
            text_y = badge_margin + (badge_size - text_height) // 2

            draw.text((text_x, text_y), rank_text, fill=(255, 255, 255), font=font)

            # Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            logger.info(f"Added rank overlay #{rank} to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to add rank overlay: {e}")
            raise

    def create_video_from_images(
        self,
        images: List[Dict],
        title: str,
        output_path: Path,
        audio_path: Path = None
    ) -> Path:
        """
        Create video from list of images.

        Args:
            images: List of image dicts with 'rank', 'path', 'name'
            title: Video title
            output_path: Output video path
            audio_path: Optional audio file path

        Returns:
            Path to created video
        """
        logger.info(f"Creating video with {len(images)} images")

        try:
            # Create temp directory for processed slides
            temp_dir = output_path.parent / "temp_slides"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Sort images by rank (descending for countdown)
            sorted_images = sorted(images, key=lambda x: x["rank"], reverse=True)

            # Create title slide
            title_slide = temp_dir / "slide_00_title.png"
            self.create_title_slide(title, title_slide)

            # Process each image with rank overlay
            processed_slides = [title_slide]

            for idx, img_data in enumerate(sorted_images, start=1):
                rank = img_data["rank"]
                img_path = Path(img_data["path"])

                overlay_path = temp_dir / f"slide_{idx:02d}_rank{rank:02d}.png"
                self.add_rank_overlay(img_path, rank, overlay_path)
                processed_slides.append(overlay_path)

            # Create video with FFmpeg
            output_path = self._create_video_with_ffmpeg(
                processed_slides,
                output_path,
                audio_path
            )

            logger.info(f"Video created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            raise

    def _create_video_with_ffmpeg(
        self,
        slides: List[Path],
        output_path: Path,
        audio_path: Path = None
    ) -> Path:
        """Use FFmpeg to create video from slides"""
        try:
            # Create concat file for FFmpeg
            concat_file = output_path.parent / "concat_list.txt"
            with open(concat_file, 'w') as f:
                for slide in slides:
                    f.write(f"file '{slide.absolute()}'\n")
                    f.write(f"duration {self.duration_per_slide}\n")
                # Add last slide again (FFmpeg requirement)
                f.write(f"file '{slides[-1].absolute()}'\n")

            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-vf", f"fps={self.fps},scale={self.width}:{self.height}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23"
            ]

            # Add audio if provided
            if audio_path and audio_path.exists():
                cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-shortest"])

            cmd.append(str(output_path))

            # Run FFmpeg
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("FFmpeg completed successfully")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"FFmpeg execution failed: {e}")
            raise


if __name__ == "__main__":
    # Test video generation
    logging.basicConfig(level=logging.INFO)

    generator = VideoGenerator()

    # Create test slides
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    # Mock image data
    test_images = [
        {"rank": 1, "name": "Test 1", "path": "slides/test1.png"},
        {"rank": 2, "name": "Test 2", "path": "slides/test2.png"}
    ]

    output = test_dir / "test_video.mp4"
    # generator.create_video_from_images(test_images, "Test Top 10", output)
    print(f"Video would be saved to {output}")
