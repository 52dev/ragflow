# This file makes Python treat the `parser` directory as a package.
from .html_parser import HtmlParser # Assuming HtmlParser is in html_parser.py

__all__ = ['HtmlParser']
