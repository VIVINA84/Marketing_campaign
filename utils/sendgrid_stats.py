"""SendGrid Stats API client for global/provider-side metrics."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
import requests

class SendGridStats:
    BASE_URL = "https://api.sendgrid.com/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def _date(self, d: Any) -> str:
        if isinstance(d, dt.date):
            return d.strftime("%Y-%m-%d")
        if isinstance(d, str):
            return d
        raise ValueError("start_date/end_date must be date or YYYY-MM-DD string")

    def get_global_stats(
        self,
        start_date: Any,
        end_date: Any,
        aggregated_by: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        GET /v3/stats
        Docs: https://docs.sendgrid.com/api-reference/stats
        """
        params = {
            "start_date": self._date(start_date),
            "end_date": self._date(end_date),
            "aggregated_by": aggregated_by,
        }
        url = f"{self.BASE_URL}/stats"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json() or []

    @staticmethod
    def to_dataframe(data: List[Dict[str, Any]]):
        try:
            import pandas as pd
        except Exception as e:
            raise RuntimeError("pandas is required to format SendGrid stats") from e

        # Expected shape: [{"date": "YYYY-MM-DD", "stats": [{"metrics": {...}}]}]
        rows: List[Dict[str, Any]] = []
        for item in data:
            date = item.get("date")
            stats_list = item.get("stats", []) or []
            # Each 'stats' element can include 'metrics' and possible grouping data
            for s in stats_list:
                metrics = s.get("metrics", {}) or {}
                row = {"date": date}
                row.update(metrics)
                rows.append(row)
        if not rows:
            return pd.DataFrame(columns=["date"])
        df = pd.DataFrame(rows)
        # Deduplicate by date if multiple groups present (sum numeric columns)
        if "date" in df.columns and len(df) > 0:
            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if num_cols:
                df = df.groupby("date", as_index=False)[num_cols].sum()
        return df
