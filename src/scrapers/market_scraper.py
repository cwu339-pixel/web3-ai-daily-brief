"""Market data scraper using CoinGecko API (no auth required)"""
import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class MarketScraper:
    """Fetch real-time crypto market data from CoinGecko."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def get_market_snapshot(self) -> Dict[str, any]:
        """Get BTC, SOL, ETH prices and 24h changes.

        Returns:
            Dict with coin prices and changes, or empty dict on failure.
        """
        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": "bitcoin,solana,ethereum",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return self._format_snapshot(response.json())

        except requests.RequestException as e:
            logger.warning("Failed to fetch market data: %s", e)
            return {}

    def get_fear_greed_index(self) -> Optional[int]:
        """Get crypto Fear & Greed Index (0-100).

        Returns:
            Index value (0=Extreme Fear, 100=Extreme Greed), or None.
        """
        try:
            # Alternative.me API (free, no auth)
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return int(data["data"][0]["value"])

        except (requests.RequestException, KeyError, ValueError) as e:
            logger.warning("Failed to fetch Fear & Greed Index: %s", e)
            return None

    @staticmethod
    def _format_snapshot(data: Dict) -> Dict[str, Dict]:
        """Format CoinGecko response into readable structure."""
        result = {}
        coin_labels = {
            "bitcoin": "BTC",
            "solana": "SOL",
            "ethereum": "ETH",
        }

        for coin_id, label in coin_labels.items():
            if coin_id in data:
                coin_data = data[coin_id]
                result[label] = {
                    "price": coin_data.get("usd", 0),
                    "change_24h": coin_data.get("usd_24h_change", 0),
                    "market_cap": coin_data.get("usd_market_cap", 0),
                }

        return result
