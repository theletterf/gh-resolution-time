#!/usr/bin/env python3
"""
GitHub Issue Time-to-Resolution Analyzer

Analyzes closed issues from a GitHub repository to calculate
time-to-resolution statistics including mean, median, and percentiles.
"""

import os
import sys
import argparse
import requests
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Optional
import time


class GitHubIssueAnalyzer:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN environment variable or pass token parameter.")
        
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._collaborators_cache = {}
        
    def get_collaborators(self, repo: str) -> set:
        """Get all collaborators for a repository."""
        if repo in self._collaborators_cache:
            return self._collaborators_cache[repo]
            
        collaborators = set()
        url = f"https://api.github.com/repos/{repo}/collaborators"
        page = 1
        
        while True:
            try:
                response = self.session.get(url, params={'per_page': 100, 'page': page}, timeout=30)
                response.raise_for_status()
                
                collabs = response.json()
                if not collabs:
                    break
                    
                for collab in collabs:
                    collaborators.add(collab['login'])
                    
                if len(collabs) < 100:  # Last page
                    break
                    
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"Warning: Could not fetch collaborators: {e}")
                break
                
        self._collaborators_cache[repo] = collaborators
        print(f"Found {len(collaborators)} collaborators")
        return collaborators
        
    def is_member_issue(self, issue: Dict, collaborators: set) -> bool:
        """Check if issue was created by a repository member."""
        author = issue.get('user', {}).get('login')
        return author in collaborators
        
    def fetch_issues(self, repo: str, state: str = 'closed', per_page: int = 100) -> List[Dict]:
        """Fetch all issues from a repository with pagination."""
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            'state': state,
            'per_page': per_page,
            'sort': 'created',
            'direction': 'desc'
        }
        
        all_issues = []
        page = 1
        
        while True:
            print(f"Fetching page {page}... ", end='', flush=True)
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # Check rate limit
                remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
                if remaining < 10:
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    wait_time = max(reset_time - int(time.time()), 0) + 1
                    print(f"\nRate limit approaching. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                
                issues = response.json()
                if not issues:
                    break
                    
                # Filter out pull requests
                actual_issues = [issue for issue in issues if not issue.get('pull_request')]
                all_issues.extend(actual_issues)
                print(f"Found {len(actual_issues)} issues")
                
                # Check if there's a next page
                if 'next' not in response.links:
                    break
                    
                url = response.links['next']['url']
                params = {}  # URL already contains parameters
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"\nError fetching issues: {e}")
                break
                
        return all_issues
    
    def categorize_issues(self, issues: List[Dict], collaborators: set) -> Dict[str, List[Dict]]:
        """Categorize issues by author type (member vs external)."""
        member_issues = []
        external_issues = []
        
        for issue in issues:
            if self.is_member_issue(issue, collaborators):
                member_issues.append(issue)
            else:
                external_issues.append(issue)
                
        return {
            'member': member_issues,
            'external': external_issues
        }
    
    def calculate_resolution_times(self, issues: List[Dict]) -> List[float]:
        """Calculate resolution times in hours for closed issues."""
        durations = []
        
        for issue in issues:
            if not issue.get('closed_at'):
                continue
                
            try:
                created_at = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                closed_at = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00'))
                
                duration = closed_at - created_at
                hours = duration.total_seconds() / 3600
                durations.append(hours)
                
            except (ValueError, KeyError) as e:
                print(f"Warning: Could not parse timestamps for issue #{issue.get('number')}: {e}")
                continue
                
        return durations
    
    def analyze_resolution_times(self, durations: List[float]) -> Dict:
        """Analyze resolution times and return statistics."""
        if not durations:
            return {}
            
        durations_days = [d / 24 for d in durations]
        
        stats = {
            'count': len(durations),
            'mean_hours': statistics.mean(durations),
            'median_hours': statistics.median(durations),
            'mean_days': statistics.mean(durations_days),
            'median_days': statistics.median(durations_days),
            'min_days': min(durations_days),
            'max_days': max(durations_days),
            'std_dev_days': statistics.stdev(durations_days) if len(durations_days) > 1 else 0
        }
        
        # Calculate percentiles
        sorted_days = sorted(durations_days)
        stats['p25_days'] = sorted_days[int(len(sorted_days) * 0.25)]
        stats['p75_days'] = sorted_days[int(len(sorted_days) * 0.75)]
        stats['p90_days'] = sorted_days[int(len(sorted_days) * 0.90)]
        stats['p95_days'] = sorted_days[int(len(sorted_days) * 0.95)]
        
        return stats
    
    def print_results(self, stats: Dict, title: str = "GITHUB ISSUE RESOLUTION TIME ANALYSIS"):
        """Print analysis results in a formatted way."""
        if not stats:
            print("No closed issues found to analyze.")
            return
            
        print(f"\n{'='*60}")
        print(title)
        print(f"{'='*60}")
        print(f"Total Issues Analyzed: {stats['count']:,}")
        print()
        print("RESOLUTION TIME STATISTICS (in days):")
        print(f"  Mean:     {stats['mean_days']:.2f}")
        print(f"  Median:   {stats['median_days']:.2f}")
        print(f"  Min:      {stats['min_days']:.2f}")
        print(f"  Max:      {stats['max_days']:.2f}")
        print(f"  Std Dev:  {stats['std_dev_days']:.2f}")
        print()
        print("PERCENTILES (in days):")
        print(f"  25th:     {stats['p25_days']:.2f}")
        print(f"  75th:     {stats['p75_days']:.2f}")
        print(f"  90th:     {stats['p90_days']:.2f}")
        print(f"  95th:     {stats['p95_days']:.2f}")
        print(f"{'='*60}")
    
    def generate_html_report(self, durations_data: Dict, filename: str, repo: str):
        """Generate HTML report with histogram chart using Chart.js."""
        
        # Prepare data for all categories
        all_data = []
        categories = []
        
        for category, durations in durations_data.items():
            if durations:
                days = [d / 24 for d in durations]  # Convert hours to days
                all_data.append({
                    'name': category,
                    'data': days,
                    'stats': self.analyze_resolution_times(durations)
                })
                categories.append(category)
        
        if not all_data:
            print("No data to generate HTML report.")
            return
            
        # Create histogram bins (0-100 days with 5-day intervals)
        max_days = max(max(item['data']) for item in all_data)
        bin_size = 5
        max_bin = min(int(max_days) + bin_size, 100)  # Cap at 100 days for readability
        bins = list(range(0, max_bin + bin_size, bin_size))
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Issue Resolution Time Analysis - {repo}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .stats-card {{
            background: #f8f9fc;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }}
        .stats-card h3 {{
            margin: 0 0 15px 0;
            color: #2d3748;
            font-size: 1.3em;
        }}
        .stats-row {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
        }}
        .stats-label {{
            color: #4a5568;
            font-weight: 500;
        }}
        .stats-value {{
            color: #2d3748;
            font-weight: bold;
        }}
        .summary {{
            background: #e6fffa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #38b2ac;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #718096;
            border-top: 1px solid #e2e8f0;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Issue Resolution Time Analysis</h1>
            <p>Repository: {repo}</p>
        </div>
        
        <div class="content">
            <div class="summary">
                <h3>📊 Analysis Summary</h3>
                <p>This report analyzes the time it takes to resolve GitHub issues, showing distribution patterns and key statistics.</p>
            </div>
            
            <div class="chart-container">
                <canvas id="histogramChart"></canvas>
            </div>
            
            <div class="stats-grid">'''
        
        # Add statistics cards for each category
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b']
        
        for i, item in enumerate(all_data):
            stats = item['stats']
            color = colors[i % len(colors)]
            
            html_content += f'''
                <div class="stats-card">
                    <h3 style="color: {color}">📈 {item['name'].title()} Issues Statistics</h3>
                    <div class="stats-row">
                        <span class="stats-label">Total Issues:</span>
                        <span class="stats-value">{stats['count']:,}</span>
                    </div>
                    <div class="stats-row">
                        <span class="stats-label">Mean Resolution:</span>
                        <span class="stats-value">{stats['mean_days']:.1f} days</span>
                    </div>
                    <div class="stats-row">
                        <span class="stats-label">Median Resolution:</span>
                        <span class="stats-value">{stats['median_days']:.1f} days</span>
                    </div>
                    <div class="stats-row">
                        <span class="stats-label">90th Percentile:</span>
                        <span class="stats-value">{stats['p90_days']:.1f} days</span>
                    </div>
                    <div class="stats-row">
                        <span class="stats-label">Range:</span>
                        <span class="stats-value">{stats['min_days']:.1f} - {stats['max_days']:.1f} days</span>
                    </div>
                </div>'''
        
        html_content += '''
            </div>
        </div>
        
        <div class="footer">
            Generated by GitHub Issue Analyzer
        </div>
    </div>

    <script>
        // Prepare data for Chart.js
        const ctx = document.getElementById('histogramChart').getContext('2d');
        
        const binLabels = [];
        const binSize = 5;
        const maxBin = ''' + str(max_bin) + ''';
        
        for (let i = 0; i < maxBin; i += binSize) {
            binLabels.push(`${i}-${i + binSize}`);
        }
        
        const datasets = [];
        const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b'];
        
        '''
        
        # Add JavaScript data for each category
        for i, item in enumerate(all_data):
            # Create histogram data
            hist_data = [0] * len(bins[:-1])
            for value in item['data']:
                if value <= max_bin:  # Only include values up to max_bin
                    bin_index = min(int(value // bin_size), len(hist_data) - 1)
                    hist_data[bin_index] += 1
            
            html_content += f'''
        datasets.push({{
            label: '{item['name'].title()} Issues',
            data: {hist_data},
            backgroundColor: '{colors[i % len(colors)]}80',
            borderColor: '{colors[i % len(colors)]}',
            borderWidth: 2,
            borderRadius: 4
        }});
        '''
        
        html_content += '''
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: binLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Issue Resolution Time Distribution (Histogram)',
                        font: { size: 18 }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Resolution Time (Days)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Number of Issues'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    </script>
</body>
</html>'''
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n📊 HTML report generated: {filename}")
        except Exception as e:
            print(f"Error generating HTML report: {e}")


def main():
    parser = argparse.ArgumentParser(description='Analyze GitHub issue resolution times')
    parser.add_argument('repo', help='GitHub repository (e.g., owner/repo)')
    parser.add_argument('--token', help='GitHub personal access token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--state', default='closed', choices=['open', 'closed', 'all'], 
                       help='Issue state to analyze (default: closed)')
    parser.add_argument('--per-page', type=int, default=100, 
                       help='Issues per page (default: 100, max: 100)')
    parser.add_argument('--separate-members', action='store_true',
                       help='Show separate analysis for repository members vs external users')
    parser.add_argument('--exclude-members', action='store_true',
                       help='Exclude issues created by repository members')
    parser.add_argument('--html', metavar='FILENAME', 
                       help='Generate HTML report with histogram chart (e.g., --html report.html)')
    
    args = parser.parse_args()
    
    try:
        analyzer = GitHubIssueAnalyzer(token=args.token)
        print(f"Analyzing issues for repository: {args.repo}")
        print(f"Fetching {args.state} issues...\n")
        
        issues = analyzer.fetch_issues(args.repo, args.state, args.per_page)
        print(f"\nTotal issues fetched: {len(issues)}")
        
        if args.state != 'open':
            # Prepare data for HTML report
            html_data = {}
            
            # Get collaborators if we need to filter/separate by membership
            if args.separate_members or args.exclude_members:
                print("Fetching repository collaborators...")
                collaborators = analyzer.get_collaborators(args.repo)
                categorized = analyzer.categorize_issues(issues, collaborators)
                
                if args.exclude_members:
                    # Only analyze external issues
                    issues_to_analyze = categorized['external']
                    print(f"\nAnalyzing {len(issues_to_analyze)} external user issues (excluding {len(categorized['member'])} member issues)")
                    durations = analyzer.calculate_resolution_times(issues_to_analyze)
                    stats = analyzer.analyze_resolution_times(durations)
                    analyzer.print_results(stats, "EXTERNAL USER ISSUES - RESOLUTION TIME ANALYSIS")
                    
                    # Prepare HTML data
                    if args.html:
                        html_data['External Users'] = durations
                    
                elif args.separate_members:
                    # Analyze both separately
                    print(f"\nMember issues: {len(categorized['member'])}")
                    print(f"External issues: {len(categorized['external'])}")
                    
                    # Analyze member issues
                    if categorized['member']:
                        member_durations = analyzer.calculate_resolution_times(categorized['member'])
                        member_stats = analyzer.analyze_resolution_times(member_durations)
                        analyzer.print_results(member_stats, "REPOSITORY MEMBER ISSUES - RESOLUTION TIME ANALYSIS")
                        if args.html:
                            html_data['Repository Members'] = member_durations
                    
                    # Analyze external issues
                    if categorized['external']:
                        external_durations = analyzer.calculate_resolution_times(categorized['external'])
                        external_stats = analyzer.analyze_resolution_times(external_durations)
                        analyzer.print_results(external_stats, "EXTERNAL USER ISSUES - RESOLUTION TIME ANALYSIS")
                        if args.html:
                            html_data['External Users'] = external_durations
            else:
                # Standard analysis of all issues
                durations = analyzer.calculate_resolution_times(issues)
                stats = analyzer.analyze_resolution_times(durations)
                analyzer.print_results(stats)
                
                # Prepare HTML data
                if args.html:
                    html_data['All Issues'] = durations
            
            # Generate HTML report if requested
            if args.html and html_data:
                analyzer.generate_html_report(html_data, args.html, args.repo)
        else:
            print("Analysis of resolution times is only available for closed issues.")
            
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
        sys.exit(1)


if __name__ == '__main__':
    main()