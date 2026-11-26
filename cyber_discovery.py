#!/usr/bin/env python3
"""Discover recent cybersecurity GitHub repositories and post to Discord."""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STATE_FILE = Path('posted_repos.json')
API = 'https://api.github.com/search/repositories'
MAX_POSTS = 5
MIN_STARS = 5
LOOKBACK_DAYS = 30
CATEGORIES = {
    'OSINT': 'osint',
    'Digital Forensics': 'digital-forensics',
    'Threat Intelligence': 'threat-intelligence',
    'Malware Analysis': 'malware-analysis',
    'Pentesting': 'pentesting',
    'Security Tools': 'security-tools',
}
BLOCKED = ('awesome-', 'awesome_', 'cheatsheet', 'cheat-sheet', 'interview-questions', 'roadmap')


def request_json(url, token=None):
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'CyberDiscoveryDiscordBot/1.0',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(url, headers=headers)
    with urlopen(req, timeout=35) as response:
        return json.load(response)


def search_repos(token):
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    found = {}
    for category, topic in CATEGORIES.items():
        query = f'topic:{topic} created:>={since} stars:>={MIN_STARS} fork:false archived:false'
        url = API + '?' + urlencode({'q': query, 'sort': 'updated', 'order': 'desc', 'per_page': 50})
        try:
            results = request_json(url, token).get('items', [])
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print(f'Search failed for {category}: {exc}')
            continue
        print(f'{category}: {len(results)} candidates')
        for repo in results:
            repo_id = str(repo.get('id', ''))
            if repo_id:
                if repo_id not in found:
                    found[repo_id] = (repo, set())
                found[repo_id][1].add(category)
        time.sleep(0.3)
    return found


def quality_ok(repo):
    name = (repo.get('name') or '').lower()
    description = (repo.get('description') or '').strip()
    if (not description or len(description) < 25 or
            repo.get('stargazers_count', 0) < MIN_STARS or
            repo.get('fork') or repo.get('archived') or repo.get('disabled') or
            any(term in name for term in BLOCKED)):
        return False
    url = repo.get('html_url') or ''
    if not re.fullmatch(r'https://github\.com/[^/\s]+/[^/\s]+', url):
        return False
    return True


def load_seen():
    if not STATE_FILE.exists():
        return set()
    data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    return set(map(str, data.get('posted_ids', [])))


def save_seen(seen):
    # Keep the full set so old projects are not reposted later.
    STATE_FILE.write_text(json.dumps({'posted_ids': sorted(seen)}, indent=2) + '\n', encoding='utf-8')


def post_to_discord(webhook, repo, categories):
    description = (repo.get('description') or '').strip()[:450]
    stars = repo.get('stargazers_count', 0)
    language = repo.get('language') or 'Not specified'
    created = (repo.get('created_at') or '')[:10]
    payload = {
        'username': 'GitHub Cyber Discovery',
        'embeds': [{
            'title': (repo.get('full_name') or 'GitHub project')[:256],
            'url': repo['html_url'],
            'description': description,
            'color': 3447003,
            'fields': [
                {'name': 'Categories', 'value': ', '.join(sorted(categories))[:1024], 'inline': False},
                {'name': 'Stars', 'value': str(stars), 'inline': True},
                {'name': 'Language', 'value': str(language)[:100], 'inline': True},
                {'name': 'Created', 'value': created or 'Unknown', 'inline': True},
            ],
            'footer': {'text': 'Newly created GitHub repository • Not security-vetted'}
        }],
        'allowed_mentions': {'parse': []}
    }
    req = Request(webhook, data=json.dumps(payload).encode('utf-8'),
                  headers={'Content-Type': 'application/json', 'User-Agent': 'CyberDiscoveryDiscordBot/1.0'},
                  method='POST')
    with urlopen(req, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f'Discord returned HTTP {response.status}')


def main():
    webhook = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if not webhook.startswith('https://discord.com/api/webhooks/'):
        raise SystemExit('Missing or invalid DISCORD_WEBHOOK_URL secret')
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    seen = load_seen()
    found = search_repos(token)
    candidates = [(repo, cats) for repo, cats in found.values() if quality_ok(repo)]
    candidates.sort(key=lambda x: (len(x[1]), x[0].get('stargazers_count', 0), x[0].get('created_at', '')), reverse=True)
    unposted = [(repo, cats) for repo, cats in candidates if str(repo['id']) not in seen]
    print(f'{len(candidates)} qualified; {len(unposted)} not yet posted')
    if not found:
        raise SystemExit('No search results obtained; check GitHub API logs')
    if test_mode:
        print('TEST MODE: posts one project but does not update tracking.')
        if candidates:
            post_to_discord(webhook, *candidates[0])
        else:
            print('No qualified project available for test.')
        return
    for repo, cats in unposted[:MAX_POSTS]:
        post_to_discord(webhook, repo, cats)
        seen.add(str(repo['id']))
        save_seen(seen)
        print('Posted:', repo['full_name'])
        time.sleep(1)
    if not unposted:
        print('No new qualifying projects.')


if __name__ == '__main__':
    main()
