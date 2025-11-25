"""
Video Generator - Creates videos from HTML slides with audio narration
"""
import os
import re
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from google.cloud import texttospeech
from playwright.sync_api import sync_playwright
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip

logger = logging.getLogger(__name__)


class SlideDesign:
    """Design constants for slides"""
    WIDTH = 1080
    HEIGHT = 1920

    # Colors
    BG_PRIMARY = "#0A0E27"
    BG_SECONDARY = "#1A1E3F"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B8B9C5"
    ACCENT_COLOR = "#FF4500"  # Orange-red for rank badges
    GOLD = "#FFD700"

    # Fonts
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


class TopTenSlide:
    """Generates HTML slides for Top 10 content"""

    def __init__(self):
        self.design = SlideDesign()

    def create_title_slide(self, topic: str) -> str:
        """Create opening title slide HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.BG_PRIMARY} 0%, {self.design.BG_SECONDARY} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: {self.design.FONT_FAMILY};
                    color: {self.design.TEXT_PRIMARY};
                }}
                .title {{
                    font-size: 72px;
                    font-weight: 800;
                    text-align: center;
                    padding: 0 80px;
                    line-height: 1.2;
                    text-shadow: 0 4px 12px rgba(0,0,0,0.5);
                }}
                .subtitle {{
                    font-size: 36px;
                    font-weight: 400;
                    color: {self.design.TEXT_SECONDARY};
                    margin-top: 40px;
                    text-transform: uppercase;
                    letter-spacing: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="subtitle">Top 10</div>
            <div class="title">{topic}</div>
        </body>
        </html>
        """

    def create_item_slide(self, rank: int, name: str, tagline: str) -> str:
        """Create slide for each Top 10 item"""
        # Determine badge color based on rank
        badge_color = self.design.GOLD if rank <= 3 else self.design.ACCENT_COLOR

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.BG_PRIMARY} 0%, {self.design.BG_SECONDARY} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: {self.design.FONT_FAMILY};
                    color: {self.design.TEXT_PRIMARY};
                    position: relative;
                }}
                .rank-badge {{
                    position: absolute;
                    top: 100px;
                    width: 180px;
                    height: 180px;
                    background: {badge_color};
                    border-radius: 50%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-size: 80px;
                    font-weight: 900;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                    border: 6px solid {self.design.TEXT_PRIMARY};
                }}
                .name {{
                    font-size: 64px;
                    font-weight: 800;
                    text-align: center;
                    padding: 0 60px;
                    line-height: 1.3;
                    margin-top: 180px;
                    text-shadow: 0 4px 12px rgba(0,0,0,0.5);
                }}
                .tagline {{
                    font-size: 32px;
                    font-weight: 400;
                    color: {self.design.TEXT_SECONDARY};
                    text-align: center;
                    padding: 0 80px;
                    margin-top: 40px;
                    line-height: 1.4;
                }}
            </style>
        </head>
        <body>
            <div class="rank-badge">#{rank}</div>
            <div class="name">{name}</div>
            <div class="tagline">{tagline}</div>
        </body>
        </html>
        """

    def create_cta_slide(self, topic: str) -> str:
        """Create call-to-action ending slide"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.BG_PRIMARY} 0%, {self.design.BG_SECONDARY} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: {self.design.FONT_FAMILY};
                    color: {self.design.TEXT_PRIMARY};
                }}
                .main-text {{
                    font-size: 56px;
                    font-weight: 700;
                    text-align: center;
                    padding: 0 80px;
                    line-height: 1.3;
                }}
                .emoji {{
                    font-size: 120px;
                    margin-bottom: 40px;
                }}
                .cta {{
                    font-size: 36px;
                    color: {self.design.TEXT_SECONDARY};
                    margin-top: 60px;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}
            </style>
        </head>
        <body>
            <div class="emoji">👍</div>
            <div class="main-text">Thanks for Watching!</div>
            <div class="cta">Subscribe for More Top 10 Lists</div>
        </body>
        </html>
        """

    def _render_html_to_image(self, html_content: str) -> str:
        """Render HTML to image using Playwright"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": self.design.WIDTH, "height": self.design.HEIGHT}
                )
                page.set_content(html_content)

                # Create temp file for screenshot
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                screenshot_path = temp_file.name
                temp_file.close()

                page.screenshot(path=screenshot_path, full_page=True)
                browser.close()

                return screenshot_path

        except Exception as e:
            logger.error(f"Failed to render HTML to image: {e}")
            raise


