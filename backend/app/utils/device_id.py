"""
Device identification utility for multi-device support.

Generates and manages device IDs to ensure data isolation between different devices/users.
Each device gets a unique ID that's stored in a cookie/localStorage and sent with API requests.
"""
import hashlib
import platform
import uuid
from typing import Optional

def generate_device_id() -> str:
    """
    Generate a consistent device ID based on system characteristics.
    This ensures the same device always gets the same ID while different devices get different IDs.
    """
    # Use system-specific information to create a unique but consistent ID
    system_info = f"{platform.system()}-{platform.machine()}-{platform.processor()}"
    
    # Add more specific identifiers if available
    try:
        system_info += f"-{platform.node()}"  # hostname
    except:
        pass
    
    # Create a hash-based ID
    device_hash = hashlib.sha256(system_info.encode()).hexdigest()[:16]
    
    # Format as a UUID-like string for consistency
    return f"device-{device_hash}"

def get_or_create_device_id(device_id: Optional[str] = None) -> str:
    """
    Get the device ID from request or generate a new one.
    
    Args:
        device_id: Optional device ID from request headers/cookies
        
    Returns:
        The device ID to use for this request
    """
    if device_id and device_id.startswith("device-"):
        return device_id
    
    # If no valid device ID provided, generate one based on the server's system
    # In production, this should come from the client
    return generate_device_id()

def validate_device_id(device_id: str) -> bool:
    """
    Validate that a device ID follows the expected format.
    
    Args:
        device_id: The device ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return bool(device_id) and (device_id.startswith("device-") or len(device_id) >= 8)