"""Scrapers module."""
from .base import BaseScraper
from .verkkokauppa import VerkkokauppaScraper
from .gigantti import GiganttiScraper
from .power import PowerScraper

__all__ = [
    "BaseScraper",
    "VerkkokauppaScraper",
    "GiganttiScraper",
    "PowerScraper",
]
