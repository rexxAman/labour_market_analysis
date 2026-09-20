import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def fetch_html(url: str, timeout: int = 10) -> str:
    """
    Fetches HTML content from a URL with robust UTF-8 and character set decoding
    to prevent mojibake/garbled text.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8,id;q=0.7,th;q=0.6,ms;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Auto-detect encoding if headers returned default ISO-8859-1 or None
        if response.encoding is None or response.encoding.lower() in ['iso-8859-1', 'ascii']:
            response.encoding = response.apparent_encoding or 'utf-8'
            
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch HTML from {url}: {e}")
        return ""

def extract_text_from_html(html_content: str) -> str:
    """Extracts main text content from HTML, stripping boilerplate."""
    if not html_content:
        return ""
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript', 'svg', 'iframe']):
            element.decompose()
            
        text = soup.get_text(separator='\n')
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from HTML: {e}")
        return ""
