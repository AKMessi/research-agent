"""
Reddit integration for authentic user discussions.

Uses multiple methods to get Reddit content:
1. Reddit JSON API (no auth needed)
2. Pushshift API (historical data)
3. Search-specific subreddits
"""
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console

console = Console(legacy_windows=True)


@dataclass
class RedditPost:
    """A Reddit post."""
    title: str
    content: str
    author: str
    subreddit: str
    url: str
    permalink: str
    score: int
    num_comments: int
    created_utc: float
    
    @property
    def created_date(self) -> str:
        """Convert UTC timestamp to readable date."""
        return datetime.fromtimestamp(self.created_utc).strftime('%Y-%m-%d')


class RedditScraper:
    """Reddit content scraper using multiple methods."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def search_reddit_json(self, query: str, limit: int = 10) -> List[RedditPost]:
        """
        Search Reddit using the JSON API (no auth needed).
        
        Args:
            query: Search query
            limit: Number of results
        
        Returns:
            List of RedditPost objects
        """
        try:
            url = f"https://www.reddit.com/search.json"
            params = {
                "q": query,
                "limit": limit,
                "sort": "relevance",
                "t": "year"  # Last year
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for child in data.get("data", {}).get("children", []):
                    post_data = child.get("data", {})
                    
                    post = RedditPost(
                        title=post_data.get("title", ""),
                        content=post_data.get("selftext", "")[:2000],
                        author=post_data.get("author", "unknown"),
                        subreddit=post_data.get("subreddit", ""),
                        url=post_data.get("url", ""),
                        permalink=f"https://reddit.com{post_data.get('permalink', '')}",
                        score=post_data.get("score", 0),
                        num_comments=post_data.get("num_comments", 0),
                        created_utc=post_data.get("created_utc", 0)
                    )
                    posts.append(post)
                
                return posts
            else:
                console.print(f"[dim]Reddit API returned {response.status_code}[/dim]")
                
        except Exception as e:
            console.print(f"[dim]Reddit JSON API error: {e}[/dim]")
        
        return []
    
    def get_subreddit_posts(self, subreddit: str, query: str = "", limit: int = 10) -> List[RedditPost]:
        """
        Get posts from a specific subreddit.
        
        Args:
            subreddit: Subreddit name (without r/)
            query: Optional search term
            limit: Number of posts
        
        Returns:
            List of RedditPost objects
        """
        try:
            if query:
                # Search within subreddit
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": query,
                    "limit": limit,
                    "sort": "relevance",
                    "restrict_sr": "on"
                }
            else:
                # Get hot posts
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                params = {"limit": limit}
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for child in data.get("data", {}).get("children", []):
                    post_data = child.get("data", {})
                    
                    post = RedditPost(
                        title=post_data.get("title", ""),
                        content=post_data.get("selftext", "")[:2000],
                        author=post_data.get("author", "unknown"),
                        subreddit=post_data.get("subreddit", ""),
                        url=post_data.get("url", ""),
                        permalink=f"https://reddit.com{post_data.get('permalink', '')}",
                        score=post_data.get("score", 0),
                        num_comments=post_data.get("num_comments", 0),
                        created_utc=post_data.get("created_utc", 0)
                    )
                    posts.append(post)
                
                return posts
                
        except Exception as e:
            console.print(f"[dim]Subreddit fetch error: {e}[/dim]")
        
        return []
    
    def search_product_reviews(self, product_name: str, context: str = "") -> List[RedditPost]:
        """
        Search for product reviews and discussions across relevant subreddits.
        
        Args:
            product_name: Product to search for
            context: Additional context
        
        Returns:
            List of RedditPost objects
        """
        all_posts = []
        
        # Build search queries
        search_terms = [product_name]
        if context:
            search_terms.append(context)
        
        query = " ".join(search_terms)
        
        # Method 1: General Reddit search
        console.print(f"[dim]  Searching Reddit: {query}[/dim]")
        posts = self.search_reddit_json(query, limit=10)
        all_posts.extend(posts)
        
        # Method 2: Search relevant subreddits directly
        relevant_subreddits = []
        query_lower = query.lower()
        
        # Determine relevant subreddits based on query
        if any(word in query_lower for word in ["gpu", "graphics", "rtx", "amd", "nvidia"]):
            relevant_subreddits = ["buildapc", "hardware", "nvidia", "amd", "gpus"]
        elif any(word in query_lower for word in ["laptop", "computer"]):
            relevant_subreddits = ["laptops", "SuggestALaptop", "buildapc"]
        elif any(word in query_lower for word in ["phone", "smartphone", "iphone", "android"]):
            relevant_subreddits = ["phones", "PickAnAndroidForMe", "iphone"]
        elif any(word in query_lower for word in ["camera", "photography"]):
            relevant_subreddits = ["cameras", "photography", "videography"]
        else:
            relevant_subreddits = ["BuyItForLife", "goodvalue", "Frugal"]
        
        # Search each subreddit
        for subreddit in relevant_subreddits[:3]:
            try:
                console.print(f"[dim]  Searching r/{subreddit}...[/dim]")
                sub_posts = self.get_subreddit_posts(subreddit, product_name, limit=5)
                all_posts.extend(sub_posts)
            except Exception as e:
                console.print(f"[dim]  r/{subreddit} error: {e}[/dim]")
        
        # Remove duplicates by permalink
        seen = set()
        unique_posts = []
        for post in all_posts:
            if post.permalink not in seen:
                seen.add(post.permalink)
                unique_posts.append(post)
        
        # Sort by score
        unique_posts.sort(key=lambda x: x.score, reverse=True)
        
        return unique_posts[:15]  # Return top 15
    
    def format_for_llm(self, posts: List[RedditPost]) -> str:
        """
        Format Reddit posts for LLM consumption.
        
        Args:
            posts: List of RedditPost objects
        
        Returns:
            Formatted string
        """
        if not posts:
            return ""
        
        formatted = []
        formatted.append("=== REDDIT DISCUSSIONS ===\n")
        
        for i, post in enumerate(posts[:10], 1):
            formatted.append(f"\n--- Reddit Post {i} ---")
            formatted.append(f"Title: {post.title}")
            formatted.append(f"Subreddit: r/{post.subreddit}")
            formatted.append(f"Upvotes: {post.score} | Comments: {post.num_comments}")
            formatted.append(f"Date: {post.created_date}")
            content_preview = post.content[:600] + "..." if len(post.content) > 600 else post.content
            formatted.append(f"Content: {content_preview}")
            formatted.append(f"Link: {post.permalink}")
        
        return "\n".join(formatted)


def get_reddit_scraper() -> RedditScraper:
    """Factory function to get Reddit scraper."""
    return RedditScraper()
