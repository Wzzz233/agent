from typing import Any, Dict, List
import json


def validate_json_format(data: str) -> bool:
    """
    Validate if a string is a valid JSON format

    Args:
        data: String to validate

    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


def validate_message_structure(message: Dict[str, Any]) -> bool:
    """
    Validate the structure of a message dictionary

    Args:
        message: Message dictionary to validate

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(message, dict):
        return False

    if 'role' not in message or 'content' not in message:
        return False

    if not isinstance(message['role'], str) or not isinstance(message['content'], str):
        return False

    valid_roles = ['user', 'assistant', 'system']
    if message['role'] not in valid_roles:
        return False

    return True


def validate_message_list(messages: List[Dict[str, Any]]) -> bool:
    """
    Validate a list of message dictionaries

    Args:
        messages: List of message dictionaries to validate

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(messages, list):
        return False

    for message in messages:
        if not validate_message_structure(message):
            return False

    return True


def sanitize_input(text: str) -> str:
    """
    Sanitize input text by removing potentially harmful content

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text
    """
    # Remove null bytes and other potentially problematic characters
    sanitized = text.replace('\x00', '')  # Remove null bytes
    sanitized = sanitized.strip()  # Remove leading/trailing whitespace

    return sanitized