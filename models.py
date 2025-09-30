"""
Data models for the Valgrind Log Analyzer

This module defines the core data structures used throughout the application
for representing memory issues, stack traces, and analysis statistics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional


class IssueType(Enum):
    """Enumeration of different types of memory issues detected by Valgrind."""
    DEFINITELY_LOST = "definitely_lost"
    POSSIBLY_LOST = "possibly_lost"
    STILL_REACHABLE = "still_reachable"
    INVALID_READ = "invalid_read"
    INVALID_WRITE = "invalid_write"
    USE_AFTER_FREE = "use_after_free"
    OTHER = "other"


class IssueSeverity(Enum):
    """Severity levels for memory issues."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


@dataclass
class StackFrame:
    """Represents a single frame in a stack trace."""
    address: str
    function_name: str
    library: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    
    def __str__(self) -> str:
        """String representation of the stack frame."""
        location = ""
        if self.source_file and self.line_number:
            location = f" ({self.source_file}:{self.line_number})"
        elif self.source_file:
            location = f" ({self.source_file})"
        
        return f"{self.function_name} [{self.library}]{location}"


@dataclass
class MemoryIssue:
    """Represents a memory issue detected by Valgrind."""
    issue_type: IssueType
    bytes_count: int
    blocks_count: int
    loss_record: str
    stack_trace: List[StackFrame]
    source_location: Optional[str] = None
    severity: IssueSeverity = IssueSeverity.MEDIUM
    
    def __post_init__(self):
        """Post-initialization to set severity based on issue type."""
        if self.severity == IssueSeverity.MEDIUM:  # Only set if not explicitly provided
            severity_mapping = {
                IssueType.DEFINITELY_LOST: IssueSeverity.CRITICAL,
                IssueType.POSSIBLY_LOST: IssueSeverity.HIGH,
                IssueType.INVALID_READ: IssueSeverity.CRITICAL,
                IssueType.INVALID_WRITE: IssueSeverity.CRITICAL,
                IssueType.USE_AFTER_FREE: IssueSeverity.CRITICAL,
                IssueType.STILL_REACHABLE: IssueSeverity.LOW,
                IssueType.OTHER: IssueSeverity.MEDIUM,
            }
            self.severity = severity_mapping.get(self.issue_type, IssueSeverity.MEDIUM)


@dataclass
class Statistics:
    """Aggregated statistics for memory issues analysis."""
    total_issues: int
    total_bytes_lost: int
    total_blocks_lost: int
    issues_by_type: Dict[IssueType, int]
    bytes_by_type: Dict[IssueType, int]
    blocks_by_type: Dict[IssueType, int]
    top_sources: List[str]
    severity_distribution: Dict[IssueSeverity, int]
    
    def get_percentage_by_type(self) -> Dict[IssueType, float]:
        """Calculate percentage distribution of issues by type."""
        if self.total_issues == 0:
            return {}
        
        return {
            issue_type: (count / self.total_issues) * 100
            for issue_type, count in self.issues_by_type.items()
        }
    
    def get_bytes_percentage_by_type(self) -> Dict[IssueType, float]:
        """Calculate percentage distribution of bytes by type."""
        if self.total_bytes_lost == 0:
            return {}
        
        return {
            issue_type: (bytes_count / self.total_bytes_lost) * 100
            for issue_type, bytes_count in self.bytes_by_type.items()
        }


@dataclass
class ClassifiedIssues:
    """Container for issues organized by classification."""
    issues_by_type: Dict[IssueType, List[MemoryIssue]]
    statistics: Statistics
    all_issues: List[MemoryIssue]
    
    def get_critical_issues(self) -> List[MemoryIssue]:
        """Get all issues with critical severity."""
        return [
            issue for issue in self.all_issues
            if issue.severity == IssueSeverity.CRITICAL
        ]
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[MemoryIssue]:
        """Get all issues with the specified severity level."""
        return [
            issue for issue in self.all_issues
            if issue.severity == severity
        ]