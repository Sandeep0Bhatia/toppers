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
    """Generates viral, unique, compelling Top 10 list topics designed to maximize engagement"""

    # Trending content categories that drive views
    CATEGORIES = [
        "Psychology & Human Behavior",  # What makes people tick
        "Controversial Truths",  # Debunking myths
        "Hidden Gems & Underrated",  # Discovery angle
        "Jaw-Dropping Coincidences",  # Viral-worthy moments
        "Mind-Bending Paradoxes",  # Intellectual hooks
        "Rare Phenomenon & Anomalies",  # Weird and fascinating
        "Power & Influence",  # Status-seeking content
        "Dark History & Secrets",  # Intrigue factor
        "Unexpected Connections",  # "You won't believe it's connected"
        "Transformation Stories",  # Before-after narratives
        "Breaking the Rules",  # Counter-culture appeal
        "Scientific Mind-Blowers",  # "Scientists were shocked"
        "Hidden Patterns in Nature",  # Discovery-driven
        "Money & Status",  # Aspirational
        "Survival & Extreme Scenarios",  # Tension and stakes
        # Visually compelling categories (generate desirable, attractive imagery)
        "Luxury Lifestyles & Aesthetics",  # High-end visuals - mansions, yachts, exotic locations
        "Exotic Destinations & Beauty",  # Stunning visuals - waterfalls, beaches, architecture
        "Opulent & Lavish",  # Jewels, gold, premium materials
        "Natural Wonders & Landscapes",  # Breathtaking imagery - mountains, deserts, forests
        "Fashion & Style Evolution",  # Visually striking - designers, outfits, transformations
        "Architecture & Design Marvels",  # Iconic buildings, modern design - heavily visual
        "Art & Masterpieces",  # Paintings, sculptures, installations - instantly compelling
        "Extreme Beauty & Aesthetics",  # Perfect faces, perfect bodies, peak conditions
        "Supercars & Exotic Vehicles",  # Highly desirable - Ferrari, McLaren, Bugatti
        "Exclusive Islands & Hideaways",  # Private islands, secret locations - aspirational
        "Gourmet & Culinary Delights",  # Food photography - plating, luxury dining
        "Rare & Precious Collections",  # Diamonds, artifacts, collectibles - visually rich
        "Paradise Experiences",  # Underwater diving, forests, tropical scenes
        "Premium Fashion Houses",  # Designer collections, runway shows
        "Architectural Wonders",  # Ancient & modern - visually stunning
    ]

    # Viral trigger frameworks that drive engagement
    VIRAL_FRAMEWORKS = [
        # Contrarian angle
        "Top 10 Things Everyone Believes That Are Actually WRONG",
        "Top 10 {field} That Defy Logic",
        "Top 10 Myths Debunked: What You Didn't Know",
        
        # Scarcity/Rarity
        "Top 10 Rarest {items} Ever Discovered",
        "Top 10 Most Exclusive {experiences} In The World",
        "Top 10 Almost-Extinct {things} Making a Comeback",
        
        # Curiosity gaps
        "Top 10 Unsolved {mysteries} That Still Baffle Scientists",
        "Top 10 Forbidden {items} You Can't Access",
        "Top 10 Hidden {secrets} Behind Everyday Things",
        
        # Status/aspiration
        "Top 10 Habits of the World's Most Successful {people}",
        "Top 10 Things Only {group} Know About",
        "Top 10 Secrets of {elite_category}",
        
        # Weird/unusual
        "Top 10 Strangest {phenomena} Science Can't Explain",
        "Top 10 Most Unusual {things} Ever Recorded",
        "Top 10 Bizarre {creatures} Living Undetected",
        
        # Practical utility with a twist
        "Top 10 {Skills} That Changed People's Lives (In Weeks)",
        "Top 10 Forgotten {techniques} That Still Work Better",
        "Top 10 Cheap Hacks That Outperform Expensive {products}",
        
        # Emotional resonance
        "Top 10 Touching Stories That Will Restore Your Faith In Humanity",
        "Top 10 Most Inspiring {people} Nobody's Heard Of",
        
        # Plot twist angle
        "Top 10 {historical_events} With Shocking Plot Twists",
        "Top 10 Celebrities Who Had Secret {identities}",
        
        # "You won't believe" angle
        "Top 10 {Places} Where Strange Things Happen",
        "Top 10 {Professions} With Crazy Untold Secrets"
    ]

    # Psychological hooks that make content shareable
    ENGAGEMENT_HOOKS = {
        "curiosity": ["What you don't know", "Hidden", "Secret", "Untold", "Shocking", "Revealed"],
        "contrast": ["Actually Wrong", "Defy Logic", "Myth Busted", "The Truth Is", "You've Been Lied To"],
        "urgency": ["Disappearing", "Going Extinct", "Won't Last Long", "Before It's Too Late"],
        "exclusivity": ["Only", "Elite", "Rare", "Forbidden", "Underground"],
        "emotional": ["Touching", "Restored Faith", "Inspiring", "Heart-Warming", "Unforgettable"],
        "weird": ["Strangest", "Bizarre", "Unexplained", "Creepy", "Unsettling"],
        # Visual/aesthetic hooks for image generation
        "desirable": ["Stunning", "Breathtaking", "Jaw-Dropping Beauty", "Absolutely Gorgeous", "Mesmerizing", "Luxurious"],
        "aspirational": ["Dream", "Fantasy", "Wish List", "Goals", "Most Coveted", "Bucket List"],
        "visual_intrigue": ["Visual Masterpiece", "Unbelievably Beautiful", "Beyond Imagination", "Iconic", "Legendary"]
    }

    # Image quality optimization frameworks - topics that generate stunning visuals
    VISUAL_FRAMEWORKS = [
        # Luxury & Desirable
        "Top 10 Most Luxurious {items} Money Can Buy",
        "Top 10 Dream {experiences} of the Ultra-Wealthy",
        "Top 10 Most Expensive & Exclusive {things}",
        
        # Natural beauty & landscapes
        "Top 10 Most Breathtaking {places} On Earth",
        "Top 10 Stunning {natural_phenomena} That Defy Belief",
        "Top 10 Hidden {locations} With Unbelievable Beauty",
        
        # Aesthetic & design
        "Top 10 Most Iconic {architectural_structures} Ever Built",
        "Top 10 Most Visually Stunning {art_forms}",
        "Top 10 Most Beautiful {design_elements}",
        
        # Fashion & style
        "Top 10 Most Iconic Fashion {moments} In History",
        "Top 10 Most Jaw-Dropping {fashion_collections}",
        
        # Vehicles & transportation
        "Top 10 Most Desirable {supercars} Ever Made",
        "Top 10 Rarest & Most Exclusive {vehicles}",
        
        # Collections & artifacts
        "Top 10 Most Precious {collections} In The World",
        "Top 10 Rarest {treasures} Ever Discovered",
        
        # Paradise & escape
        "Top 10 Most Paradise-Like {destinations}",
        "Top 10 Most Exclusive {private_locations}"
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
            self.model = genai.GenerativeModel('gemini-1.5-flash')
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
        """Use Gemini AI to generate VIRAL, unique, compelling topics with stunning imagery"""
        if not self.model:
            return None

        try:
            category = random.choice(self.CATEGORIES)
            # 40% chance of visual/aspirational topics for stunning imagery
            if random.random() < 0.4 and any(cat in category for cat in ["Luxury", "Exotic", "Opulent", "Beauty", "Fashion", "Architecture", "Art", "Supercars", "Islands", "Gourmet", "Rare", "Paradise", "Premium"]):
                framework = random.choice(self.VISUAL_FRAMEWORKS)
                hook_category = random.choice(["desirable", "aspirational", "visual_intrigue", "curiosity", "exclusivity"])
            else:
                framework = random.choice(self.VIRAL_FRAMEWORKS)
                hook_category = random.choice(list(self.ENGAGEMENT_HOOKS.keys()))
            hooks = self.ENGAGEMENT_HOOKS[hook_category]

            # Determine if this will be a visually-driven topic
            is_visual_topic = any(cat in category for cat in ["Luxury", "Exotic", "Opulent", "Beauty", "Fashion", "Architecture", "Art", "Supercars", "Islands", "Gourmet", "Rare", "Paradise", "Premium"])

            prompt = f"""You are a VIRAL CONTENT MASTERMIND creating YouTube Shorts topics that GET MILLIONS OF VIEWS and SHARES.
Generate ONE ultra-compelling "Top 10" topic that will make viewers STOP SCROLLING INSTANTLY{' and generate STUNNING, ATTRACTIVE IMAGERY' if is_visual_topic else ''}.

Category: {category}
Framework to inspire: {framework}
Engagement Hook Type: {hook_category} ({', '.join(hooks)})

CRITICAL REQUIREMENTS FOR VIRAL TOPICS:
1. Title MUST be SHORT and PUNCHY (under 70 characters preferred)
2. Must trigger INTENSE curiosity, shock, or FOMO
3. Must feel URGENT, FORBIDDEN, or EXCLUSIVE knowledge
4. Use POWER WORDS: "Shocking", "Banned", "Hidden", "Exposed", "Never", "Secret", "Forbidden"
5. Add SPECIFIC NUMBERS or DETAILS (not generic)
6. Create a CURIOSITY GAP - hint at shocking revelation without revealing
7. Make it CONTROVERSIAL or COUNTER-INTUITIVE (challenge common beliefs)
8. Target EMOTIONS: fear, desire, outrage, fascination
9. Must be SHAREABLE - people want to show friends/family
{f'''6. MUST generate VISUALLY STUNNING images - focus on:
   - High luxury aesthetics (gold, diamonds, opulence)
   - Breathtaking natural beauty (exotic locations, waterfalls, landscapes)
   - Aspirational lifestyle imagery (mansions, yachts, exotic cars)
   - Fashion/design masterpieces (runway shows, haute couture, iconic designs)
   - Art and architectural wonders (monuments, galleries, iconic buildings)
   - Premium materials and craftsmanship (rare collections, precious items)
   - Paradise-like environments (exclusive islands, tropical paradises)''' if is_visual_topic else ""}

Viral Topic Examples (STUDY THE INTENSITY):
- "Top 10 Banned Foods That Were Too Dangerous"
- "Top 10 Lies Your Doctor Never Told You"
- "Top 10 Things Billionaires Hide From You"
- "Top 10 Secrets The Government Won't Admit"
- "Top 10 Times People Cheated Death"
- "Top 10 Creepy Things Found In The Ocean"
- "Top 10 Scams Everyone Falls For"
- "Top 10 Dark Secrets Behind Disney"
{f'''- "Top 10 Most Luxurious Mansions Money Can Buy"
- "Top 10 Most Stunning Hidden Locations On Earth"
- "Top 10 Rarest Supercars Ever Made"
- "Top 10 Most Breathtaking Architectural Wonders"
- "Top 10 Dream Vacation Spots Of The Ultra-Wealthy"''' if is_visual_topic else ""}

AVOID these topics (already used):
{chr(10).join(f"- {t}" for t in avoid_topics[:10])}

NOW - Generate ONE irresistible topic{' that will produce gorgeous imagery' if is_visual_topic else ''}:
"Top 10 [SPECIFIC THING] + [Curiosity/Contrast/Urgency Hook]"

Return ONLY the topic title. Be bold, specific, and slightly edge-pushing (but not offensive).
"""

            response = self.model.generate_content(prompt)
            topic = response.text.strip()

            # Clean up
            topic = topic.strip('"').strip("'").strip()
            
            # Ensure quality
            if not topic or len(topic) < 10:
                return None

            # Ensure it starts with "Top 10"
            if not topic.startswith("Top 10"):
                topic = f"Top 10 {topic}"

            logger.info(f"Generated VIRAL topic: {topic} (Visual: {is_visual_topic})")

            return {
                "topic": topic,
                "category": category,
                "method": "ai_viral_generated",
                "hook_type": hook_category,
                "visual_focus": is_visual_topic
            }

        except Exception as e:
            logger.error(f"Failed to generate AI topic: {e}")
            return None

    def _generate_template_topic(self, avoid_topics: List[str]) -> Dict[str, str]:
        """Generate VIRAL topics using proven engagement patterns + stunning visual topics"""
        logger.info("Using viral framework topic generation")

        # ULTRA-VIRAL topic patterns designed for maximum engagement
        viral_examples = [
            # Shocking secrets & lies (HIGH INTENSITY)
            {"topic": "Top 10 Lies Your Doctor Never Told You", "hook": "contrast", "category": "Controversial Truths", "visual": False},
            {"topic": "Top 10 Dark Secrets Behind Famous Brands", "hook": "curiosity", "category": "Dark History & Secrets", "visual": False},
            {"topic": "Top 10 Things Billionaires Hide From You", "hook": "exclusivity", "category": "Power & Influence", "visual": False},
            {"topic": "Top 10 Scams Everyone Falls For", "hook": "urgency", "category": "Psychology & Human Behavior", "visual": False},

            # Banned/forbidden content (CURIOSITY SPIKE)
            {"topic": "Top 10 Banned Foods That Were Too Dangerous", "hook": "exclusivity", "category": "Dark History & Secrets", "visual": False},
            {"topic": "Top 10 Experiments Science Won't Repeat", "hook": "weird", "category": "Scientific Mind-Blowers", "visual": False},
            {"topic": "Top 10 Places You're Forbidden To Visit", "hook": "exclusivity", "category": "Rare Phenomenon & Anomalies", "visual": False},

            # Death/survival (INTENSE EMOTION)
            {"topic": "Top 10 Times People Cheated Death", "hook": "emotional", "category": "Survival & Extreme Scenarios", "visual": False},
            {"topic": "Top 10 Last Words That Will Haunt You", "hook": "weird", "category": "Dark History & Secrets", "visual": False},
            {"topic": "Top 10 Near-Death Experiences That Changed Everything", "hook": "emotional", "category": "Transformation Stories", "visual": False},

            # Creepy/unsettling (VIRAL HORROR)
            {"topic": "Top 10 Creepy Things Found In The Ocean", "hook": "weird", "category": "Rare Phenomenon & Anomalies", "visual": False},
            {"topic": "Top 10 Disturbing Facts About Space", "hook": "weird", "category": "Scientific Mind-Blowers", "visual": False},
            {"topic": "Top 10 Unsolved Disappearances That Defy Logic", "hook": "weird", "category": "Dark History & Secrets", "visual": False},

            # Money/wealth secrets (ASPIRATION)
            {"topic": "Top 10 Side Hustles That Made Millionaires", "hook": "emotional", "category": "Transformation Stories", "visual": False},
            {"topic": "Top 10 Investment Secrets The Rich Won't Share", "hook": "exclusivity", "category": "Power & Influence", "visual": False},

            # Psychology/manipulation (POWER)
            {"topic": "Top 10 Mind Tricks That Control People", "hook": "curiosity", "category": "Psychology & Human Behavior", "visual": False},
            {"topic": "Top 10 Ways You're Being Manipulated Daily", "hook": "urgency", "category": "Controversial Truths", "visual": False},

            # AI/tech fears (TIMELY)
            {"topic": "Top 10 Times AI Scared Scientists", "hook": "weird", "category": "Scientific Mind-Blowers", "visual": False},
            {"topic": "Top 10 Tech Secrets Companies Don't Want Out", "hook": "exclusivity", "category": "Breaking the Rules", "visual": False},
            
            # ==================== VISUAL/IMAGE-FOCUSED TOPICS ====================
            
            # Luxury & aspirational visuals
            {"topic": "Top 10 Most Luxurious Mansions Money Can Buy", "hook": "aspirational", "category": "Luxury Lifestyles & Aesthetics", "visual": True},
            {"topic": "Top 10 Most Exclusive Supercars Only Billionaires Drive", "hook": "desirable", "category": "Supercars & Exotic Vehicles", "visual": True},
            {"topic": "Top 10 Most Breathtaking Hidden Locations On Earth", "hook": "visual_intrigue", "category": "Exotic Destinations & Beauty", "visual": True},
            {"topic": "Top 10 Most Stunning Beaches That Look Like Paradise", "hook": "desirable", "category": "Paradise Experiences", "visual": True},
            
            # Architectural wonders - highly visual
            {"topic": "Top 10 Most Iconic Architectural Wonders Ever Built", "hook": "visual_intrigue", "category": "Architecture & Design Marvels", "visual": True},
            {"topic": "Top 10 Most Beautiful Modern Buildings In The World", "hook": "desirable", "category": "Architectural Wonders", "visual": True},
            
            # Fashion & style - naturally visual
            {"topic": "Top 10 Most Stunning Fashion Collections From Designer Houses", "hook": "aspirational", "category": "Fashion & Style Evolution", "visual": True},
            {"topic": "Top 10 Most Iconic Red Carpet Moments In Fashion History", "hook": "visual_intrigue", "category": "Premium Fashion Houses", "visual": True},
            
            # Art & masterpieces - instantly compelling visuals
            {"topic": "Top 10 Most Valuable Art Masterpieces That Made History", "hook": "visual_intrigue", "category": "Art & Masterpieces", "visual": True},
            
            # Natural beauty - breathtaking imagery
            {"topic": "Top 10 Most Stunning Natural Wonders You Must See", "hook": "desirable", "category": "Natural Wonders & Landscapes", "visual": True},
            {"topic": "Top 10 Most Gorgeous Waterfalls Hiding Around The World", "hook": "visual_intrigue", "category": "Hidden Gems & Underrated", "visual": True},
            
            # Luxury collections & rare items
            {"topic": "Top 10 Most Precious Diamond Collections In The World", "hook": "aspirational", "category": "Rare & Precious Collections", "visual": True},
            {"topic": "Top 10 Rarest Artifacts Ever Discovered By Archaeologists", "hook": "visual_intrigue", "category": "Rare & Precious Collections", "visual": True},
            
            # Exclusive experiences
            {"topic": "Top 10 Most Exclusive Private Islands Only The Rich Can Access", "hook": "aspirational", "category": "Exclusive Islands & Hideaways", "visual": True},
            {"topic": "Top 10 Most Lavish Yacht Experiences In The World", "hook": "desirable", "category": "Opulent & Lavish", "visual": True},
            
            # Gourmet & culinary (food photography is visually stunning)
            {"topic": "Top 10 Most Luxurious Restaurants With Unreal Food Plating", "hook": "desirable", "category": "Gourmet & Culinary Delights", "visual": True},
            {"topic": "Top 10 Most Expensive Dishes That Are Visual Masterpieces", "hook": "visual_intrigue", "category": "Gourmet & Culinary Delights", "visual": True},
        ]

        # Filter out recent topics
        fresh_examples = [e for e in viral_examples if e["topic"] not in avoid_topics]

        if fresh_examples:
            selected = random.choice(fresh_examples)
        else:
            # All examples were recent, pick random anyway
            selected = random.choice(viral_examples)

        selected["method"] = "viral_template_generated"
        logger.info(f"Generated VIRAL topic: {selected['topic']} (Visual: {selected['visual']})")
        return selected

    def _get_emergency_fallback(self) -> Dict[str, str]:
        """Emergency fallback - still a viral topic"""
        return {
            "topic": "Top 10 Secrets Hidden In Plain Sight That Will Change Your Perspective",
            "category": "Psychology & Human Behavior",
            "method": "fallback",
            "hook_type": "curiosity"
        }


if __name__ == "__main__":
    # Test topic generation
    logging.basicConfig(level=logging.INFO)
    selector = TopicSelector()
    topic = selector.generate_topic()
    print(f"\nGenerated Topic: {topic['topic']}")
    print(f"Category: {topic['category']}")
    