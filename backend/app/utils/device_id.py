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
    
    Trusts the frontend device ID for cross-environment consistency.
    The frontend generates device IDs based on browser characteristics,
    ensuring the same device gets the same ID across different environments.
    
    Args:
        device_id: Optional device ID from request headers/cookies
        
    Returns:
        The device ID to use for this request
    """
    # Trust frontend device ID if provided (cross-environment consistency)
    if device_id and (device_id.startswith("device-") or device_id.startswith("rack-")):
        return device_id
    
    # If no valid device ID provided, generate one based on the server's system
    # This is a fallback for requests without device identification
    return generate_device_id()

def validate_device_id(device_id: str) -> bool:
    """
    Validate that a device ID follows the expected format.
    
    Accepts both device IDs (device-*) and rack IDs (RACK-*, rack-*, rack-01-primary) for fleet operations.
    
    Args:
        device_id: The device ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not device_id:
        return False
    
    # Accept device IDs (device-*)
    if device_id.startswith("device-"):
        return len(device_id) >= 10  # device- + at least 8 chars
    
    # Accept rack IDs (RACK-*, rack-*, rack-01-primary)
    if device_id.startswith("RACK-") or device_id.startswith("rack-"):
        return len(device_id) >= 8
    
    # Accept special fleet IDs
    if device_id == "rack-01-primary":
        return True
    
    # Accept other reasonable IDs (fallback)
    return len(device_id) >= 8