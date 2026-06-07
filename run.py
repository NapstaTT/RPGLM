"""
Execution entry point for RGPLM v0.2.
Allows running the server smoothly from the root directory on any platform (including Android/Termux).
"""

import sys
from pathlib import Path
import uvicorn

if __name__ == "__main__":
    # Ensure the root directory is in the Python path for relative imports
    root_dir = Path(__file__).parent.resolve()
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    # Run the FastAPI server via Uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)