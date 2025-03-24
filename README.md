# Issue Manager (Beta)

Issue Manager is a simple command-line application for managing issues. It allows you to add, list, edit, archive, delete, and search for issues. The application uses SQLite for data storage and supports exporting issues to CSV files.

## 1.0 Features

- **Add Issue**: Add a new issue with a title, description, and tags.
- **List Current Issues**: List all current (non-archived) issues.
- **Edit Issue**: Edit the details of an existing issue.
- **Archive Issue**: Archive a resolved issue.
- **List Archived Issues**: List all archived issues.
- **Export All Issues to CSV**: Export all issues to a CSV file.
- **Search Issues**: Search for issues based on a search term.
- **Delete Issue**: Delete an open issue.

## 1.1 New Features and Fixes

- **Confirmation Prompts**: Added confirmation prompts for adding, editing, archiving, and deleting issues.
- **Limit on Number of Issues**: Limited the number of current issues to 7 to motivate users to resolve issues.
- **Enhanced Input Editing**: Enabled arrow keys and delete buttons while entering information using the `readline` module.
- **Fixed Edit Issue Bug**: Fixed a bug where editing an issue created a new issue instead of updating the existing one.
- **Database Integration**: Replaced JSON data storage with SQLite database for better performance and scalability.

## Main Feature

SQite Enhancements

1. Error Handling: Implement try-except blocks to handle potential database errors (e.g., connection issues, invalid SQL queries).
2. Data Types: Use appropriate SQLite3 data types (TEXT, INTEGER, REAL, BLOB, etc.) for the columns.
3. Security: Use parameterized queries to prevent SQL injection vulnerabilities.
4. Performance: Optimize the queries and use indexes for faster data retrieval.
6. Database Interaction: Include methods for interacting with the database, such as creating, reading, updating, and deleting records.
7. Validation: Include validation logic to ensure that the data being stored meets certain criteria.
8. Abstraction: Provide an abstraction layer between the database and the application logic, making it easier to manage and manipulate data.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/unqdlphn/issue_manager.git
    cd issue_manager/src
    ```

2. Create and activate a virtual environment:
    ```sh
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. If you are on Windows, install `pyreadline`:
    ```sh
    pip install pyreadline
    ```

## Usage

Run the script to start the application:
```sh
python issue_manager.py


Menu Options

Add Issue: Add a new issue by providing a title, description, and tags.
List Current Issues: List all current (non-archived) issues.
Edit Issue: Edit the details of an existing issue by providing the issue ID.
Archive Issue: Archive a resolved issue by providing the issue ID.
List Archived Issues: List all archived issues.
Export All Issues to CSV: Export all issues to a CSV file.
Search Issues: Search for issues based on a search term.
Delete Issue: Delete an open issue by providing the issue ID.
Exit: Exit the application.

Example

Issue Manager 1.0 (Beta)
--------------------
1. Add Issue
2. List Current Issues
3. Edit Issue
4. Archive Issue
5. List Archived Issues
6. Export All Issues to CSV
7. Search Issues
8. Delete Issue
9. Exit

Enter choice: 1
Enter title: Example Issue
Enter description: This is an example issue.
Enter tags (comma separated): example, test
Are you sure you want to add this issue? (y/n): y
--------------------
Issue added.
--------------------

License

This project is licensed under the MIT License. See the LICENSE file for details.



### Explanation

- **Features**: Lists the main features of the application.
- **New Features and Fixes**: Describes the new features and fixes that have been added, including the switch from JSON to SQLite for data storage.
- **Main Feature**: Describes the main feature for the current update.
- **Installation**: Provides instructions for setting up the project.
- **Usage**: Explains how to run the application and describes the menu options.
- **Example**: Provides an example of how to use the application.
- **License**: Mentions the license under which the project is distributed.

This `README.md` file provides a comprehensive overview of the project, including its features, installation instructions, usage, and new features and fixes.