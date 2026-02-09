#!/usr/bin/env python3
"""Simple file-based rate limiter for free LLM APIs.

Tracks daily request counts and token usage per provider to stay within free tiers.
State file: /home/ubuntu/newslancashire/logs/llm_usage.json

Free tier limits:
  gemini:  500 req/day, 250,000 tokens/day
  groq:    1000 req/day, 100,000 tokens/day, 30 req/min
  kimi:    Trial credits (no hard daily limit, but credits deplete)
  deepseek: Credits exhausted
"""

import json
import os
import time
from datetime import datetime

USAGE_FILE = '/home/ubuntu/newslancashire/logs/llm_usage.json'

LIMITS = {
    'gemini': {'max_requests': 450, 'max_tokens': 230000},     # 90% of 500/250K — safety margin
    'groq':   {'max_requests': 900, 'max_tokens': 90000},      # 90% of 1000/100K
    'kimi':   {'max_requests': 9999, 'max_tokens': 99999999},   # Trial credits — no hard limit
    'deepseek': {'max_requests': 9999, 'max_tokens': 99999999}, # Pay-as-you-go
}

# Groq: 30 req/min limit
GROQ_MIN_INTERVAL = 2.1  # seconds between Groq calls (30/min ≈ 1 every 2s, +0.1s buffer)


def _load_usage():
    """Load usage state, reset if it's a new day."""
    try:
        with open(USAGE_FILE) as f:
            data = json.load(f)
        if data.get('date') != datetime.now().strftime('%Y-%m-%d'):
            return _new_day()
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return _new_day()


def _new_day():
    """Reset counters for a new day."""
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'providers': {},
        'groq_last_call': 0,
    }


def _save_usage(data):
    """Save usage state."""
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def can_use(provider):
    """Check if a provider has capacity remaining today."""
    data = _load_usage()
    limits = LIMITS.get(provider, {'max_requests': 9999, 'max_tokens': 99999999})
    usage = data.get('providers', {}).get(provider, {'requests': 0, 'tokens': 0})

    if usage.get('requests', 0) >= limits['max_requests']:
        return False
    if usage.get('tokens', 0) >= limits['max_tokens']:
        return False

    # Groq per-minute rate limit
    if provider == 'groq':
        last_call = data.get('groq_last_call', 0)
        if time.time() - last_call < GROQ_MIN_INTERVAL:
            time.sleep(GROQ_MIN_INTERVAL - (time.time() - last_call))

    return True


def record_usage(provider, tokens_used=0):
    """Record an API call and token usage."""
    data = _load_usage()
    if 'providers' not in data:
        data['providers'] = {}
    if provider not in data['providers']:
        data['providers'][provider] = {'requests': 0, 'tokens': 0}

    data['providers'][provider]['requests'] += 1
    data['providers'][provider]['tokens'] += tokens_used

    if provider == 'groq':
        data['groq_last_call'] = time.time()

    _save_usage(data)


def get_daily_summary():
    """Return a summary string of today's usage."""
    data = _load_usage()
    lines = [f"LLM usage for {data.get('date', 'unknown')}:"]
    for prov, usage in data.get('providers', {}).items():
        limits = LIMITS.get(prov, {})
        req = usage.get('requests', 0)
        tok = usage.get('tokens', 0)
        max_req = limits.get('max_requests', '?')
        max_tok = limits.get('max_tokens', '?')
        lines.append(f"  {prov}: {req}/{max_req} requests, {tok:,}/{max_tok:,} tokens")
    return '\n'.join(lines)
