# AI Integration Setup Guide

## Overview
This guide will help you set up AI integrations for your YouTube automation pipeline, including OpenAI GPT for content generation and Sora AI for video creation.

## Required API Keys

### 1. OpenAI API Key (Required for GPT and DALL-E)
1. Visit [OpenAI API](https://platform.openai.com/api-keys)
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the API key

### 2. Sora AI API Key (Future)
- Sora AI is currently in limited preview
- API access will be available in the future
- For now, the system uses mock generation for testing

## Configuration Setup

### Method 1: Environment Variables (Recommended)
Create a `.env` file in your project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
ENABLE_GPT=true
ENABLE_DALLE=false  # Set to true if you want thumbnail generation

# Sora AI Configuration (Future)
SORA_API_KEY=your_sora_api_key_when_available
ENABLE_SORA=false  # Currently set to false for mock mode

# AI Features
AI_MOCK_MODE=true  # Set to false when real APIs are available
```

### Method 2: Configuration File
Add to your `config/config.json`:

```json
{
  "ai": {
    "openai_api_key": "your_openai_api_key_here",
    "sora_api_key": "your_sora_api_key_when_available",
    "enable_sora": false,
    "enable_gpt": true,
    "enable_dalle": false
  }
}
```

## Install Required Dependencies

Run these commands to install AI dependencies:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Install OpenAI library
pip install openai

# Install image processing (for thumbnails)
pip install Pillow

# Install requests (for API calls)
pip install requests
```

## Features Available

### 1. GPT-Powered Content Generation ✅
- **Title Generation**: SEO-optimized YouTube titles
- **Description Creation**: Engaging video descriptions with hashtags
- **Tag Suggestions**: Relevant tags for better discoverability
- **Prompt Enhancement**: Improve basic prompts for better AI generation

### 2. Video Generation (Mock Mode) 🧪
- **Sora AI Integration**: Ready for when API becomes available
- **Mock Generation**: Creates placeholder video metadata for testing
- **Multiple Styles**: Cinematic, realistic, artistic, documentary

### 3. Thumbnail Generation (Optional) 🎨
- **DALL-E Integration**: AI-generated custom thumbnails
- **Text Thumbnails**: Simple fallback thumbnail creation
- **Automatic Processing**: Thumbnails generated with each video

## Usage Examples

### Web Dashboard
1. Navigate to `http://localhost:8000`
2. Use the "AI Content Generation" section
3. Enter a prompt like: "A cat walking through a futuristic city"
4. Click "Generate Video" to start the full pipeline

### API Endpoints
- `POST /api/ai/generate` - Generate complete AI content
- `POST /api/ai/enhance-prompt` - Enhance a basic prompt
- `GET /api/ai/status` - Check AI services status
- `GET /api/ai/jobs` - List generation jobs

### Example API Call
```bash
curl -X POST "http://localhost:8000/api/ai/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A peaceful sunset over mountains with birds flying",
    "style": "cinematic"
  }'
```

## Current Limitations & Roadmap

### Current Status
- ✅ GPT integration for metadata generation
- ✅ Mock video generation system
- ✅ Web interface for AI features
- ✅ Real-time job monitoring
- 🔄 OpenAI dependencies need to be installed
- 🔄 API keys need to be configured

### Future Enhancements
- 🔮 Real Sora AI integration (when API is available)
- 🔮 Advanced prompt templates
- 🔮 Content scheduling and batching
- 🔮 Analytics and performance tracking
- 🔮 Custom style templates

## Testing the AI Pipeline

### 1. Check AI Status
```bash
curl http://localhost:8000/api/ai/status
```

### 2. Test Prompt Enhancement
```bash
curl -X POST "http://localhost:8000/api/ai/enhance-prompt" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "cat video"}'
```

### 3. Generate Test Content
Use the web dashboard to generate test content and monitor the process in real-time.

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Working**
   - Verify the key is correct and active
   - Check your OpenAI account has sufficient credits
   - Ensure the key has proper permissions

2. **Import Errors**
   - Install missing dependencies: `pip install openai Pillow requests`
   - Activate the virtual environment

3. **WebSocket Connection Issues**
   - Ensure `websockets` is installed: `pip install websockets`
   - Check firewall settings for port 8000

4. **Mock Mode Not Working**
   - Check file permissions for the `videos/input` directory
   - Verify the logging directory exists: `mkdir -p logs`

## Support

For questions or issues:
1. Check the logs in the `logs/` directory
2. Use the web dashboard to monitor real-time status
3. Review the AI status endpoint for configuration issues

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Regularly rotate your API keys
- Monitor your API usage and costs