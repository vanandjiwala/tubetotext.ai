# app/api/v1/endpoints/youtube.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
import re
from urllib.parse import urlparse, parse_qs
import httpx
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import asyncio

router = APIRouter()

# Pydantic models
class YouTubeURLRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    language: str = Field(default='en', description="Preferred transcript language (e.g., 'en', 'es', 'fr')")
    
    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v):
        if not v:
            raise ValueError('URL cannot be empty')
        
        # Parse the URL
        parsed_url = urlparse(v)
        
        # Check if domain is YouTube
        valid_domains = [
            'youtube.com', 'www.youtube.com', 
            'youtu.be', 'www.youtu.be',
            'm.youtube.com'
        ]
        
        if parsed_url.netloc.lower() not in valid_domains:
            raise ValueError('URL must be from YouTube domain (youtube.com or youtu.be)')
        
        # Extract video ID to validate it's a valid YouTube URL format
        video_id = extract_video_id(v)
        if not video_id:
            raise ValueError('Invalid YouTube URL format')
            
        return v

class YouTubeVideoInfo(BaseModel):
    video_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    view_count: Optional[str] = None
    upload_date: Optional[str] = None
    channel_name: Optional[str] = None
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None
    available_languages: Optional[List[str]] = None
    processed_at: datetime

class YouTubeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[YouTubeVideoInfo] = None
    error: Optional[str] = None

# Helper function to extract video ID from YouTube URL
def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

async def get_video_transcript(video_id: str, language: str = 'en') -> dict:
    """
    Extract transcript from YouTube video using youtube-transcript-api
    """
    try:
        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Get available languages
        available_languages = []
        for transcript in transcript_list:
            available_languages.append(transcript.language_code)
        
        # Try to get transcript in requested language, fallback to first available
        try:
            transcript = transcript_list.find_transcript([language])
        except:
            # If requested language not available, get the first available transcript
            transcript = next(iter(transcript_list))
            language = transcript.language_code
        
        # Fetch the transcript
        transcript_data = transcript.fetch()
        
        # Format transcript as plain text
        formatter = TextFormatter()
        text_transcript = formatter.format_transcript(transcript_data)
        
        return {
            "transcript": text_transcript,
            "language": language,
            "available_languages": available_languages,
            "success": True
        }
        
    except Exception as e:
        return {
            "transcript": None,
            "language": None,
            "available_languages": [],
            "success": False,
            "error": str(e)
        }

async def get_video_info(video_id: str, language: str = 'en') -> dict:
    """
    Get video information and transcript
    For video metadata, you could integrate with YouTube Data API
    For now, we'll focus on transcript extraction
    """
    
    # Get transcript
    transcript_result = await get_video_transcript(video_id, language)
    
    # Mock metadata (in real implementation, use YouTube Data API)
    mock_data = {
        "title": f"Video {video_id}",
        "description": "Video description would come from YouTube Data API",
        "duration": "Unknown",
        "view_count": "Unknown",
        "upload_date": "Unknown",
        "channel_name": "Unknown",
        "transcript": transcript_result.get("transcript"),
        "transcript_language": transcript_result.get("language"),
        "available_languages": transcript_result.get("available_languages", []),
        "transcript_available": transcript_result.get("success", False)
    }
    
    return mock_data

@router.post("/convert", response_model=YouTubeResponse)
async def convert_youtube_to_text(request: YouTubeURLRequest):
    """
    Convert YouTube video to text information
    
    This endpoint accepts a YouTube URL and returns:
    - Video metadata (title, description, duration, etc.)
    - Video transcript/captions as text
    """
    try:
        # Extract video ID
        video_id = extract_video_id(request.url)
        
        if not video_id:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract video ID from URL"
            )
        
        # Get video information and transcript
        video_data = await get_video_info(video_id, request.language)
        
        # Create response
        video_info = YouTubeVideoInfo(
            video_id=video_id,
            title=video_data.get("title"),
            description=video_data.get("description"),
            duration=video_data.get("duration"),
            view_count=video_data.get("view_count"),
            upload_date=video_data.get("upload_date"),
            channel_name=video_data.get("channel_name"),
            transcript=video_data.get("transcript"),
            transcript_language=video_data.get("transcript_language"),
            available_languages=video_data.get("available_languages", []),
            processed_at=datetime.utcnow()
        )
        
        success_message = "Successfully converted YouTube video to text"
        if not video_data.get("transcript_available", False):
            success_message += " (Note: Transcript not available for this video)"
        
        return YouTubeResponse(
            success=True,
            message=success_message,
            data=video_info
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing YouTube video: {str(e)}"
        )

@router.get("/supported-formats")
async def get_supported_youtube_formats():
    """Get information about supported YouTube URL formats"""
    return {
        "supported_formats": [
            "https://www.youtube.com/watch?v=VIDEO_ID",
            "https://youtube.com/watch?v=VIDEO_ID",
            "https://youtu.be/VIDEO_ID",
            "https://www.youtube.com/embed/VIDEO_ID",
            "https://m.youtube.com/watch?v=VIDEO_ID"
        ],
        "domains": [
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "m.youtube.com"
        ]
    }

# Add missing import for asyncio


# Update app/api/v1/api.py - ADD this import and router
# Add this line to your existing imports:
# from app.api.v1.endpoints import youtube

# Add this line to include the router:
# api_router.include_router(
#     youtube.router, 
#     prefix="/youtube", 
#     tags=["youtube"]
# )