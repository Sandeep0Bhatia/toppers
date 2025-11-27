# Toppers Project Context

## Project Overview
**Toppers** is an AI-powered automated video generator that creates engaging Top 10 list videos for YouTube Shorts. The system uses AI research, Google Gemini image generation, and video composition to produce 60-second vertical videos (1080x1920 for YouTube Shorts format).

## Recent Updates (2025-11-25)

### Contextual Image Generation Implementation
**Problem Solved:** Images were previously generic and not aligned with the specific narration content.

**Solution:** Enhanced the research and image prompt generation pipeline to create contextual images that match the narration focus.

#### Changes Made:

1. **Updated Research Task** ([src/toppers/config/tasks.yaml:1-47](src/toppers/config/tasks.yaml#L1-L47))
   - Added `narration_focus`: The ONE specific fact/moment that will be emphasized in narration
   - Added `visual_context`: Simple 8-word description of the visual moment (e.g., "under construction in 1889")

2. **Updated Image Prompt Task** ([src/toppers/config/tasks.yaml:98-149](src/toppers/config/tasks.yaml#L98-L149))
   - Changed from generic prompts to contextual prompts
   - Format: `[Item Name] [visual_context]`
   - Maintains 10-15 word limit for realistic photography with Gemini

3. **Deployment to Google Cloud Run**
   - Successfully deployed to `toppers-daily-job`
   - Using shared secrets from sibling project `tickr`
   - Verified contextual image generation working correctly

#### Example Transformation:

**Before (Generic):**
```
"Eiffel Tower in Paris during daytime"
```

**After (Contextual):**
```
"Eiffel Tower under construction in 1889"
```
Aligns with narration: "Built for the 1889 World's Fair, it was meant to be temporary!"

---

## Project Structure

```
/Users/sandeep/projects/toppers/
├── job.py                           # Main pipeline orchestrator
├── src/toppers/
│   ├── topic_selector.py            # Generates creative Top 10 topics (Gemini AI)
│   ├── researcher.py                # CrewAI-based research system
│   ├── agents.py                    # CrewAI agent definitions
│   ├── image_generator.py           # AI image generation (Google Gemini)
│   ├── video_generator.py           # Video composition with HTML slides
│   ├── youtube_uploader.py          # YouTube API integration
│   └── config/
│       └── tasks.yaml               # CrewAI task configurations (UPDATED)
├── requirements.txt
├── Dockerfile
├── deploy_job.sh
└── test_contextual_images.py        # Test script for new functionality
```

---

## Pipeline Flow

### 1. Topic Selection ([topic_selector.py](src/toppers/topic_selector.py))
- Uses Google Gemini AI (gemini-1.5-flash)
- Maintains history in Google Cloud Storage (last 30 topics)
- Categories: Beauty, Intelligence, Culture, Nature, Food, History, Innovation, Arts, Wellness, Human Values

### 2. Research & Content Creation ([researcher.py](src/toppers/researcher.py) + [agents.py](src/toppers/agents.py))
Three specialized CrewAI agents:

**A. Research Agent**
- Researches all 10 items with facts, statistics, unique characteristics
- **NEW:** Identifies `narration_focus` (the main fact to emphasize)
- **NEW:** Provides `visual_context` (8-word visual description)

**B. Content Writer Agent**
- Transforms research into 60-second script (140-160 words)
- Structure: Hook (3s) + Countdown (#10→#1) + Payoff + CTA

**C. Image Prompt Agent**
- **NEW:** Creates contextual prompts using `visual_context` from research
- Keeps prompts simple: 10-15 words max
- Format: "A photograph of {item} {visual_context}"

### 3. Image Generation ([image_generator.py](src/toppers/image_generator.py))
- **Current Provider:** Google Gemini (gemini-2.5-flash-image)
- **Other Supported:** DALL-E 3, Stability AI, Replicate
- **Strategy:** Simple, realistic photography (no artistic jargon)
- **Output:** PNG files in `slides/slides_{timestamp}/`

### 4. Video Creation ([video_generator.py](src/toppers/video_generator.py))
- HTML slides for title and CTA (Playwright)
- AI-generated images for items #1-10
- Google Cloud Text-to-Speech for narration
- MoviePy for video assembly (H.264, 1080x1920, 30fps)
- Background music at 15% volume (optional)

### 5. YouTube Upload ([youtube_uploader.py](src/toppers/youtube_uploader.py))
- YouTube Data API v3 with OAuth 2.0
- Uploads as YouTube Short (vertical format)
- Configurable privacy status

---

## Configuration

### Environment Variables ([.env](.env))
```bash
# AI Models
MODEL=gpt-4o-mini
OPENAI_API_KEY=<from secrets>
GEMINI_API_KEY=<from secrets>
SERPER_API_KEY=<from secrets>

# GCP Configuration
GCP_PROJECT_ID=true-solstice-475115-f6
GCP_REGION=us-central1
GCP_BUCKET_NAME=toppers-videos

# Image Generation
IMAGE_GENERATOR=gemini  # Currently using Gemini

# Video Settings
VIDEO_DURATION=60
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
FPS=30

# YouTube
YOUTUBE_PRIVACY=public
```

### Google Cloud Run Job
- **Job Name:** `toppers-daily-job`
- **Region:** `us-central1`
- **Memory:** 4Gi
- **CPU:** 2 cores
- **Timeout:** 30 minutes
- **Service Account:** `764168065157-compute@developer.gserviceaccount.com`
- **Secrets:** Shared with `tickr` project
  - `openai-api-key:latest`
  - `gemini-api-key:latest`
  - `serper-api-key:latest`

---

## Key Implementation Details

### Contextual Image Prompts

**Research Output Example:**
```json
{
  "rank": 1,
  "name": "Grand Canyon",
  "narration_focus": "The sunrise creates spectacular color displays on the canyon walls",
  "visual_context": "sunrise casting hues on canyon walls",
  "key_facts": [...],
  "surprising_fact": "..."
}
```

**Image Prompt Generated:**
```
"Grand Canyon sunrise casting hues on canyon walls"
```

**Narration Alignment:**
```
"Number 1: Grand Canyon. Watch the sunrise here and you'll see nature's
masterpiece unfold as golden and crimson hues paint the ancient rock layers!"
```

### Why This Works

1. **Research Phase** identifies the most interesting visual moment
2. **Image Prompt Phase** uses that specific moment (not generic description)
3. **Script Phase** writes narration that highlights the same moment
4. **Result:** Images and narration are perfectly aligned

### Image Quality Improvements

**Previous Issues:**
- Images were too artistic/illustrated
- Used complex prompts with technical jargon (8K, cinematic, etc.)

**Current Solution:**
- Simple "A photograph of {prompt}" format
- Max 10-15 words
- Realistic photography style
- Google Gemini handles well with simple prompts

---

## Recent Test Run (2025-11-25 18:10 UTC)

**Topic:** "Top 10 Natural Wonders of the World"

**Sample Contextual Prompts Generated:**
1. ✅ "Grand Canyon sunrise casting hues on canyon walls"
2. ✅ "Great Barrier Reef underwater view of flourishing coral and fish"
3. ✅ "Iguazu Falls rainbow over Devil's Throat waterfall"
4. ✅ "Mount Everest climbers at the summit with flags"
5. ✅ "Aurora Borealis colorful lights dancing in a night sky"
6. ✅ "Victoria Falls thundering water plunging into the gorge"
7. ✅ "Salar de Uyuni vast expanse reflecting the sky"
8. ✅ "Antelope Canyon sunlight penetrating through narrow crevices"
9. ✅ "Yosemite National Park sunrise over El Capitan's granite face"
10. ✅ "Table Mountain silhouetted against sunset"

**Results:**
- All 10 images generated successfully
- Video assembly in progress
- Contextual alignment verified ✅

---

## Testing

### Test Script: [test_contextual_images.py](test_contextual_images.py)

```bash
python test_contextual_images.py
```

**What it does:**
1. Runs full research pipeline with new `narration_focus` and `visual_context` fields
2. Generates contextual image prompts
3. Creates script narration
4. Verifies alignment between images and narration
5. Saves results to `test_output/contextual_test_results.json`

---

## Deployment

### Build & Deploy
```bash
# Build AMD64 image for Cloud Run
docker buildx build --platform linux/amd64 \
  -t gcr.io/true-solstice-475115-f6/toppers-daily-job:latest . --push

# Deploy job
gcloud run jobs create toppers-daily-job \
  --image=gcr.io/true-solstice-475115-f6/toppers-daily-job:latest \
  --region=us-central1 \
  --max-retries=1 \
  --task-timeout=30m \
  --memory=4Gi \
  --cpu=2 \
  --service-account=764168065157-compute@developer.gserviceaccount.com \
  --set-env-vars="..." \
  --set-secrets="..."
```

### Execute Job
```bash
gcloud run jobs execute toppers-daily-job --region=us-central1
```

### View Logs
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=toppers-daily-job" \
  --limit=100 \
  --project=true-solstice-475115-f6
```

---

## Dependencies

### Key Packages
- `crewai[tools]` - Multi-agent orchestration
- `google-generativeai` - Gemini AI (topics + images)
- `openai` - DALL-E 3 image generation (fallback)
- `moviepy` - Video composition
- `playwright` - HTML to image rendering
- `google-cloud-storage` - Topic history persistence
- `google-cloud-texttospeech` - Narration audio
- `google-api-python-client` - YouTube uploads

### System Requirements
- Python 3.11
- FFmpeg
- Playwright Chromium browser

---

## Known Issues & Limitations

### Current
- None identified with new contextual image system

### Previous (Resolved)
- ❌ Images were generic, not matching narration → ✅ Fixed with contextual prompts
- ❌ Images too artistic/illustrated → ✅ Fixed with simplified prompts for Gemini

---

## Future Enhancements

### Potential Improvements
1. **Two-pass generation:** Generate images after script is written for even tighter alignment
2. **Dynamic prompt extraction:** Parse narration to extract specific visual details
3. **Multi-provider fallback:** Auto-fallback to DALL-E if Gemini fails
4. **Image style variation:** Allow different styles per topic category

---

## Related Projects

### Sibling Project: Tickr
Located at `/Users/sandeep/projects/agents/tickr/`
- Shares GCP secrets with Toppers
- Similar Cloud Run deployment pattern
- Different content generation focus

---

## Troubleshooting

### Common Issues

**1. Secret Permission Denied**
```
ERROR: Permission denied on secret
```
**Solution:** Use service account `764168065157-compute@developer.gserviceaccount.com` and share secrets from tickr project

**2. ARM64 vs AMD64 Image**
```
ERROR: Container manifest must support amd64/linux
```
**Solution:** Build with `docker buildx build --platform linux/amd64`

**3. Images Too Artistic**
**Solution:** Already fixed! Using simple prompts with Gemini works great.

---

## Success Metrics

### Quality Indicators
- ✅ All 10 images generated successfully
- ✅ Images are contextual to narration content
- ✅ Prompts are simple (10-15 words)
- ✅ Realistic photography style achieved
- ✅ Video assembly completes without errors
- ✅ YouTube upload successful

### Recent Performance (2025-11-25)
- Research: ~2 minutes
- Image Generation: ~6 minutes (10 images via Gemini)
- Video Creation: ~4 minutes
- Upload: ~1 minute
- **Total:** ~13 minutes per video

---

## Contact & Support

- **Project Owner:** sandeep@thehawkai.com
- **GCP Project:** true-solstice-475115-f6
- **GitHub:** (if applicable)

---

## Changelog

### 2025-11-25 - Contextual Image Generation
- ✅ Added `narration_focus` field to research task
- ✅ Added `visual_context` field to research task
- ✅ Updated image prompt generation to use visual context
- ✅ Deployed to Cloud Run with shared tickr secrets
- ✅ Verified contextual images working correctly
- ✅ Created test script for validation

### Previous Updates
- 2025-11-xx - Added Google Gemini image generation support
- 2025-11-xx - Simplified image prompts for realistic photography
- 2025-11-xx - Fixed Playwright Chromium installation in Docker
- 2025-11-xx - Fixed KeyError handling for script/narration keys

---

## Quick Reference

### File Locations
- Main Entry: [job.py](job.py)
- Configuration: [src/toppers/config/tasks.yaml](src/toppers/config/tasks.yaml)
- Image Gen: [src/toppers/image_generator.py](src/toppers/image_generator.py)
- Research: [src/toppers/researcher.py](src/toppers/researcher.py)
- Test Script: [test_contextual_images.py](test_contextual_images.py)

### Important Paths
- Output: `/app/output/content_{timestamp}.json`
- Images: `/app/slides/slides_{timestamp}/rank_{nn}_{name}.png`
- Videos: `/app/videos/toppers_{timestamp}.mp4`

### Key Commands
```bash
# Local test
python test_contextual_images.py

# Deploy
docker buildx build --platform linux/amd64 -t gcr.io/true-solstice-475115-f6/toppers-daily-job:latest . --push

# Execute
gcloud run jobs execute toppers-daily-job --region=us-central1

# Logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=toppers-daily-job" --limit=100
```

---

*Last Updated: 2025-11-25 by Claude (via sandeep@thehawkai.com)*
*Status: ✅ Contextual image generation fully implemented and tested*
