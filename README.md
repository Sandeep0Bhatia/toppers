# Toppers - AI-Powered Top 10 List Video Generator

Automatically generates engaging Top 10 list videos for YouTube Shorts using AI research, text-to-image generation, and video composition.

## Features

- **Smart Topic Generation**: AI-generated creative Top 10 topics (beauty, culture, intellect, travel, etc.)
- **Deep Research**: Comprehensive analysis of each Top 10 item using web search and AI
- **Text-to-Image Slides**: AI-generated visual slides for each item using Stable Diffusion/DALL-E
- **Video Creation**: Automated video composition with narration and background music
- **YouTube Upload**: Automatic upload to YouTube Shorts
- **Cloud Deployment**: Runs as scheduled job on Google Cloud Run

## Project Structure

```
toppers/
├── src/toppers/         # Source code
│   ├── topic_selector.py    # Generates creative Top 10 topics
│   ├── researcher.py         # Researches each Top 10 item
│   ├── agents.py             # CrewAI agents configuration
│   ├── image_generator.py    # Text-to-image generation
│   ├── video_generator.py    # Video creation from slides
│   ├── youtube_uploader.py   # YouTube upload
│   └── config/               # Configuration files
│       └── tasks.yaml        # CrewAI tasks
├── job.py                # Main pipeline script
├── Dockerfile            # Container configuration
├── requirements.txt      # Python dependencies
└── deploy_job.sh        # GCP deployment script
```

## Setup

### Prerequisites

1. Google Cloud Project with billing enabled
2. YouTube Data API v3 credentials
3. OpenAI API key (for GPT-4 and DALL-E)
4. Serper API key (for web search)
5. Google Cloud Storage bucket

### Environment Variables

Create a `.env` file:

```bash
# AI APIs
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
SERPER_API_KEY=your_serper_key

# Google Cloud
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=toppers-videos

# YouTube (OAuth credentials)
# Place client_secrets.json in project root
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run pipeline
python job.py
```

### Deploy to Google Cloud Run

```bash
# Make deployment script executable
chmod +x deploy_job.sh

# Deploy
./deploy_job.sh
```

## Example Topics

- Top 10 Countries with the Most Beautiful Landscapes
- Top 10 Books That Will Change Your Perspective on Life
- Top 10 Cities with the Kindest People
- Top 10 Historical Figures Who Changed the World
- Top 10 Foods That Boost Brain Power
- Top 10 Places to Find Inner Peace
- Top 10 Innovations That Shaped Modern Society

## Architecture

1. **Topic Selection**: AI generates a random interesting Top 10 topic
2. **Research**: CrewAI agents research each of the 10 items in depth
3. **Image Generation**: Text-to-image AI creates visual slides for each item
4. **Video Creation**: Combines slides with narration and music into 60-second video
5. **Upload**: Automatically uploads to YouTube as a Short

## License

MIT License
