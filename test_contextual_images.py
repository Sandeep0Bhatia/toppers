"""
Test script to verify contextual image generation with narration focus
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from toppers.researcher import TopTenResearcher

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_contextual_research():
    """Test the enhanced research with narration_focus and visual_context"""

    logger.info("=" * 80)
    logger.info("TESTING CONTEXTUAL IMAGE PROMPTS")
    logger.info("=" * 80)

    # Initialize researcher
    researcher = TopTenResearcher()

    # Test with a simple topic
    test_topic = "Top 10 Most Iconic Landmarks in Europe"

    logger.info(f"\nTest Topic: {test_topic}")
    logger.info("-" * 80)

    # Step 1: Research
    logger.info("\n[STEP 1] Running research with narration_focus...")
    research_data = researcher.research_topic(test_topic)

    # Display research results
    logger.info(f"\nResearch Results for '{research_data.get('topic')}':")
    logger.info("=" * 80)

    for item in research_data.get("items", []):
        logger.info(f"\n#{item['rank']} - {item['name']}")
        logger.info(f"  Tagline: {item.get('tagline', 'N/A')}")
        logger.info(f"  Surprising Fact: {item.get('surprising_fact', 'N/A')}")
        logger.info(f"  🎯 Narration Focus: {item.get('narration_focus', 'MISSING')}")
        logger.info(f"  🖼️  Visual Context: {item.get('visual_context', 'MISSING')}")

    # Step 2: Generate image prompts
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 2] Generating contextual image prompts...")
    image_prompts = researcher.generate_image_prompts(test_topic, research_data)

    # Display image prompts
    logger.info(f"\nImage Prompts (Theme: {image_prompts.get('theme')}):")
    logger.info("=" * 80)

    for prompt_item in image_prompts.get("prompts", []):
        logger.info(f"\n#{prompt_item['rank']} - {prompt_item['name']}")
        logger.info(f"  📸 Prompt: \"{prompt_item['prompt']}\"")
        logger.info(f"  Style: {prompt_item.get('style_notes', 'N/A')}")
        logger.info(f"  Word Count: {len(prompt_item['prompt'].split())} words")

    # Step 3: Create script to see narration
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 3] Creating script to verify alignment...")
    script_data = researcher.create_script(test_topic, research_data)

    logger.info(f"\nScript Hook: {script_data.get('hook')}")
    logger.info("\nItem Narrations:")
    logger.info("-" * 80)

    for item in script_data.get("items_script", []):
        narration = item.get('script') or item.get('narration', '')
        logger.info(f"\n#{item['rank']} - {item['name']}")
        logger.info(f"  Narration: {narration}")

    logger.info(f"\nCTA: {script_data.get('cta')}")

    # Save results
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    test_results = {
        "topic": test_topic,
        "research": research_data,
        "image_prompts": image_prompts,
        "script": script_data
    }

    output_file = output_dir / "contextual_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Test results saved to {output_file}")
    logger.info("=" * 80)

    # Verify all items have narration_focus and visual_context
    missing_fields = []
    for item in research_data.get("items", []):
        if "narration_focus" not in item:
            missing_fields.append(f"#{item['rank']} missing narration_focus")
        if "visual_context" not in item:
            missing_fields.append(f"#{item['rank']} missing visual_context")

    if missing_fields:
        logger.warning("\n⚠️  MISSING FIELDS DETECTED:")
        for msg in missing_fields:
            logger.warning(f"  - {msg}")
        logger.warning("\nThis means the research agent didn't follow the new schema.")
        logger.warning("You may need to retry or adjust the task description.")
    else:
        logger.info("\n✅ All items have narration_focus and visual_context!")
        logger.info("✅ Image prompts should now be contextual to narration!")

    return test_results


if __name__ == "__main__":
    try:
        results = test_contextual_research()
        print("\n✅ Test completed successfully!")
        print(f"\nCheck test_output/contextual_test_results.json for detailed results.")
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        exit(1)
