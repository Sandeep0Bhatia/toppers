"""
Main pipeline for Toppers - AI-Powered Top 10 List Video Generator
"""
import os
import json
import logging
import random
import google.generativeai as genai
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from toppers.topic_selector import TopicSelector
from toppers.researcher import TopTenResearcher
from toppers.image_generator import ImageGenerator
from toppers.video_generator import VideoGenerator
from toppers.youtube_uploader import upload_toppers_video

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToppersPipeline:
    """Main pipeline for generating Top 10 videos"""

    def __init__(self):
        self.output_dir = Path("output")
        self.slides_dir = Path("slides")
        self.videos_dir = Path("videos")

        # Create directories
        for dir_path in [self.output_dir, self.slides_dir, self.videos_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.topic_selector = TopicSelector()
        self.researcher = TopTenResearcher()
        self.image_generator = ImageGenerator(provider=os.getenv("IMAGE_GENERATOR", "dalle"))
        self.video_generator = VideoGenerator(
            width=int(os.getenv("VIDEO_WIDTH", 1080)),
            height=int(os.getenv("VIDEO_HEIGHT", 1920)),
            fps=int(os.getenv("FPS", 30))
        )

        # Initialize Gemini model for optional AI-assisted selection of intros
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.genai_model = None
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.genai_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Initialized Gemini model for intro selection")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini model: {e}")
    def _generate_intro_candidates(self, topic: str, visual_focus: bool) -> list:
        """Return a list of intro candidate strings for the given topic.

        These are short (5-12s) hooks designed to precede the Top 10 countdown.
        """
        templates = [
            "Stop scrolling — {topic}. Ready? In the next 60 seconds you'll see the Top 10 that will change how you think.",
            "You won't believe this — {topic}. We're counting down the Top 10 secrets experts don't tell you. Stay until the end for the jaw-dropper.",
            "Dream destinations and unbelievable luxury — {topic}. Watch the Top 10 most stunning visuals that people only see once in a lifetime.",
            "These stories restore your faith — {topic}. Ten moments of courage, wonder, and surprise. Get ready to feel inspired.",
            "Backed by research, here's {topic}. We ran the numbers — these Top 10 are the most significant you need to know.",
            "Think you know the story? {topic}. Watch as we reveal the Top 10 with the wildest plot twists you never heard of."
        ]

        # If visual focus, prioritize aspirational/visual templates
        candidates = []
        for t in templates:
            candidates.append(t.format(topic=topic))

        # Add small automatic variants (shorten or add urgency)
        variants = []
        for c in candidates:
            variants.append(c)
            variants.append(c.replace("Ready? ", "Ready now? "))
            if "watch" in c.lower():
                variants.append(c + " Don't blink.")

        # Deduplicate while preserving order
        seen = set()
        final = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                final.append(v)

        return final[:8]

    def _select_best_intro(self, topic: str, candidates: list, visual_focus: bool) -> str:
        """Select the best intro from candidates. Use AI ranking if model available, else fallback to heuristics/random.

        Returns the chosen intro string.
        """
        if not candidates:
            return ""

        # If we have a Gemini model, ask it to choose the single best intro.
        if self.genai_model:
            try:
                prompt = f"You are a viral content strategist. Given the topic: '{topic}', choose the single best short intro from the following list that will maximize hook and shares. Return ONLY the chosen intro text, verbatim, and nothing else.\n\n"
                prompt += "\n\n".join(f"{i+1}. {c}" for i, c in enumerate(candidates))
                prompt += "\n\nContext: The video is a YouTube Short (vertical, 60s). If the topic is visually-driven, prefer aspirational/visual hooks."

                resp = self.genai_model.generate_content(prompt)
                choice = resp.text.strip().strip('"').strip("'")
                # Validate the choice exists in candidates (fuzzy match)
                for c in candidates:
                    if choice.lower() in c.lower() or c.lower() in choice.lower():
                        return c
                # If direct match failed, return the raw choice if it's non-empty
                if choice:
                    return choice
            except Exception as e:
                logger.warning(f"AI intro selection failed: {e}")

        # Fallback heuristics: prefer visual wording if visual_focus
        if visual_focus:
            for c in candidates:
                if any(k in c.lower() for k in ("stunning", "visual", "luxury", "breathtaking", "paradise", "dream")):
                    return c

        # Otherwise return a random candidate
        return random.choice(candidates)
    def run(self):
        """Execute the complete pipeline"""
        try:
            logger.info("=" * 80)
            logger.info("TOPPERS PIPELINE STARTING")
            logger.info("=" * 80)

            # Step 1: Select Topic
            logger.info("\n[STEP 1] Selecting Topic...")
            topic_data = self.topic_selector.generate_topic()
            topic = topic_data["topic"]
            logger.info(f"✓ Selected topic: {topic}")
            logger.info(f"  Category: {topic_data.get('category', 'N/A')}")

            # Step 2: Research & Create Content
            logger.info("\n[STEP 2] Researching and creating content...")
            content = self.researcher.create_full_content(topic)
            logger.info(f"✓ Research completed")
            logger.info(f"  Found {len(content['research'].get('items', []))} items")

            # Save content to file for reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_file = self.output_dir / f"content_{timestamp}.json"
            with open(content_file, 'w') as f:
                json.dump(content, f, indent=2)
            logger.info(f"  Saved content to {content_file}")

            # Step 3: Generate Images
            logger.info("\n[STEP 3] Generating images...")
            slide_dir = self.slides_dir / f"slides_{timestamp}"
            slide_dir.mkdir(parents=True, exist_ok=True)

            images = self.image_generator.generate_all_images(
                content["image_prompts"],
                slide_dir
            )
            logger.info(f"✓ Generated {len(images)} images")

            if len(images) == 0:
                raise Exception("No images were generated successfully")

            # Step 4: Create Video
            logger.info("\n[STEP 4] Creating video...")
            video_path = self.videos_dir / f"toppers_{timestamp}.mp4"

            # Prepare script for narration
            script_data = content.get("script", {})
            full_script = ""

            # Add preamble from researcher if available
            if "preamble" in script_data:
                full_script += f"{script_data['preamble']} "

            # Add any hook researcher created
            if "hook" in script_data:
                full_script += f"{script_data['hook']} "

            items_script = script_data.get("items_script", [])
            for item in items_script:
                # Handle both 'script' and 'narration' keys from researcher
                narration = item.get('script') or item.get('narration', '')
                full_script += f"Number {item['rank']}: {item['name']}. {narration} "

            if "cta" in script_data:
                full_script += f"{script_data['cta']}"

            self.video_generator.create_video_from_images(
                images=images,
                title=topic,
                output_path=video_path,
                script=full_script if full_script else None
            )
            logger.info(f"✓ Video created: {video_path}")

            # Step 5: Upload to YouTube
            logger.info("\n[STEP 5] Uploading to YouTube...")

            # Create summary from script
            script_data = content.get("script", {})
            summary = f"{topic}\n\n"

            if "hook" in script_data:
                summary += f"{script_data['hook']}\n\n"

            # Add first few items as preview
            items_script = script_data.get("items_script", [])
            for item in items_script[:3]:
                summary += f"#{item['rank']} {item['name']}\n"

            summary += f"\n... and {len(items_script) - 3} more!\n\n"
            summary += "Watch to see the complete countdown!"

            video_id = upload_toppers_video(
                video_path=str(video_path),
                topic=topic,
                summary=summary,
                privacy_status=os.getenv("YOUTUBE_PRIVACY", "public")
            )

            if video_id:
                logger.info(f"✓ Video uploaded successfully!")
                logger.info(f"  Video ID: {video_id}")
                logger.info(f"  URL: https://www.youtube.com/watch?v={video_id}")
            else:
                logger.warning("⚠ Video upload failed")

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Topic: {topic}")
            logger.info(f"Images: {len(images)}")
            logger.info(f"Video: {video_path}")
            if video_id:
                logger.info(f"YouTube: https://www.youtube.com/watch?v={video_id}")
            logger.info("=" * 80)

            return {
                "success": True,
                "topic": topic,
                "video_path": str(video_path),
                "video_id": video_id,
                "images_count": len(images)
            }

        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """Main entry point"""
    logger.info("Starting Toppers Video Generator")

    # Check required environment variables
    # Only require keys that are mandatory for running the pipeline in most setups.
    required_vars = [
        "SERPER_API_KEY",
        "GCP_BUCKET_NAME"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return 1

    # Run pipeline
    pipeline = ToppersPipeline()
    result = pipeline.run()

    if result["success"]:
        logger.info("✅ Job completed successfully")
        return 0
    else:
        logger.error("❌ Job failed")
        return 1


if __name__ == "__main__":
    exit(main())
