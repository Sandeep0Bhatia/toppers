"""
Researcher - Uses CrewAI to research and analyze Top 10 items
"""
import os
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any
from crewai import Crew, Task
from toppers.agents import (
    create_research_agent,
    create_content_writer_agent,
    create_image_prompt_agent
)

logger = logging.getLogger(__name__)


class TopTenResearcher:
    """Researches and creates content for Top 10 lists using CrewAI"""

    def __init__(self):
        self.config_path = Path(__file__).parent / "config" / "tasks.yaml"
        self.tasks_config = self._load_tasks_config()

        # Create agents
        self.research_agent = create_research_agent()
        self.writer_agent = create_content_writer_agent()
        self.visual_agent = create_image_prompt_agent()

    def _load_tasks_config(self) -> Dict:
        """Load tasks configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded tasks config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load tasks config: {e}")
            raise

    def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Research the Top 10 items for a given topic.

        Args:
            topic: The Top 10 topic to research

        Returns:
            Dict with researched items
        """
        logger.info(f"Starting research for: {topic}")

        try:
            # Create research task
            research_task_config = self.tasks_config['research_top10']
            research_task = Task(
                description=research_task_config['description'].format(topic=topic),
                expected_output=research_task_config['expected_output'],
                agent=self.research_agent
            )

            # Create crew and execute
            crew = Crew(
                agents=[self.research_agent],
                tasks=[research_task],
                verbose=True
            )

            result = crew.kickoff()
            logger.info("Research completed")

            # Parse JSON result
            research_data = self._parse_json_result(result)
            return research_data

        except Exception as e:
            logger.error(f"Research failed: {e}")
            raise

    def create_script(self, topic: str, research_data: Dict) -> Dict[str, Any]:
        """
        Create video script from research data.

        Args:
            topic: The Top 10 topic
            research_data: Research results from research_topic()

        Returns:
            Dict with script content
        """
        logger.info(f"Creating script for: {topic}")

        try:
            # Create script task
            script_task_config = self.tasks_config['create_script']
            script_task = Task(
                description=script_task_config['description'].format(
                    topic=topic,
                    research_data=json.dumps(research_data, indent=2)
                ),
                expected_output=script_task_config['expected_output'],
                agent=self.writer_agent
            )

            # Create crew and execute
            crew = Crew(
                agents=[self.writer_agent],
                tasks=[script_task],
                verbose=True
            )

            result = crew.kickoff()
            logger.info("Script created")

            # Parse JSON result
            script_data = self._parse_json_result(result)
            return script_data

        except Exception as e:
            logger.error(f"Script creation failed: {e}")
            raise

    def generate_image_prompts(self, topic: str, research_data: Dict) -> Dict[str, Any]:
        """
        Generate AI image prompts for each Top 10 item.

        Args:
            topic: The Top 10 topic
            research_data: Research results from research_topic()

        Returns:
            Dict with image prompts for each item
        """
        logger.info(f"Generating image prompts for: {topic}")

        try:
            # Create image prompt task
            prompt_task_config = self.tasks_config['generate_image_prompts']
            prompt_task = Task(
                description=prompt_task_config['description'].format(
                    topic=topic,
                    research_data=json.dumps(research_data, indent=2)
                ),
                expected_output=prompt_task_config['expected_output'],
                agent=self.visual_agent
            )

            # Create crew and execute
            crew = Crew(
                agents=[self.visual_agent],
                tasks=[prompt_task],
                verbose=True
            )

            result = crew.kickoff()
            logger.info("Image prompts generated")

            # Parse JSON result
            prompts_data = self._parse_json_result(result)
            return prompts_data

        except Exception as e:
            logger.error(f"Image prompt generation failed: {e}")
            raise

    def _parse_json_result(self, result: Any) -> Dict:
        """Parse JSON from CrewAI result"""
        try:
            # Result might be a string or object
            if isinstance(result, str):
                result_str = result
            elif hasattr(result, 'raw_output'):
                result_str = result.raw_output
            elif hasattr(result, 'output'):
                result_str = result.output
            else:
                result_str = str(result)

            # Clean up markdown code blocks if present
            result_str = result_str.strip()
            if result_str.startswith('```json'):
                result_str = result_str[7:]
            if result_str.startswith('```'):
                result_str = result_str[3:]
            if result_str.endswith('```'):
                result_str = result_str[:-3]
            result_str = result_str.strip()

            # Parse JSON
            data = json.loads(result_str)
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON result: {e}")
            logger.error(f"Raw result: {result_str[:500]}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing result: {e}")
            raise

    def create_full_content(self, topic: str) -> Dict[str, Any]:
        """
        Complete pipeline: research, script, and image prompts.

        Args:
            topic: The Top 10 topic

        Returns:
            Dict with all content: research, script, image_prompts
        """
        logger.info(f"Creating full content for: {topic}")

        try:
            # Step 1: Research
            research_data = self.research_topic(topic)

            # Step 2: Create script
            script_data = self.create_script(topic, research_data)

            # Step 3: Generate image prompts
            image_prompts = self.generate_image_prompts(topic, research_data)

            return {
                "topic": topic,
                "research": research_data,
                "script": script_data,
                "image_prompts": image_prompts
            }

        except Exception as e:
            logger.error(f"Full content creation failed: {e}")
            raise


if __name__ == "__main__":
    # Test researcher
    logging.basicConfig(level=logging.INFO)

    researcher = TopTenResearcher()
    topic = "Top 10 Countries with the Most Beautiful Landscapes"

    content = researcher.create_full_content(topic)

    print("\n=== RESEARCH ===")
    print(json.dumps(content["research"], indent=2)[:500])

    print("\n=== SCRIPT ===")
    print(json.dumps(content["script"], indent=2)[:500])

    print("\n=== IMAGE PROMPTS ===")
    print(json.dumps(content["image_prompts"], indent=2)[:500])
