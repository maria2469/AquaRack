"""
CLI status tool — reproduces the full workflow without a browser (FR-1.9).

Usage:
    python -m cli.cli status
    python -m cli.cli recommend
    python -m cli.cli search "high thermal load"
    python -m cli.cli report --format csv
"""
import json

import click
import requests

from app.config import settings

BASE = f"http://{settings.API_HOST}:{settings.API_PORT}"


def _headers():
    h = {}
    if settings.API_TOKEN:
        h["Authorization"] = f"Bearer {settings.API_TOKEN}"
    return h


@click.group()
def cli():
    """AquaMind AI — Phase 1 headless CLI."""
    pass


@cli.command()
def status():
    """Show latest telemetry, water model, and recommendation."""
    resp = requests.get(f"{BASE}/api/v1/dashboard/summary", headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    click.echo(json.dumps(data, indent=2, default=str))


@cli.command()
def recommend():
    """Trigger the AI Decision Agent for a new recommendation."""
    resp = requests.post(f"{BASE}/api/v1/recommend", json={}, headers=_headers(), timeout=15)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2, default=str))


@cli.command()
@click.argument("query")
@click.option("--k", default=5)
def search(query, k):
    """Search memory (RAG) for similar past events."""
    resp = requests.get(
        f"{BASE}/api/v1/memory/search", params={"q": query, "k": k}, headers=_headers(), timeout=10
    )
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2, default=str))


@cli.command()
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv", "pdf"]))
@click.option("--out", default=None)
def report(fmt, out):
    """Download the daily summary report."""
    resp = requests.get(
        f"{BASE}/api/v1/reports/daily", params={"format": fmt}, headers=_headers(), timeout=30
    )
    resp.raise_for_status()
    out = out or f"aquamind_daily_report.{fmt}"
    with open(out, "wb") as f:
        f.write(resp.content)
    click.echo(f"Saved report to {out}")


if __name__ == "__main__":
    cli()
