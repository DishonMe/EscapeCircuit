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


DEFAULT_GOOGLE_CLIENT_ID = "your_google_client_id_here"

def load_env_file(env_path: str = "apps/nextjs-app/.env"):
    """Load environment variables from .env file and extract GOOGLE_CLIENT_ID"""
    env_file = Path(env_path)
    example_file = env_file.with_name(".env.example")

    if not env_file.exists():
        if example_file.exists():
            env_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Created {env_path} from {example_file.name}.")
        else:
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text(
                "NEXT_PUBLIC_API_URL=http://localhost:8080/api\n"
                "NEXT_PUBLIC_ENABLE_API_MOCKING=false\n"
                "NEXT_PUBLIC_MOCK_API_PORT=8080\n"
                "NEXT_PUBLIC_URL=http://localhost:3000\n",
                encoding="utf-8",
            )
            print(f"Created {env_path} with default frontend settings.")

    google_client_id = None
    found_google_client_id = False
    
    with env_file.open('r', encoding='utf-8') as f:
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
                    found_google_client_id = True
                    google_client_id = value
                    os.environ["GOOGLE_CLIENT_ID"] = value
                    os.environ["NEXT_PUBLIC_GOOGLE_CLIENT_ID"] = value
                    print(f"Loaded: GOOGLE_CLIENT_ID from NEXT_PUBLIC_GOOGLE_CLIENT_ID")
    
    if not google_client_id:
        google_client_id = DEFAULT_GOOGLE_CLIENT_ID
        os.environ["GOOGLE_CLIENT_ID"] = google_client_id
        os.environ["NEXT_PUBLIC_GOOGLE_CLIENT_ID"] = google_client_id
        if not found_google_client_id:
            existing_text = env_file.read_text(encoding='utf-8')
            with env_file.open('a', encoding='utf-8') as f:
                if existing_text and not existing_text.endswith('\n'):
                    f.write('\n')
                f.write('NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id_here\n')
            print(f"Added placeholder NEXT_PUBLIC_GOOGLE_CLIENT_ID to {env_path}.")
        print("Google OAuth is not configured; continuing with login disabled.")
    
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
