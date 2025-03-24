import os
import sys
import pytest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock, mock_open
import csv
from datetime import datetime
import shutil

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import database

class TestDatabase:
    """Tests for the database.py module"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing"""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        
        # Patch the database path for testing
        original_path = database.DATABASE_PATH
        database.DATABASE_PATH = path
        
        yield path
        
        # Reset the path and clean up
        database.DATABASE_PATH = original_path
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def backup_dir(self):
        """Create a temporary backup directory"""
        temp_dir = tempfile.mkdtemp()
        original_backup_dir = database.BACKUP_DIR
        database.BACKUP_DIR = temp_dir
        
        yield temp_dir
        
        # Reset and clean up
        database.BACKUP_DIR = original_backup_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_connection(self, temp_db):
        """Test getting a database connection"""
        conn = database.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        # Test that the row factory is set
        assert conn.row_factory == sqlite3.Row
        conn.close()
    
    def test_transaction(self, temp_db):
        """Test transaction context manager"""
        # Test successful transaction
        with database.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test VALUES (1, 'test')")
            
        # Verify transaction was committed
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")
        row = cursor.fetchone()
        assert row is not None
        assert row['id'] == 1
        assert row['name'] == 'test'
        conn.close()
            
        # Test transaction rollback
        with pytest.raises(sqlite3.Error):
            with database.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test VALUES (2, 'rollback')")
                # This should cause an error and rollback
                cursor.execute("INSERT INTO nonexistent_table VALUES (1, 'error')")
                
        # Verify transaction was rolled back
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM test")
        count = cursor.fetchone()['count']
        assert count == 1  # Still only the first row
        conn.close()
    
    def test_initialize_database(self, temp_db):
        """Test initializing the database"""
        # Initialize database
        database.initialize_database()
        
        # Verify the issues table was created
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
        assert cursor.fetchone() is not None
        
        # Check that indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row['name'] for row in cursor.fetchall()]
        assert "idx_issues_status" in indexes
        assert "idx_issues_created_at" in indexes
        conn.close()
    
    def test_initialize_database_existing_table(self, temp_db):
        """Test initializing the database when tables already exist"""
        # Create the issues table first
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()
        
        # Now run initialize_database
        database.initialize_database()
        
        # Check if resolution column was added
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(issues)")
        columns = [col[1] for col in cursor.fetchall()]
        assert "resolution" in columns
        conn.close()
    
    def test_migrate_data_to_fit_constraints(self, temp_db):
        """Test migrating data to fit constraints"""
        # Set up database with test data
        conn = database.get_connection()
        cursor = conn.cursor()
        
        # Create table and add oversized data
        cursor.execute('''
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            resolution TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        long_title = "X" * 200
        long_desc = "Y" * 200
        long_res = "Z" * 200
        
        cursor.execute(
            "INSERT INTO issues (title, description, resolution) VALUES (?, ?, ?)",
            (long_title, long_desc, long_res)
        )
        conn.commit()
        conn.close()
        
        # Run the migration function
        result = database.migrate_data_to_fit_constraints()
        assert result is True
        
        # Check if data was truncated
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, resolution FROM issues WHERE id = 1")
        row = cursor.fetchone()
        assert len(row['title']) <= 140
        assert len(row['description']) <= 140
        assert len(row['resolution']) <= 140
        assert row['title'].endswith('...')
        assert row['description'].endswith('...')
        assert row['resolution'].endswith('...')
        conn.close()
    
    def test_execute_query(self, temp_db):
        """Test execute_query function"""
        # Setup test data
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test VALUES (1, 'test1')")
        cursor.execute("INSERT INTO test VALUES (2, 'test2')")
        conn.commit()
        conn.close()
        
        # Test the query execution
        results = database.execute_query("SELECT * FROM test ORDER BY id")
        assert len(results) == 2
        assert dict(results[0])['name'] == 'test1'
        assert dict(results[1])['name'] == 'test2'
        
        # Test with parameters
        results = database.execute_query("SELECT * FROM test WHERE id = ?", (1,))
        assert len(results) == 1
        assert dict(results[0])['name'] == 'test1'
        
        # Test error handling
        with patch('database.transaction', side_effect=sqlite3.Error("Test error")):
            results = database.execute_query("SELECT * FROM nonexistent_table")
            assert results == []
    
    def test_execute_insert(self, temp_db):
        """Test execute_insert function"""
        # Setup test table
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        
        # Test insertion
        lastrowid = database.execute_insert("INSERT INTO test (name) VALUES (?)", ('test_insert',))
        assert lastrowid == 1
        
        # Verify insertion
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test WHERE id = ?", (lastrowid,))
        row = cursor.fetchone()
        assert row is not None
        assert row['name'] == 'test_insert'
        conn.close()
        
        # Test error handling
        with patch('database.transaction', side_effect=sqlite3.Error("Test error")):
            lastrowid = database.execute_insert("INSERT INTO nonexistent_table (name) VALUES (?)", ('error',))
            assert lastrowid == -1
    
    def test_create_issue(self, temp_db):
        """Test create_issue function"""
        # Initialize database
        database.initialize_database()
        
        # Test creating an issue
        issue_id = database.create_issue(
            title="Test Title",
            description="Test Description",
            status="open",
            resolution=None
        )
        assert issue_id > 0
        
        # Verify issue was created
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        issue = cursor.fetchone()
        assert issue is not None
        assert issue['title'] == "Test Title"
        assert issue['description'] == "Test Description"
        conn.close()
        
        # Test with long input that needs truncation
        long_title = "X" * 150
        long_desc = "Y" * 150
        issue_id = database.create_issue(
            title=long_title,
            description=long_desc,
            status="open"
        )
        
        # Verify truncation
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
        issue = cursor.fetchone()
        assert len(issue['title']) <= 140
        assert len(issue['description']) <= 140
        conn.close()
    
    def test_get_all_issues(self, temp_db):
        """Test get_all_issues function"""
        # Initialize database and add test issues
        database.initialize_database()
        database.create_issue("Issue 1", "Description 1", "open")
        database.create_issue("Issue 2", "Description 2", "closed")
        
        # Test retrieving all issues
        issues = database.get_all_issues()
        assert len(issues) == 2
        titles = [issue['title'] for issue in issues]
        assert "Issue 1" in titles
        assert "Issue 2" in titles
    
    def test_get_issue_by_id(self, temp_db):
        """Test get_issue_by_id function"""
        # Initialize database and add a test issue
        database.initialize_database()
        issue_id = database.create_issue("Test Issue", "Test Description", "open")
        
        # Test retrieving issue by ID
        issue = database.get_issue_by_id(issue_id)
        assert issue is not None
        assert issue['title'] == "Test Issue"
        
        # Test with non-existent ID
        issue = database.get_issue_by_id(999)
        assert issue is None
    
    def test_update_issue(self, temp_db):
        """Test update_issue function"""
        # Initialize database and add a test issue
        database.initialize_database()
        issue_id = database.create_issue("Original Title", "Original Description", "open")
        
        # Test updating the issue
        result = database.update_issue(
            issue_id=issue_id,
            title="Updated Title",
            description="Updated Description",
            status="closed",
            resolution="Fixed"
        )
        assert result is True
        
        # Verify update
        issue = database.get_issue_by_id(issue_id)
        assert issue['title'] == "Updated Title"
        assert issue['description'] == "Updated Description"
        assert issue['status'] == "closed"
        assert issue['resolution'] == "Fixed"
        
        # Test with non-existent ID
        result = database.update_issue(999, "Nonexistent", "Update")
        assert result is False
        
        # Test with long values that need truncation
        long_title = "X" * 150
        long_desc = "Y" * 150
        long_res = "Z" * 150
        
        database.update_issue(
            issue_id=issue_id,
            title=long_title,
            description=long_desc,
            resolution=long_res
        )
        
        # Verify truncation
        issue = database.get_issue_by_id(issue_id)
        assert len(issue['title']) <= 140
        assert len(issue['description']) <= 140
        assert len(issue['resolution']) <= 140
    
    def test_delete_issue(self, temp_db):
        """Test delete_issue function"""
        # Initialize database and add a test issue
        database.initialize_database()
        issue_id = database.create_issue("Delete Test", "To be deleted", "open")
        
        # Verify issue exists
        assert database.get_issue_by_id(issue_id) is not None
        
        # Test deleting the issue
        result = database.delete_issue(issue_id)
        assert result is True
        
        # Verify issue was deleted
        assert database.get_issue_by_id(issue_id) is None
        
        # Test with non-existent ID
        result = database.delete_issue(999)
        assert result is False
    
    def test_export_to_csv(self, temp_db):
        """Test export_to_csv function"""
        # Initialize database and add test issues
        database.initialize_database()
        database.create_issue("CSV Test 1", "Export test 1", "open")
        database.create_issue("CSV Test 2", "Export test 2", "closed")
        
        # Create a temporary CSV file
        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        
        try:
            # Test exporting to CSV
            result = database.export_to_csv(csv_path)
            assert result is True
            
            # Verify CSV file contents
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) > 1  # Header + data rows
                assert any("CSV Test 1" in str(row) for row in rows)
                assert any("CSV Test 2" in str(row) for row in rows)
            
            # Test with empty database
            conn = database.get_connection()
            conn.execute("DELETE FROM issues")
            conn.commit()
            conn.close()
            
            # Should return False when no issues exist
            result = database.export_to_csv(csv_path)
            assert result is False
        finally:
            # Clean up
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_create_backup(self, temp_db, backup_dir):
        """Test create_backup function"""
        # Initialize database
        database.initialize_database()
        database.create_issue("Backup Test", "Test backup functionality", "open")
        
        # Test creating a backup
        backup_path = database.create_backup()
        assert backup_path != ""
        assert os.path.exists(backup_path)
        
        # Verify the backup file
        conn = sqlite3.connect(backup_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues")
        issues = cursor.fetchall()
        assert len(issues) == 1
        assert issues[0]['title'] == "Backup Test"
        conn.close()
    
    def test_restore_from_backup(self, temp_db, backup_dir):
        """Test restore_from_backup function"""
        # Create original data and backup
        database.initialize_database()
        database.create_issue("Original", "Original data", "open")
        backup_path = database.create_backup()
        
        # Clear the database and add new data
        conn = database.get_connection()
        conn.execute("DELETE FROM issues")
        conn.commit()
        conn.close()
        
        database.create_issue("New", "New data after backup", "open")
        
        # Test restoring from backup
        result = database.restore_from_backup(backup_path)
        assert result is True
        
        # Verify restored data
        issues = database.get_all_issues()
        assert len(issues) == 1
        assert issues[0]['title'] == "Original"
        
        # Test with non-existent backup file
        result = database.restore_from_backup("/nonexistent/path.db")
        assert result is False
    
    def test_search_issues(self, temp_db):
        """Test search_issues function"""
        # Initialize database with test data
        database.initialize_database()
        database.create_issue("Apple Pie", "Recipe for apple pie", "open")
        database.create_issue("Banana Split", "How to make banana split", "open")
        database.create_issue("Cherry Cake", "Cherry cake recipe", "closed")
        
        # Test searching for issues
        results = database.search_issues("apple")
        assert len(results) == 1
        assert results[0]['title'] == "Apple Pie"
        
        results = database.search_issues("recipe")
        assert len(results) == 2
        titles = [issue['title'] for issue in results]
        assert "Apple Pie" in titles
        assert "Cherry Cake" in titles
        
        # Test with no results
        results = database.search_issues("nonexistent")
        assert len(results) == 0
    
    def test_get_issues_by_status(self, temp_db):
        """Test get_issues_by_status function"""
        # Initialize database with test data
        database.initialize_database()
        database.create_issue("Open Issue 1", "First open issue", "open")
        database.create_issue("Open Issue 2", "Second open issue", "open")
        database.create_issue("Closed Issue", "A closed issue", "closed")
        
        # Test filtering by status
        open_issues = database.get_issues_by_status("open")
        assert len(open_issues) == 2
        titles = [issue['title'] for issue in open_issues]
        assert "Open Issue 1" in titles
        assert "Open Issue 2" in titles
        
        closed_issues = database.get_issues_by_status("closed")
        assert len(closed_issues) == 1
        assert closed_issues[0]['title'] == "Closed Issue"
        
        # Test with status that doesn't exist
        nonexistent_issues = database.get_issues_by_status("nonexistent")
        assert len(nonexistent_issues) == 0
    
    def test_optimize_database(self, temp_db):
        """Test optimize_database function"""
        # Initialize database
        database.initialize_database()
        
        # Test optimizing the database
        result = database.optimize_database()
        assert result is True
        
        # Simulate an error with a mocked connection
        with patch('database.get_connection', side_effect=sqlite3.Error("Test error")):
            result = database.optimize_database()
            assert result is False
    
    def test_get_database_stats(self, temp_db):
        """Test get_database_stats function"""
        # Initialize database with test data
        database.initialize_database()
        database.create_issue("Issue 1", "Description 1", "open")
        database.create_issue("Issue 2", "Description 2", "open")
        database.create_issue("Issue 3", "Description 3", "closed")
        
        # Test getting database stats
        stats = database.get_database_stats()
        assert stats['total_issues'] == 3
        assert stats['open_issues'] == 2
        assert stats['closed_issues'] == 1
        assert stats['database_size_kb'] > 0
        
        # Test with error
        with patch('database.execute_query', side_effect=Exception("Test error")):
            stats = database.get_database_stats()
            assert stats['total_issues'] == 0
            assert stats['open_issues'] == 0
            assert stats['closed_issues'] == 0
    
    def test_execute_batch(self, temp_db):
        """Test execute_batch function"""
        # Initialize database
        database.initialize_database()
        
        # Prepare test data for batch insert
        query = "INSERT INTO issues (title, description, status) VALUES (?, ?, ?)"
        params_list = [
            ("Batch 1", "First batch item", "open"),
            ("Batch 2", "Second batch item", "open"),
            ("Batch 3", "Third batch item", "closed")
        ]
        
        # Test batch execution
        result = database.execute_batch(query, params_list)
        assert result is True
        
        # Verify batch insertion
        issues = database.get_all_issues()
        assert len(issues) == 3
        titles = [issue['title'] for issue in issues]
        assert "Batch 1" in titles
        assert "Batch 2" in titles
        assert "Batch 3" in titles
        
        # Test error handling
        with patch('database.transaction', side_effect=sqlite3.Error("Test error")):
            result = database.execute_batch("INSERT INTO nonexistent_table VALUES (?)", [("error",)])
            assert result is False
    
    def test_execute_script(self, temp_db):
        """Test execute_script function"""
        # Prepare test script
        script = """
        CREATE TABLE test_script (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO test_script (name) VALUES ('Script Test 1');
        INSERT INTO test_script (name) VALUES ('Script Test 2');
        """
        
        # Test script execution
        result = database.execute_script(script)
        assert result is True
        
        # Verify script execution
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_script ORDER BY id")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0]['name'] == "Script Test 1"
        assert rows[1]['name'] == "Script Test 2"
        conn.close()
        
        # Test error handling
        with patch('database.transaction', side_effect=sqlite3.Error("Test error")):
            result = database.execute_script("Invalid SQL")
            assert result is False
    
    def test_create_issues_batch(self, temp_db):
        """Test create_issues_batch function"""
        # Initialize database
        database.initialize_database()
        
        # Prepare batch of issues
        issues = [
            {"title": "Batch Issue 1", "description": "First batch issue"},
            {"title": "Batch Issue 2", "description": "Second batch issue", "status": "closed"},
            {"title": "Batch Issue 3", "description": "Third batch issue"}
        ]
        
        # Test batch creation
        result = database.create_issues_batch(issues)
        assert result is True
        
        # Verify batch creation
        db_issues = database.get_all_issues()
        assert len(db_issues) == 3
        titles = [issue['title'] for issue in db_issues]
        assert "Batch Issue 1" in titles
        assert "Batch Issue 2" in titles
        assert "Batch Issue 3" in titles
    
    def test_get_connection_info(self, temp_db):
        """Test get_connection_info function"""
        # Test getting connection info
        info = database.get_connection_info()
        assert 'foreign_keys' in info
        assert 'journal_mode' in info
        assert 'synchronous' in info
        assert 'cache_size' in info
        
        # Test with error
        with patch('database.get_connection', side_effect=Exception("Test error")):
            info = database.get_connection_info()
            assert 'error' in info
    
    def test_enable_full_text_search(self, temp_db):
        """Test enable_full_text_search function"""
        # Initialize database
        database.initialize_database()
        
        # Add test data
        database.create_issue("FTS Test", "Testing full text search", "open")
        
        # Test enabling FTS
        try:
            result = database.enable_full_text_search()
            
            # Not all SQLite installations support FTS5, so we'll adapt our test
            if result:
                # Verify FTS table creation
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues_fts'")
                assert cursor.fetchone() is not None
                conn.close()
            else:
                # If not supported, the function should have gracefully failed
                pass
        except sqlite3.OperationalError:
            # This is expected if SQLite doesn't support FTS5
            # (e.g., on some test environments)
            pass
    
    def test_full_text_search(self, temp_db):
        """Test full_text_search function"""
        # Initialize database
        database.initialize_database()
        
        # Add test data
        database.create_issue("FTS Apple", "Full text search with apple", "open")
        database.create_issue("FTS Banana", "Full text search with banana", "open")
        
        # Test full text search
        try:
            # Try to enable FTS
            database.enable_full_text_search()
            
            # Test search
            results = database.full_text_search("apple")
            
            # We should either get results from FTS or fallback to regular search
            assert len(results) >= 1
            
            # Either way, our 'apple' issue should be in the results
            titles = [issue['title'] for issue in results]
            assert "FTS Apple" in titles
        except sqlite3.OperationalError:
            # Fall back to testing regular search
            results = database.search_issues("apple")
            assert len(results) == 1
            assert results[0]['title'] == "FTS Apple"
    
    def test_complete_database_setup(self, temp_db):
        """Test complete_database_setup function"""
        # Test the complete setup function
        result = database.complete_database_setup()
        assert result is True
        
        # Verify the database was initialized
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
        assert cursor.fetchone() is not None
        conn.close()
