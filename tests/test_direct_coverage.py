import os
import sys
import tempfile
import pytest
import sqlite3
import csv

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import models  # Import the module, not just the class
from models import Issue
import issue_manager

class TestDirectCoverage:
    """
    Special test class focused on directly testing functions with 0% coverage.
    No mocking or patching is used to ensure true code coverage.
    """
    
    @pytest.fixture
    def setup_temp_db(self):
        """Create a temporary database file to use for tests"""
        # Create temp database file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Create temp directory for data files
        temp_dir = os.path.dirname(db_path)
        
        # Store original values
        original_model_db = models.DATABASE_FILE  # Access as module attribute, not class attribute
        original_issue_db = issue_manager.DATABASE_FILE
        original_data_dir = issue_manager.DATA_DIR
        
        # Update paths to temp locations
        models.DATABASE_FILE = db_path  # Update the module attribute
        issue_manager.DATABASE_FILE = db_path
        issue_manager.DATA_DIR = temp_dir
        issue_manager.ALL_ISSUES_FILE = os.path.join(temp_dir, "all_issues.csv")
        issue_manager.ARCHIVE_FILE = os.path.join(temp_dir, "archives.csv")
        
        # Create the issues table
        conn = sqlite3.connect(db_path)
        conn.execute('''
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            resolution TEXT,
            date TEXT NOT NULL,
            modified TEXT NOT NULL,
            tags TEXT
        )
        ''')
        conn.commit()
        conn.close()
        
        yield db_path, temp_dir
        
        # Cleanup
        models.DATABASE_FILE = original_model_db  # Restore module attribute
        issue_manager.DATABASE_FILE = original_issue_db
        issue_manager.DATA_DIR = original_data_dir
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_issue_save_direct(self, setup_temp_db):
        """Test Issue.save method directly without any mocking"""
        db_path, _ = setup_temp_db
        
        # Create and save an issue
        test_issue = Issue("Direct Save", "Testing direct save method", tags=["direct", "save"])
        test_issue.save()  # This should invoke the real save method
        
        # Verify directly in the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE title = 'Direct Save'")
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row['description'] == "Testing direct save method"
        assert row['tags'] == "direct, save"
    
    def test_issue_update_direct(self, setup_temp_db):
        """Test Issue.update method directly without any mocking"""
        db_path, _ = setup_temp_db
        
        # Create and save an issue
        test_issue = Issue("Update Test", "Original description")
        test_issue.save()
        
        # Get the ID
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues WHERE title = 'Update Test'")
        issue_id = cursor.fetchone()['id']
        conn.close()
        
        # Update the issue directly
        test_issue.id = issue_id
        test_issue.description = "Updated description"
        test_issue.update()  # This should invoke the real update method
        
        # Verify in database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row['description'] == "Updated description"
    
    def test_issue_delete_direct(self, setup_temp_db):
        """Test Issue.delete method directly without any mocking"""
        db_path, _ = setup_temp_db
        
        # Create and save an issue
        test_issue = Issue("Delete Test", "To be deleted")
        test_issue.save()
        
        # Get the ID
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues WHERE title = 'Delete Test'")
        issue_id = cursor.fetchone()[0]
        conn.close()
        
        # Delete the issue directly
        Issue.delete(issue_id)  # This should invoke the real delete method
        
        # Verify in database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is None
    
    def test_export_to_csv_direct(self, setup_temp_db):
        """Test export_to_csv function directly without any mocking"""
        _, temp_dir = setup_temp_db
        
        # Create issues for export
        issue1 = Issue("CSV Export 1", "First export test")
        issue2 = Issue("CSV Export 2", "Second export test", tags=["csv", "test"])
        
        # Set up a CSV file path
        csv_path = os.path.join(temp_dir, "direct_export_test.csv")
        
        # Call the function directly
        issue_manager.export_to_csv({"issues": [issue1, issue2]}, csv_path)
        
        # Verify file exists and content is correct
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) >= 3  # Header + 2 data rows
            assert any("CSV Export 1" in str(row) for row in rows)
            assert any("CSV Export 2" in str(row) for row in rows)
            assert any("First export test" in str(row) for row in rows)
