#!/usr/bin/env python3
"""
Valgrind Log Analyzer - Main entry point

A Python tool that analyzes Valgrind memory debugging logs and generates
comprehensive Excel reports categorizing different types of memory issues.
"""

import sys
import argparse
import csv
import logging
from pathlib import Path
from typing import List, Optional
import time

from models import MemoryIssue, ClassifiedIssues, IssueType
from log_parser import LogParser, LogParserError
from issue_classifier import IssueClassifier
from excel_reporter import ExcelReporter, ExcelReportError


def export_to_csv(classified_issues: ClassifiedIssues, output_path: str) -> None:
    """
    Export classified issues to CSV format as fallback.
    
    Args:
        classified_issues: The analyzed and classified memory issues data
        output_path: Path where the CSV file should be saved
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'Issue Type', 'Severity', 'Bytes', 'Blocks', 
            'Loss Record', 'Primary Function', 'Source Location'
        ])
        
        # Write data rows
        for issue in classified_issues.all_issues:
            # Get primary function from stack trace
            primary_function = "Unknown"
            if issue.stack_trace:
                for frame in issue.stack_trace:
                    if frame.function_name and frame.function_name != "???":
                        primary_function = frame.function_name
                        break
            
            # Get source location
            source_location = issue.source_location or "Unknown"
            if source_location == "Unknown" and issue.stack_trace:
                for frame in issue.stack_trace:
                    if frame.source_file:
                        if frame.line_number:
                            source_location = f"{frame.source_file}:{frame.line_number}"
                        else:
                            source_location = frame.source_file
                        break
            
            writer.writerow([
                issue.issue_type.value.replace("_", " ").title(),
                issue.severity.name,
                issue.bytes_count,
                issue.blocks_count,
                issue.loss_record,
                primary_function,
                source_location
            ])


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: Enable verbose logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def main() -> None:
    """
    Main entry point for the Valgrind log analyzer.
    """
    parser = argparse.ArgumentParser(
        description="Analyze Valgrind memory debugging logs and generate Excel reports"
    )
    parser.add_argument(
        "input_file",
        help="Path to the Valgrind log file to analyze"
    )
    parser.add_argument(
        "-o", "--output",
        default="valgrind_report.xlsx",
        help="Output Excel file path (default: valgrind_report.xlsx)"
    )
    parser.add_argument(
        "--csv-fallback",
        action="store_true",
        help="Use CSV export if Excel generation fails"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Analyzing Valgrind log: {args.input_file}")
        
        # Initialize components
        parser = LogParser()
        classifier = IssueClassifier()
        reporter = ExcelReporter()
        
        # Parse the log file
        logging.info("Parsing Valgrind log file...")
        issues = parser.parse_file(str(input_path))
        
        if not issues:
            print("No memory issues found in the log file.")
            return
        
        print(f"Found {len(issues)} memory issues")
        
        # Classify and analyze issues
        logging.info("Classifying and analyzing issues...")
        classified_issues = classifier.classify_issues(issues)
        
        # Generate Excel report
        logging.info("Generating Excel report...")
        try:
            reporter.generate_report(classified_issues, args.output)
            print(f"Excel report generated successfully: {args.output}")
            
        except ExcelReportError as e:
            if args.csv_fallback:
                print(f"Excel generation failed: {e}")
                print("Attempting CSV fallback...")
                csv_output = args.output.replace('.xlsx', '.csv')
                export_to_csv(classified_issues, csv_output)
                print(f"CSV report generated: {csv_output}")
            else:
                raise
        
    except LogParserError as e:
        print(f"Error parsing log file: {e}", file=sys.stderr)
        sys.exit(1)
    except ExcelReportError as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        if not args.csv_fallback:
            print("Use --csv-fallback option to generate CSV output instead", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()