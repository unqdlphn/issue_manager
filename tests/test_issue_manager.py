import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import datetime
import sqlite3
import tempfile
import csv

# Import the module
import issue_manager
from models import Issue

class TestIssueManager:
    """Tests for the issue_manager module"""
    
    def test_create_table(self, mock_db):
        """Test creating the issues table"""
        issue_manager.create_table()
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues';")
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'issues'
    
    def test_add_issue(self, mock_db, mock_input, captured_output):
        """Test adding a new issue"""
        # Set up mock input
        mock_input([
            "Test Issue",
            "This is a test issue",
            "test, issue",
            "y"  # confirm
        ])
        
        with patch.object(Issue, 'save') as mock_save:
            result = issue_manager.add_issue()
            assert mock_save.called
            assert result is True  # Should return True when action is taken
        
        output = captured_output()
        assert "Issue added" in output
    
    def test_add_issue_cancel(self, mock_db, mock_input, captured_output):
        """Test canceling issue addition"""
        mock_input([
            "Test Issue",
            "This is a test issue",
            "test",
            "n"  # cancel confirmation
        ])
        
        with patch.object(Issue, 'save') as mock_save:
            result = issue_manager.add_issue()
            assert not mock_save.called
            assert result is False  # Should return False when action is canceled
        
        output = captured_output()
        assert "Issue addition canceled" in output
    
    def test_list_issues_empty(self, mock_db, captured_output):
        """Test listing issues when there are none"""
        with patch.object(Issue, 'load_all', return_value=[]):
            issue_manager.list_issues()
        
        output = captured_output()
        assert "No current issues found" in output
    
    def test_list_issues(self, mock_db, captured_output):
        """Test listing issues"""
        test_issue = Issue("Test", "Description", tags=["test"])
        test_issue.id = 1
        test_issue.date = "2023-01-01"
        test_issue.status = "Open"
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]):
            issue_manager.list_issues()
        
        output = captured_output()
        assert "Current Issues" in output
        assert "Test" in output
    
    def test_edit_issue(self, mock_db, mock_input, captured_output):
        """Test editing an issue"""
        test_issue = Issue("Old Title", "Old Description", tags=["old"])
        test_issue.id = 1
        test_issue.status = "Open"
        
        mock_input([
            "1",  # Issue ID
            "New Title",
            "New Description",
            "new, tags",
            "o",  # Status: Open
            "y"   # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update:
            result = issue_manager.edit_issue()
            assert mock_update.called
            assert result is True
            assert test_issue.title == "New Title"
            assert test_issue.description == "New Description"
        
        output = captured_output()
        assert "Issue updated" in output
    
    def test_edit_issue_cancel(self, mock_db, mock_input, captured_output):
        """Test canceling issue edit"""
        test_issue = Issue("Old Title", "Old Description", tags=["old"])
        test_issue.id = 1
        test_issue.status = "Open"
        
        mock_input([
            "1",  # Issue ID
            "New Title",
            "New Description",
            "new, tags",
            "o",  # Status: Open
            "n"   # Cancel confirmation
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update:
            result = issue_manager.edit_issue()
            assert not mock_update.called
            assert result is False
        
        output = captured_output()
        assert "Issue edit canceled" in output
    
    def test_archive_issue(self, mock_db, mock_input, captured_output):
        """Test archiving a resolved issue"""
        test_issue = Issue("Test", "Description", status="Resolved", tags=["test"])
        test_issue.id = 1
        
        mock_input([
            "1",  # Issue ID
            "y"   # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'update') as mock_update, \
             patch('issue_manager.export_to_csv') as mock_export:
            result = issue_manager.archive_issue()
            assert mock_update.called
            assert mock_export.called
            assert result is True
            assert test_issue.status == "Archived"
        
        output = captured_output()
        assert "Issue archived" in output
    
    def test_delete_issue(self, mock_db, mock_input, captured_output):
        """Test deleting an open issue"""
        test_issue = Issue("Test", "Description", status="Open", tags=["test"])
        test_issue.id = 1
        
        mock_input([
            "1",  # Issue ID
            "y"   # Confirm
        ])
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch.object(Issue, 'delete') as mock_delete:
            result = issue_manager.delete_issue()
            assert mock_delete.called
            assert result is True
        
        output = captured_output()
        assert "Issue deleted" in output
    
    def test_search_issues(self, mock_db, mock_input, captured_output):
        """Test searching for issues"""
        test_issue = Issue("Test Search", "Description with search term", tags=["search"])
        test_issue.id = 1
        
        mock_input(["search"])  # Search term
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]):
            issue_manager.search_issues()
        
        output = captured_output()
        assert "Search Results" in output
        assert "Test Search" in output
    
    def test_search_issues_no_results(self, mock_db, mock_input, captured_output):
        """Test searching for issues with no results"""
        test_issue = Issue("Test", "Description", tags=["test"])
        test_issue.id = 1
        
        mock_input(["nonexistent"])  # Search term that won't match
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]):
            issue_manager.search_issues()
        
        output = captured_output()
        assert "No issues found matching the search term" in output
    
    def test_show_archived(self, mock_db, captured_output):
        """Test showing archived issues"""
        test_issue = Issue("Test", "Description", status="Archived", tags=["test"])
        test_issue.id = 1
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]):
            issue_manager.show_archived()
        
        output = captured_output()
        assert "Archived Issues" in output
        assert "Test" in output
    
    def test_show_archived_empty(self, mock_db, captured_output):
        """Test showing archived issues when there are none"""
        test_issue = Issue("Test", "Description", status="Open", tags=["test"])
        test_issue.id = 1
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]):
            issue_manager.show_archived()
        
        output = captured_output()
        assert "No archived issues found" in output
    
    def test_export_all_issues(self, mock_db, captured_output):
        """Test exporting all issues to CSV"""
        test_issue = Issue("Test", "Description", tags=["test"])
        test_issue.id = 1
        
        with patch.object(Issue, 'load_all', return_value=[test_issue]), \
             patch('issue_manager.export_to_csv') as mock_export:
            issue_manager.export_all_issues()
            assert mock_export.called
        
        output = captured_output()
        assert "All issues have been exported to CSV" in output
    
    def test_configure_readline(self):
        """Test readline configuration"""
        with patch('readline.set_history_length') as mock_set_length, \
             patch('readline.read_history_file') as mock_read, \
             patch('readline.parse_and_bind') as mock_parse, \
             patch('os.path.exists', return_value=True):
            issue_manager.configure_readline()
            mock_set_length.assert_called_once_with(1000)
            mock_read.assert_called_once()
            mock_parse.assert_called_once_with('tab: complete')

    def test_main_exit(self, mock_input, captured_output):
        """Test main function with exit"""
        mock_input(["9"])  # Choose exit option
        
        with patch('issue_manager.create_table') as mock_create, \
             patch('issue_manager.configure_readline') as mock_readline, \
             patch('readline.write_history_file') as mock_write, \
             patch('issue_manager.export_all_issues') as mock_export:
            issue_manager.main()
            mock_create.assert_called_once()
            mock_readline.assert_called_once()
            mock_write.assert_called_once()
            mock_export.assert_called_once()
    
    def test_main_menu_options(self, mock_input, captured_output):
        """Test main function with different menu options"""
        # Test each menu option followed by exit option
        mock_input([
            "1", "y",  # Add Issue option + process another
            "2", "y",  # List Issues option + process another
            "3", "y",  # Edit Issue option + process another
            "4", "y",  # Archive Issue option + process another 
            "5", "y",  # List Archived Issues option + process another
            "6", "y",  # Export All Issues option + process another
            "7", "y",  # Search Issues option + process another
            "8", "y",  # Delete Issue option + process another
            "9"        # Exit option
        ])
        
        with patch('issue_manager.add_issue', return_value=True) as mock_add, \
             patch('issue_manager.list_issues') as mock_list, \
             patch('issue_manager.edit_issue', return_value=True) as mock_edit, \
             patch('issue_manager.archive_issue', return_value=True) as mock_archive, \
             patch('issue_manager.show_archived') as mock_show_archived, \
             patch('issue_manager.export_all_issues') as mock_export, \
             patch('issue_manager.search_issues') as mock_search, \
             patch('issue_manager.delete_issue', return_value=True) as mock_delete, \
             patch('readline.write_history_file') as mock_write:
            issue_manager.main()
            
            # Verify each function was called
            mock_add.assert_called_once()
            mock_list.assert_called_once()
            mock_edit.assert_called_once()
            mock_archive.assert_called_once()
            mock_show_archived.assert_called_once()
            mock_export.assert_called()  # Called for option 6 and on exit
            mock_search.assert_called_once()
            mock_delete.assert_called_once()
            mock_write.assert_called_once()
    
    def test_main_process_another_no(self, mock_input, captured_output):
        """Test main function with 'n' to process another issue"""
        mock_input([
            "1",  # Add Issue option
            "n"   # Don't process another issue (exit)
        ])
        
        with patch('issue_manager.add_issue', return_value=True) as mock_add, \
             patch('issue_manager.export_all_issues') as mock_export, \
             patch('readline.write_history_file') as mock_write:
            issue_manager.main()
            mock_add.assert_called_once()
            mock_export.assert_called_once()
            mock_write.assert_called_once()
    
    def test_main_invalid_choice(self, mock_input, captured_output):
        """Test main function with invalid menu choice"""
        mock_input([
            "invalid",  # Invalid option
            "9"         # Then exit
        ])
        
        with patch('issue_manager.export_all_issues') as mock_export:
            issue_manager.main()
            mock_export.assert_called_once()
        
        output = captured_output()
        assert "Invalid choice" in output
    
    def test_main_keyboard_interrupt(self, mock_input):
        """Test keyboard interrupt handling in main function"""
        mock_input(["1"])  # Add issue, but will be interrupted
        
        with patch('issue_manager.add_issue', side_effect=KeyboardInterrupt()), \
             patch('readline.write_history_file') as mock_write, \
             patch('issue_manager.export_all_issues') as mock_export:
            try:
                issue_manager.main()
            except SystemExit:
                pass  # Expected behavior
            
            mock_write.assert_called_once()
            mock_export.assert_called_once()
    
    def test_configure_readline_file_not_found(self):
        """Test configure_readline when history file is not found"""
        with patch('readline.set_history_length') as mock_set_length, \
             patch('readline.read_history_file', side_effect=FileNotFoundError()) as mock_read, \
             patch('readline.parse_and_bind') as mock_parse, \
             patch('os.path.exists', return_value=True):
            issue_manager.configure_readline()
            mock_set_length.assert_called_once_with(1000)
            mock_read.assert_called_once()
            mock_parse.assert_called_once_with('tab: complete')
            # Should not raise exception even when file not found
    
    def test_export_to_csv_new_file(self, mock_db, tmpdir):
        """Test exporting issues to a new CSV file"""
        # Create test issues
        test_issue = Issue("CSV Test", "Export test", tags=["csv", "test"])
        test_issue.id = 1
        test_issue.date = "2023-01-01"
        test_issue.status = "Open"
        
        # Create a temporary CSV file path
        csv_path = os.path.join(tmpdir, "test_export.csv")
        
        # Call the export function
        issue_manager.export_to_csv({"issues": [test_issue]}, csv_path, append=False)
        
        # Verify CSV was created and contains the correct data
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2  # Header + 1 data row
            assert "CSV Test" in rows[1]
            assert "Export test" in rows[1]
            assert "csv, test" in str(rows[1]) or "['csv', 'test']" in str(rows[1])
    
    def test_export_to_csv_append(self, mock_db, tmpdir):
        """Test appending issues to an existing CSV file"""
        # Create test issues
        issue1 = Issue("First Issue", "First description", tags=["first"])
        issue1.id = 1
        issue1.date = "2023-01-01"
        issue1.status = "Open"
        
        issue2 = Issue("Second Issue", "Second description", tags=["second"])
        issue2.id = 2
        issue2.date = "2023-01-02"
        issue2.status = "Open"
        
        # Create a temporary CSV file path
        csv_path = os.path.join(tmpdir, "test_append.csv")
        
        # First export
        issue_manager.export_to_csv({"issues": [issue1]}, csv_path, append=False)
        
        # Append second export
        issue_manager.export_to_csv({"issues": [issue2]}, csv_path, append=True)
        
        # Verify CSV contains both issues
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 3  # Header + 2 data rows
            assert "First Issue" in str(rows[1])
            assert "Second Issue" in str(rows[2])
    
    def test_export_to_csv_empty_file(self, mock_db, tmpdir):
        """Test appending to an empty CSV file"""
        # Create test issue
        test_issue = Issue("Empty Test", "Append to empty", tags=["empty"])
        test_issue.id = 1
        
        # Create an empty CSV file
        csv_path = os.path.join(tmpdir, "empty.csv")
        with open(csv_path, 'w') as f:
            pass
        
        # Append to empty file
        issue_manager.export_to_csv({"issues": [test_issue]}, csv_path, append=True)
        
        # Check that the header was written correctly
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 2  # Header + 1 data row
            # Verify that the header is in the first row
            assert 'title' in str(rows[0]).lower() or 'id' in str(rows[0]).lower()
            assert "Empty Test" in str(rows[1])
    
    def test_truncate_text(self):
        """Test the truncate_text function"""
        # Test with text shorter than max length
        result = issue_manager.truncate_text("Short text", 50)
        assert result == "Short text"
        
        # Test with text equal to max length
        text = "x" * 50
        result = issue_manager.truncate_text(text, 50)
        assert result == text
        
        # Test with text longer than max length
        long_text = "This is a very long text that needs to be truncated"
        result = issue_manager.truncate_text(long_text, 20)
        assert len(result) == 20
        assert result == "This is a very lon..."
        
        # Test with None
        result = issue_manager.truncate_text(None, 10)
        assert result is None

    def test_export_to_csv_direct(self, mock_db, tmpdir):
        """Test the export_to_csv function directly (not mocked)"""
        # Create test issue
        test_issue = Issue("Direct Export", "Testing direct export", tags=["csv"])
        test_issue.id = 1
        test_issue.date = "2023-01-01"
        test_issue.status = "Open"
        
        # Create temp file in the tmpdir
        csv_path = os.path.join(tmpdir, "direct_export.csv")
        
        # Call export_to_csv directly
        issue_manager.export_to_csv({"issues": [test_issue]}, csv_path)
        
        # Verify the file was created with correct content
        assert os.path.exists(csv_path)
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "Direct Export" in content
            assert "Testing direct export" in content
            assert "Open" in content

    def test_export_to_csv_direct_implementation(self, mock_db, tmpdir):
        """Test the export_to_csv function implementation directly without patching"""
        # Create test issue
        test_issue = Issue("Real CSV Export", "Testing real csv export", tags=["csv", "real"])
        test_issue.id = 1
        test_issue.date = "2023-01-01"
        test_issue.status = "Open"
        
        # Create CSV file path
        csv_path = os.path.join(tmpdir, "real_export.csv")
        
        # Do not patch anything - use the real implementation
        issue_manager.export_to_csv({"issues": [test_issue]}, csv_path)
        
        # Verify file was created with expected content
        assert os.path.exists(csv_path)
        
        # Read the file directly to check contents
        with open(csv_path, 'r') as f:
            content = f.read()
            assert "Real CSV Export" in content
            assert "Testing real csv export" in content
            
            # Check that the header was written
            first_line = content.splitlines()[0] if content.splitlines() else ""
            assert "title" in first_line.lower()
