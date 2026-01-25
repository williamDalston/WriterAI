# Input sanitization functions
import logging
import re

logger = logging.getLogger(__name__)

def sanitize_input(text: str) -> str:
    '''
    Sanitizes user input to prevent prompt injection or other malicious content.
    Removes potentially harmful characters or sequences.
    '''
    if not isinstance(text, str):
        logger.warning(f"Non-string input to sanitize_input: {type(text)}")
        return str(text) # Convert to string if not already

    # Remove common injection patterns (e.g., triple backticks, special characters)
    # This is a basic example; real sanitization might involve more sophisticated NLP or regex
    sanitized_text = text.replace('```', '')  # Remove markdown code blocks
    sanitized_text = re.sub(r'[<>{}$]', '', sanitized_text) # Remove common special chars
    sanitized_text = sanitized_text.strip() # Remove leading/trailing whitespace

    if len(text) != len(sanitized_text):
        logger.debug(f"Input sanitized: Original '{text[:50]}...' -> Sanitized '{sanitized_text[:50]}...'")
    return sanitized_text

def validate_text_length(text: str, max_length: int) -> bool:
    '''Checks if text length is within limits.'''
    return len(text) <= max_length

# Add more sanitization/validation functions as needed
