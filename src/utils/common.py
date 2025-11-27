"""
Common Utility Functions
"""

from datetime import datetime


def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()
