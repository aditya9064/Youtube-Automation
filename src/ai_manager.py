#!/usr/bin/env python3
"""
AI Manager for YouTube Automation Pipeline
Handles AI content generation including video, titles, descriptions, and thumbnails
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import requests
import time

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI library not available. Install with: pip install openai")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL library not available. Install with: pip install Pillow")

class AIContentGenerator:
    """Manages AI content generation for video automation"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.setup_logging()
        self.load_ai_config()
        
    def setup_logging(self):
        """Setup logging for AI operations"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler('logs/ai_generation.log')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def load_ai_config(self):
        """Load AI configuration from config manager"""
        try:
            if self.config_manager:
                config = self.config_manager.load_config()
                self.ai_config = config.get('ai', {})
            else:
                # Load from environment or default config
                self.ai_config = {
                    'openai_api_key': os.getenv('OPENAI_API_KEY'),
                    'sora_api_key': os.getenv('SORA_API_KEY'),
                    'enable_sora': os.getenv('ENABLE_SORA', 'false').lower() == 'true',
                    'enable_gpt': os.getenv('ENABLE_GPT', 'true').lower() == 'true',
                    'enable_dalle': os.getenv('ENABLE_DALLE', 'false').lower() == 'true'
                }
                
            # Initialize OpenAI client if available
            if OPENAI_AVAILABLE and self.ai_config.get('openai_api_key'):
                openai.api_key = self.ai_config['openai_api_key']
                self.openai_client = openai.OpenAI(api_key=self.ai_config['openai_api_key'])
            else:
                self.openai_client = None
                
        except Exception as e:
            self.logger.error(f"Error loading AI config: {e}")
            self.ai_config = {}
            self.openai_client = None

    async def generate_video_content(self, prompt: str, style: str = "cinematic") -> Dict:
        """
        Generate video content using Sora AI
        Note: This is a placeholder as Sora API is not publicly available yet
        """
        try:
            self.logger.info(f"Starting video generation with prompt: {prompt[:50]}...")
            
            if not self.ai_config.get('enable_sora', False):
                return {
                    'success': False,
                    'error': 'Sora AI is not enabled in configuration',
                    'mock_mode': True
                }
            
            # Mock Sora API call (replace with actual API when available)
            video_data = await self._mock_sora_generation(prompt, style)
            
            if video_data['success']:
                self.logger.info(f"Video generated successfully: {video_data['filename']}")
                
                # Generate metadata for the video
                metadata = await self.generate_video_metadata(prompt, video_data['filename'])
                video_data['metadata'] = metadata
                
            return video_data
            
        except Exception as e:
            self.logger.error(f"Error generating video content: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _mock_sora_generation(self, prompt: str, style: str) -> Dict:
        """
        Mock Sora video generation for testing
        Replace this with actual Sora API calls when available
        """
        try:
            # Simulate API call delay
            await asyncio.sleep(2)
            
            # Generate a mock filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sora_generated_{timestamp}.mp4"
            output_path = Path("videos/input") / filename
            
            # Create placeholder video info
            video_info = {
                'success': True,
                'filename': filename,
                'filepath': str(output_path),
                'duration': 30,  # seconds
                'resolution': '1920x1080',
                'format': 'mp4',
                'prompt': prompt,
                'style': style,
                'generated_at': datetime.now().isoformat(),
                'mock_mode': True
            }
            
            # Log the mock generation
            self.logger.info(f"Mock video generated: {filename}")
            
            return video_info
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Mock generation failed: {str(e)}"
            }

    async def generate_video_metadata(self, original_prompt: str, video_filename: str) -> Dict:
        """Generate title, description, and tags using GPT"""
        try:
            if not self.ai_config.get('enable_gpt', True) or not self.openai_client:
                return self._generate_fallback_metadata(original_prompt, video_filename)
            
            self.logger.info("Generating video metadata with GPT...")
            
            # Create a comprehensive prompt for metadata generation
            metadata_prompt = f"""
            Generate YouTube video metadata for an AI-generated video with the following details:
            
            Original Prompt: {original_prompt}
            Video File: {video_filename}
            
            Please provide:
            1. A catchy, SEO-friendly title (max 100 characters)
            2. An engaging description (200-500 words)
            3. 10-15 relevant tags
            4. A suggested category
            
            Format the response as JSON with keys: title, description, tags, category
            
            The video was generated using Sora AI. Make the content appealing to YouTube viewers interested in AI-generated content.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert YouTube content creator and SEO specialist."},
                    {"role": "user", "content": metadata_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                json_str = content[start_idx:end_idx]
                metadata = json.loads(json_str)
                
                # Validate and clean up
                metadata = self._validate_metadata(metadata)
                
                self.logger.info("Metadata generated successfully with GPT")
                return metadata
                
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse GPT response as JSON, using fallback")
                return self._generate_fallback_metadata(original_prompt, video_filename)
            
        except Exception as e:
            self.logger.error(f"Error generating metadata with GPT: {e}")
            return self._generate_fallback_metadata(original_prompt, video_filename)

    def _generate_fallback_metadata(self, prompt: str, filename: str) -> Dict:
        """Generate fallback metadata without AI"""
        # Extract keywords from prompt
        words = prompt.lower().split()
        keywords = [word for word in words if len(word) > 3][:10]
        
        # Generate basic metadata
        timestamp = datetime.now().strftime("%B %d, %Y")
        
        metadata = {
            'title': f"AI Generated Video: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
            'description': f"""
This amazing video was generated using advanced AI technology!

🎬 Original Prompt: {prompt}
🤖 Generated with: Sora AI by OpenAI
📅 Created: {timestamp}
🔥 File: {filename}

This video showcases the incredible capabilities of AI in creating stunning visual content. The AI understood the prompt and created this unique video that brings the concept to life.

#AIGenerated #SoraAI #OpenAI #ArtificialIntelligence #VideoAI #GenerativeAI #AIVideo #MachineLearning #DeepLearning #AIContent

Like and subscribe for more AI-generated content!
            """.strip(),
            'tags': [
                'AI Generated', 'Sora AI', 'OpenAI', 'Artificial Intelligence',
                'Video AI', 'Generative AI', 'AI Video', 'Machine Learning',
                'Deep Learning', 'AI Content', 'Technology', 'Innovation'
            ] + keywords,
            'category': 'Science & Technology'
        }
        
        return self._validate_metadata(metadata)

    def _validate_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean up metadata"""
        # Ensure title is within YouTube limits
        if len(metadata.get('title', '')) > 100:
            metadata['title'] = metadata['title'][:97] + '...'
        
        # Ensure description is reasonable length
        if len(metadata.get('description', '')) > 5000:
            metadata['description'] = metadata['description'][:4997] + '...'
        
        # Limit tags
        if isinstance(metadata.get('tags'), list) and len(metadata['tags']) > 15:
            metadata['tags'] = metadata['tags'][:15]
        
        # Ensure category is valid
        valid_categories = [
            'Film & Animation', 'Autos & Vehicles', 'Music', 'Pets & Animals',
            'Sports', 'Travel & Events', 'Gaming', 'People & Blogs',
            'Comedy', 'Entertainment', 'News & Politics', 'Howto & Style',
            'Education', 'Science & Technology', 'Nonprofits & Activism'
        ]
        
        if metadata.get('category') not in valid_categories:
            metadata['category'] = 'Science & Technology'
        
        return metadata

    async def generate_thumbnail(self, video_path: str, prompt: str) -> Optional[str]:
        """Generate or create a thumbnail for the video"""
        try:
            if not PIL_AVAILABLE:
                self.logger.warning("PIL not available, skipping thumbnail generation")
                return None
            
            self.logger.info(f"Generating thumbnail for: {video_path}")
            
            # Try DALL-E first if available
            if self.ai_config.get('enable_dalle', False) and self.openai_client:
                thumbnail_path = await self._generate_dalle_thumbnail(prompt, video_path)
                if thumbnail_path:
                    return thumbnail_path
            
            # Fallback to simple text thumbnail
            return self._generate_text_thumbnail(prompt, video_path)
            
        except Exception as e:
            self.logger.error(f"Error generating thumbnail: {e}")
            return None

    async def _generate_dalle_thumbnail(self, prompt: str, video_path: str) -> Optional[str]:
        """Generate thumbnail using DALL-E"""
        try:
            # Create thumbnail prompt
            thumbnail_prompt = f"Create a YouTube thumbnail for a video about: {prompt}. Make it eye-catching, colorful, and engaging for YouTube viewers. Include text overlay if appropriate."
            
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=thumbnail_prompt,
                size="1792x1024",  # YouTube thumbnail ratio
                quality="standard",
                n=1,
            )
            
            # Download and save the image
            image_url = response.data[0].url
            
            # Create thumbnail filename
            video_name = Path(video_path).stem
            thumbnail_path = f"videos/thumbnails/{video_name}_thumbnail.png"
            
            # Ensure thumbnails directory exists
            Path("videos/thumbnails").mkdir(parents=True, exist_ok=True)
            
            # Download and save
            img_response = requests.get(image_url)
            with open(thumbnail_path, 'wb') as f:
                f.write(img_response.content)
            
            self.logger.info(f"DALL-E thumbnail generated: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            self.logger.error(f"DALL-E thumbnail generation failed: {e}")
            return None

    def _generate_text_thumbnail(self, prompt: str, video_path: str) -> str:
        """Generate a simple text-based thumbnail"""
        try:
            # Create a simple thumbnail with text
            img = Image.new('RGB', (1280, 720), color='#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("Arial.ttf", 60)
                small_font = ImageFont.truetype("Arial.ttf", 40)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Add main text
            main_text = "AI Generated Video"
            w, h = draw.textsize(main_text, font=font)
            draw.text(((1280-w)/2, 250), main_text, fill='white', font=font)
            
            # Add prompt text (truncated)
            prompt_text = prompt[:50] + ("..." if len(prompt) > 50 else "")
            w2, h2 = draw.textsize(prompt_text, font=small_font)
            draw.text(((1280-w2)/2, 350), prompt_text, fill='#ffdd44', font=small_font)
            
            # Add Sora AI branding
            brand_text = "Powered by Sora AI"
            w3, h3 = draw.textsize(brand_text, font=small_font)
            draw.text(((1280-w3)/2, 450), brand_text, fill='#44ddff', font=small_font)
            
            # Save thumbnail
            video_name = Path(video_path).stem
            thumbnail_path = f"videos/thumbnails/{video_name}_thumbnail.png"
            
            # Ensure directory exists
            Path("videos/thumbnails").mkdir(parents=True, exist_ok=True)
            
            img.save(thumbnail_path)
            
            self.logger.info(f"Text thumbnail generated: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            self.logger.error(f"Text thumbnail generation failed: {e}")
            return None

    async def enhance_prompt(self, basic_prompt: str) -> str:
        """Enhance a basic prompt using GPT to make it more detailed for Sora"""
        try:
            if not self.openai_client:
                return basic_prompt
            
            enhancement_prompt = f"""
            Enhance this basic video prompt for Sora AI video generation. Make it more detailed, cinematic, and specific while keeping the original intent:
            
            Basic prompt: {basic_prompt}
            
            Enhanced prompt should include:
            - Specific visual details
            - Camera movements and angles
            - Lighting and atmosphere
            - Style and mood
            - Duration suggestions
            
            Keep it under 200 words and make it compelling for AI video generation.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in AI video generation prompts and cinematic direction."},
                    {"role": "user", "content": enhancement_prompt}
                ],
                max_tokens=300,
                temperature=0.8
            )
            
            enhanced = response.choices[0].message.content.strip()
            self.logger.info("Prompt enhanced with GPT")
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Error enhancing prompt: {e}")
            return basic_prompt

    def get_ai_status(self) -> Dict:
        """Get status of AI services"""
        status = {
            'openai_available': OPENAI_AVAILABLE and bool(self.openai_client),
            'pil_available': PIL_AVAILABLE,
            'sora_enabled': self.ai_config.get('enable_sora', False),
            'gpt_enabled': self.ai_config.get('enable_gpt', True),
            'dalle_enabled': self.ai_config.get('enable_dalle', False),
            'config_loaded': bool(self.ai_config)
        }
        
        return status


