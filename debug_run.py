
import uvicorn
import os
import sys

# Add current directory to path so imports work
sys.path.append(os.getcwd())

if __name__ == "__main__":
    # Import app inside main to avoid import errors if paths are wrong at module level
    from app.main import app
    print("Starting Debug Agent on port 8001...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
