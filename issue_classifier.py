"""
IssueClassifier module for the Valgrind Log Analyzer

This module provides functionality to classify and analyze memory issues,
calculate statistics, and prioritize issues by severity.
"""

from typing import List, Dict, Counter
from collections import defaultdict, Counter

from models import (
    MemoryIssue, IssueType, IssueSeverity, Statistics, 
    ClassifiedIssues, StackFrame
)


class IssueClassifier:
    """
    Classifier for categorizing and analyzing memory issues from Valgrind logs.
    
    This class provides methods to group issues by type, calculate aggregate
    statistics, and prioritize issues based on severity and impact.
    """
    
    def __init__(self):
        """Initialize the IssueClassifier."""
        pass
    
    def classify_issues(self, issues: List[MemoryIssue]) -> ClassifiedIssues:
        """
        Classify and organize memory issues by type and calculate statistics.
        
        Args:
            issues: List of MemoryIssue objects to classify
            
        Returns:
            ClassifiedIssues object containing organized data and statistics
        """
        if not issues:
            return self._create_empty_classification()
        
        # Group issues by type
        issues_by_type = self._group_issues_by_type(issues)
        
        # Calculate comprehensive statistics
        statistics = self.calculate_statistics(issues)
        
        # Sort issues by priority within each type
        prioritized_issues_by_type = {}
        for issue_type, type_issues in issues_by_type.items():
            prioritized_issues_by_type[issue_type] = self.prioritize_issues(type_issues)
        
        # Sort all issues by priority
        all_prioritized_issues = self.prioritize_issues(issues)
        
        return ClassifiedIssues(
            issues_by_type=prioritized_issues_by_type,
            statistics=statistics,
            all_issues=all_prioritized_issues
        )
    
    def _create_empty_classification(self) -> ClassifiedIssues:
        """Create an empty ClassifiedIssues object for when no issues are found."""
        empty_stats = Statistics(
            total_issues=0,
            total_bytes_lost=0,
            total_blocks_lost=0,
            issues_by_type={},
            bytes_by_type={},
            blocks_by_type={},
            top_sources=[],
            severity_distribution={}
        )
        
        return ClassifiedIssues(
            issues_by_type={},
            statistics=empty_stats,
            all_issues=[]
        )
    
    def _group_issues_by_type(self, issues: List[MemoryIssue]) -> Dict[IssueType, List[MemoryIssue]]:
        """
        Group issues by their type.
        
        Args:
            issues: List of MemoryIssue objects
            
        Returns:
            Dictionary mapping IssueType to list of issues
        """
        grouped = defaultdict(list)
        for issue in issues:
            grouped[issue.issue_type].append(issue)
        return dict(grouped)
    
    def calculate_statistics(self, issues: List[MemoryIssue]) -> Statistics:
        """
        Calculate comprehensive statistics for the given issues.
        
        Args:
            issues: List of MemoryIssue objects
            
        Returns:
            Statistics object with aggregated data
        """
        if not issues:
            return Statistics(
                total_issues=0,
                total_bytes_lost=0,
                total_blocks_lost=0,
                issues_by_type={},
                bytes_by_type={},
                blocks_by_type={},
                top_sources=[],
                severity_distribution={}
            )
        
        # Initialize counters
        issues_by_type = Counter()
        bytes_by_type = Counter()
        blocks_by_type = Counter()
        severity_distribution = Counter()
        
        total_bytes = 0
        total_blocks = 0
        
        # Aggregate data
        for issue in issues:
            issues_by_type[issue.issue_type] += 1
            bytes_by_type[issue.issue_type] += issue.bytes_count
            blocks_by_type[issue.issue_type] += issue.blocks_count
            severity_distribution[issue.severity] += 1
            
            total_bytes += issue.bytes_count
            total_blocks += issue.blocks_count
        
        # Calculate top sources
        top_sources = self._identify_top_sources(issues)
        
        return Statistics(
            total_issues=len(issues),
            total_bytes_lost=total_bytes,
            total_blocks_lost=total_blocks,
            issues_by_type=dict(issues_by_type),
            bytes_by_type=dict(bytes_by_type),
            blocks_by_type=dict(blocks_by_type),
            top_sources=top_sources,
            severity_distribution=dict(severity_distribution)
        )
    
    def _identify_top_sources(self, issues: List[MemoryIssue], limit: int = 10) -> List[str]:
        """
        Identify the most frequent issue sources and locations.
        
        Args:
            issues: List of MemoryIssue objects
            limit: Maximum number of top sources to return
            
        Returns:
            List of top source locations ordered by frequency
        """
        source_counter = Counter()
        
        for issue in issues:
            # Count by source location if available
            if issue.source_location:
                source_counter[issue.source_location] += 1
            # Otherwise, count by top stack frame function
            elif issue.stack_trace:
                top_frame = issue.stack_trace[0]
                if top_frame.function_name != "unknown":
                    source_key = f"{top_frame.function_name} ({top_frame.library})"
                    source_counter[source_key] += 1
        
        # Return top sources by frequency
        return [source for source, _ in source_counter.most_common(limit)]
    
    def prioritize_issues(self, issues: List[MemoryIssue]) -> List[MemoryIssue]:
        """
        Sort issues by priority based on severity and impact.
        
        Priority is determined by:
        1. Severity level (Critical > High > Medium > Low > Info)
        2. Bytes lost (higher bytes = higher priority)
        3. Blocks count (higher blocks = higher priority)
        
        Args:
            issues: List of MemoryIssue objects to prioritize
            
        Returns:
            List of issues sorted by priority (highest priority first)
        """
        def priority_key(issue: MemoryIssue) -> tuple:
            # Return tuple for sorting: (severity_value, -bytes, -blocks)
            # Negative bytes and blocks for descending order
            return (
                issue.severity.value,  # Lower value = higher severity
                -issue.bytes_count,    # Higher bytes = higher priority
                -issue.blocks_count    # Higher blocks = higher priority
            )
        
        return sorted(issues, key=priority_key)
    
    def get_issues_by_severity(self, issues: List[MemoryIssue], 
                              severity: IssueSeverity) -> List[MemoryIssue]:
        """
        Filter issues by severity level.
        
        Args:
            issues: List of MemoryIssue objects
            severity: Severity level to filter by
            
        Returns:
            List of issues with the specified severity
        """
        return [issue for issue in issues if issue.severity == severity]
    
    def get_critical_issues(self, issues: List[MemoryIssue]) -> List[MemoryIssue]:
        """
        Get all critical severity issues.
        
        Args:
            issues: List of MemoryIssue objects
            
        Returns:
            List of critical issues sorted by priority
        """
        critical_issues = self.get_issues_by_severity(issues, IssueSeverity.CRITICAL)
        return self.prioritize_issues(critical_issues)
    
    def calculate_bytes_percentage_by_type(self, statistics: Statistics) -> Dict[IssueType, float]:
        """
        Calculate percentage distribution of bytes lost by issue type.
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary mapping IssueType to percentage of total bytes
        """
        if statistics.total_bytes_lost == 0:
            return {}
        
        return {
            issue_type: (bytes_count / statistics.total_bytes_lost) * 100
            for issue_type, bytes_count in statistics.bytes_by_type.items()
        }
    
    def calculate_issues_percentage_by_type(self, statistics: Statistics) -> Dict[IssueType, float]:
        """
        Calculate percentage distribution of issue count by type.
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary mapping IssueType to percentage of total issues
        """
        if statistics.total_issues == 0:
            return {}
        
        return {
            issue_type: (count / statistics.total_issues) * 100
            for issue_type, count in statistics.issues_by_type.items()
        }
    
    def get_summary_by_severity(self, statistics: Statistics) -> Dict[IssueSeverity, Dict[str, int]]:
        """
        Get summary statistics grouped by severity level.
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary mapping severity to summary statistics
        """
        summary = {}
        
        for severity in IssueSeverity:
            if severity in statistics.severity_distribution:
                count = statistics.severity_distribution[severity]
                summary[severity] = {
                    'count': count,
                    'percentage': (count / statistics.total_issues) * 100 if statistics.total_issues > 0 else 0
                }
            else:
                summary[severity] = {'count': 0, 'percentage': 0.0}
        
        return summary
    
    def get_bytes_lost_by_category(self, statistics: Statistics) -> Dict[str, int]:
        """
        Get total bytes lost organized by category with human-readable names.
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary mapping category names to total bytes lost
        """
        category_mapping = {
            IssueType.DEFINITELY_LOST: "Definitely Lost",
            IssueType.POSSIBLY_LOST: "Possibly Lost", 
            IssueType.STILL_REACHABLE: "Still Reachable",
            IssueType.INVALID_READ: "Invalid Reads",
            IssueType.INVALID_WRITE: "Invalid Writes",
            IssueType.USE_AFTER_FREE: "Use After Free",
            IssueType.OTHER: "Other Issues"
        }
        
        return {
            category_mapping.get(issue_type, str(issue_type)): bytes_count
            for issue_type, bytes_count in statistics.bytes_by_type.items()
        }
    
    def get_blocks_lost_by_category(self, statistics: Statistics) -> Dict[str, int]:
        """
        Get total blocks lost organized by category with human-readable names.
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary mapping category names to total blocks lost
        """
        category_mapping = {
            IssueType.DEFINITELY_LOST: "Definitely Lost",
            IssueType.POSSIBLY_LOST: "Possibly Lost", 
            IssueType.STILL_REACHABLE: "Still Reachable",
            IssueType.INVALID_READ: "Invalid Reads",
            IssueType.INVALID_WRITE: "Invalid Writes",
            IssueType.USE_AFTER_FREE: "Use After Free",
            IssueType.OTHER: "Other Issues"
        }
        
        return {
            category_mapping.get(issue_type, str(issue_type)): blocks_count
            for issue_type, blocks_count in statistics.blocks_by_type.items()
        }
    
    def get_detailed_source_analysis(self, issues: List[MemoryIssue]) -> Dict[str, Dict[str, any]]:
        """
        Get detailed analysis of issue sources including frequency and impact.
        
        Args:
            issues: List of MemoryIssue objects to analyze
            
        Returns:
            Dictionary mapping source locations to detailed analysis
        """
        source_analysis = defaultdict(lambda: {
            'count': 0,
            'total_bytes': 0,
            'total_blocks': 0,
            'issue_types': set(),
            'severities': set()
        })
        
        for issue in issues:
            source_key = issue.source_location or "Unknown"
            if source_key == "Unknown" and issue.stack_trace:
                # Use top stack frame if no source location
                top_frame = issue.stack_trace[0]
                if top_frame.function_name != "unknown":
                    source_key = f"{top_frame.function_name} ({top_frame.library})"
            
            analysis = source_analysis[source_key]
            analysis['count'] += 1
            analysis['total_bytes'] += issue.bytes_count
            analysis['total_blocks'] += issue.blocks_count
            analysis['issue_types'].add(issue.issue_type.value)
            analysis['severities'].add(issue.severity.value)
        
        # Convert sets to lists for JSON serialization
        for source, analysis in source_analysis.items():
            analysis['issue_types'] = list(analysis['issue_types'])
            analysis['severities'] = list(analysis['severities'])
        
        return dict(source_analysis)
    
    def get_memory_leak_summary(self, statistics: Statistics) -> Dict[str, any]:
        """
        Get a comprehensive summary of memory leaks (excluding invalid reads/writes).
        
        Args:
            statistics: Statistics object containing aggregated data
            
        Returns:
            Dictionary with memory leak summary information
        """
        leak_types = [
            IssueType.DEFINITELY_LOST,
            IssueType.POSSIBLY_LOST,
            IssueType.STILL_REACHABLE
        ]
        
        total_leak_bytes = sum(
            statistics.bytes_by_type.get(leak_type, 0)
            for leak_type in leak_types
        )
        
        total_leak_blocks = sum(
            statistics.blocks_by_type.get(leak_type, 0)
            for leak_type in leak_types
        )
        
        total_leak_issues = sum(
            statistics.issues_by_type.get(leak_type, 0)
            for leak_type in leak_types
        )
        
        return {
            'total_leaked_bytes': total_leak_bytes,
            'total_leaked_blocks': total_leak_blocks,
            'total_leak_issues': total_leak_issues,
            'leak_percentage_of_total': (
                (total_leak_bytes / statistics.total_bytes_lost) * 100
                if statistics.total_bytes_lost > 0 else 0
            ),
            'breakdown_by_type': {
                'definitely_lost_bytes': statistics.bytes_by_type.get(IssueType.DEFINITELY_LOST, 0),
                'possibly_lost_bytes': statistics.bytes_by_type.get(IssueType.POSSIBLY_LOST, 0),
                'still_reachable_bytes': statistics.bytes_by_type.get(IssueType.STILL_REACHABLE, 0)
            }
        }