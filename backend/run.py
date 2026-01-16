"""
Run script for the Laoshi Coach Backend.

Usage:
    python -m backend.run

Or from the backend directory:
    python run.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("Starting Laoshi Coach Backend...")
    print("API available at: http://localhost:5000/api")
    print("Health check: http://localhost:5000/api/health")
    print("\nPress Ctrl+C to stop the server.")
    app.run(debug=True, host='0.0.0.0', port=5000)
