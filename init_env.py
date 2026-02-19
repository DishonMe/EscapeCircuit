#!/usr/bin/env python3
"""
Helper script to load .env from frontend and run the concurrently command.
This ensures the same GOOGLE_CLIENT_ID is used by both backend and frontend.

The backend reads GOOGLE_CLIENT_ID from apps/nextjs-app/.env
"""

import os
import subprocess
import sys
from pathlib import Path

def load_env_file(env_path: str = "apps/nextjs-app/.env"):
    """Load environment variables from .env file and extract GOOGLE_CLIENT_ID"""
    if not os.path.exists(env_path):
        print(f"ERROR: {env_path} file not found!")
        print("\nSetup required:")
        print("1. Edit apps/nextjs-app/.env")
        print("2. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID with your actual Google Client ID")
        print("3. See HOWTORUN.md for more details")
        return False
    
    google_client_id = None
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                if value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Look for NEXT_PUBLIC_GOOGLE_CLIENT_ID and set GOOGLE_CLIENT_ID for backend
                if key == "NEXT_PUBLIC_GOOGLE_CLIENT_ID":
                    google_client_id = value
                    os.environ["GOOGLE_CLIENT_ID"] = value
                    print(f"Loaded: GOOGLE_CLIENT_ID from NEXT_PUBLIC_GOOGLE_CLIENT_ID")
    
    if not google_client_id:
        print(f"ERROR: NEXT_PUBLIC_GOOGLE_CLIENT_ID not found in {env_path}!")
        print("Edit the file and set your Google Client ID")
        return False
    
    return True

if __name__ == "__main__":
    # Load from frontend .env
    if not load_env_file("apps/nextjs-app/.env"):
        sys.exit(1)
    
    # Now run the concurrently command
    if sys.platform == "win32":
        backend_cmd = "pip install -r requirements.txt && cd src && python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080"
        frontend_cmd = "cd apps\\nextjs-app && npm run dev"
    else:
        backend_cmd = "pip3 install -r requirements.txt && cd src && python3 -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080"
        frontend_cmd = "cd apps/nextjs-app && npm run dev"

    cmd = (
        f'npx -y concurrently -k -n "API,WEB" -c "blue,magenta" '
        f'"{backend_cmd}" '
        f'"{frontend_cmd}"'
    )
    
    print("\n=== Starting servers ===\n")
    result = subprocess.call(cmd, shell=True)
    sys.exit(result)
