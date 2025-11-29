import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Your credentials (from .env file)
EMAIL = os.getenv("EMAIL", "your-email@example.com")
SECRET = os.getenv("SECRET", "your-secret-string")

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Server configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8000       # Default port

# Quiz solver configuration
TIMEOUT_SECONDS = 180      # 3 minutes total timeout
BROWSER_TIMEOUT = 30000    # 30 seconds for page loads (milliseconds)