# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-03-24

### Added

- Added confirmation prompts for adding, editing, archiving, and deleting issues.
- Limited the number of current issues to 7 to motivate users to resolve issues.
- Enabled arrow keys and delete buttons while entering information using the `readline` module.
- Replaced JSON data storage with SQLite database for better performance and scalability.
- Comprehensive test suite with 88% code coverage
- Direct tests for model methods (save, update, delete)
- Edge case testing for input validation
- Tests for error handling paths in all components

### Improved
- Increased code coverage from 74% to 88% (+14%)
- Fixed export_to_csv testing (previously 0% coverage, now 100%)
- Improved models.py coverage from 48% to 86% (+38%)
- Improved issue_manager.py coverage from 64% to 85% (+21%)
- Improved user experience with enhanced input validation

### Fixed
- Fixed a bug where editing an issue created a new issue instead of updating the existing one.
- Fixed bug with empty file check in CSV export
- Added proper validation for issue tags with special characters
- Fixed issues with maximum character limits 
- Fixed issue with CSV export not handling special characters correctly
- Improved error handling throughout the application

### Development
- Added pytest-cov to generate HTML coverage reports
- Created specialized test fixtures for database and input mocking
- Added .gitignore patterns for test artifacts
- Organized tests into logical groups (direct, interactive, edge cases)

## [1.0.0] - 2025-01-14

### Added

- Initial release of the Issue Tracker application
- Basic functionality for adding, editing, archiving, and deleting issues
- CSV export functionality for all issues
- Basic input validation for issue fields
- Basic error handling for file operations