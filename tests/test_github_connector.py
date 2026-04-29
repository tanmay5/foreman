"""Smoke tests for the GitHub connector.

These tests stub the httpx client. They're not exhaustive — the goal at
v0.1 is to make sure the parser doesn't break on a realistic API
response shape and that the URL parsing handles the expected format.
"""

from __future__ import annotations

from foreman.connectors.github import _item_to_pr


def test_item_to_pr_extracts_owner_repo_from_html_url() -> None:
    item = {
        "number": 42,
        "title": "Add circuit breaker to user service",
        "html_url": "https://github.com/acme/widgets/pull/42",
        "user": {"login": "octocat"},
        "created_at": "2026-04-25T17:30:00Z",
        "updated_at": "2026-04-27T09:14:00Z",
    }
    pr = _item_to_pr(item)
    assert pr.number == 42
    assert pr.title.startswith("Add circuit")
    assert pr.repo == "acme/widgets"
    assert pr.author == "octocat"
    assert pr.url.endswith("/pull/42")


def test_item_to_pr_handles_missing_author() -> None:
    item = {
        "number": 1,
        "title": "x",
        "html_url": "https://github.com/a/b/pull/1",
        "user": None,
        "created_at": "2026-04-25T17:30:00Z",
        "updated_at": "2026-04-25T17:30:00Z",
    }
    pr = _item_to_pr(item)
    assert pr.author == "?"
