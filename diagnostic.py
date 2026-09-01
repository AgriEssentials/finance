#!/usr/bin/env python3
"""Diagnostic script to check if app can start"""

import sys
import os

print("=" * 60)
print("🔍 STOCK ANALYSIS APP - DIAGNOSTIC CHECK")
print("=" * 60)

# Check Python version
print(f"\n✓ Python Version: {sys.version}")
print(f"✓ Python Path: {sys.executable}")

# Check if we're in the right directory
print(f"\n✓ Current Directory: {os.getcwd()}")

# Try to import critical modules
print("\n--- Checking Imports ---")

try:
    import fastapi
    print("✓ fastapi - OK")
except Exception as e:
    print(f"✗ fastapi - ERROR: {e}")

try:
    import uvicorn
    print("✓ uvicorn - OK")
except Exception as e:
    print(f"✗ uvicorn - ERROR: {e}")

try:
    import yfinance
    print("✓ yfinance - OK")
except Exception as e:
    print(f"✗ yfinance - ERROR: {e}")

try:
    import pandas
    print("✓ pandas - OK")
except Exception as e:
    print(f"✗ pandas - ERROR: {e}")

try:
    import sqlalchemy
    print("✓ sqlalchemy - OK")
except Exception as e:
    print(f"✗ sqlalchemy - ERROR: {e}")

try:
    import transformers
    print("✓ transformers - OK (DistilBERT available)")
except Exception as e:
    print(f"✗ transformers - NOT INSTALLED (required for sentiment)")
    print("   Run: pip install transformers")

try:
    import torch
    print("✓ torch - OK")
except Exception as e:
    print(f"✗ torch - NOT INSTALLED (required for transformers)")
    print("   Run: pip install torch")

try:
    import newspaper
    print("✓ newspaper3k - OK")
except Exception as e:
    print(f"✗ newspaper3k - NOT INSTALLED (optional, for article extraction)")
    print("   Run: pip install newspaper3k")

# Try to import app modules
print("\n--- Checking App Modules ---")

sys.path.insert(0, 'backend')

try:
    from app.sentiment import sentiment_analyzer
    print("✓ sentiment module - OK")
except Exception as e:
    print(f"✗ sentiment module - ERROR: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.main import app
    print("✓ main module - OK")
except Exception as e:
    print(f"✗ main module - ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\n💡 Next Steps:")
print("1. If all says ✓ OK, run: python run.py")
print("2. If any ✗ errors, install missing packages")
print("3. Open browser to: http://localhost:8000")
print("\n" + "=" * 60)