class ContentPipeline:
    """Complete AI content generation pipeline"""
    
    def __init__(self, config_manager=None):
        self.ai_generator = AIContentGenerator(config_manager)
        self.setup_logging()
        
    def setup_logging(self):
        """Setup pipeline logging"""
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler('logs/content_pipeline.log')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    async def generate_complete_content(self, prompt: str, style: str = "cinematic") -> Dict:
        """Generate complete video content including video, metadata, and thumbnail"""
        try:
            self.logger.info(f"Starting complete content generation for: {prompt[:50]}...")
            
            results = {
                'success': False,
                'prompt': prompt,
                'style': style,
                'started_at': datetime.now().isoformat(),
                'steps': {}
            }
            
            # Step 1: Enhance the prompt
            self.logger.info("Step 1: Enhancing prompt...")
            enhanced_prompt = await self.ai_generator.enhance_prompt(prompt)
            results['enhanced_prompt'] = enhanced_prompt
            results['steps']['prompt_enhancement'] = {'success': True}
            
            # Step 2: Generate video
            self.logger.info("Step 2: Generating video...")
            video_result = await self.ai_generator.generate_video_content(enhanced_prompt, style)
            results['video'] = video_result
            results['steps']['video_generation'] = {'success': video_result.get('success', False)}
            
            if not video_result.get('success'):
                results['error'] = f"Video generation failed: {video_result.get('error', 'Unknown error')}"
                return results
            
            # Step 3: Generate thumbnail
            self.logger.info("Step 3: Generating thumbnail...")
            thumbnail_path = await self.ai_generator.generate_thumbnail(
                video_result['filepath'], 
                enhanced_prompt
            )
            results['thumbnail'] = thumbnail_path
            results['steps']['thumbnail_generation'] = {'success': bool(thumbnail_path)}
            
            # Step 4: Compile final result
            results['success'] = True
            results['completed_at'] = datetime.now().isoformat()
            
            # Calculate total time
            start_time = datetime.fromisoformat(results['started_at'])
            end_time = datetime.fromisoformat(results['completed_at'])
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Complete content generation finished in {results['duration_seconds']:.1f}s")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in complete content generation: {e}")
            results['success'] = False
            results['error'] = str(e)
            results['completed_at'] = datetime.now().isoformat()
            return results


if __name__ == "__main__":
    # Test the AI manager
    import asyncio
    
    async def test_ai_manager():
        ai_manager = AIContentGenerator()
        
        # Test status
        status = ai_manager.get_ai_status()
        print("AI Status:", json.dumps(status, indent=2))
        
        # Test pipeline
        pipeline = ContentPipeline()
        result = await pipeline.generate_complete_content(
            "A cat walking through a futuristic city at sunset"
        )
        
        print("Pipeline Result:", json.dumps(result, indent=2, default=str))
    
    asyncio.run(test_ai_manager())