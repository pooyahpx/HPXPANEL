#!/usr/bin/env python3
"""
HPXPANEL CLI entrypoint (container binary name kept for compose compatibility).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from cli.main import app

    if len(sys.argv) == 1:
        sys.argv.append("--help")
    app()
except ImportError as e:
    print(f"Error importing CLI: {e}")
    print("Make sure you're running this from the HPXPANEL project directory.")
    sys.exit(1)
except Exception as e:
    print(f"Error running CLI: {e}")
    sys.exit(1)
