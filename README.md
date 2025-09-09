# GitHub Issue Analyzer

A Python tool for analyzing GitHub issue resolution times and first response times with support for filtering by repository membership.

## Features

- **Dual Analysis Modes:**
  - Time-to-resolution for GitHub issues
  - Time-to-first-response from repository members (excluding bots)
- Calculates comprehensive statistics (mean, median, percentiles, std deviation)
- Filters out pull requests automatically
- Supports filtering by repository membership
- Interactive HTML reports with histogram charts
- Handles GitHub API pagination and rate limiting
- Works with organization repositories requiring SSO

## Requirements

- Python 3.7+
- `requests` library
- GitHub Personal Access Token

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```bash
   pip install requests
   ```

## Setup

### GitHub Token

You'll need a GitHub Personal Access Token with appropriate permissions:

1. Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `public_repo` - for public repositories (includes collaborator read access)
   - `repo` - for private repositories (includes public_repo and collaborator access)
   
   **Note:** For member filtering features (`--separate-members`, `--exclude-members`), the token needs read access to repository collaborators, which is included in both `public_repo` and `repo` scopes.

4. If analyzing organization repositories with SSO:
   - After creating the token, click "Configure SSO"
   - Authorize for the target organization

Set your token as an environment variable:
```bash
export GITHUB_TOKEN="your_token_here"
```

## Usage

### Basic Usage

Analyze all closed issues:
```bash
python github_issue_analyzer.py owner/repository
```

### Command Line Options

```bash
python github_issue_analyzer.py [repository] [options]

Required:
  repository              GitHub repository in format owner/repo (e.g., microsoft/vscode)

Optional:
  --token TOKEN          GitHub personal access token (alternative to GITHUB_TOKEN env var)
  --state {open,closed,all}  Issue state to analyze (default: closed)
  --per-page N           Issues per page, max 100 (default: 100)
  --separate-members     Show separate analysis for members vs external users
  --exclude-members      Exclude issues created by repository members
  --html FILENAME        Generate HTML report with histogram chart
  --first-response       Analyze time-to-first-response instead of resolution time
  --include-unresolved   Include issues closed without resolution (not_planned state)
```

### Examples

**Basic analysis:**
```bash
python github_issue_analyzer.py microsoft/vscode
```

**Analyze only external user issues:**
```bash
python github_issue_analyzer.py microsoft/vscode --exclude-members
```

**Show separate statistics for members vs external users:**
```bash
python github_issue_analyzer.py microsoft/vscode --separate-members
```

**Use custom token:**
```bash
python github_issue_analyzer.py microsoft/vscode --token "ghp_your_token_here"
```

**Generate HTML report with histogram chart:**
```bash
python github_issue_analyzer.py microsoft/vscode --html report.html
```

**Generate HTML report with separate member analysis:**
```bash
python github_issue_analyzer.py microsoft/vscode --separate-members --html report.html
```

**Analyze time-to-first-response:**
```bash
python github_issue_analyzer.py microsoft/vscode --first-response
```

**Generate HTML report for first response times:**
```bash
python github_issue_analyzer.py microsoft/vscode --first-response --html response-times.html
```

**Include all closed issues (resolved + unresolved):**
```bash
python github_issue_analyzer.py microsoft/vscode --include-unresolved
```

## Output

The tool provides comprehensive statistics including:

- **Count**: Total number of issues analyzed
- **Mean/Median**: Average and median resolution times in days
- **Range**: Minimum and maximum resolution times
- **Standard Deviation**: Measure of variability
- **Percentiles**: 25th, 75th, 90th, and 95th percentiles

### Sample Output

```
============================================================
GITHUB ISSUE RESOLUTION TIME ANALYSIS
============================================================
Total Issues Analyzed: 1,245

RESOLUTION TIME STATISTICS (in days):
  Mean:     12.34
  Median:   5.67
  Min:      0.01
  Max:      456.78
  Std Dev:  23.45

PERCENTILES (in days):
  25th:     2.34
  75th:     15.67
  90th:     45.89
  95th:     78.90
============================================================
```

### HTML Reports

When using the `--html` option, the tool generates a beautiful, interactive HTML report featuring:

- **Interactive histogram chart** showing resolution time distribution
- **Professional styling** with gradient headers and responsive design
- **Comprehensive statistics** in organized cards
- **Multiple categories** when using `--separate-members`
- **Chart.js integration** for smooth, interactive charts
- **Mobile-friendly** responsive design

The HTML report includes:
- Histogram with 5-day bins showing issue distribution
- Color-coded categories for different user types
- Detailed statistics tables for each category
- Professional styling suitable for presentations or reports

## Time-to-First-Response Analysis

The `--first-response` option analyzes how quickly repository members respond to new issues:

**What counts as "first response":**
- First comment from a repository member (collaborator)
- Excludes bot responses (dependabot, renovate, etc.)
- Measures time from issue creation to first human member response

**Use cases:**
- Measuring customer support response times
- SLA monitoring for issue acknowledgment
- Comparing response times for different user types

**Example output:**
```bash
python github_issue_analyzer.py microsoft/vscode --first-response --separate-members
```

This shows how quickly the team responds to community issues vs internal team issues.

## Resolved vs Closed Issues

By default, the tool analyzes only **resolved** issues using GitHub's `state_reason` field:

**Resolved issues (`state_reason: completed`):**
- Issues that were actually fixed/implemented
- Provides accurate resolution time metrics
- Default behavior for meaningful analysis

**Closed without resolution (`state_reason: not_planned`):**
- Issues closed as duplicate, wontfix, invalid, etc.
- Excluded by default since they weren't actually resolved
- Include with `--include-unresolved` flag

**Legacy issues:**
- Older issues without `state_reason` are treated as resolved
- Maintains backward compatibility with historical data

This distinction provides more accurate metrics by separating actual problem resolution from administrative closures.

## Member Filtering

The tool can distinguish between repository members (collaborators) and external users:

- **Members**: Users with push access to the repository
- **External**: All other users (community, customers, etc.)

This is useful for:
- Measuring customer support performance
- Comparing internal vs external issue resolution
- Excluding internal issues from SLA calculations

## Rate Limiting

The tool automatically handles GitHub API rate limits:
- Monitors remaining requests
- Pauses when approaching limits
- Resumes after rate limit reset

## Troubleshooting

**403 Forbidden Error:**
- Check if your token is valid: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`
- For organization repositories, ensure SSO is authorized
- Verify token has `public_repo` or `repo` scope
- If using member filtering options, ensure token has collaborator read permissions

**Empty Results:**
- Check if the repository exists and is accessible
- Verify the repository has closed issues
- Try with `--state all` to see if there are any issues

**Slow Performance:**
- Large repositories may take time to fetch all issues
- The tool shows progress for each page fetched
- Collaborator lookup is cached for performance

## License

This tool is provided as-is for analysis purposes.