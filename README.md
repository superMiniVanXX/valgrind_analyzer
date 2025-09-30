# Valgrind Log Analyzer

A Python tool that analyzes Valgrind memory debugging logs and generates comprehensive Excel reports categorizing different types of memory issues.

## Project Structure

```
valgrind-log-analyzer/
├── valgrind_analyzer.py    # Main CLI entry point
├── models.py              # Core data models and enums
├── log_parser.py          # Valgrind log parsing functionality
├── issue_classifier.py    # Issue categorization and analysis
├── excel_reporter.py      # Excel report generation
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python valgrind_analyzer.py <valgrind_log_file> [-o output.xlsx] [--csv-fallback]
```

## Features

- Parse Valgrind memory debugging logs
- Categorize memory issues by type (definitely lost, possibly lost, still reachable, etc.)
- Extract detailed stack trace information
- Generate comprehensive Excel reports with multiple worksheets
- Provide summary statistics and analysis

## Development Status

This project is currently under development. Core data models and project structure have been established. Implementation of parsing, classification, and reporting functionality is in progress.