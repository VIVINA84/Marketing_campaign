"""Segmentation Agent - Finds and segments the right audience from CSV dataset."""
import pandas as pd
from typing import Dict, List, Any
import os
import re
import json
import random
import config

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

class SegmentationAgent:
    """Agent that processes CSV data and segments audience based on strategy."""
    
    def __init__(self, csv_path: str):
        """
        Initialize segmentation agent with CSV dataset.
        
        Args:
            csv_path: Path to CSV file containing audience data
        """
        self.csv_path = csv_path
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load CSV data into pandas DataFrame."""
        if os.path.exists(self.csv_path):
            df = pd.read_csv(self.csv_path)
        else:
            # Create sample data if file doesn't exist
            df = self._create_sample_data()
        # normalize columns
        df.columns = [str(c).strip().lower() for c in df.columns]
        # ensure email exists and is string
        if 'email' in df.columns:
            df['email'] = df['email'].astype(str).str.strip()
            df = df[df['email'].str.contains('@', na=False)]
        # synthesize name if missing
        if 'name' not in df.columns:
            df['name'] = df['email'].apply(lambda x: x.split('@')[0].replace('.', ' ').title() if isinstance(x, str) and '@' in x else 'Customer')
        self.df = df.reset_index(drop=True)
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample audience data for testing."""
        import random
        data = {
            'email': [f'user{i}@example.com' for i in range(1, 101)],
            'name': [f'User {i}' for i in range(1, 101)],
            'age': [random.randint(18, 65) for _ in range(100)],
            'location': [random.choice(['USA', 'UK', 'Canada', 'Australia', 'Germany']) for _ in range(100)],
            'interests': [random.choice(['Technology', 'Sports', 'Travel', 'Food', 'Fashion']) for _ in range(100)],
            'purchase_history': [random.choice(['High', 'Medium', 'Low', 'None']) for _ in range(100)],
            'engagement_score': [random.randint(1, 10) for _ in range(100)]
        }
        return pd.DataFrame(data)
    
    def segment_audience(self, strategy: Dict[str, Any], segment_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Segment audience using LLM-driven rules if enabled; fallback to rule-based.
        """
        if self.df is None or self.df.empty:
            return {"error": "No data available for segmentation"}

        if config.USE_LLM_SEGMENTATION and _OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            try:
                return self._segment_with_llm(strategy)
            except Exception as e:
                # Fallback to rule-based segmentation on any failure
                fallback = self._rule_based_segmentation(strategy, segment_criteria)
                fallback["llm_error"] = str(e)
                return fallback
        else:
            return self._rule_based_segmentation(strategy, segment_criteria)

    def _rule_based_segmentation(self, strategy: Dict[str, Any], segment_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        segments: Dict[str, Any] = {}
        if segment_criteria is None:
            segment_criteria = {
                "by_location": True,
                "by_engagement": True,
                "by_purchase_history": True
            }
        # helper to map to records safely
        def records(df):
            cols = [c for c in ["email", "name"] if c in df.columns]
            return df[cols].to_dict("records") if cols else []
        if "location" in self.df.columns and segment_criteria.get("by_location"):
            segments["by_location"] = self.df.groupby("location", include_groups=False).apply(records).to_dict()
        if "engagement_score" in self.df.columns and segment_criteria.get("by_engagement"):
            high = self.df[self.df["engagement_score"] >= 7]
            med = self.df[(self.df["engagement_score"] >= 4) & (self.df["engagement_score"] < 7)]
            low = self.df[self.df["engagement_score"] < 4]
            segments["by_engagement"] = {
                "high": records(high),
                "medium": records(med),
                "low": records(low)
            }
        if "purchase_history" in self.df.columns and segment_criteria.get("by_purchase_history"):
            segments["by_purchase_history"] = self.df.groupby("purchase_history", include_groups=False).apply(records).to_dict()
        total_contacts = len(self.df)
        segment_counts = {k: sum(len(vv) for vv in v.values()) if isinstance(v, dict) else 0 for k, v in segments.items()}
        return {
            "segments": segments,
            "total_contacts": total_contacts,
            "segment_counts": segment_counts,
            "selected_segment": self._select_primary_segment(segments, strategy)
        }

    def _segment_with_llm(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        sample_n = max(1, min(config.SEGMENTATION_SAMPLE_SIZE, len(self.df)))
        sample_df = self.df.sample(n=sample_n, random_state=42) if len(self.df) > sample_n else self.df.copy()
        # Prepare schema and sample
        schema = list(self.df.columns)
        sample_rows = sample_df.head(50).to_dict(orient='records')
        brief = strategy.get("brief") if isinstance(strategy, dict) else None
        # Build prompt
        system = (
            "You are a marketing data analyst. Create segmentation rules for an email campaign. "
            "Output strict JSON with keys: segments, primary_segment_label. "
            "Each segments item: {label, criteria, priority}. criteria must be a simple Python/pandas expression over available columns. "
            "Use at most %d segments. Do not invent columns." % config.MAX_SEGMENTS
        )
        user = {
            "campaign_brief": brief or strategy if isinstance(strategy, (str, dict)) else "",
            "available_columns": schema,
            "sample_users": sample_rows,
            "instructions": (
                "Propose 2-5 segments with clear, programmatically applicable criteria. "
                "Examples: engagement_score >= 7; purchase_history in ['High']; interests.str.contains('Tech', case=False). "
                "Select one primary_segment_label best suited for this campaign." )
        }
        completion = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)}
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content
        try:
            llm_json = json.loads(content)
        except Exception:
            # try to extract JSON using simple heuristic
            m = re.search(r"\{[\s\S]*\}", content)
            if not m:
                raise ValueError("LLM did not return JSON")
            llm_json = json.loads(m.group(0))
        segments_def = llm_json.get("segments", [])
        primary_label = llm_json.get("primary_segment_label")
        # Apply criteria to full dataframe
        seg_map: Dict[str, List[Dict[str, Any]]] = {}
        for seg in segments_def[: config.MAX_SEGMENTS]:
            label = str(seg.get("label", "Segment")).strip() or "Segment"
            criteria = str(seg.get("criteria", "")).strip()
            try:
                # very limited criteria handling
                df_masked = self._apply_criteria(criteria)
                seg_map[label] = df_masked[[c for c in ["email", "name"] if c in df_masked.columns]].to_dict("records")
            except Exception:
                # if criteria fails, leave empty
                seg_map[label] = []
        # Compute totals
        total_contacts = len(self.df)
        segment_counts = {k: len(v) for k, v in seg_map.items()}
        # Select primary segment
        selected_segment = []
        if primary_label and primary_label in seg_map and len(seg_map[primary_label]) > 0:
            selected_segment = seg_map[primary_label]
        else:
            # choose the largest non-empty
            non_empty = sorted(((k, len(v)) for k, v in seg_map.items() if v), key=lambda x: -x[1])
            if non_empty:
                selected_segment = seg_map[non_empty[0][0]]
        # final fallback
        if not selected_segment:
            selected_segment = self._select_primary_segment({"by_engagement": {}}, strategy)
        return {
            "segments": {"by_llm": seg_map},
            "total_contacts": total_contacts,
            "segment_counts": segment_counts,
            "selected_segment": selected_segment
        }

    def _apply_criteria(self, criteria: str) -> pd.DataFrame:
        """Apply a limited safe subset of criteria to the dataframe."""
        if not criteria:
            return self.df.iloc[0:0]
        df = self.df
        # support simple contains checks like interests.str.contains('Tech', case=False)
        contains_match = re.findall(r"(\w+)\.str\.contains\('(.*?)'(?:,\s*case=(True|False))?\)", criteria)
        mask = pd.Series([True] * len(df))
        for col, term, case in contains_match:
            if col in df.columns:
                mask &= df[col].astype(str).str.contains(term, case=(case != 'False'), na=False)
        # remove the contains parts to evaluate the rest as query if present
        simplified = criteria
        for col, term, case in contains_match:
            simplified = simplified.replace(f"{col}.str.contains('{term}'", "True", 1)
            if case:
                simplified = simplified.replace(f", case={case})", ")", 1)
            else:
                simplified = simplified.replace(")", ")", 1)
        simplified = re.sub(r"\band\b|\bor\b|\(|\)", lambda m: m.group(0), simplified)
        try:
            # support simple comparisons on numeric/categorical fields via query
            if simplified and simplified != criteria:

                # attempt pandas query
                qmask = df.query(simplified, engine='python')
                # combine by index
                mask &= df.index.isin(qmask.index)
            elif simplified and simplified.strip() not in ("True", "False"):
                qmask = df.query(simplified, engine='python')
                mask &= df.index.isin(qmask.index)
        except Exception:
            # ignore query errors
            pass
        return df[mask]
    
    def _select_primary_segment(self, segments: Dict, strategy: Dict[str, Any]) -> List[Dict[str, str]]:
        """Select primary segment based on strategy with robust fallbacks."""
        # Prefer high engagement if available
        if isinstance(segments, dict) and "by_engagement" in segments and isinstance(segments["by_engagement"], dict):
            high = segments["by_engagement"].get("high")
            if isinstance(high, list) and high:
                return high[:50]
        # Fallback to first non-empty segment list
        for segment_group in segments.values():
            if isinstance(segment_group, dict):
                for segment in segment_group.values():
                    if isinstance(segment, list) and segment:
                        return segment[:50]
        # Ultimate fallback: return first 50 contacts using available columns
        cols = [c for c in ["email", "name"] if c in self.df.columns]
        if not cols:
            return []
        return self.df[cols].head(50).to_dict("records")

