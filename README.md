# GitHub Cybersecurity Discovery Bot

Automatically discovers recently created cybersecurity repositories on GitHub and shares curated links in a Discord channel using GitHub Actions and a Discord webhook.

> **Security notice:** A repository appearing in Discord is **not** an endorsement or security review. Inspect code, dependencies, licensing, and maintainers before running any third-party tool.

## What it does

Twice daily, the bot queries the GitHub repository search API for projects tagged with six cybersecurity topics:

| Category | GitHub topic |
| --- | --- |
| OSINT | `osint` |
| Digital Forensics | `digital-forensics` |
| Threat Intelligence | `threat-intelligence` |
| Malware Analysis | `malware-analysis` |
| Pentesting | `pentesting` |
| Security Tools | `security-tools` |

It filters and ranks the results, posts up to **five** projects per run, and records their GitHub repository IDs to prevent normal scheduled runs from reposting the same projects. With two scheduled runs, the theoretical maximum is **10 posts per day**, but fewer may qualify.

## Current selection rules

These values are defined near the top of [`cyber_discovery.py`](cyber_discovery.py):

| Setting | Current value |
| --- | --- |
| `MIN_STARS` | 5 |
| `LOOKBACK_DAYS` | 30 days since repository creation |
| `MAX_POSTS` | 5 per run |
| Search categories | 6 |
| GitHub search page size | 50 results per category |

Additional quality checks reject forks, archived or disabled repositories, projects with no meaningful description (under 25 characters), malformed GitHub links, and repository names containing certain list/cheatsheet/roadmap terms. Results are prioritized by the number of matched categories, stars, and creation date. This is **automated quality filtering, not a malware scan or manual vetting**.

Each Discord post includes the repository name/link, description, matching categories, star count, main language, and creation date.

## How the automation works

```text
GitHub Actions scheduled run
       |
       v
cyber_discovery.py -> GitHub Search API
       |
       v
Filter + rank repositories
       |
       v
Compare IDs with posted_repos.json
       |
       v
Discord webhook -> #github-projects
       |
       v
Save updated posted_repos.json in GitHub
```

No computer needs to remain powered on: GitHub runs the scheduled job in its hosted environment.

## Set up your own Discord channel

1. Create a Discord text channel, such as `#github-projects`.
2. Open **Server Settings → Integrations → Webhooks → New Webhook**.
3. Name the webhook (for example, **GitHub Cyber Discovery**) and select the destination channel.
4. Copy the webhook URL. **Anyone possessing this URL can send messages through it; keep it private.**
5. In this repository, go to **Settings → Secrets and variables → Actions → New repository secret**.
6. Add a secret named **`DISCORD_WEBHOOK_URL`** containing the URL.
7. Under **Settings → Actions → General**, make sure Actions is enabled and the workflow has the **Read and write permissions** needed to commit tracking history, subject to repository policy.

A Discord bot token, Discord Developer Portal application, and IFTTT are **not required**.

## Scheduling and manual testing

The workflow is [`.github/workflows/discover.yml`](.github/workflows/discover.yml). Its current schedule is:

```yaml
- cron: '17 1,13 * * *'
```

GitHub interprets these times as **UTC**: **01:17 and 13:17 UTC** each day (approximately 8:17 PM / 8:17 AM Eastern Standard Time, or 9:17 PM / 9:17 AM Eastern Daylight Time). GitHub-hosted scheduled jobs can be delayed.

To test:

1. Open the repository's **Actions** tab.
2. Select **Discover Cybersecurity GitHub Projects**.
3. Click **Run workflow**.
4. Enable **test_mode** to send one qualifying example without changing history.
5. Open the run logs and check the destination Discord channel.

**Test mode may repost a previously seen project**, because it intentionally bypasses the saved-history update.

## Repository files

| Path | Purpose |
| --- | --- |
| `cyber_discovery.py` | Searches, filters, ranks, and posts projects |
| `.github/workflows/discover.yml` | Defines schedule, environment, and commit steps |
| `posted_repos.json` | Generated history of posted GitHub repository IDs |
| `README.md` | This guide |

The tracking file may not exist until a successful normal run creates it. Do not delete or reset it unless you deliberately want to allow old projects to be reposted.

## Configuration

Change the constants in `cyber_discovery.py` to adjust the minimum stars, search lookback, categories, or posts per run. Change the workflow's `cron` expression to adjust the schedule. Changes to code or workflow YAML should be committed and tested.

The workflow supplies GitHub's automatically generated `GITHUB_TOKEN` for authenticated GitHub API requests; no personal access token is required by the supplied configuration. The Discord URL belongs only in the Actions secret, **never in a committed file**.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Nothing posts | Actions run history; search logs; whether any new repos pass the filters |
| Webhook error | Secret name, webhook validity, channel selection |
| GitHub API failures | Rate limits, GitHub availability, and per-category errors in logs |
| Repeated posts | Whether `posted_repos.json` was committed; whether test mode was used |
| History fails to commit | Workflow permissions, branch protection, or concurrent changes |
| Schedule runs late | GitHub Actions scheduled jobs are best-effort, not exact-time delivery |

If one category's search fails, the script logs the error and continues with other categories. If all searches yield no results, the job exits with an error instead of silently resetting history.

## GitHub and Discord terminology

- **Repository:** A version-controlled collection of files for a project.
- **Commit:** A saved change with a message and history.
- **GitHub Actions:** GitHub's automation runner.
- **Workflow:** A YAML file defining when and how Actions runs.
- **GitHub API:** The interface used to search GitHub projects.
- **Discord webhook:** A secret URL that lets the script send messages to a Discord channel.
- **Secret:** A protected configuration value stored in repository Actions settings.
- **JSON state:** A text file containing data used to remember previous posts.

## Responsible use

Review third-party code before downloading or executing it. Stars and descriptions are useful discovery signals but do not establish safety, authorization, maintenance quality, or legitimacy. Respect the licenses and acceptable-use policies of discovered projects.

Maintained by [CaptnCrypto](https://github.com/CaptnCrypto).
