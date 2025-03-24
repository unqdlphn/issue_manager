import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import sqlite3

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import issue_manager
from models import Issue

class TestEdgeCases:
    """Tests focused on improving coverage of edge cases."""

    def test_list_issues_archived(self, mock_db, captured_output):
        """Test list_issues with show_archived=True"""
        # Create test archived issues
        archived_issue = Issue("Archived Title", "Archived Description", status="Archived", resolution="Fixed")
        archived_issue.id = 1
        
        # Test with archived issues
        with patch.object(Issue, 'load_all', return_value=[archived_issue]):
            issue_manager.list_issues(show_archived=True)
            
        output = captured_output()
        assert "Archived Issues" in output
        assert "Archived Title" in output
        assert "Fixed" in output
    
    def test_edit_issue_detailed(self, mock_db, mock_input, captured_output):
        """Test edit_issue with detailed inputs including status changes"""
        test_issue = Issue("Edit Test", "Original description", tags=["old1", "old2"])
        test_issue.id = 1
        test_issue.status = "Open"
        
        # Edit all fields including status change to Resolved
        mock_input([
            "1",                    # Issue ID
            "Updated Title",        # New title
            "Updated Description",  # New description
            "new1, new2, new3",     # New tags
            "r",                    # Change status to Resolved
            "Issue was fixed",      # Resolution
            "y"                     # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update:
            result = issue_manager.edit_issue()
            assert result is True
            assert test_issue.title == "Updated Title"
            assert test_issue.description == "Updated Description"
            assert test_issue.status == "Resolved"
            assert test_issue.resolution == "Issue was fixed"
            assert test_issue.tags == ["new1", "new2", "new3"]
            assert mock_update.called
        
        output = captured_output()
        assert "Issue updated" in output
    
    def test_edit_issue_status_archived(self, mock_db, mock_input, captured_output):
        """Test editing an issue and changing status to Archived"""
        test_issue = Issue("Status Test", "Original description", tags=["test"])
        test_issue.id = 1
        test_issue.status = "Open"
        
        # Keep all fields but change status to Archived
        mock_input([
            "1",         # Issue ID
            "",          # Keep title
            "",          # Keep description
            "",          # Keep tags
            "a",         # Change to Archived
            "y"          # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update:
            result = issue_manager.edit_issue()
            assert result is True
            assert test_issue.status == "Archived"
            assert mock_update.called
    
    def test_edit_issue_invalid_status(self, mock_db, mock_input, captured_output):
        """Test editing an issue with invalid status input"""
        test_issue = Issue("Invalid Status", "Test description", tags=["test"])
        test_issue.id = 1
        test_issue.status = "Open"
        
        # Input invalid status
        mock_input([
            "1",              # Issue ID
            "",               # Keep title
            "",               # Keep description
            "",               # Keep tags
            "x",              # Invalid status
            "y"               # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update:
            result = issue_manager.edit_issue()
            assert result is True
            assert test_issue.status == "Open"  # Status should remain unchanged
            assert mock_update.called
    
    def test_archive_resolved_issue_success(self, mock_db, mock_input, captured_output):
        """Test successfully archiving a resolved issue"""
        resolved_issue = Issue("Resolved Test", "Test description", status="Resolved")
        resolved_issue.id = 1
        
        mock_input([
            "1",  # Issue ID
            "y"   # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[resolved_issue]), \
             patch.object(Issue, 'update') as mock_update, \
             patch('issue_manager.export_to_csv') as mock_export:
            result = issue_manager.archive_issue()
            assert result is True
            assert resolved_issue.status == "Archived"
            assert mock_update.called
            assert mock_export.called
    
    def test_delete_issue_not_found(self, mock_db, mock_input, captured_output):
        """Test deleting an issue that doesn't exist"""
        open_issue = Issue("Open Test", "Test description", status="Open")
        open_issue.id = 1
        
        # Try to delete non-existent issue
        mock_input(["2"])  # ID that doesn't exist
        
        with patch.object(Issue, 'load_all', return_value=[open_issue]):
            result = issue_manager.delete_issue()
            assert result is False
        
        output = captured_output()
        assert "Issue not found" in output
    
    def test_search_issues_empty_term(self, mock_input, captured_output):
        """Test searching with empty search term"""
        mock_input([""])  # Empty search term
        
        issue_manager.search_issues()
        
        output = captured_output()
        assert "Search term cannot be empty" in output
    
    def test_configure_readline_create_file(self):
        """Test configure_readline creating history file"""
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('readline.set_history_length') as mock_set_length, \
             patch('readline.read_history_file') as mock_read, \
             patch('readline.parse_and_bind') as mock_parse:
            
            issue_manager.configure_readline()
            
            # File should be created
            mock_file.assert_called_once_with(issue_manager.HISTORY_FILE, 'w')
            mock_set_length.assert_called_once_with(1000)
            mock_read.assert_called_once()
            mock_parse.assert_called_once_with('tab: complete')
