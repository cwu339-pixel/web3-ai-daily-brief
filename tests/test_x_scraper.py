from __future__ import annotations

from src.scrapers.x_scraper import XScraper


def test_x_scraper_handles_from_env(monkeypatch):
    monkeypatch.setenv("X_HANDLES", "@openai, anthro_picai, ,xai")
    scraper = XScraper()
    assert scraper.handles == ["openai", "anthro_picai", "xai"]


def test_x_scraper_without_handles_returns_empty(monkeypatch):
    monkeypatch.delenv("X_HANDLES", raising=False)
    scraper = XScraper(handles=[])
    assert scraper.fetch(max_items=5) == []
