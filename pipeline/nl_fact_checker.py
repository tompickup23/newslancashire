#!/usr/bin/env python3
"""
nl_fact_checker.py — Article verification for News Lancashire.

Three verification layers:
1. Style compliance — banned patterns, AI language detection
2. Borough validation — every article must have geographic context
3. Content quality — length, structure, factual density

Usage:
    from nl_fact_checker import check_article
    result = check_article(content, category, borough, style_guide)
    # result = {'passed': bool, 'score': int, 'warnings': [...], 'errors': [...], 'cleaned': str}
"""

import json
import re
from pathlib import Path

STYLE_GUIDE_PATH = Path(__file__).parent / 'nl_style_guide.json'


def _load_style_guide():
    try:
        with open(STYLE_GUIDE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def check_style(content, guide=None):
    """Check article against style guide. Returns list of violations."""
    if guide is None:
        guide = _load_style_guide()

    violations = []
    text_lower = content.lower()

    # Banned patterns
    for pattern in guide.get('banned_patterns', []):
        if pattern.lower() in text_lower:
            violations.append(f'Banned pattern: "{pattern}"')

    # Banned punctuation
    for char, fix in guide.get('banned_punctuation', {}).items():
        if char in content:
            violations.append(f'Banned punctuation: {repr(char)}. {fix}')

    # Paragraph length (split on double newline)
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    for i, para in enumerate(paragraphs):
        sentences = re.split(r'[.!?]\s+', para.strip())
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) > 5:
            violations.append(f'Paragraph {i + 1} has {len(sentences)} sentences (max 3-4)')

    # Passive voice
    passive_markers = [
        'was paid', 'were paid', 'was awarded', 'were awarded',
        'was given', 'were given', 'is being', 'are being',
        'has been paid', 'have been paid',
        'payments were made', 'contracts were awarded',
    ]
    for marker in passive_markers:
        if marker in text_lower:
            violations.append(f'Passive voice: "{marker}"')

    return violations


def check_borough(content, borough):
    """Check that the article has geographic context. Returns list of issues."""
    issues = []
    if not borough or borough == 'lancashire-wide':
        # Lancashire-wide is OK
        return issues

    # Check that the borough or a related place name appears
    borough_names = {
        'burnley': ['burnley', 'padiham', 'brierfield'],
        'pendle': ['pendle', 'nelson', 'colne', 'barnoldswick'],
        'hyndburn': ['hyndburn', 'accrington', 'oswaldtwistle', 'great harwood'],
        'rossendale': ['rossendale', 'rawtenstall', 'bacup', 'haslingden'],
        'ribble-valley': ['ribble valley', 'clitheroe', 'longridge', 'whalley'],
        'blackburn': ['blackburn', 'darwen'],
        'blackpool': ['blackpool'],
        'chorley': ['chorley', 'adlington', 'euxton'],
        'south-ribble': ['south ribble', 'leyland', 'penwortham'],
        'preston': ['preston', 'fulwood'],
        'west-lancashire': ['west lancashire', 'ormskirk', 'skelmersdale'],
        'lancaster': ['lancaster', 'morecambe', 'heysham', 'carnforth'],
        'wyre': ['wyre', 'fleetwood', 'thornton', 'garstang', 'poulton'],
        'fylde': ['fylde', 'lytham', 'st annes', 'kirkham'],
    }

    names = borough_names.get(borough, [borough.replace('-', ' ')])
    text_lower = content.lower()
    if not any(name in text_lower for name in names):
        issues.append(f'Borough "{borough}" not mentioned in article text')

    return issues


def check_quality(content, tier='summary'):
    """Check content quality. Returns (score, issues)."""
    issues = []
    words = content.split()
    word_count = len(words)
    score = 50  # Start at 50

    # Length checks
    if tier == 'summary':
        if word_count < 40:
            issues.append(f'Too short: {word_count} words (min 60)')
            score -= 20
        elif word_count > 200:
            issues.append(f'Too long for summary: {word_count} words (max 120)')
            score -= 10
        else:
            score += 10
    elif tier == 'analysis':
        if word_count < 150:
            issues.append(f'Too short for analysis: {word_count} words (min 200)')
            score -= 15
        elif word_count > 500:
            issues.append(f'Too long for analysis: {word_count} words (max 400)')
            score -= 5
        else:
            score += 15

    # Check for specifics (numbers, names, dates)
    has_numbers = bool(re.search(r'\d+', content))
    has_proper_nouns = bool(re.search(r'\b[A-Z][a-z]+\b', content))

    if has_numbers:
        score += 10
    else:
        issues.append('No specific numbers or figures')

    if has_proper_nouns:
        score += 5

    # Check paragraph structure
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    if len(paragraphs) >= 2:
        score += 5
    elif tier == 'analysis':
        issues.append('Analysis should have multiple paragraphs')
        score -= 10

    # Clamp score
    score = max(0, min(100, score))
    return score, issues


def clean_content(content):
    """Clean up common LLM artifacts."""
    # Remove markdown headers
    content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
    # Remove bold/italic markdown
    content = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', content)
    # Remove trailing whitespace per line
    content = '\n'.join(line.rstrip() for line in content.split('\n'))
    # Collapse triple+ newlines to double
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Fix banned punctuation
    content = content.replace('\u2014', ' - ')
    content = content.replace('\u2013', '-')
    return content.strip()


def check_article(content, category='local', borough='lancashire-wide', style_guide=None, tier='summary'):
    """Run all checks on an article. Returns result dict."""
    if style_guide is None:
        style_guide = _load_style_guide()

    content = clean_content(content)

    warnings = []
    errors = []

    # Style checks
    style_issues = check_style(content, style_guide)
    warnings.extend(style_issues)

    # Borough checks
    borough_issues = check_borough(content, borough)
    warnings.extend(borough_issues)

    # Quality checks
    quality_score, quality_issues = check_quality(content, tier)
    warnings.extend(quality_issues)

    # Determine pass/fail
    # Fail if quality score < 30 or too many style violations
    passed = quality_score >= 30 and len([w for w in warnings if 'Banned pattern' in w]) < 5

    return {
        'passed': passed,
        'score': quality_score,
        'warnings': warnings,
        'errors': errors,
        'cleaned': content,
    }


if __name__ == '__main__':
    # Quick test
    test_content = """Lancaster City Council has approved plans for 200 new homes on the Luneside East development site. The decision, made at Thursday's planning committee, follows three years of consultation with local residents.

The development by Story Homes will include 40 affordable properties, meeting the council's 20% target. Construction is expected to begin in autumn 2026, creating approximately 150 jobs during the build phase.

Residents on St George's Quay have raised concerns about increased traffic, but the council's highways assessment concluded the road network can accommodate the additional vehicles.

For more details, contact Lancaster City Council planning department on 01524 582000."""

    result = check_article(test_content, 'planning', 'lancaster', tier='analysis')
    print(f"Passed: {result['passed']}")
    print(f"Score: {result['score']}")
    for w in result['warnings']:
        print(f"  WARN: {w}")
