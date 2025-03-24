import os
import sys
import pytest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
import datetime

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from models import Issue

class TestIssueModel:
    """Tests for the Issue model class"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a temporary database file for testing"""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        
        # Create the issues table
        conn = sqlite3.connect(path)
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
        
        # Patch the database file path
        original_db_file = Issue.DATABASE_FILE
        with patch('models.DATABASE_FILE', path):
            Issue.DATABASE_FILE = path  # This ensures the class attribute is updated
            yield path
            Issue.DATABASE_FILE = original_db_file  # Restore original
        
        # Clean up
        if os.path.exists(path):
            os.unlink(path)
    
    def test_issue_init(self):
        """Test Issue initialization"""
        # Test with default values
        issue = Issue("Test Title", "Test Description")
        assert issue.title == "Test Title"
        assert issue.description == "Test Description"
        assert issue.status == "Open"
        assert issue.resolution is None
        assert isinstance(issue.tags, list)
        assert len(issue.tags) == 0
        
        # Test with custom values
        issue = Issue("Title", "Description", status="Closed", resolution="Fixed", tags=["tag1", "tag2"])
        assert issue.title == "Title"
        assert issue.description == "Description"
        assert issue.status == "Closed"
        assert issue.resolution == "Fixed"
        assert issue.tags == ["tag1", "tag2"]
    
    def test_issue_save(self, mock_db):
        """Test saving an issue to the database"""
        # Create and save a new issue
        issue = Issue("Save Test", "Testing save method", tags=["test", "save"])
        issue.save()
        
        # Verify it was saved to the database
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues")
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row['title'] == "Save Test"
        assert row['description'] == "Testing save method"
        assert row['status'] == "Open"
        assert row['tags'] == "test, save"
    
    def test_issue_save_with_error(self, mock_db):
        """Test error handling when saving an issue"""
        issue = Issue("Error Test", "Testing error handling")
        
        # Create a mock connection that raises an error
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            # Should not raise exception but print error
            with patch('builtins.print') as mock_print:
                issue.save()
                mock_print.assert_called()
    
    def test_load_all(self, mock_db):
        """Test loading all issues from the database"""
        # Add test data
        conn = sqlite3.connect(mock_db)
        conn.execute('''
        INSERT INTO issues (title, description, status, resolution, date, modified, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ("Test 1", "Description 1", "Open", None, "2023-01-01", "2023-01-01", "tag1, tag2"))
        
        conn.execute('''
        INSERT INTO issues (title, description, status, resolution, date, modified, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ("Test 2", "Description 2", "Closed", "Fixed", "2023-01-02", "2023-01-02", "tag3"))
        conn.commit()
        conn.close()
        
        # Test loading issues
        issues = Issue.load_all()
        
        assert len(issues) == 2
        assert isinstance(issues[0], Issue)
        assert issues[0].title == "Test 1"
        assert issues[0].id == 1
        assert issues[0].tags == ["tag1", "tag2"]
        
        assert issues[1].title == "Test 2"
        assert issues[1].status == "Closed"
        assert issues[1].resolution == "Fixed"
        assert issues[1].tags == ["tag3"]
    
    def test_load_all_empty(self, mock_db):
        """Test loading issues from an empty database"""
        issues = Issue.load_all()
        assert len(issues) == 0
    
    def test_load_all_with_error(self, mock_db):
        """Test error handling when loading issues"""
        # Create a mock connection that raises an error
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            # Should not raise exception but print error and return empty list
            with patch('builtins.print') as mock_print:
                issues = Issue.load_all()
                assert issues == []
                mock_print.assert_called()
    
    def test_update(self, mock_db):
        """Test updating an issue"""
        # Create and save a new issue
        issue = Issue("Original", "Original description")
        issue.save()
        
        # Get the ID of the saved issue
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues")
        issue_id = cursor.fetchone()['id']
        conn.close()
        
        # Load the issue, modify it, and update
        issues = Issue.load_all()
        issue = issues[0]
        assert issue.id == issue_id
        
        # Update the issue
        issue.title = "Updated"
        issue.description = "Updated description"
        issue.status = "Closed"
        issue.resolution = "Fixed"
        issue.tags = ["updated", "test"]
        issue.update()
        
        # Verify the update
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row['title'] == "Updated"
        assert row['description'] == "Updated description"
        assert row['status'] == "Closed"
        assert row['resolution'] == "Fixed"
        assert row['tags'] == "updated, test"
    
    def test_update_with_error(self, mock_db):
        """Test error handling when updating an issue"""
        # Create issue with ID for update
        issue = Issue("Error Test", "Testing error handling")
        issue.id = 1
        
        # Create a mock connection that raises an error
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            # Should not raise exception but print error
            with patch('builtins.print') as mock_print:
                issue.update()
                mock_print.assert_called()
    
    def test_delete(self, mock_db):
        """Test deleting an issue"""
        # Create and save a new issue
        issue = Issue("Delete Test", "Testing delete method")
        issue.save()
        
        # Get the ID of the saved issue
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues")
        issue_id = cursor.fetchone()[0]
        conn.close()
        
        # Delete the issue
        Issue.delete(issue_id)
        
        # Verify it was deleted
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is None
    
    def test_delete_with_error(self, mock_db):
        """Test error handling when deleting an issue"""
        # Create a mock connection that raises an error
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            # Should not raise exception but print error
            with patch('builtins.print') as mock_print:
                Issue.delete(1)
                mock_print.assert_called()
    
    def test_issue_dir_creation(self, tmpdir):
        """Test that the data directory is created when saving an issue"""
        # Set up temporary path
        temp_db = os.path.join(tmpdir, "subdir", "issues.db")
        
        # Patch DATABASE_FILE to point to our temp location
        with patch('models.DATABASE_FILE', temp_db):
            Issue.DATABASE_FILE = temp_db
            
            # Create and save an issue
            issue = Issue("Dir Test", "Testing directory creation")
            issue.save()
            
            # Directory should be created
            assert os.path.exists(os.path.dirname(temp_db))
    
    def test_issue_save_existing_table(self, mock_db):
        """Test saving an issue with various attributes"""
        # Create an issue with all attributes set
        issue = Issue(
            "Complex Issue", 
            "Testing complex save", 
            status="In Progress", 
            resolution="Working on it", 
            tags=["complex", "important", "urgent"]
        )
        issue.save()
        
        # Verify all attributes were saved correctly
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues")
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row['title'] == "Complex Issue"
        assert row['description'] == "Testing complex save"
        assert row['status'] == "In Progress"
        assert row['resolution'] == "Working on it"
        assert row['tags'] == "complex, important, urgent"
    
    def test_issue_save_with_special_chars(self, mock_db):
        """Test saving an issue with special characters"""
        # Create an issue with special characters
        issue = Issue(
            "Special ' \" Chars", 
            "Testing with ' and \" special characters",
            tags=["test'quote", "comma,here"]
        )
        issue.save()
        
        # Load it back and verify
        issues = Issue.load_all()
        assert len(issues) == 1
        assert issues[0].title == "Special ' \" Chars"
        assert issues[0].description == "Testing with ' and \" special characters"
        assert "test'quote" in issues[0].tags
        assert "comma,here" in issues[0].tags
    
    def test_update_status_and_resolution(self, mock_db):
        """Test updating status and resolution specifically"""
        # Create and save a new issue
        issue = Issue("Update Status", "Testing status update")
        issue.save()
        
        # Get the ID of the saved issue
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues")
        issue_id = cursor.fetchone()[0]
        conn.close()
        
        # Load the issue, update status and resolution
        issues = Issue.load_all()
        issue = issues[0]
        assert issue.id == issue_id
        
        issue.status = "Resolved"
        issue.resolution = "Fixed the issue"
        issue.update()
        
        # Verify the update
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status, resolution FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row['status'] == "Resolved"
        assert row['resolution'] == "Fixed the issue"
    
    def test_delete_nonexistent_issue(self, mock_db):
        """Test deleting a non-existent issue"""
        # Try to delete an issue that doesn't exist
        Issue.delete(999)
        
        # This should not cause an error
        # We can verify the database is still intact
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count > 0  # Tables still exist

    def test_model_save_direct(self, mock_db):
        """Test saving a model directly (not mocked)"""
        # Create a test issue
        issue = Issue("Direct Save Test", "Testing direct save")
        
        # Save it without any mocking
        issue.save()
        
        # Verify it's saved in the database
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE title = ?", ("Direct Save Test",))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row['description'] == "Testing direct save"

    def test_model_update_direct(self, mock_db):
        """Test updating a model directly (not mocked)"""
        # Create and save an issue
        issue = Issue("Update Direct", "Original description")
        issue.save()
        
        # Get the ID
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues WHERE title = ?", ("Update Direct",))
        issue_id = cursor.fetchone()['id']
        conn.close()
        
        # Set ID and update the issue
        issue.id = issue_id
        issue.description = "Updated directly"
        issue.update()  # Direct call, no mocking
        
        # Verify the update
        conn = sqlite3.connect(mock_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row['description'] == "Updated directly"

    def test_model_delete_direct(self, mock_db):
        """Test deleting a model directly (not mocked)"""
        # Create and save an issue
        issue = Issue("Delete Direct", "To be deleted directly")
        issue.save()
        
        # Get the ID
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM issues WHERE title = ?", ("Delete Direct",))
        issue_id = cursor.fetchone()[0]
        conn.close()
        
        # Call delete directly without mocking
        Issue.delete(issue_id)
        
        # Verify deletion
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is None
