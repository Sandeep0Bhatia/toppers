"""
Video Generator - Creates videos from HTML slides with audio narration
Based on tickr implementation for consistency
"""
import os
import re
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from google.cloud import texttospeech
from playwright.sync_api import sync_playwright
import html

try:
    # MoviePy 2.x
    from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
except ImportError:
    # MoviePy 1.x fallback
    from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip

# Audio fade fx (may not exist in very old moviepy versions)
try:
    from moviepy.audio.fx.all import audio_fadein, audio_fadeout
except Exception:
    audio_fadein = None
    audio_fadeout = None

logger = logging.getLogger(__name__)


class SlideDesign:
    """Design constants for Top 10 slides"""
    WIDTH = 1080   # 9:16 for YouTube Shorts
    HEIGHT = 1920
    PADDING = 80

    # Color palette
    COLORS = {
        "white": "#FFFFFF",
        "black": "#000000",
        "primary": "#FF4500",    # Orange-red
        "secondary": "#FFD700",  # Gold
        "bg_dark": "#0A0E27",
        "bg_light": "#1A1E3F",
        "text_light": "#B8B9C5",
    }


class TopTenSlide:
    """Generates HTML slides for Top 10 content using Playwright"""

    def __init__(self, design: SlideDesign = None):
        self.design = design or SlideDesign()

    def create_title_slide(self, topic: str) -> str:
        """Generate title slide HTML and return path to screenshot"""
        clean_topic = html.escape(self._clean_text(topic))

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.COLORS["bg_dark"]} 0%, {self.design.COLORS["bg_light"]} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                }}
                .subtitle {{
                    font-size: 80px;
                    font-weight: 400;
                    color: {self.design.COLORS["text_light"]};
                    margin-bottom: 60px;
                    text-transform: uppercase;
                    letter-spacing: 8px;
                }}
                .title {{
                    font-size: 100px;
                    font-weight: 800;
                    color: {self.design.COLORS["white"]};
                    text-align: center;
                    padding: 0 {self.design.PADDING}px;
                    line-height: 1.2;
                }}
            </style>
        </head>
        <body>
            <div class="subtitle">TOP 10</div>
            <div class="title">{clean_topic}</div>
        </body>
        </html>
        """

        return self._render_html_to_image(html_content)

    def create_item_slide(self, rank: int, name: str, tagline: str) -> str:
        """Generate slide for Top 10 item and return path to screenshot"""
        clean_name = html.escape(self._clean_text(name))
        clean_tagline = html.escape(self._clean_text(tagline))

        # Gold for top 3, orange-red for rest
        badge_color = self.design.COLORS["secondary"] if rank <= 3 else self.design.COLORS["primary"]

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.COLORS["bg_dark"]} 0%, {self.design.COLORS["bg_light"]} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                    position: relative;
                }}
                .rank-badge {{
                    position: absolute;
                    top: 120px;
                    width: 220px;
                    height: 220px;
                    background: {badge_color};
                    border-radius: 50%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-size: 120px;
                    font-weight: 900;
                    color: {self.design.COLORS["white"]};
                    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                    border: 8px solid {self.design.COLORS["white"]};
                }}
                .name {{
                    font-size: 90px;
                    font-weight: 800;
                    color: {self.design.COLORS["white"]};
                    text-align: center;
                    padding: 0 {self.design.PADDING}px;
                    line-height: 1.3;
                    margin-top: 200px;
                }}
                .tagline {{
                    font-size: 50px;
                    font-weight: 400;
                    color: {self.design.COLORS["text_light"]};
                    text-align: center;
                    padding: 0 {self.design.PADDING}px;
                    margin-top: 60px;
                    line-height: 1.4;
                }}
            </style>
        </head>
        <body>
            <div class="rank-badge">#{rank}</div>
            <div class="name">{clean_name}</div>
            <div class="tagline">{clean_tagline}</div>
        </body>
        </html>
        """

        return self._render_html_to_image(html_content)

    def create_cta_slide(self) -> str:
        """Generate call-to-action ending slide and return path to screenshot"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {self.design.WIDTH}px;
                    height: {self.design.HEIGHT}px;
                    background: linear-gradient(135deg, {self.design.COLORS["bg_dark"]} 0%, {self.design.COLORS["bg_light"]} 100%);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                }}
                .main-text {{
                    font-size: 90px;
                    font-weight: 700;
                    color: {self.design.COLORS["white"]};
                    text-align: center;
                    padding: 0 {self.design.PADDING}px;
                    line-height: 1.3;
                    margin-bottom: 100px;
                }}
                .cta {{
                    font-size: 60px;
                    color: {self.design.COLORS["text_light"]};
                    text-transform: uppercase;
                    letter-spacing: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="main-text">Thanks for Watching!</div>
            <div class="cta">Subscribe for More</div>
        </body>
        </html>
        """

        return self._render_html_to_image(html_content)

    def _render_html_to_image(self, html_content: str) -> str:
        """Render HTML to image using Playwright and return path to image file"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": self.design.WIDTH, "height": self.design.HEIGHT})
            page.set_content(html_content)

            # Create temp file for screenshot
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            screenshot_path = temp_file.name
            temp_file.close()

            # Take screenshot
            page.screenshot(path=screenshot_path, full_page=True)
            browser.close()

            return screenshot_path

    def _clean_text(self, text: str) -> str:
        """Remove ALL special characters, emojis, and AI markers"""
        # Remove ALL emojis and unicode symbols
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)  # Remove 4-byte unicode (emojis)
        text = re.sub(r'[\u2600-\u27BF]', '', text)  # Remove dingbats
        text = re.sub(r'[\uE000-\uF8FF]', '', text)  # Remove private use
        text = re.sub(r'[\u2700-\u27BF]', '', text)  # Remove misc symbols

        # Remove AI-related markers
        ai_patterns = [
            r'AI-powered\s*',
            r'powered by AI\s*',
            r'real-time analysis\s*',
            r'machine learning\s*',
        ]
        for pattern in ai_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text


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
        # Background music controls (configurable via env vars)
        try:
            self.bg_volume = float(os.getenv("BG_MUSIC_VOLUME", "0.18"))
        except Exception:
            self.bg_volume = 0.18
        try:
            self.bg_fade_in = float(os.getenv("BG_FADE_IN", "0.5"))
        except Exception:
            self.bg_fade_in = 0.5
        try:
            self.bg_fade_out = float(os.getenv("BG_FADE_OUT", "1.0"))
        except Exception:
            self.bg_fade_out = 1.0

        logger.info(f"Initialized VideoGenerator: {width}x{height} @ {fps}fps")

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
            # Generate narration audio if script provided
            audio_path = None
            if script:
                audio_path = self._generate_narration(script, title)

            # Create slides
            slide_paths = []

            # 1. Title slide
            logger.info("Creating title slide...")
            title_img = self.slide_generator.create_title_slide(title)
            slide_paths.append(title_img)

            # 2. Sort images by rank (descending for countdown)
            sorted_images = sorted(images, key=lambda x: x["rank"], reverse=True)

            # 3. Item slides (use actual generated images, not HTML slides for items)
            for img_data in sorted_images:
                slide_paths.append(img_data["path"])

            # 4. CTA slide
            logger.info("Creating CTA slide...")
            cta_img = self.slide_generator.create_cta_slide()
            slide_paths.append(cta_img)

            # Create video with MoviePy
            video_path = self._create_video_from_slides(
                slide_paths,
                audio_path,
                title,
                output_path.name
            )

            logger.info(f"Video created successfully: {video_path}")
            return Path(video_path)

        except Exception as e:
            logger.error(f"Video creation failed: {e}", exc_info=True)
            raise

    def _generate_narration(self, script: str, topic: str) -> Optional[str]:
        """Generate narration audio using Google Cloud TTS"""
        try:
            # Clean the script for TTS
            clean_script = script

            # Remove ALL emojis and unicode symbols
            clean_script = re.sub(r'[\U00010000-\U0010ffff]', '', clean_script)
            clean_script = re.sub(r'[\u2600-\u27BF]', '', clean_script)
            clean_script = re.sub(r'[\uE000-\uF8FF]', '', clean_script)

            # Remove hashtags and @ mentions
            clean_script = re.sub(r'#\w+', '', clean_script)
            clean_script = re.sub(r'@\w+', '', clean_script)

            # Remove URLs
            clean_script = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', clean_script)

            # Remove special markdown/formatting characters
            clean_script = re.sub(r'[*_`~]', '', clean_script)

            # Remove dollar signs when used as currency symbol
            clean_script = re.sub(r'\$(?=\d)', '', clean_script)

            # Remove other non-spoken punctuation but keep periods, commas, question marks, exclamation
            clean_script = re.sub(r'[^\w\s.,!?\'-]', ' ', clean_script)

            # Clean up multiple spaces
            clean_script = re.sub(r'\s+', ' ', clean_script)
            clean_script = clean_script.strip()

            logger.info(f"Cleaned narration script: {clean_script[:100]}...")

            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=clean_script)

            # TTS voice configuration can be controlled via environment variables:
            # - TTS_VOICE_NAME (e.g. en-US-Neural2-F)
            # - TTS_LANGUAGE_CODE (default: en-US)
            # - TTS_SSML_GENDER (MALE/FEMALE/NEUTRAL)
            # - TTS_SPEAKING_RATE (float)
            # - TTS_PITCH (float)
            # Using Google Cloud TTS Neural2-C voice for authoritative female tone
            # en-US-Neural2-C: Professional, authoritative female voice (A is male, C is female)
            tts_voice_name = os.getenv("TTS_VOICE_NAME", "en-US-Neural2-C")
            tts_language = os.getenv("TTS_LANGUAGE_CODE", "en-US")
            tts_gender = os.getenv("TTS_SSML_GENDER", "FEMALE").upper()
            try:
                if tts_gender == "MALE":
                    ssml_gender = texttospeech.SsmlVoiceGender.MALE
                elif tts_gender == "NEUTRAL":
                    ssml_gender = texttospeech.SsmlVoiceGender.NEUTRAL
                else:
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
            except Exception:
                ssml_gender = texttospeech.SsmlVoiceGender.FEMALE

            voice = texttospeech.VoiceSelectionParams(
                language_code=tts_language,
                name=tts_voice_name,
                ssml_gender=ssml_gender
            )

            # Audio tuning parameters for authoritative tone
            # Slightly slower pace for authority, slightly lower pitch for maturity
            try:
                speaking_rate = float(os.getenv("TTS_SPEAKING_RATE", "0.92"))
            except Exception:
                speaking_rate = 0.92
            try:
                pitch = float(os.getenv("TTS_PITCH", "-1.5"))
            except Exception:
                pitch = -1.5

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch
            )

            response = client.synthesize_speech(
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
            logger.error(f"TTS generation failed: {str(e)}", exc_info=True)
            logger.error("Video will be created without narration audio")
            return None

    def _set_audio_compat(self, video_clip, audio_clip):
        """Helper to set audio with MoviePy 1.x/2.x compatibility"""
        try:
            # Try MoviePy 2.x method first
            return video_clip.with_audio(audio_clip)
        except AttributeError:
            # Fallback to MoviePy 1.x method
            return video_clip.set_audio(audio_clip)

    def _create_video_from_slides(
        self,
        slide_paths: List[str],
        audio_path: Optional[str],
        title: str,
        output_filename: str
    ) -> str:
        """Stitch slides into video with narration"""
        try:
            # Load audio to get duration
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                total_duration = audio_clip.duration
            else:
                # Default: 3 seconds per slide
                total_duration = len(slide_paths) * 3
                audio_clip = None

            # Calculate duration per slide
            duration_per_slide = total_duration / len(slide_paths)

            # Create video clips from slides with explicit size (1080x1920 for YouTube Shorts)
            clips = []
            for slide_path in slide_paths:
                clip = ImageClip(slide_path, duration=duration_per_slide)
                # Ensure clip maintains 1080x1920 resolution
                try:
                    clip = clip.resized((1080, 1920))
                except AttributeError:
                    clip = clip.resize((1080, 1920))
                clips.append(clip)

            # Concatenate clips
            final_clip = concatenate_videoclips(clips, method="compose")

            # Add audio (narration + background music)
            logger.info(f"Audio clip exists: {audio_clip is not None}")
            if audio_clip:
                logger.info(f"Audio clip duration: {audio_clip.duration}s")
                # Check for background music file
                bg_music_path = Path(__file__).parent / "bg.mp4"
                logger.info(f"Looking for background music at: {bg_music_path}")

                if bg_music_path.exists():
                    # Background music exists - mix with narration
                    try:
                        logger.info(f"Loading background music from {bg_music_path}")
                        bg_music = AudioFileClip(str(bg_music_path))

                        # Loop background music to match video duration if needed
                        if bg_music.duration < total_duration:
                            loops_needed = int(total_duration / bg_music.duration) + 1
                            bg_music = bg_music.loop(n=loops_needed)

                        # Trim to exact duration
                        try:
                            bg_music = bg_music.subclipped(0, total_duration)
                        except AttributeError:
                            bg_music = bg_music.subclip(0, total_duration)

                        # Apply configured background music volume so narration is clear
                        bg_music = bg_music.volumex(self.bg_volume)

                        # Apply fade-in/out for polish when fx available
                        try:
                            if audio_fadein:
                                bg_music = bg_music.fx(audio_fadein, self.bg_fade_in)
                            elif hasattr(bg_music, "audio_fadein"):
                                bg_music = bg_music.audio_fadein(self.bg_fade_in)
                        except Exception:
                            logger.debug("Background music fade-in not applied (fx missing)")
                        try:
                            if audio_fadeout:
                                bg_music = bg_music.fx(audio_fadeout, self.bg_fade_out)
                            elif hasattr(bg_music, "audio_fadeout"):
                                bg_music = bg_music.audio_fadeout(self.bg_fade_out)
                        except Exception:
                            logger.debug("Background music fade-out not applied (fx missing)")

                        # Mix narration with background music
                        final_audio = CompositeAudioClip([audio_clip, bg_music])
                        final_clip = self._set_audio_compat(final_clip, final_audio)
                        logger.info("Successfully added background music at 18% volume")
                    except Exception as e:
                        logger.warning(f"Failed to load background music: {e}. Using narration only.")
                        final_clip = self._set_audio_compat(final_clip, audio_clip)
                else:
                    # No background music file - use narration only
                    logger.info(f"Background music file not found at {bg_music_path}. Using narration only.")
                    final_clip = self._set_audio_compat(final_clip, audio_clip)
            else:
                # No narration - try to add just background music
                bg_music_path = Path(__file__).parent / "bg.mp4"
                if bg_music_path.exists():
                    try:
                        logger.info(f"No narration audio. Loading background music from {bg_music_path}")
                        bg_music = AudioFileClip(str(bg_music_path))

                        if bg_music.duration < total_duration:
                            loops_needed = int(total_duration / bg_music.duration) + 1
                            bg_music = bg_music.loop(n=loops_needed)

                        # Trim to exact duration
                        try:
                            bg_music = bg_music.subclipped(0, total_duration)
                        except AttributeError:
                            bg_music = bg_music.subclip(0, total_duration)

                        # Use configured background music volume when no narration is present
                        bg_music = bg_music.volumex(self.bg_volume)
                        try:
                            if audio_fadein:
                                bg_music = bg_music.fx(audio_fadein, self.bg_fade_in)
                            elif hasattr(bg_music, "audio_fadein"):
                                bg_music = bg_music.audio_fadein(self.bg_fade_in)
                        except Exception:
                            logger.debug("Background music fade-in not applied (fx missing)")
                        try:
                            if audio_fadeout:
                                bg_music = bg_music.fx(audio_fadeout, self.bg_fade_out)
                            elif hasattr(bg_music, "audio_fadeout"):
                                bg_music = bg_music.audio_fadeout(self.bg_fade_out)
                        except Exception:
                            logger.debug("Background music fade-out not applied (fx missing)")

                        final_clip = self._set_audio_compat(final_clip, bg_music)
                        logger.info(f"Successfully added background music at {self.bg_volume*100:.0f}% volume (no narration)")
                    except Exception as e:
                        logger.warning(f"Failed to add background music: {e}. Video will have no audio.")
                else:
                    logger.info(f"No narration and no background music file found. Video will have no audio.")

            # Output path
            output_path = Path("videos") / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if video has audio
            has_audio = final_clip.audio is not None
            logger.info(f"Writing video with audio: {has_audio}")

            final_clip.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                audio=has_audio,
                preset='medium',
                threads=4
            )

            # Cleanup
            final_clip.close()
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)

            return str(output_path)

        except Exception as e:
            logger.error(f"Video assembly failed: {str(e)}", exc_info=True)
            raise


if __name__ == "__main__":
    # Test video generation
    logging.basicConfig(level=logging.INFO)

    generator = VideoGenerator()
    print("Video generator initialized successfully")
