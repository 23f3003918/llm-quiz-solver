#!/usr/bin/env python3
"""
Test script to verify quiz solver setup
"""
import requests
import json
import sys
from config import EMAIL, SECRET

# Test endpoints
LOCAL_URL = "http://localhost:8000"
DEMO_QUIZ_URL = "https://tds-llm-analysis.s-anand.net/demo"


def test_health_check():
    """Test if server is running"""
    print("Testing health check...")
    try:
        response = requests.get(f"{LOCAL_URL}/")
        if response.status_code == 200:
            print("✓ Server is running")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Server returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is it running?")
        print("  Start it with: python main.py")
        return False


def test_invalid_secret():
    """Test that invalid secrets are rejected"""
    print("\nTesting invalid secret rejection...")
    payload = {
        "email": EMAIL,
        "secret": "wrong-secret",
        "url": DEMO_QUIZ_URL
    }
    
    response = requests.post(f"{LOCAL_URL}/solve", json=payload)
    
    if response.status_code == 403:
        print("✓ Invalid secret correctly rejected (403)")
        return True
    else:
        print(f"✗ Expected 403, got {response.status_code}")
        return False


def test_invalid_json():
    """Test that invalid JSON is rejected"""
    print("\nTesting invalid JSON rejection...")
    
    response = requests.post(
        f"{LOCAL_URL}/solve",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 400 or response.status_code == 422:
        print(f"✓ Invalid JSON correctly rejected ({response.status_code})")
        return True
    else:
        print(f"✗ Expected 400/422, got {response.status_code}")
        return False


def test_valid_request():
    """Test a valid request to the demo quiz"""
    print("\nTesting valid request with demo quiz...")
    payload = {
        "email": EMAIL,
        "secret": SECRET,
        "url": DEMO_QUIZ_URL
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{LOCAL_URL}/solve", json=payload)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✓ Request accepted (200)")
        print("  Check the server logs to see solving progress")
        return True
    else:
        print(f"✗ Expected 200, got {response.status_code}")
        return False


def main():
    print("="*60)
    print("Quiz Solver - Test Script")
    print("="*60)
    
    # Check configuration
    print(f"\nConfiguration:")
    print(f"  Email: {EMAIL}")
    print(f"  Secret: {'*' * len(SECRET) if SECRET else 'NOT SET'}")
    
    if EMAIL == "your-email@example.com" or not SECRET or SECRET == "your-secret-string":
        print("\n⚠️  WARNING: You need to configure .env file!")
        print("  1. Copy .env.template to .env")
        print("  2. Fill in your EMAIL and SECRET")
        return
    
    # Run tests
    results = []
    
    results.append(("Health Check", test_health_check()))
    
    if results[-1][1]:  # Only continue if server is running
        results.append(("Invalid Secret", test_invalid_secret()))
        results.append(("Invalid JSON", test_invalid_json()))
        results.append(("Valid Request", test_valid_request()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nPassed {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 All tests passed! Your setup is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()