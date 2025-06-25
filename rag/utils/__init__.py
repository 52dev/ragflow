# This file makes Python treat the `utils` directory as a package.
import logging

def num_tokens_from_string(s: str, model_name: str = "gpt-3.5-turbo") -> int:
    """Returns the number of tokens in a text string (mocked)."""
    logging.debug(f"Mock num_tokens_from_string called for string (len {len(s)}), model_name: {model_name}")
    # A simple heuristic: average token length is around 4 chars.
    # This is a very rough approximation.
    return len(s) // 4

class MockEncoder:
    def __init__(self, name="mock_encoder"):
        self.name = name
        logging.debug(f"MockEncoder '{self.name}' initialized.")

    def encode(self, text: str) -> list[int]:
        """Mock encoding: returns a list of character ASCII values."""
        logging.debug(f"MockEncoder.encode called for text: {text[:50]}...")
        if not isinstance(text, str):
            return []
        return [ord(char) for char in text]

    def decode(self, tokens: list[int]) -> str:
        """Mock decoding: returns a string from ASCII values."""
        logging.debug(f"MockEncoder.decode called for {len(tokens)} tokens.")
        if not isinstance(tokens, list):
            return ""
        try:
            return "".join([chr(token) for token in tokens])
        except ValueError: # e.g. if tokens are not valid ordinals
            logging.warning("MockEncoder.decode received invalid tokens.")
            return ""

# Instantiate a global mock encoder instance, similar to how tiktoken might be used.
encoder = MockEncoder()

# Ensure these are available for import like: from rag.utils import num_tokens_from_string, encoder
__all__ = ['num_tokens_from_string', 'encoder']
