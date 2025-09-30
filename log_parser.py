"""
LogParser module for the Valgrind Log Analyzer

This module provides functionality to parse Valgrind memory debugging log files
and extract memory issue information including stack traces and issue details.
"""

import re
import os
from typing import List, Optional, TextIO
from pathlib import Path

from models import MemoryIssue, StackFrame, IssueType


class LogParserError(Exception):
    """Custom exception for log parsing errors."""
    pass


class LogParser:
    """
    Parser for Valgrind log files that extracts memory issues and stack traces.
    
    This class handles reading Valgrind log files, validating their format,
    and extracting structured memory issue data for analysis.
    """
    
    def __init__(self):
        """Initialize the LogParser with compiled regex patterns."""
        # Compile regex patterns for better performance
        self._issue_patterns = self._compile_issue_patterns()
        self._stack_frame_pattern = re.compile(
            r'==\d+==\s+(?:at|by)\s+0x[0-9A-F]+:\s*(.+?)(?:\s+\((.+?)\))?$',
            re.IGNORECASE
        )
        self._valgrind_header_pattern = re.compile(r'==\d+==\s+Memcheck,')
        
    def _compile_issue_patterns(self) -> dict:
        """Compile regex patterns for different types of memory issues."""
        patterns = {
            IssueType.DEFINITELY_LOST: re.compile(
                r'==\d+==\s+([\d,]+)(?:\s+\([^)]+\))?\s+bytes?\s+in\s+([\d,]+)\s+blocks?\s+are\s+definitel?y\s+lost\s+in\s+loss\s+record\s+(.+)',
                re.IGNORECASE
            ),
            IssueType.POSSIBLY_LOST: re.compile(
                r'==\d+==\s+([\d,]+)(?:\s+\([^)]+\))?\s+bytes?\s+in\s+([\d,]+)\s+blocks?\s+are\s+possibl?y\s+lost\s+in\s+loss\s+record\s+(.+)',
                re.IGNORECASE
            ),
            IssueType.STILL_REACHABLE: re.compile(
                r'==\d+==\s+([\d,]+)(?:\s+\([^)]+\))?\s+bytes?\s+in\s+([\d,]+)\s+blocks?\s+are\s+still\s+reachabl?e\s+in\s+loss\s+record\s+(.+)',
                re.IGNORECASE
            ),
            IssueType.INVALID_READ: re.compile(
                r'==\d+==\s+Invalid\s+read\s+of\s+size\s+(\d+)',
                re.IGNORECASE
            ),
            IssueType.INVALID_WRITE: re.compile(
                r'==\d+==\s+Invalid\s+write\s+of\s+size\s+(\d+)',
                re.IGNORECASE
            ),
        }
        return patterns
    
    def parse_file(self, filepath: str) -> List[MemoryIssue]:
        """
        Parse a Valgrind log file and extract memory issues.
        
        Args:
            filepath: Path to the Valgrind log file
            
        Returns:
            List of MemoryIssue objects extracted from the log
            
        Raises:
            LogParserError: If file cannot be read or is invalid format
        """
        # Validate file path and accessibility
        self._validate_file(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                # Validate that this is a Valgrind log file
                self._validate_valgrind_format(file)
                
                # Reset file pointer and parse issues
                file.seek(0)
                return self._parse_issues(file)
                
        except UnicodeDecodeError as e:
            raise LogParserError(f"File encoding error: {e}")
        except IOError as e:
            raise LogParserError(f"Error reading file: {e}")
    
    def _validate_file(self, filepath: str) -> None:
        """
        Validate that the file exists and is readable.
        
        Args:
            filepath: Path to the file to validate
            
        Raises:
            LogParserError: If file is invalid or inaccessible
        """
        path = Path(filepath)
        
        if not path.exists():
            raise LogParserError(f"File does not exist: {filepath}")
        
        if not path.is_file():
            raise LogParserError(f"Path is not a file: {filepath}")
        
        if not os.access(filepath, os.R_OK):
            raise LogParserError(f"File is not readable: {filepath}")
        
        if path.stat().st_size == 0:
            raise LogParserError(f"File is empty: {filepath}")
    
    def _validate_valgrind_format(self, file: TextIO) -> None:
        """
        Validate that the file appears to be a Valgrind log.
        
        Args:
            file: Open file handle to validate
            
        Raises:
            LogParserError: If file doesn't appear to be a Valgrind log
        """
        # Read first few lines to check for Valgrind header
        header_found = False
        lines_checked = 0
        max_lines_to_check = 50  # Check first 50 lines for header
        
        for line in file:
            lines_checked += 1
            if self._valgrind_header_pattern.search(line):
                header_found = True
                break
            if lines_checked >= max_lines_to_check:
                break
        
        if not header_found:
            raise LogParserError(
                "File does not appear to be a valid Valgrind log file. "
                "Expected to find Valgrind header within first 50 lines."
            )
    
    def _parse_issues(self, file: TextIO) -> List[MemoryIssue]:
        """
        Parse memory issues from the file content.
        
        Args:
            file: Open file handle to parse
            
        Returns:
            List of MemoryIssue objects
        """
        issues = []
        lines = file.readlines()
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Try to match each issue type pattern
            issue_match = self._match_issue_line(line)
            if issue_match:
                issue_type, bytes_count, blocks_count, loss_record = issue_match
                
                # Extract stack trace starting from next line
                stack_trace, lines_consumed = self._extract_stack_trace(lines, i + 1)
                
                # Create MemoryIssue object
                issue = MemoryIssue(
                    issue_type=issue_type,
                    bytes_count=bytes_count,
                    blocks_count=blocks_count,
                    loss_record=loss_record,
                    stack_trace=stack_trace,
                    source_location=self._get_source_location(stack_trace)
                )
                
                issues.append(issue)
                i += lines_consumed + 1
            else:
                i += 1
        
        return issues
    
    def _match_issue_line(self, line: str) -> Optional[tuple]:
        """
        Try to match a line against known issue patterns.
        
        Args:
            line: Line to match against patterns
            
        Returns:
            Tuple of (issue_type, bytes_count, blocks_count, loss_record) or None
        """
        for issue_type, pattern in self._issue_patterns.items():
            match = pattern.search(line)
            if match:
                if issue_type in [IssueType.INVALID_READ, IssueType.INVALID_WRITE]:
                    # For invalid read/write, bytes are in first group, no blocks
                    return (issue_type, int(match.group(1)), 1, "N/A")
                else:
                    # For memory leaks, extract bytes, blocks, and loss record
                    # Remove commas from numbers before converting to int
                    bytes_count = int(match.group(1).replace(',', ''))
                    blocks_count = int(match.group(2).replace(',', ''))
                    loss_record = match.group(3).strip()
                    return (issue_type, bytes_count, blocks_count, loss_record)
        
        return None
    
    def _extract_stack_trace(self, lines: List[str], start_index: int) -> tuple:
        """
        Extract stack trace information starting from the given index.
        
        Args:
            lines: All lines from the file
            start_index: Index to start extracting stack trace
            
        Returns:
            Tuple of (stack_frames_list, lines_consumed)
        """
        stack_frames = []
        lines_consumed = 0
        
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            
            # Stop if we hit an empty line or next issue
            if not line or not line.startswith('=='):
                break
            
            # Try to parse as stack frame
            frame = self._parse_stack_frame(line)
            if frame:
                stack_frames.append(frame)
                lines_consumed += 1
            else:
                # If it's not a stack frame but still a Valgrind line, continue
                if line.startswith('==') and ('at 0x' in line or 'by 0x' in line):
                    lines_consumed += 1
                else:
                    break
        
        return stack_frames, lines_consumed
    
    def _parse_stack_frame(self, line: str) -> Optional[StackFrame]:
        """
        Parse a single stack frame line.
        
        Args:
            line: Line containing stack frame information
            
        Returns:
            StackFrame object or None if line doesn't match pattern
        """
        match = self._stack_frame_pattern.search(line)
        if not match:
            return None
        
        function_info = match.group(1).strip()
        location_info = match.group(2) if match.group(2) else ""
        
        # Extract address from the line
        address_match = re.search(r'0x[0-9A-F]+', line)
        address = address_match.group(0) if address_match else "unknown"
        
        # Parse function name and library from the function_info and location_info
        function_name, library = self._parse_function_and_library(function_info, location_info)
        
        # Parse source file and line number from location_info
        source_file, line_number = self._parse_location_info(location_info)
        
        return StackFrame(
            address=address,
            function_name=function_name,
            library=library,
            source_file=source_file,
            line_number=line_number
        )
    
    def _parse_function_and_library(self, function_info: str, location_info: str) -> tuple:
        """
        Parse function name and library from function info and location info.
        
        Args:
            function_info: String containing function information
            location_info: String containing location information (may include library)
            
        Returns:
            Tuple of (function_name, library)
        """
        # Clean up function names that might have extra info
        if function_info == "???":
            function_name = "unknown"
        else:
            function_name = function_info
        
        # Check if location_info contains library information (starts with "in ")
        library = "unknown"
        if location_info and location_info.startswith("in "):
            library = location_info[3:].strip()  # Remove "in " prefix
        
        return function_name, library
    
    def _parse_location_info(self, location_info: str) -> tuple:
        """
        Parse source file and line number from location info.
        
        Args:
            location_info: String containing location information
            
        Returns:
            Tuple of (source_file, line_number)
        """
        if not location_info:
            return None, None
        
        # Skip library information (starts with "in ")
        if location_info.startswith("in "):
            return None, None
        
        # Look for pattern like "filename.cpp:123"
        location_match = re.search(r'([^:]+):(\d+)$', location_info)
        if location_match:
            source_file = location_match.group(1).strip()
            line_number = int(location_match.group(2))
            return source_file, line_number
        
        # If no line number, might just be a file path
        if location_info and location_info != "???":
            return location_info, None
        
        return None, None
    
    def _get_source_location(self, stack_trace: List[StackFrame]) -> Optional[str]:
        """
        Get the most relevant source location from stack trace.
        
        Args:
            stack_trace: List of stack frames
            
        Returns:
            String representation of source location or None
        """
        # First pass: look for frames with both file and line number
        for frame in stack_trace:
            if frame.source_file and frame.line_number:
                return f"{frame.source_file}:{frame.line_number}"
        
        # Second pass: look for frames with just file name
        for frame in stack_trace:
            if frame.source_file:
                return frame.source_file
        
        return None