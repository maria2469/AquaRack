"""
Lambda Handler Test Script for AquaRack

Tests AWS Lambda handler functionality locally.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.lambda_handler import handler, _ACTION_MAP
    from app.config import settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


def test_lambda_handler():
    """Test Lambda handler with different actions."""
    print("=" * 60)
    print("AWS Lambda Handler Test")
    print("=" * 60)
    
    print(f"AWS_REGION: {settings.AWS_REGION}")
    print(f"Available actions: {list(_ACTION_MAP.keys())}")
    
    results = []
    
    # Test 1: telemetry_snapshot
    print("\n" + "=" * 60)
    print("1. Testing telemetry_snapshot action")
    print("=" * 60)
    
    try:
        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {
                "action": "telemetry_snapshot"
            }
        }
        
        result = handler(event)
        print(f"[OK] telemetry_snapshot executed successfully")
        print(f"  Result: {result}")
        results.append(("telemetry_snapshot", True))
    except Exception as e:
        print(f"[X] telemetry_snapshot failed: {e}")
        results.append(("telemetry_snapshot", False))
    
    # Test 2: resolve_episode_outcomes
    print("\n" + "=" * 60)
    print("2. Testing resolve_episode_outcomes action")
    print("=" * 60)
    
    try:
        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {
                "action": "resolve_episode_outcomes"
            }
        }
        
        result = handler(event)
        print(f"[OK] resolve_episode_outcomes executed successfully")
        print(f"  Result: {result}")
        results.append(("resolve_episode_outcomes", True))
    except Exception as e:
        print(f"[X] resolve_episode_outcomes failed: {e}")
        results.append(("resolve_episode_outcomes", False))
    
    # Test 3: Default action (retier_memories)
    print("\n" + "=" * 60)
    print("3. Testing default action (retier_memories)")
    print("=" * 60)
    
    try:
        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {}  # No action specified, should default to retier_memories
        }
        
        result = handler(event)
        print(f"[OK] Default action executed successfully")
        print(f"  Result: {result}")
        results.append(("default_action", True))
    except Exception as e:
        print(f"[X] Default action failed: {e}")
        results.append(("default_action", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:25s}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All Lambda handler tests passed!")
    else:
        print("[WARNING] Some tests failed - check the errors above")
        print("\nNote: Lambda handler works locally. For AWS deployment, see AWS_DEPLOYMENT.md")


if __name__ == "__main__":
    test_lambda_handler()