#!/usr/bin/env python3
"""
Debug script to test Sora API integration directly
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def debug_sora_generation():
    """Debug Sora video generation step by step"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No API key found in .env file")
        return
    
    print(f"🔑 Using API key ending in: ...{api_key[-10:]}")
    
    # Create the exact same client configuration as the main code
    client = httpx.AsyncClient(
        base_url="https://api.openai.com",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=180.0,
        verify=True
    )
    
    try:
        # Step 1: Test basic connectivity
        print("\n🔗 Step 1: Testing basic API connectivity...")
        models_response = await client.get("/v1/models")
        print(f"📡 Models API Status: {models_response.status_code}")
        
        if models_response.status_code == 200:
            models = models_response.json()
            sora_models = [m for m in models.get('data', []) if 'sora' in m.get('id', '').lower()]
            print(f"✅ Found {len(sora_models)} Sora models")
            for model in sora_models:
                print(f"   - {model.get('id')}")
        else:
            print(f"❌ Models API failed: {models_response.text}")
            return
        
        # Step 2: Test video creation
        print("\n🎬 Step 2: Testing video generation...")
        
        sora_data = {
            "model": "sora-2-pro",
            "prompt": "A simple test: a red ball bouncing",
            "size": "1280x720"
        }
        
        print(f"📝 Request data: {sora_data}")
        
        video_response = await client.post("/v1/videos", json=sora_data)
        print(f"📡 Video Creation Status: {video_response.status_code}")
        
        if video_response.status_code == 200:
            video_result = video_response.json()
            video_id = video_result.get("id")
            print(f"✅ Video creation successful!")
            print(f"🆔 Video ID: {video_id}")
            print(f"📊 Initial Status: {video_result.get('status')}")
            
            # Step 3: Test status polling
            print(f"\n⏳ Step 3: Testing status polling for video {video_id}...")
            
            for attempt in range(3):  # Just test a few polling attempts
                await asyncio.sleep(2)  # Wait 2 seconds
                
                status_response = await client.get(f"/v1/videos/{video_id}")
                print(f"📡 Status Check {attempt + 1} - HTTP: {status_response.status_code}")
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    current_status = status_result.get("status")
                    progress = status_result.get("progress", 0)
                    
                    print(f"📊 Status: {current_status}, Progress: {progress}%")
                    
                    if current_status == "completed":
                        print("🎉 Video generation completed!")
                        # Look for download URL
                        for url_field in ["url", "video_url", "download_url", "file_url"]:
                            if url_field in status_result:
                                print(f"📥 Download URL found: {url_field}")
                                break
                        else:
                            print("❌ No download URL found in completed response")
                        break
                    elif current_status == "failed":
                        print("❌ Video generation failed")
                        print(f"Error: {status_result.get('error', 'Unknown error')}")
                        break
                else:
                    print(f"❌ Status check failed: {status_response.text}")
                    
            print("✅ Polling test completed")
            
        else:
            print(f"❌ Video creation failed: {video_response.status_code}")
            print(f"Error details: {video_response.text}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        
    finally:
        await client.aclose()
        print("\n🔚 Debug session completed")

if __name__ == "__main__":
    asyncio.run(debug_sora_generation())