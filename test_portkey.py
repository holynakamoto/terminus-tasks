#!/usr/bin/env python3
"""Test script to verify Portkey configuration works with LiteLLM"""

import os
import sys

# Try to use OpenHands' Python interpreter if available (it has LiteLLM installed)
OPENHANDS_PYTHON = os.path.expanduser("~/.local/share/uv/tools/openhands/bin/python")
if os.path.exists(OPENHANDS_PYTHON) and not sys.executable.startswith(OPENHANDS_PYTHON):
    print(f"⚠️  Note: LiteLLM is installed in OpenHands' environment.")
    print(f"   To test with LiteLLM, run: {OPENHANDS_PYTHON} test_portkey.py")
    print(f"   Or test directly with OpenHands CLI: openhands")
    print()

# Set environment variables before importing litellm
# Use environment variables if already set, otherwise use defaults
os.environ.setdefault("ANTHROPIC_API_KEY", "fdZYjptATE8UssqQiT/x5fdrgJ2g")
os.environ.setdefault("ANTHROPIC_BASE_URL", "https://api.portkey.ai/v1")

# Try to set headers if possible
portkey_provider = os.getenv("PORTKEY_PROVIDER", os.getenv("ANTHROPIC_HEADERS", '{"x-portkey-provider":"anthropic-main"}'))
if not portkey_provider.startswith("{"):
    os.environ.setdefault("ANTHROPIC_HEADERS", f'{{"x-portkey-provider":"{portkey_provider}"}}')
elif "ANTHROPIC_HEADERS" not in os.environ:
    os.environ["ANTHROPIC_HEADERS"] = portkey_provider

print("Testing Portkey configuration with LiteLLM...")
print(f"Python: {sys.executable}")
print(f"ANTHROPIC_API_KEY: {os.environ['ANTHROPIC_API_KEY'][:20]}...")
print(f"ANTHROPIC_BASE_URL: {os.environ['ANTHROPIC_BASE_URL']}")
print(f"ANTHROPIC_HEADERS: {os.environ.get('ANTHROPIC_HEADERS', 'Not set')}")
print()

try:
    import litellm
    
    # Try to get version (some versions don't have __version__)
    try:
        version = litellm.__version__
    except AttributeError:
        try:
            import pkg_resources
            version = pkg_resources.get_distribution("litellm").version
        except:
            version = "unknown"
    print(f"LiteLLM version: {version}")
    print()
    
    # Test 1: Check if base URL is being read
    print("Test 1: Checking LiteLLM configuration...")
    print(f"  litellm.api_base: {getattr(litellm, 'api_base', 'Not set')}")
    print()
    
    # Test 2: Try a simple completion with explicit parameters
    print("Test 2: Attempting completion request with explicit api_base and api_key...")
    try:
        response = litellm.completion(
            model="anthropic/claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": "Say 'test' and nothing else."}],
            max_tokens=10,
            api_base=os.environ["ANTHROPIC_BASE_URL"],  # Explicitly set
            api_key=os.environ["ANTHROPIC_API_KEY"],   # Explicitly set
        )
        print("✅ SUCCESS! Portkey connection works!")
        print(f"Response: {response.choices[0].message.content}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        print()
        
        # Try without explicit api_base but with api_key
        print("Test 3: Trying without explicit api_base (using env vars only)...")
        try:
            response = litellm.completion(
                model="anthropic/claude-sonnet-4-5-20250929",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                api_key=os.environ["ANTHROPIC_API_KEY"],  # Still pass api_key explicitly
            )
            print("✅ SUCCESS with env var only!")
            sys.exit(0)
        except Exception as e2:
            print(f"❌ FAILED: {type(e2).__name__}: {e2}")
            print()
            print("This suggests LiteLLM is not reading ANTHROPIC_BASE_URL from environment.")
            print("You may need to:")
            print("  1. Pass api_base explicitly in code")
            print("  2. Use a LiteLLM config file")
            print("  3. Check if Portkey provider name is correct")
            sys.exit(1)
            
except ImportError:
    print("❌ LiteLLM not installed in current Python environment.")
    print()
    print("LiteLLM is installed in OpenHands' environment. Options:")
    print(f"  1. Use OpenHands Python: {OPENHANDS_PYTHON} test_portkey.py")
    print("  2. Install LiteLLM: pip install litellm")
    print("  3. Test with OpenHands CLI directly: openhands")
    print()
    print("Since OpenHands CLI uses LiteLLM, the best test is to run OpenHands:")
    print("  source setup_portkey.sh")
    print("  openhands")
    sys.exit(1)

