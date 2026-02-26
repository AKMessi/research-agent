"""
YouTube transcript and metadata extraction.

Extracts video transcripts for tech review channels.
Uses youtube-transcript-api (free).
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import re
from rich.console import Console

console = Console(legacy_windows=True)

# Popular tech review channels for GPU/hardware reviews
TECH_CHANNELS = [
    "UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips
    "UCR0O0gJH3_ZI0lLGwSi6B1w",  # Hardware Unboxed
    "UCkWQ0gDrqOCmcUKzHjJhjrg",  # Gamers Nexus
    "UCpOlO8lX_-IbC7oMmEx8_gA",  # JayzTwoCents
    "UCJ4h45yYWK_uXx9lsvJgV0g",  # Paul's Hardware
    "UC0XJDob2KV1VjhPIZboOPdw",  # Digital Foundry
]


@dataclass
class YouTubeVideo:
    """YouTube video with transcript."""
    video_id: str
    title: str
    channel: str
    transcript: str
    transcript_segments: List[Dict[str, Any]]
    url: str
    duration: int = 0
    view_count: int = 0
    published_at: str = ""
    success: bool = False
    error: Optional[str] = None


class YouTubeScraper:
    """
    YouTube video transcript scraper.
    
    Note: Requires youtube-transcript-api to be installed.
    pip install youtube-transcript-api
    """
    
    def __init__(self):
        self.transcript_api = None
        self.youtube_api = None
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.transcript_api = YouTubeTranscriptApi
        except ImportError:
            console.print("[yellow]youtube-transcript-api not installed. Transcript extraction disabled.[/yellow]")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL.
        
        Args:
            url: YouTube URL
        
        Returns:
            Video ID or None
        """
        # Patterns for YouTube URLs
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/watch\?.*v=)([^&\n?#]+)',
            r'youtube\.com\/shorts\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try parsing
        parsed = urlparse(url)
        if parsed.hostname in ('youtu.be',):
            return parsed.path[1:]
        if parsed.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [None])[0]
            if parsed.path.startswith(('/embed/', '/v/')):
                return parsed.path.split('/')[2]
        
        return None
    
    def get_transcript(self, video_id: str) -> YouTubeVideo:
        """
        Get transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            YouTubeVideo with transcript
        """
        if not self.transcript_api:
            return YouTubeVideo(
                video_id=video_id,
                title="",
                channel="",
                transcript="",
                transcript_segments=[],
                url=f"https://youtube.com/watch?v={video_id}",
                success=False,
                error="youtube-transcript-api not installed"
            )
        
        try:
            # Get transcript
            transcript_list = self.transcript_api.get_transcript(video_id)
            
            # Combine all text
            full_text = " ".join([item['text'] for item in transcript_list])
            
            # Get video info (basic)
            url = f"https://youtube.com/watch?v={video_id}"
            
            return YouTubeVideo(
                video_id=video_id,
                title=f"Video {video_id}",  # Would need YouTube API for real title
                channel="",
                transcript=full_text[:5000],  # Limit length
                transcript_segments=transcript_list[:50],  # Limit segments
                url=url,
                success=True
            )
            
        except Exception as e:
            return YouTubeVideo(
                video_id=video_id,
                title="",
                channel="",
                transcript="",
                transcript_segments=[],
                url=f"https://youtube.com/watch?v={video_id}",
                success=False,
                error=str(e)
            )
    
    def search_videos(self, query: str, max_results: int = 5) -> List[str]:
        """
        Search for YouTube videos related to query.
        
        Note: Requires YouTube Data API or scraping. 
        For now, returns empty list (implement with API key).
        
        Args:
            query: Search query
            max_results: Max results to return
        
        Returns:
            List of video IDs
        """
        # Without YouTube API, we can't search
        # This would require YOUTUBE_API_KEY
        return []
    
    def process_search_results(self, urls: List[str]) -> List[YouTubeVideo]:
        """
        Process YouTube URLs from search results.
        
        Args:
            urls: List of URLs that might be YouTube
        
        Returns:
            List of YouTubeVideo with transcripts
        """
        videos = []
        
        for url in urls:
            video_id = self.extract_video_id(url)
            if video_id:
                video = self.get_transcript(video_id)
                if video.success:
                    videos.append(video)
        
        return videos
    
    def format_for_llm(self, videos: List[YouTubeVideo]) -> str:
        """
        Format video transcripts for LLM consumption.
        
        Args:
            videos: List of YouTubeVideo objects
        
        Returns:
            Formatted string
        """
        if not videos:
            return ""
        
        formatted = []
        formatted.append("=== YOUTUBE VIDEO TRANSCRIPTS ===\n")
        
        for i, video in enumerate(videos[:3], 1):  # Top 3
            formatted.append(f"\n--- Video {i} ---")
            formatted.append(f"URL: {video.url}")
            formatted.append(f"Transcript excerpt:\n{video.transcript[:1500]}...")
        
        return "\n".join(formatted)


def get_youtube_scraper() -> YouTubeScraper:
    """Factory function to get YouTube scraper."""
    return YouTubeScraper()
