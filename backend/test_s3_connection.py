"""
S3 Connection Test Script for AquaRack

Tests AWS S3 connectivity and permissions.
Run this script to verify your AWS credentials and S3 bucket access.
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
    from app.lib.s3_client import _get_s3_client, upload_report_to_s3
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)


def test_aws_credentials():
    """Test if AWS credentials are configured."""
    print("=" * 60)
    print("1. Testing AWS Credentials Configuration")
    print("=" * 60)
    
    has_access_key = bool(os.getenv("AWS_ACCESS_KEY_ID"))
    has_secret_key = bool(os.getenv("AWS_SECRET_ACCESS_KEY"))
    has_region = bool(settings.AWS_REGION)
    
    print(f"AWS_ACCESS_KEY_ID: {'[SET]' if has_access_key else '[NOT SET]'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'[SET]' if has_secret_key else '[NOT SET]'}")
    print(f"AWS_REGION: {settings.AWS_REGION}")
    print(f"S3_ENABLED: {settings.S3_ENABLED}")
    print(f"S3_BUCKET: {settings.S3_BUCKET}")
    
    if not (has_access_key and has_secret_key):
        print("\n[X] AWS credentials not configured!")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        return False
    
    print("[OK] AWS credentials configured")
    return True


def test_s3_client():
    """Test S3 client initialization."""
    print("\n" + "=" * 60)
    print("2. Testing S3 Client Initialization")
    print("=" * 60)
    
    try:
        client = _get_s3_client()
        if client is None:
            print("[X] S3 client initialization failed")
            print("Check your AWS credentials and network connection")
            return False
        
        print("[OK] S3 client initialized successfully")
        return True
    except Exception as e:
        print(f"[X] S3 client error: {e}")
        return False


def test_bucket_access():
    """Test S3 bucket access and existence."""
    print("\n" + "=" * 60)
    print("3. Testing S3 Bucket Access")
    print("=" * 60)
    
    try:
        client = _get_s3_client()
        if client is None:
            print("[X] Cannot test bucket access - S3 client not available")
            return False
        
        # Check if bucket exists
        response = client.list_buckets()
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        
        print(f"Available buckets: {buckets}")
        
        if settings.S3_BUCKET in buckets:
            print(f"[OK] Bucket '{settings.S3_BUCKET}' exists and is accessible")
            return True
        else:
            print(f"[X] Bucket '{settings.S3_BUCKET}' not found")
            print(f"Please create the bucket in AWS S3 console")
            return False
            
    except Exception as e:
        print(f"[X] Bucket access error: {e}")
        return False


def test_upload():
    """Test uploading a small file to S3."""
    print("\n" + "=" * 60)
    print("4. Testing S3 Upload")
    print("=" * 60)
    
    try:
        test_content = "timestamp,cpu,gpu\n2024-01-01,50,60"
        test_filename = "s3_test_report.csv"
        
        print(f"Uploading test file: {test_filename}")
        s3_uri = upload_report_to_s3(test_filename, test_content, "text/csv")
        
        if s3_uri:
            print(f"[OK] Upload successful: {s3_uri}")
            return True
        else:
            print("[X] Upload failed")
            return False
            
    except Exception as e:
        print(f"[X] Upload error: {e}")
        return False


def test_local_fallback():
    """Test local fallback storage."""
    print("\n" + "=" * 60)
    print("5. Testing Local Fallback Storage")
    print("=" * 60)
    
    try:
        fallback_dir = settings.S3_LOCAL_FALLBACK_DIR
        print(f"Local fallback directory: {fallback_dir}")
        
        if os.path.exists(fallback_dir):
            files = os.listdir(fallback_dir)
            print(f"[OK] Local fallback directory exists")
            print(f"  Files in fallback: {len(files)}")
            
            if files:
                print(f"  Sample files: {files[:5]}")
            return True
        else:
            print(f"[X] Local fallback directory does not exist")
            return False
            
    except Exception as e:
        print(f"[X] Local fallback error: {e}")
        return False


def main():
    """Run all S3 tests."""
    print("\n" + "=" * 60)
    print("AquaRack S3 Connection Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: AWS Credentials
    results.append(("AWS Credentials", test_aws_credentials()))
    
    if not results[0][1]:  # If credentials failed, skip S3 tests
        print("\n" + "=" * 60)
        print("Skipping S3 tests due to missing credentials")
        print("=" * 60)
        
        # Still test local fallback
        results.append(("Local Fallback", test_local_fallback()))
    else:
        # Test 2: S3 Client
        results.append(("S3 Client", test_s3_client()))
        
        # Test 3: Bucket Access
        results.append(("Bucket Access", test_bucket_access()))
        
        # Test 4: Upload (only if previous tests passed)
        if all(r[1] for r in results[:-1]):
            results.append(("S3 Upload", test_upload()))
        
        # Test 5: Local Fallback
        results.append(("Local Fallback", test_local_fallback()))
    
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
        print("[SUCCESS] All tests passed!")
    else:
        print("[WARNING] Some tests failed - check the errors above")
        print("\nFor S3 setup instructions, see: S3_SETUP_GUIDE.md")


if __name__ == "__main__":
    main()