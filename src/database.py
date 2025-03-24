"""Database connection handling for the issue manager application."""

import sqlite3
import os
import csv
import shutil
import contextlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Generator, ContextManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='database.log'
)
logger = logging.getLogger('database')

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "issues.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")

def get_connection():
    """Create and return a database connection."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    # Enable SQLite enhancements
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and speed
    conn.execute("PRAGMA cache_size = -10000")  # Use 10MB of memory for caching
    conn.execute("PRAGMA temp_store = MEMORY")  # Store temporary tables and indices in memory
    
    return conn

@contextlib.contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize_database():
    """Create necessary tables if they don't exist."""
    with transaction() as conn:
        cursor = conn.cursor()
        
        # Check if issues table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create issues table with character limits
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(title) <= 140),
                description TEXT CHECK(length(description) <= 140),
                resolution TEXT CHECK(length(resolution) <= 140),
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        else:
            # Check if resolution column exists, if not add it
            cursor.execute("PRAGMA table_info(issues)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "resolution" not in columns:
                cursor.execute("ALTER TABLE issues ADD COLUMN resolution TEXT CHECK(length(resolution) <= 140)")
            
            # SQLite doesn't support adding constraints to existing columns,
            # so we'll handle validation in application code
            logger.info("Applied column constraints for title, description and resolution (140 chars)")
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_issues_created_at ON issues(created_at)')

def migrate_data_to_fit_constraints():
    """Truncate data in existing records to fit the new constraints."""
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Get all issues
            cursor.execute("SELECT id, title, description, resolution FROM issues")
            issues = cursor.fetchall()
            
            # Update records that exceed length constraints
            for issue in issues:
                id = issue['id']
                title = issue['title']
                description = issue['description']
                resolution = issue['resolution'] if issue['resolution'] is not None else ""
                
                updates = []
                params = []
                
                if len(title) > 140:
                    updates.append("title = ?")
                    params.append(title[:137] + "...")
                
                if description and len(description) > 140:
                    updates.append("description = ?")
                    params.append(description[:137] + "...")
                
                if resolution and len(resolution) > 140:
                    updates.append("resolution = ?")
                    params.append(resolution[:137] + "...")
                
                if updates:
                    query = f"UPDATE issues SET {', '.join(updates)} WHERE id = ?"
                    params.append(id)
                    cursor.execute(query, params)
            
            logger.info("Successfully migrated data to fit the 140 character constraints")
            return True
    except sqlite3.Error as e:
        logger.error(f"Error migrating data: {e}")
        return False

def execute_query(query: str, params: Tuple = ()) -> List[sqlite3.Row]:
    """Execute a query and return all results."""
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def execute_insert(query: str, params: Tuple) -> int:
    """Execute an insert query and return the last inserted id."""
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return -1

def create_issue(title: str, description: str, status: str = "open", resolution: str = None) -> int:
    """Create a new issue and return its ID."""
    # Validate input lengths
    if len(title) > 140:
        title = title[:137] + "..."
    
    if description and len(description) > 140:
        description = description[:137] + "..."
    
    if resolution and len(resolution) > 140:
        resolution = resolution[:137] + "..."
    
    query = """
    INSERT INTO issues (title, description, status, resolution, created_at, updated_at) 
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    return execute_insert(query, (title, description, status, resolution))

def get_all_issues() -> List[Dict[str, Any]]:
    """Retrieve all issues from the database."""
    query = "SELECT * FROM issues ORDER BY created_at DESC"
    issues = execute_query(query)
    return [dict(issue) for issue in issues]

def get_issue_by_id(issue_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a specific issue by ID."""
    query = "SELECT * FROM issues WHERE id = ?"
    issues = execute_query(query, (issue_id,))
    return dict(issues[0]) if issues else None

def update_issue(issue_id: int, title: str = None, description: str = None, 
                status: str = None, resolution: str = None) -> bool:
    """Update an existing issue. Only updates provided fields."""
    current = get_issue_by_id(issue_id)
    if not current:
        return False
    
    title = title if title is not None else current['title']
    description = description if description is not None else current['description']
    status = status if status is not None else current['status']
    resolution = resolution if resolution is not None else current.get('resolution')
    
    # Validate input lengths
    if len(title) > 140:
        title = title[:137] + "..."
    
    if description and len(description) > 140:
        description = description[:137] + "..."
    
    if resolution and len(resolution) > 140:
        resolution = resolution[:137] + "..."
    
    query = """
    UPDATE issues SET title = ?, description = ?, status = ?, resolution = ?, 
    updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """
    execute_query(query, (title, description, status, resolution, issue_id))
    return True

def delete_issue(issue_id: int) -> bool:
    """Delete an issue by ID."""
    query = "DELETE FROM issues WHERE id = ?"
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (issue_id,))
            rows_affected = cursor.rowcount
            return rows_affected > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting issue {issue_id}: {e}")
        return False

def export_to_csv(filepath: str) -> bool:
    """Export all issues to a CSV file."""
    issues = get_all_issues()
    if not issues:
        return False
    
    try:
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=issues[0].keys())
            writer.writeheader()
            writer.writerows(issues)
        return True
    except Exception:
        return False

