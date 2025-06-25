# Dummy web_utils.py
import re
import logging

def is_valid_url(url: str) -> bool:
    """
    Mock function to validate a URL.
    A simple regex check for basic URL structure.
    """
    if not isinstance(url, str):
        return False

    # This is a very basic regex for URL validation.
    # A more robust one would be much more complex.
    # For mocking purposes, this should suffice.
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https:// or ftp:// or ftps://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    is_valid = re.match(regex, url) is not None
    logging.debug(f"Mock is_valid_url called for '{url}', result: {is_valid}")
    return is_valid

# Example usage in crawler.py:
# from api.utils.web_utils import is_valid_url
# if not is_valid_url(self._param.url):
#     raise ValueError("Invalid URL")
