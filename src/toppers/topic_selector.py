"""
Topic Selector - Generates creative Top 10 list ideas
"""
import os
import json
import logging
import random
from typing import Dict, List
from google.cloud import storage
from datetime import datetime
import google.generativeai as genai

logger = logging.getLogger(__name__)


class TopicHistoryManager:
    """Manages persistent topic history using Google Cloud Storage"""

    def __init__(
        self,
        bucket_name: str = None,
        history_file: str = "topic_history.json",
        max_history: int = 30
    ):
        self.bucket_name = bucket_name or os.getenv("GCP_BUCKET_NAME", "toppers-videos")
        self.history_file = history_file
        self.max_history = max_history
        self.storage_client = None
        self.bucket = None
        self._init_storage()

    def _init_storage(self):
        """Initialize Google Cloud Storage client and bucket"""
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)
            logger.info(f"Initialized topic history storage: gs://{self.bucket_name}/{self.history_file}")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage: {e}")
            raise

    def _load_history(self) -> List[Dict[str, str]]:
        """Load topic history from Cloud Storage"""
        try:
            blob = self.bucket.blob(self.history_file)
            if not blob.exists():
                logger.info("Topic history file does not exist. Creating new history.")
                return []
            content = blob.download_as_text()
            history = json.loads(content)
            logger.info(f"Loaded {len(history)} topics from history")
            return history
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse history file: {e}. Starting fresh.")
            return []
        except Exception as e:
            logger.error(f"Failed to load topic history: {e}")
            return []

    def _save_history(self, history: List[Dict[str, str]]):
        """Save topic history to Cloud Storage"""
        try:
            blob = self.bucket.blob(self.history_file)
            content = json.dumps(history, indent=2)
            blob.upload_from_string(content, content_type="application/json")
            logger.info(f"Saved {len(history)} topics to history")
        except Exception as e:
            logger.error(f"Failed to save topic history: {e}")

    def add_topic(self, topic: str, category: str = ""):
        """Add a topic to the history"""
        try:
            history = self._load_history()
            entry = {
                "topic": topic,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            # Remove duplicates
            history = [h for h in history if h["topic"] != topic]
            # Add to front
            history.insert(0, entry)
            # Keep only last N entries
            history = history[:self.max_history]
            self._save_history(history)
            logger.info(f"Added topic to history. Total: {len(history)} topics")
        except Exception as e:
            logger.error(f"Failed to add topic to history: {e}")

    def get_recent_topics(self, count: int = None) -> List[str]:
        """Get list of recently used topics"""
        try:
            history = self._load_history()
            topics = [entry["topic"] for entry in history]
            if count:
                return topics[:count]
            return topics
        except Exception as e:
            logger.error(f"Failed to get recent topics: {e}")
            return []


class TopicSelector:
    """Generates creative Top 10 list topics"""

    CATEGORIES = [
        "Beauty & Aesthetics",
        "Intelligence & Education",
        "Culture & Traditions",
        "Nature & Geography",
        "Food & Cuisine",
        "History & Heritage",
        "Innovation & Technology",
        "Arts & Creativity",
        "Wellness & Lifestyle",
        "Human Values & Character"
    ]

    TOPIC_TEMPLATES = [
        "Top 10 Countries with the Most {adjective} {subject}",
        "Top 10 Cities Known for {characteristic}",
        "Top 10 {subject} That Changed {context}",
        "Top 10 Places to Experience {experience}",
        "Top 10 Books About {theme}",
        "Top 10 Innovations in {field}",
        "Top 10 Traditional {subject} Around the World",
        "Top 10 {adjective} Destinations for {purpose}",
        "Top 10 Historical {subject} That Shaped {outcome}",
        "Top 10 Foods That {benefit}"
    ]

    def __init__(self, use_cloud_storage: bool = True):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        if use_cloud_storage:
            try:
                self.history = TopicHistoryManager(max_history=30)
                logger.info("Using Cloud Storage for topic history (last 30 topics)")
            except Exception as e:
                logger.error(f"Failed to initialize Cloud Storage history: {e}")
                raise

        # Initialize Gemini
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("GEMINI_API_KEY not set, using fallback topic generation")
            self.model = None

    def generate_topic(self) -> Dict[str, str]:
        """Generate a creative Top 10 topic"""
        try:
            # Get recent topics to avoid
            recent_topics = self.history.get_recent_topics()
            logger.info(f"Recent topics to avoid: {recent_topics}")

            # Use AI to generate topic
            topic_data = self._generate_ai_topic(recent_topics)

            if not topic_data:
                # Fallback to template-based generation
                topic_data = self._generate_template_topic(recent_topics)

            # Add to history
            if topic_data:
                self.history.add_topic(
                    topic_data["topic"],
                    topic_data.get("category", "")
                )

            return topic_data

        except Exception as e:
            logger.error(f"Failed to generate topic: {e}")
            # Emergency fallback
            return self._get_emergency_fallback()

    def _generate_ai_topic(self, avoid_topics: List[str]) -> Dict[str, str]:
        """Use Gemini AI to generate creative topic"""
        if not self.model:
            return None

        try:
            category = random.choice(self.CATEGORIES)

            prompt = f"""Generate ONE creative and engaging "Top 10" list topic for a YouTube Short video.

Category: {category}

Guidelines:
- Must be interesting, educational, and shareable
- Focus on: beauty, culture, intellect, human values, nature, innovation
- Examples:
  * "Top 10 Countries with the Most Beautiful Landscapes"
  * "Top 10 Books That Will Transform Your Thinking"
  * "Top 10 Cities with the Friendliest People"
  * "Top 10 Ancient Innovations Still Used Today"
  * "Top 10 Foods That Boost Mental Clarity"

AVOID these recent topics:
{chr(10).join(f"- {t}" for t in avoid_topics[:10])}

Return ONLY the topic title, nothing else. Make it compelling and specific.
"""

            response = self.model.generate_content(prompt)
            topic = response.text.strip()

            # Remove quotes if present
            topic = topic.strip('"').strip("'")

            # Ensure it starts with "Top 10"
            if not topic.startswith("Top 10"):
                topic = f"Top 10 {topic}"

            logger.info(f"Generated AI topic: {topic}")

            return {
                "topic": topic,
                "category": category,
                "method": "ai_generated"
            }

        except Exception as e:
            logger.error(f"Failed to generate AI topic: {e}")
            return None

    def _generate_template_topic(self, avoid_topics: List[str]) -> Dict[str, str]:
        """Generate topic using templates"""
        logger.info("Using template-based topic generation")

        # Predefined examples
        examples = [
            {"topic": "Top 10 Countries with the Most Beautiful Architecture", "category": "Beauty & Aesthetics"},
            {"topic": "Top 10 Books That Changed How People Think", "category": "Intelligence & Education"},
            {"topic": "Top 10 Cities Known for Their Kindness", "category": "Human Values & Character"},
            {"topic": "Top 10 Natural Wonders You Must See", "category": "Nature & Geography"},
            {"topic": "Top 10 Ancient Civilizations and Their Wisdom", "category": "History & Heritage"},
            {"topic": "Top 10 Foods That Improve Brain Function", "category": "Wellness & Lifestyle"},
            {"topic": "Top 10 Innovations That Transformed Daily Life", "category": "Innovation & Technology"},
            {"topic": "Top 10 Traditional Art Forms Around the World", "category": "Arts & Creativity"},
            {"topic": "Top 10 Countries with Rich Cultural Heritage", "category": "Culture & Traditions"},
            {"topic": "Top 10 Places to Find Inner Peace", "category": "Wellness & Lifestyle"},
        ]

        # Filter out recent topics
        fresh_examples = [e for e in examples if e["topic"] not in avoid_topics]

        if fresh_examples:
            selected = random.choice(fresh_examples)
        else:
            # All examples were recent, pick random anyway
            selected = random.choice(examples)

        selected["method"] = "template_generated"
        logger.info(f"Generated template topic: {selected['topic']}")
        return selected

    def _get_emergency_fallback(self) -> Dict[str, str]:
        """Emergency fallback topic"""
        return {
            "topic": "Top 10 Amazing Facts About Human Nature",
            "category": "Human Values & Character",
            "method": "fallback"
        }


if __name__ == "__main__":
    # Test topic generation
    logging.basicConfig(level=logging.INFO)
    selector = TopicSelector()
    topic = selector.generate_topic()
    print(f"\nGenerated Topic: {topic['topic']}")
    print(f"Category: {topic['category']}")
