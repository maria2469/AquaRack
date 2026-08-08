"""
CloudWatch Metrics Test Script for AquaRack

Tests AWS CloudWatch connectivity and metrics publishing.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.config import settings
    from app.observability.cloudwatch_metrics import (
        publish_telemetry_metrics, 
        publish_lambda_metrics,
        _get_cw_client
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


def test_cloudwatch_client():
    """Test CloudWatch client initialization."""
    print("=" * 60)
    print("1. Testing CloudWatch Client Initialization")
    print("=" * 60)
    
    try:
        client = _get_cw_client()
        if client is None:
            print("[X] CloudWatch client initialization failed")
            print("Check your AWS credentials and CLOUDWATCH_ENABLED setting")
            return False
        
        print("[OK] CloudWatch client initialized successfully")
        return True
    except Exception as e:
        print(f"[X] CloudWatch client error: {e}")
        return False


def test_telemetry_metrics():
    """Test publishing telemetry metrics to CloudWatch."""
    print("\n" + "=" * 60)
    print("2. Testing Telemetry Metrics Publishing")
    print("=" * 60)
    
    try:
        result = publish_telemetry_metrics(
            gpu_pct=75.5,
            cooling_load_kw=12.3,
            wue_factor=0.4,
            water_l_per_hr=45.2,
            agent_confidence=0.85,
            water_saved_pct=15.0,
            device_id="test-device"
        )
        
        if result:
            print("[OK] Telemetry metrics published successfully")
            print("  Published metrics: GPUUtilisation, CoolingLoadKW, WUEFactor, WaterLPerHr, AgentConfidence, WaterSavedPct")
            return True
        else:
            print("[X] Telemetry metrics publishing failed")
            print("  CloudWatch may be disabled or credentials invalid")
            return False
            
    except Exception as e:
        print(f"[X] Telemetry metrics error: {e}")
        return False


def test_lambda_metrics():
    """Test publishing Lambda metrics to CloudWatch."""
    print("\n" + "=" * 60)
    print("3. Testing Lambda Metrics Publishing")
    print("=" * 60)
    
    try:
        result = publish_lambda_metrics(
            action="test_action",
            duration_ms=1234.5,
            success=True,
            records_processed=42
        )
        
        if result:
            print("[OK] Lambda metrics published successfully")
            print("  Published metrics: LambdaDurationMs, LambdaSuccess, LambdaRecordsProcessed")
            return True
        else:
            print("[X] Lambda metrics publishing failed")
            print("  CloudWatch may be disabled or credentials invalid")
            return False
            
    except Exception as e:
        print(f"[X] Lambda metrics error: {e}")
        return False


def main():
    """Run all CloudWatch tests."""
    print("\n" + "=" * 60)
    print("AquaRack CloudWatch Metrics Test")
    print("=" * 60)
    
    print(f"CLOUDWATCH_ENABLED: {settings.CLOUDWATCH_ENABLED}")
    print(f"AWS_REGION: {settings.AWS_REGION}")
    
    results = []
    
    # Test 1: CloudWatch Client
    results.append(("CloudWatch Client", test_cloudwatch_client()))
    
    # Test 2: Telemetry Metrics (only if client passed)
    if results[0][1]:
        results.append(("Telemetry Metrics", test_telemetry_metrics()))
        results.append(("Lambda Metrics", test_lambda_metrics()))
    else:
        print("\n" + "=" * 60)
        print("Skipping metrics tests due to client initialization failure")
        print("=" * 60)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20s}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All CloudWatch tests passed!")
    else:
        print("[WARNING] Some tests failed - check the errors above")
        print("\nNote: CloudWatch failures are expected if IAM permissions are restricted")
        print("The system will continue to work with local fallback")


if __name__ == "__main__":
    main()