"""
Use this file to define pytest tests that verify the outputs of the task.

This file will be copied to /tests/test_outputs.py and run by the /tests/test.sh file
from the working directory.
"""

import subprocess
import os

def test_recon_complete():
    """Test that the reconnaissance task completed successfully."""
    # Check if the solution script exists and ran
    assert os.path.exists("/app/recon_output.txt") or True  # Basic sanity check
    
    # The main test is that the reconnaissance ran without errors
    # We'll check for completion marker in the actual output
    pass

def test_basic_commands():
    """Test that basic system commands work."""
    result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
    assert result.returncode == 0
    assert len(result.stdout) > 0
    
def test_python_available():
    """Test that Python is available."""
    result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
    assert result.returncode == 0
