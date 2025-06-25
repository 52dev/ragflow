# Dummy html_parser.py
import logging

class HtmlParser:
    def __init__(self, pdf_parser=None):
        """
        Dummy constructor for HtmlParser.
        The original might take other parsers or configurations.
        """
        logging.info(f"Mock HtmlParser initialized with pdf_parser: {pdf_parser}")
        self.pdf_parser = pdf_parser

    def __call__(self, filename: str, binary_content: bytes = None, callback=None):
        """
        Mock call method for HtmlParser.
        This method is often used to process the HTML file.
        It should return whatever the Invoke component expects.
        The Invoke component seems to pass the result to `json.loads`
        and then to `pd.DataFrame`. So, a list of dicts (serializable to JSON array of objects)
        would be a safe bet.
        """
        logging.info(f"Mock HtmlParser called with filename: {filename}, has_content: {binary_content is not None}")

        # Simulate parsing that results in structured data.
        # Example: a list of paragraphs or sections.
        # This structure should be compatible with pd.DataFrame().
        # If the original returned a complex object, this mock needs to be more detailed.
        # For now, a simple list of dicts.

        mock_parsed_data = [
            {"type": "title", "text": f"Mock Title for {filename}", "page_number": 1},
            {"type": "paragraph", "text": "This is a mock paragraph extracted from the HTML content.", "page_number": 1},
            {"type": "table_caption", "text": "Mock Table 1", "page_number": 1},
            # Add more mock elements as needed by the Invoke component's logic
        ]

        if callback:
            logging.info("Mock HtmlParser calling callback.")
            # The callback structure is unknown, assume it takes the parsed data.
            # Or it might be for progress updates. For a dummy, just call it.
            try:
                callback(mock_parsed_data)
            except Exception as e:
                logging.warning(f"Mock HtmlParser callback failed: {e}")

        logging.info(f"Mock HtmlParser returning: {mock_parsed_data}")
        return mock_parsed_data

    # Add other methods that might be called by the Invoke component.
    # For example, if there's a specific method to extract tables or text:
    # def extract_tables(self, content_bytes, url=""):
    #     logging.info("Mock HtmlParser.extract_tables called.")
    #     return [{"table_id": "mock_table_1", "data": [["cell1", "cell2"]]}]
    #
    # def extract_text(self, content_bytes, url=""):
    #     logging.info("Mock HtmlParser.extract_text called.")
    #     return "Mock extracted text from HTML."

# Example usage in invoke.py:
# from deepdoc.parser import HtmlParser
# ...
# res = HtmlParser()(filename=path, binary_content=requests.get(path, timeout=30).content)
# ...
# df = pd.DataFrame(json.loads(res)) if isinstance(res, str) else pd.DataFrame(res)
