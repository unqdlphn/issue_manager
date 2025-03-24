import sqlite3
import datetime
import csv
import tabulate
import readline  # Import readline for enhanced input editing capabilities
import os
from models import Issue  # Import the Issue class from models.py

DATABASE_FILE = "issues.db"
ALL_ISSUES_FILE = "all_issues.csv"
ARCHIVE_FILE = "issue_archives.csv"  # Updated variable
MAX_ISSUES = 7  # Maximum number of issues allowed
HISTORY_FILE = os.path.expanduser('~/.issue_manager_history')

def export_to_csv(data, filename, append=False):
    """
    Export data to a CSV file.
    """
    mode = 'a' if append else 'w'
    with open(filename, mode, newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not append:
            writer.writerow(data['issues'][0].__dict__.keys())
        for issue in data['issues']:
            writer.writerow(issue.__dict__.values())

def create_table():
    """
    Create the issues table if it doesn't exist.
    """
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
        return

    title = input("Enter title (max 100 chars): ").strip()
    if not title:
        print("--------------------")
        print("Title cannot be empty.")
        print("--------------------\n")
        return
    if len(title) > 100:
        title = title[:100]
        print("Title truncated to 100 characters.")
        
    description = input("Enter description (max 500 chars): ").strip()
    if not description:
        print("--------------------")
        print("Description cannot be empty.")
        print("--------------------\n")
        return
    if len(description) > 500:
        description = description[:500]
        print("Description truncated to 500 characters.")
        
    tags_input = input("Enter tags (comma separated, max 5 tags): ").strip()
    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []
    if len(tags) > 5:
        tags = tags[:5]
        print("Limited to first 5 tags.")
        
    new_issue = Issue(title, description, tags=tags)
    confirm = input("\nAre you sure you want to add this issue? (y/n): ").strip().lower()
    if confirm == 'y':
        new_issue.save()
        print("--------------------")
        print("Issue added.")
        print("--------------------\n")
    else:
        print("--------------------")
        print("Issue addition canceled.")
        print("--------------------\n")

def list_issues(show_archived=False):
    """
    List all issues, optionally including archived issues.
    """
    issues = Issue.load_all()
    if show_archived:
        print("\nArchived Issues")
        print("--------------------")
        for issue in issues:
            if issue.status == "Archived":
                print(f"ID: {issue.id}, Title: {truncate_text(issue.title, 30)}, Date: {issue.date}")
                print(f"Description: {truncate_text(issue.description, 60)}")
                print(f"Status: {issue.status}")
                print(f"Resolution: {truncate_text(issue.resolution, 60)}")
                print("--------------------\n")
    else:
        print("\nCurrent Issues")
        print("--------------------")
        for issue in issues:
            if issue.status != "Archived":
                print(f"ID: {issue.id}, Title: {truncate_text(issue.title, 30)}, Date: {issue.date}")
                print(f"Description: {truncate_text(issue.description, 60)}")
                print(f"Status: {issue.status}")
                print("--------------------\n")

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
        return
    issues = Issue.load_all()
    for issue in issues:
        if issue.id == issue_id:
            new_title = input(f"Enter new title (max 100 chars) ({issue.title}): ").strip()
            if new_title:
                if len(new_title) > 100:
                    new_title = new_title[:100]
                    print("Title truncated to 100 characters.")
                issue.title = new_title
            
            new_description = input(f"Enter new description (max 500 chars) ({issue.description}): ").strip()
            if new_description:
                if len(new_description) > 500:
                    new_description = new_description[:500]
                    print("Description truncated to 500 characters.")
                issue.description = new_description
                
            new_tags_input = input(f"Enter new tags (comma separated, max 5) ({', '.join(issue.tags)}): ").strip()
            if new_tags_input:
                new_tags = [tag.strip() for tag in new_tags_input.split(",")]
                if len(new_tags) > 5:
                    new_tags = new_tags[:5]
                    print("Limited to first 5 tags.")
                issue.tags = new_tags
                
            new_status = input(f"Enter new status ({issue.status}) (Open, In Progress, Resolved, Archived): ").strip()
            if new_status in ["Open", "In Progress", "Resolved", "Archived"]:
                issue.status = new_status
                if new_status == "Resolved":
                    resolution = input("\nHow was the issue resolved? (max 200 chars): ").strip()
                    if len(resolution) > 200:
                        resolution = resolution[:200]
                        print("Resolution truncated to 200 characters.")
                    issue.resolution = resolution or "None"
            issue.modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            confirm = input("\nAre you sure you want to edit this issue? (y/n): ").strip().lower()
            if confirm == 'y':
                issue.update()
                print("--------------------")
                print("Issue updated.")
                print("--------------------\n")
            else:
                print("--------------------")
                print("Issue edit canceled.")
                print("--------------------\n")
            return
    print("Issue not found.")

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
        return
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
                else:
                    print("--------------------")
                    print("Issue archive canceled.")
                    print("--------------------\n")
            else:
                print("--------------------")
                print("Only resolved issues can be archived.")
                print("--------------------\n")
            return
    print("--------------------")    
    print("Issue not found.")
    print("--------------------\n")

def delete_issue():
    """
    Delete an open issue by prompting the user for the issue ID.
    """
    list_issues()
    try:
        issue_id = int(input("Enter ID of issue to delete: "))
    except ValueError:
        print("--------------------")
        print("Invalid ID. Please enter a number.")
        print("--------------------\n")
        return
    issues = Issue.load_all()
    for issue in issues:
        if issue.id == issue_id:
            if issue.status == "Open":
                confirm = input("\nAre you sure you want to delete this issue? (y/n): ").strip().lower()
                if confirm == 'y':
                    Issue.delete(issue_id)
                    print("--------------------")
                    print("Issue deleted.")
                    print("--------------------\n")
                else:
                    print("--------------------")
                    print("Issue deletion canceled.")
                    print("--------------------\n")
            else:
                print("--------------------")
                print("Only open issues can be deleted.")
                print("--------------------\n")
            return
    print("Issue not found.")

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

def export_all_issues():
    """
    Export all issues to a CSV file, ensuring no duplicates.
    """
    issues = Issue.load_all()
    unique_issues = {issue.id: issue for issue in issues}
    export_to_csv({"issues": list(unique_issues.values())}, ALL_ISSUES_FILE, append=False)
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
                break
            else:
                print("\nInvalid choice. Please enter a number between 1 and 9.")
            
            # Ask the user if they want to enter a new issue
            while True:
                new_issue_choice = input("\nProcess another issue? y/n: ").strip().upper()
                if new_issue_choice == "Y":
                    break
                elif new_issue_choice == "N":
                    export_all_issues()
                    return
                else:
                    print("\nInvalid choice. Please enter 'y' or 'n'.")
    finally:
        # Save command history when exiting
        readline.write_history_file(HISTORY_FILE)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Save history even when interrupted
        readline.write_history_file(HISTORY_FILE)
        print("\n--------------------")
        print("Issue terminated.")
        print("--------------------\n")