class VideoGenerator:
    """Generates videos with HTML slides and audio narration"""

    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30
    ):
        """Initialize video generator"""
        self.width = width
        self.height = height
        self.fps = fps
        self.slide_generator = TopTenSlide()
        self.tts_client = None

        # Initialize TTS client if credentials available
        try:
            self.tts_client = texttospeech.TextToSpeechClient()
            logger.info("Initialized Google Cloud Text-to-Speech client")
        except Exception as e:
            logger.warning(f"Could not initialize TTS client: {e}")

        logger.info(f"Initialized VideoGenerator: {width}x{height} @ {fps}fps")

    def _clean_text(self, text: str) -> str:
        """Clean text for narration - remove emojis and special markers"""
        # Remove emojis
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Remove AI-related markers
        text = re.sub(r'🤖.*?Generated with.*?Co-Authored-By:.*?Claude.*?', '', text, flags=re.DOTALL)
        text = re.sub(r'Generated with.*?Claude.*?', '', text, flags=re.DOTALL)
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove markdown links

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _generate_narration(self, script: str, topic: str) -> Optional[str]:
        """Generate narration audio using Google Cloud TTS"""
        if not self.tts_client:
            logger.warning("TTS client not available, skipping narration")
            return None

        try:
            # Clean script
            clean_script = self._clean_text(script)

            logger.info(f"Generating narration for: {topic[:50]}...")

            synthesis_input = texttospeech.SynthesisInput(text=clean_script)

            # Configure voice (professional male voice)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D",
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )

            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.95,
                pitch=-2.0
            )

            # Generate audio
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            audio_path = temp_file.name
            temp_file.close()

            with open(audio_path, 'wb') as f:
                f.write(response.audio_content)

            logger.info(f"Narration saved to {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Failed to generate narration: {e}")
            return None

    def create_video_from_images(
        self,
        images: List[Dict],
        title: str,
        output_path: Path,
        script: Optional[str] = None
    ) -> Path:
        """
        Create video from images with HTML text slides and audio.

        Args:
            images: List of image dicts with 'rank', 'path', 'name'
            title: Video title
            output_path: Output video path
            script: Optional narration script

        Returns:
            Path to created video
        """
        logger.info(f"Creating video with {len(images)} images")

        try:
            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp())

            # Generate narration audio if script provided
            audio_path = None
            if script:
                audio_path = self._generate_narration(script, title)

            # Create slides
            slides = []

            # 1. Title slide
            logger.info("Creating title slide...")
            title_html = self.slide_generator.create_title_slide(title)
            title_img = self.slide_generator._render_html_to_image(title_html)
            slides.append({"path": title_img, "duration": 3.0})

            # 2. Sort images by rank (descending for countdown)
            sorted_images = sorted(images, key=lambda x: x["rank"], reverse=True)

            # 3. Item slides (use actual generated images)
            for img_data in sorted_images:
                slides.append({
                    "path": img_data["path"],
                    "duration": 5.0
                })

            # 4. CTA slide
            logger.info("Creating CTA slide...")
            cta_html = self.slide_generator.create_cta_slide(title)
            cta_img = self.slide_generator._render_html_to_image(cta_html)
            slides.append({"path": cta_img, "duration": 3.0})

            # Create video with MoviePy
            logger.info("Assembling video with MoviePy...")
            video_clips = []

            for slide in slides:
                clip = ImageClip(slide["path"]).set_duration(slide["duration"])
                video_clips.append(clip)

            final_video = concatenate_videoclips(video_clips, method="compose")

            # Add audio if available
            if audio_path and Path(audio_path).exists():
                logger.info("Adding narration audio...")
                narration = AudioFileClip(audio_path)

                # Check for background music
                bg_music_path = Path(__file__).parent / "bg.mp4"

                if bg_music_path.exists():
                    logger.info("Adding background music...")
                    bg_music = AudioFileClip(str(bg_music_path))

                    # Loop background music if needed
                    if bg_music.duration < narration.duration:
                        n_loops = int(narration.duration / bg_music.duration) + 1
                        bg_music = bg_music.loop(n_loops)

                    bg_music = bg_music.subclip(0, narration.duration)
                    bg_music = bg_music.volumex(0.15)  # 15% volume for background

                    # Combine audio
                    final_audio = CompositeAudioClip([narration, bg_music])
                else:
                    final_audio = narration

                final_video = final_video.set_audio(final_audio)
                final_video = final_video.subclip(0, narration.duration)

            # Write final video
            output_path.parent.mkdir(parents=True, exist_ok=True)
            final_video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                threads=4
            )

            # Cleanup
            final_video.close()
            if audio_path and Path(audio_path).exists():
                Path(audio_path).unlink()

            logger.info(f"Video created successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Video creation failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    # Test video generation
    logging.basicConfig(level=logging.INFO)

    generator = VideoGenerator()

    # Test slide generation
    slide_gen = TopTenSlide()

    test_html = slide_gen.create_title_slide("Top 10 Amazing Cities")
    print("Title slide HTML generated")

    item_html = slide_gen.create_item_slide(1, "Paris", "The City of Light and Romance")
    print("Item slide HTML generated")
