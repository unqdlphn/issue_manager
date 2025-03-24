import sqlite3
import datetime
import csv
import tabulate
import readline  # Import readline for enhanced input editing capabilities
import os
from models import Issue  # Import the Issue class from models.py

# Define data directory for storing database and CSV files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATABASE_FILE = os.path.join(DATA_DIR, "issues.db")
ALL_ISSUES_FILE = os.path.join(DATA_DIR, "all_issues.csv")
ARCHIVE_FILE = os.path.join(DATA_DIR, "issue_archives.csv")  # Updated variable
MAX_ISSUES = 7  # Maximum number of issues allowed
HISTORY_FILE = os.path.expanduser('~/.issue_manager_history')

def export_to_csv(data, filename, append=False):
    """
    Export data to a CSV file.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Check if file exists and is empty (or doesn't exist)
    file_exists = os.path.exists(filename)
    file_is_empty = file_exists and os.path.getsize(filename) == 0
    write_header = not file_exists or file_is_empty or not append
    
    mode = 'a' if append else 'w'
    with open(filename, mode, newline='') as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(data['issues'][0].__dict__.keys())
        for issue in data['issues']:
            writer.writerow(issue.__dict__.values())

def create_table():
    """
    Create the issues table if it doesn't exist.
    """
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        with conn:
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
    except sqlite3.Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

def add_issue():
    """
    Add a new issue by prompting the user for details.
    """
    issues = Issue.load_all()
    current_issues = [issue for issue in issues if issue.status != "Archived"]
    if len(current_issues) >= MAX_ISSUES:
        print("--------------------")
        print("Max issues allowed. Get to work!")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken

    title = input("Enter title (max 70 chars): ").strip()
    if not title:
        print("--------------------")
        print("Title cannot be empty.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    if len(title) > 70:
        title = title[:70]
        print("Title truncated to 70 characters.")
        
    description = input("Enter description (max 140 chars): ").strip()
    if not description:
        print("--------------------")
        print("Description cannot be empty.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    if len(description) > 140:
        description = description[:140]
        print("Description truncated to 140 characters.")
        
    tags_input = input("Enter tags (comma separated, max 3 tags): ").strip()
    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
    if len(tags) > 3:
        tags = tags[:3]
        print("Limited to first 3 tags.")
        
    new_issue = Issue(title, description, tags=tags)
    confirm = input("\nAre you sure you want to add this issue? (y/n): ").strip().lower()
    if confirm == 'y':
        new_issue.save()
        print("--------------------")
        print("Issue added.")
        print("--------------------\n")
        return True  # Return True to indicate action was taken
    else:
        print("--------------------")
        print("Issue addition canceled.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken

def list_issues(show_archived=False):
    """
    List all issues, optionally including archived issues.
    """
    issues = Issue.load_all()
    
    if show_archived:
        archived_issues = [issue for issue in issues if issue.status == "Archived"]
        
        if not archived_issues:
            print("--------------------")
            print("No archived issues found.")
            print("--------------------\n")
            return
        
        headers = ["ID", "Title", "Description", "Status", "Resolution", "Date", "Modified"]
        table = [[
            issue.id, 
            truncate_text(issue.title, 30),
            truncate_text(issue.description, 50), 
            issue.status, 
            truncate_text(issue.resolution, 30),
            issue.date, 
            issue.modified
        ] for issue in archived_issues]
        
        print("\nArchived Issues")
        print(tabulate.tabulate(table, headers, tablefmt="grid"))
    else:
        current_issues = [issue for issue in issues if issue.status != "Archived"]
        
        if not current_issues:
            print("--------------------")
            print("No current issues found.")
            print("--------------------\n")
            return
        
        headers = ["ID", "Title", "Description", "Status", "Tags", "Date"]
        table = [[
            issue.id, 
            truncate_text(issue.title, 30),
            truncate_text(issue.description, 50), 
            issue.status,
            truncate_text(", ".join(issue.tags), 20),
            issue.date
        ] for issue in current_issues]
        
        print("\nCurrent Issues")
        print(tabulate.tabulate(table, headers, tablefmt="grid"))

def edit_issue():
    """
    Edit an existing issue by prompting the user for new details.
    """
    list_issues()
    try:
        issue_id = int(input("Enter ID of issue to edit: "))
    except ValueError:
        print("--------------------")
        print("Invalid ID. Please enter a number.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    issues = Issue.load_all()
    for issue in issues:
        if issue.id == issue_id:
            # Prevent editing archived issues
            if issue.status == "Archived":
                print("--------------------")
                print("Archived issues cannot be edited.")
                print("--------------------\n")
                return False  # Return False to indicate no action was taken
                
            new_title = input(f"Enter new title (max 70 chars) ({issue.title}): ").strip()
            if new_title:
                if len(new_title) > 70:
                    new_title = new_title[:70]
                    print("Title truncated to 70 characters.")
                issue.title = new_title
            
            new_description = input(f"Enter new description (max 140 chars) ({issue.description}): ").strip()
            if new_description:
                if len(new_description) > 140:
                    new_description = new_description[:140]
                    print("Description truncated to 140 characters.")
                issue.description = new_description
                
            new_tags_input = input(f"Enter new tags (comma separated, max 3) ({', '.join(issue.tags)}): ").strip()
            if new_tags_input:
                new_tags = [tag.strip() for tag in new_tags_input.split(",")]
                if len(new_tags) > 3:
                    new_tags = new_tags[:3]
                    print("Limited to first 3 tags.")
                issue.tags = new_tags
            
            # Status shortcuts prompt and processing
            status_options = {
                "o": "Open",
                "i": "In Progress",
                "r": "Resolved",
                "a": "Archived"
            }
            
            status_prompt = f"Enter new status ({issue.status}):\n"
            status_prompt += "  [o] Open\n"
            status_prompt += "  [i] In Progress\n"
            status_prompt += "  [r] Resolved\n"
            status_prompt += "  [a] Archived\n"
            status_prompt += "Enter option: "
            
            new_status_input = input(status_prompt).strip().lower()
            
            # Process status input (allow both shortcuts and full names)
            if new_status_input in status_options:
                new_status = status_options[new_status_input]
            elif new_status_input in [value.lower() for value in status_options.values()]:
                # Allow full status names (case insensitive)
                for full_status in status_options.values():
                    if full_status.lower() == new_status_input:
                        new_status = full_status
                        break
            else:
                # If invalid input, keep current status
                new_status = issue.status
                if new_status_input:  # Only show message if they tried to enter something
                    print(f"Invalid status. Keeping current status: {issue.status}")
                
            if new_status != issue.status:
                issue.status = new_status
                if new_status == "Resolved":
                    resolution = input("\nHow was the issue resolved? (max 140 chars): ").strip()
                    if len(resolution) > 140:
                        resolution = resolution[:140]
                        print("Resolution truncated to 140 characters.")
                    issue.resolution = resolution or "None"
            
            issue.modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            confirm = input("\nAre you sure you want to edit this issue? (y/n): ").strip().lower()
            if confirm == 'y':
                issue.update()
                print("--------------------")
                print("Issue updated.")
                print("--------------------\n")
                return True  # Return True to indicate action was taken
            else:
                print("--------------------")
                print("Issue edit canceled.")
                print("--------------------\n")
                return False  # Return False to indicate no action was taken
            return
    print("Issue not found.")
    return False  # Return False to indicate no action was taken

def archive_issue():
    """
    Archive a resolved issue by changing its status to 'Archived'.
    """
    list_issues()
    try:
        issue_id = int(input("Enter ID of issue to archive: "))
    except ValueError:
        print("--------------------")
        print("\nInvalid ID. Please enter a number.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    issues = Issue.load_all()
    for issue in issues:
        if issue.id == issue_id:
            if issue.status == "Resolved":
                confirm = input("\nAre you sure you want to archive this issue? (y/n): ").strip().lower()
                if confirm == 'y':
                    issue.status = "Archived"
                    issue.modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    issue.update()
                    print("--------------------")
                    print("Issue archived.")
                    print("--------------------\n")
                    export_to_csv({"issues": [issue]}, ARCHIVE_FILE, append=True)  # Updated reference
                    return True  # Return True to indicate action was taken
                else:
                    print("--------------------")
                    print("Issue archive canceled.")
                    print("--------------------\n")
                    return False  # Return False to indicate no action was taken
            else:
                print("--------------------")
                print("Only resolved issues can be archived.")
                print("--------------------\n")
                return False  # Return False to indicate no action was taken
    print("--------------------")    
    print("Issue not found.")
    print("--------------------\n")
    return False  # Return False to indicate no action was taken

def delete_issue():
    """
    Delete an open issue by prompting the user for the issue ID.
    """
    issues = Issue.load_all()
    open_issues = [issue for issue in issues if issue.status == "Open"]
    
    if not open_issues:
        print("--------------------")
        print("No open issues found to delete.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    
    headers = ["ID", "Title", "Description", "Date"]
    table = [[
        issue.id, 
        truncate_text(issue.title, 30),
        truncate_text(issue.description, 50),
        issue.date
    ] for issue in open_issues]
    
    print("\nOpen Issues (only these can be deleted)")
    print(tabulate.tabulate(table, headers, tablefmt="grid"))
    
    try:
        issue_id = int(input("\nEnter ID of issue to delete: "))
    except ValueError:
        print("--------------------")
        print("Invalid ID. Please enter a number.")
        print("--------------------\n")
        return False  # Return False to indicate no action was taken
    
    for issue in issues:
        if issue.id == issue_id:
            if issue.status == "Open":
                confirm = input("\nAre you sure you want to delete this issue? (y/n): ").strip().lower()
                if confirm == 'y':
                    Issue.delete(issue_id)
                    print("--------------------")
                    print("Issue deleted.")
                    print("--------------------\n")
                    return True  # Return True to indicate action was taken
                else:
                    print("--------------------")
                    print("Issue deletion canceled.")
                    print("--------------------\n")
                    return False  # Return False to indicate no action was taken
            else:
                print("--------------------")
                print("Only open issues can be deleted.")
                print("--------------------\n")
                return False  # Return False to indicate no action was taken
    print("--------------------")
    print("Issue not found.")
    print("--------------------\n")
    return False  # Return False to indicate no action was taken

def truncate_text(text, max_length=50):
    """
    Truncate text to a maximum length and add ellipsis if needed.
    """
    if text and len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def show_archived():
    """
    List all archived issues as a table.
    """
    issues = Issue.load_all()
    archived_issues = [issue for issue in issues if issue.status == "Archived"]
    
    if not archived_issues:
        print("--------------------")
        print("No archived issues found.")
        print("--------------------\n")
        return
    
    headers = ["ID", "Title", "Description", "Status", "Resolution", "Date", "Modified"]
    table = [[
        issue.id, 
        truncate_text(issue.title, 30),
        truncate_text(issue.description, 50), 
        issue.status, 
        truncate_text(issue.resolution, 30),
        issue.date, 
        issue.modified
    ] for issue in archived_issues]
    
    print("\nArchived Issues")
    print(tabulate.tabulate(table, headers, tablefmt="grid"))

def export_all_issues(silent=False):
    """
    Export all issues to a CSV file, ensuring no duplicates.
    
    Args:
        silent (bool): If True, suppresses the console message
    """
    issues = Issue.load_all()
    unique_issues = {issue.id: issue for issue in issues}
    export_to_csv({"issues": list(unique_issues.values())}, ALL_ISSUES_FILE, append=False)
    if not silent:
        print("--------------------")
        print("All issues have been exported to CSV.")
        print("--------------------\n")

def search_issues():
    """
    Search for issues based on user input.
    """
    search_term = input("Enter search term: ").strip()
    if not search_term:
        print("--------------------")
        print("Search term cannot be empty.")
        print("--------------------\n")
        return

    issues = Issue.load_all()
    matching_issues = [issue for issue in issues if search_term.lower() in issue.title.lower() or
                       search_term.lower() in issue.description.lower() or
                       search_term.lower() in issue.status.lower() or
                       search_term.lower() in ", ".join(issue.tags).lower()]
    
    if matching_issues:
        headers = ["ID", "Title", "Description", "Status", "Resolution", "Date", "Modified", "Tags"]
        table = [[
            issue.id, 
            truncate_text(issue.title, 30),
            truncate_text(issue.description, 50), 
            issue.status, 
            truncate_text(issue.resolution, 30),
            issue.date, 
            issue.modified, 
            truncate_text(", ".join(issue.tags), 30)
        ] for issue in matching_issues]
        print("\nSearch Results")
        print(tabulate.tabulate(table, headers, tablefmt="grid"))
    else:
        print("--------------------")
        print("No issues found matching the search term.")
        print("--------------------\n")

def configure_readline():
    """
    Configure readline for enhanced command line editing and history.
    """
    # Set the maximum number of history items to save
    readline.set_history_length(1000)
    
    # Create history file if it doesn't exist
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w'):
            pass
    
    # Read history file
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass
        
    # Enable auto-completion with Tab key
    readline.parse_and_bind('tab: complete')

def main():
    """
    Main function to display the menu and handle user input.
    """
    create_table()
    configure_readline()  # Configure readline for input enhancement
    export_done = False  # Track if export has been done
    
    try:
        while True:
            print("\nIssue Manager 1.1")
            print("--------------------")
            print("1. Add Issue")
            print("2. List Current Issues")
            print("3. Edit Issue")
            print("4. Archive Issue")
            print("5. List Archived Issues")
            print("6. Export All Issues to CSV")
            print("7. Search Issues")
            print("8. Delete Issue")
            print("9. Exit")
            choice = input("\nEnter choice: ").strip().lower()
            
            # Process user choices - function returns now indicate if action was taken
            if choice == "1":
                add_issue()
            elif choice == "2":
                list_issues()
            elif choice == "3":
                edit_issue()
            elif choice == "4":
                archive_issue()
            elif choice == "5":
                show_archived()
            elif choice == "6":
                export_all_issues()
            elif choice == "7":
                search_issues()
            elif choice == "8":
                delete_issue()
            elif choice == "9":
                # Export all issues before exiting
                print("\nBacking up all issues before exit...")
                export_all_issues()
                export_done = True
                break
            else:
                print("\nInvalid choice. Please enter a number between 1 and 9.")
                continue  # Skip the "Process another issue" prompt for invalid inputs
            
            # Ask the user if they want to continue
            while True:
                new_issue_choice = input("\nProcess another issue? y/n: ").strip().upper()
                if new_issue_choice == "Y":
                    break
                elif new_issue_choice == "N":
                    # Export all issues before exiting
                    print("\nBacking up all issues before exit...")
                    export_all_issues()
                    export_done = True
                    return
                else:
                    print("\nInvalid choice. Please enter 'y' or 'n'.")
    finally:
        # Save command history when exiting
        readline.write_history_file(HISTORY_FILE)
        # Attempt to export issues if not already done
        if not export_done:
            try:
                print("\nBacking up all issues before exit...")
                export_all_issues()
            except Exception as e:
                print(f"Warning: Could not back up issues on exit: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Save history even when interrupted
        readline.write_history_file(HISTORY_FILE)
        # Try to backup issues even when interrupted
        try:
            print("\nBacking up all issues before terminating...")
            export_all_issues()
        except Exception:
            pass
        print("\n--------------------")
        print("Issue terminated.")
        print("--------------------\n")