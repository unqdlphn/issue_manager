import os
import sys
import pytest
import tempfile
import sqlite3
from unittest.mock import patch

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture
def mock_db():
    """Create a temporary database for testing"""
    _, temp_file = tempfile.mkstemp()
    
    # Create a test connection and set up the table
    conn = sqlite3.connect(temp_file)
    conn.execute('''CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        resolution TEXT,
        date TEXT NOT NULL,
        modified TEXT NOT NULL,
        tags TEXT
    );''')
    conn.close()
    
    # Patch both file paths
    with patch('issue_manager.DATABASE_FILE', temp_file), \
         patch('models.DATABASE_FILE', temp_file):
        yield temp_file
    
    # Clean up
    if os.path.exists(temp_file):
        os.unlink(temp_file)

@pytest.fixture
def mock_input(monkeypatch):
    """Mock the input function to simulate user input"""
    inputs = []
    
    def mock_input_fn(prompt=""):
        if not inputs:
            return ""
        return inputs.pop(0)
    
    def set_inputs(new_inputs):
        nonlocal inputs
        inputs = new_inputs.copy()
    
    monkeypatch.setattr('builtins.input', mock_input_fn)
    return set_inputs

@pytest.fixture
def captured_output(capfd):
    """Capture stdout for testing console output"""
    def get_output():
        out, _ = capfd.readouterr()
        return out
    
    return get_output