def create_backup() -> str:
    """Create a backup of the database file."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_filename = f"issues_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # Ensure the database exists before attempting backup
    if os.path.exists(DATABASE_PATH):
        shutil.copy2(DATABASE_PATH, backup_path)
        return backup_path
    return ""

def restore_from_backup(backup_path: str) -> bool:
    """Restore the database from a backup file."""
    if os.path.exists(backup_path):
        # Ensure the database directory exists
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        shutil.copy2(backup_path, DATABASE_PATH)
        return True
    return False

def search_issues(keyword: str) -> List[Dict[str, Any]]:
    """Search for issues with keyword in title or description."""
    query = """
    SELECT * FROM issues 
    WHERE title LIKE ? OR description LIKE ?
    ORDER BY created_at DESC
    """
    search_term = f'%{keyword}%'
    issues = execute_query(query, (search_term, search_term))
    return [dict(issue) for issue in issues]

def get_issues_by_status(status: str) -> List[Dict[str, Any]]:
    """Get all issues filtered by status."""
    query = "SELECT * FROM issues WHERE status = ? ORDER BY created_at DESC"
    issues = execute_query(query, (status,))
    return [dict(issue) for issue in issues]

def optimize_database() -> bool:
    """Optimize the database by vacuuming."""
    try:
        conn = get_connection()
        conn.execute("VACUUM")
        conn.close()
        return True
    except sqlite3.Error:
        return False

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    stats = {
        'total_issues': 0,
        'open_issues': 0,
        'closed_issues': 0,
        'database_size_kb': 0
    }
    
    try:
        # Count issues
        query = "SELECT COUNT(*) as count FROM issues"
        stats['total_issues'] = dict(execute_query(query)[0])['count']
        
        # Count open issues
        query = "SELECT COUNT(*) as count FROM issues WHERE status = 'open'"
        stats['open_issues'] = dict(execute_query(query)[0])['count']
        
        # Count closed issues
        query = "SELECT COUNT(*) as count FROM issues WHERE status = 'closed'"
        stats['closed_issues'] = dict(execute_query(query)[0])['count']
        
        # Get database size
        if os.path.exists(DATABASE_PATH):
            stats['database_size_kb'] = os.path.getsize(DATABASE_PATH) / 1024
            
        return stats
    except Exception:
        return stats

def execute_batch(query: str, params_list: List[Tuple]) -> bool:
    """Execute a batch of queries for better performance."""
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return True
    except sqlite3.Error as e:
        logger.error(f"Batch execution error: {e}")
        return False

def execute_script(sql_script: str) -> bool:
    """Execute a SQL script containing multiple statements."""
    try:
        with transaction() as conn:
            conn.executescript(sql_script)
            return True
    except sqlite3.Error as e:
        logger.error(f"Script execution error: {e}")
        return False

def create_issues_batch(issues: List[Dict[str, Any]]) -> bool:
    """Create multiple issues at once for better performance."""
    query = """
    INSERT INTO issues (title, description, status, created_at, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    params_list = [(i['title'], i['description'], i.get('status', 'open')) for i in issues]
    return execute_batch(query, params_list)

def get_connection_info() -> Dict[str, Any]:
    """Get SQLite connection information including pragma settings."""
    info = {}
    try:
        conn = get_connection()
        pragmas = [
            "foreign_keys", "journal_mode", "synchronous", 
            "cache_size", "temp_store", "auto_vacuum"
        ]
        
        for pragma in pragmas:
            cursor = conn.execute(f"PRAGMA {pragma}")
            info[pragma] = cursor.fetchone()[0]
        
        conn.close()
        return info
    except Exception as e:
        logger.error(f"Error getting connection info: {e}")
        return {"error": str(e)}

def enable_full_text_search() -> bool:
    """Enable full-text search on issues table by creating a virtual table."""
    try:
        with transaction() as conn:
            # Check if FTS5 module is available
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues_fts'")
            if not cursor.fetchone():
                conn.executescript("""
                -- Create virtual table for full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING FTS5(
                    title, description, content='issues', content_rowid='id'
                );
                
                -- Trigger to keep the FTS index up to date
                CREATE TRIGGER IF NOT EXISTS issues_ai AFTER INSERT ON issues BEGIN
                    INSERT INTO issues_fts(rowid, title, description) 
                    VALUES (new.id, new.title, new.description);
                END;
                
                CREATE TRIGGER IF NOT EXISTS issues_ad AFTER DELETE ON issues BEGIN
                    INSERT INTO issues_fts(issues_fts, rowid, title, description) 
                    VALUES('delete', old.id, old.title, old.description);
                END;
                
                CREATE TRIGGER IF NOT EXISTS issues_au AFTER UPDATE ON issues BEGIN
                    INSERT INTO issues_fts(issues_fts, rowid, title, description) 
                    VALUES('delete', old.id, old.title, old.description);
                    INSERT INTO issues_fts(rowid, title, description) 
                    VALUES (new.id, new.title, new.description);
                END;
                
                -- Populate the FTS table with existing data
                INSERT INTO issues_fts(rowid, title, description)
                SELECT id, title, description FROM issues;
                """)
            return True
    except sqlite3.Error as e:
        logger.error(f"Error setting up full-text search: {e}")
        return False

def full_text_search(search_term: str) -> List[Dict[str, Any]]:
    """Perform a full-text search on issues."""
    try:
        query = """
        SELECT i.* FROM issues i
        JOIN issues_fts fts ON i.id = fts.rowid
        WHERE issues_fts MATCH ?
        ORDER BY rank
        """
        issues = execute_query(query, (search_term,))
        return [dict(issue) for issue in issues]
    except sqlite3.Error:
        # Fall back to regular search if FTS is not available
        return search_issues(search_term)

def complete_database_setup():
    """Complete database setup including migrations if needed."""
    initialize_database()
    migrate_data_to_fit_constraints()
    return True
