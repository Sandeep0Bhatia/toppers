"""
Image Generator - Creates AI-generated images for Top 10 slides
"""
import os
import logging
import base64
from pathlib import Path
from typing import Dict, List
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generates images using AI (DALL-E, Stability AI, or Replicate)"""

    def __init__(self, provider: str = "dalle"):
        """
        Initialize image generator.

        Args:
            provider: Image generation provider ('dalle', 'stability', 'replicate')
        """
        self.provider = provider.lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        if self.provider == "dalle":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=self.openai_api_key)
        elif self.provider == "stability":
            if not self.stability_api_key:
                raise ValueError("STABILITY_API_KEY not set for Stability AI")
        elif self.provider == "replicate":
            try:
                import replicate
                self.replicate = replicate
            except ImportError:
                raise ImportError("replicate package not installed. Run: pip install replicate")

        logger.info(f"Initialized ImageGenerator with provider: {self.provider}")

    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        width: int = 1080,
        height: int = 1920
    ) -> Path:
        """
        Generate an image from a prompt and save it.

        Args:
            prompt: Text prompt for image generation
            output_path: Path to save the generated image
            width: Image width
            height: Image height

        Returns:
            Path to the saved image
        """
        logger.info(f"Generating image with {self.provider}: {prompt[:100]}...")

        try:
            if self.provider == "dalle":
                return self._generate_dalle(prompt, output_path)
            elif self.provider == "stability":
                return self._generate_stability(prompt, output_path, width, height)
            elif self.provider == "replicate":
                return self._generate_replicate(prompt, output_path, width, height)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            # Create a fallback placeholder
            return self._create_placeholder(output_path, prompt)

    def _generate_dalle(self, prompt: str, output_path: Path) -> Path:
        """Generate image using DALL-E 3"""
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Portrait, closest to 9:16
                quality="standard",
                n=1
            )

            # Download image
            image_url = response.data[0].url
            image_data = requests.get(image_url).content

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_data)

            logger.info(f"DALL-E image saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"DALL-E generation failed: {e}")
            raise

    def _generate_stability(
        self,
        prompt: str,
        output_path: Path,
        width: int,
        height: int
    ) -> Path:
        """Generate image using Stability AI"""
        try:
            url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

            headers = {
                "Authorization": f"Bearer {self.stability_api_key}",
                "Content-Type": "application/json"
            }

            body = {
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 7,
                "height": height,
                "width": width,
                "samples": 1,
                "steps": 30
            }

            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()

            data = response.json()
            image_data = base64.b64decode(data["artifacts"][0]["base64"])

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_data)

            logger.info(f"Stability AI image saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Stability AI generation failed: {e}")
            raise

    def _generate_replicate(
        self,
        prompt: str,
        output_path: Path,
        width: int,
        height: int
    ) -> Path:
        """Generate image using Replicate SDXL"""
        try:
            output = self.replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1
                }
            )

            # Download image
            image_url = output[0]
            image_data = requests.get(image_url).content

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_data)

            logger.info(f"Replicate image saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Replicate generation failed: {e}")
            raise

    def _create_placeholder(self, output_path: Path, text: str) -> Path:
        """Create a simple placeholder image"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            # Create image
            img = Image.new('RGB', (1080, 1920), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)

            # Wrap text
            wrapped_text = textwrap.fill(text[:200], width=30)

            # Draw text
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            except:
                font = ImageFont.load_default()

            draw.text((540, 960), wrapped_text, fill=(255, 255, 255), font=font, anchor="mm")

            # Save
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            logger.warning(f"Created placeholder image at {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create placeholder: {e}")
            raise

    def generate_all_images(
        self,
        image_prompts: Dict,
        output_dir: Path
    ) -> List[Dict]:
        """
        Generate all images for a Top 10 list.

        Args:
            image_prompts: Dict with prompts from researcher
            output_dir: Directory to save images

        Returns:
            List of dicts with image paths and metadata
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        images = []

        for item in image_prompts.get("prompts", []):
            rank = item["rank"]
            name = item["name"]
            prompt = item["prompt"]

            # Generate filename
            filename = f"rank_{rank:02d}_{name[:30].replace(' ', '_')}.png"
            output_path = output_dir / filename

            try:
                # Generate image
                image_path = self.generate_image(prompt, output_path)

                images.append({
                    "rank": rank,
                    "name": name,
                    "path": str(image_path),
                    "prompt": prompt
                })

                logger.info(f"Generated image for #{rank}: {name}")

            except Exception as e:
                logger.error(f"Failed to generate image for #{rank} {name}: {e}")
                # Continue with other images
                continue

        logger.info(f"Generated {len(images)} images out of {len(image_prompts.get('prompts', []))}")
        return images


if __name__ == "__main__":
    # Test image generation
    logging.basicConfig(level=logging.INFO)

    generator = ImageGenerator(provider="dalle")

    test_prompt = """Majestic mountain landscape at sunset, snow-capped peaks,
    dramatic clouds, cinematic photography, golden hour lighting, breathtaking vista,
    ultra detailed, 8K resolution, National Geographic style"""

    output = Path("test_image.png")
    generator.generate_image(test_prompt, output)
    print(f"Test image saved to {output}")
