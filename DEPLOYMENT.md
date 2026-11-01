# Pixel Galaxy deployment

The profile uses three GitHub Actions workflows:

- **Public Activity Signal** polls the public events endpoint every 15 minutes and publishes <code>activity-status.svg</code> to the <code>profile-live</code> branch.
- **Profile Metrics** renders the Metrics dashboard, isometric calendar, achievements, and coding-habits panels daily.
- **Contribution Snake** regenerates the contribution snake SVGs daily and publishes them to the existing <code>output</code> branch.

## One-time setup for Metrics

The Metrics action needs a personal GitHub token to read account-level public activity and profile data. It uses the repository's built-in <code>GITHUB_TOKEN</code> separately to commit generated SVGs.

1. Create a GitHub personal access token with read-only access to the public profile/repository data used by Metrics. Do not grant write access.
2. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name the secret <code>METRICS_TOKEN</code> and paste the token as its value.

## First run

Open **Actions** and run these workflows once with **Run workflow**:

1. **Profile Metrics** (after adding <code>METRICS_TOKEN</code>)
2. **Contribution Snake**
3. **Public Activity Signal**

After the first successful run, the generated images will appear in the profile README. The workflows then refresh on their schedules.

## Activity signal limitation

The activity panel reports only public GitHub events observed in the last 30 minutes. It is not an online-presence detector. GitHub documents that public event data can be delayed by approximately 30 seconds to 6 hours, so the 15-minute workflow schedule does not guarantee 15-minute-fresh source data.
