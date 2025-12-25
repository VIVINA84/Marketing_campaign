"""Utility functions for loading campaigns and audience data from data folder."""
import os
import json
import pandas as pd
from typing import Dict, List, Any

def load_campaign_briefs(data_dir: str = "data") -> List[Dict[str, Any]]:
    """
    Load all available campaign briefs from the data folder.
    
    Supports:
    - JSON files (*.json) with 'name' and 'brief' keys
    - CSV files (*.csv) with 'name' and 'brief' columns
    - TXT files (*.txt) where filename is the campaign name
    
    Returns:
        List of dictionaries with 'name' and 'brief' keys
    """
    campaigns = []
    data_path = os.path.join(data_dir)
    
    if not os.path.exists(data_path):
        return campaigns
    
    # Load from JSON files
    for file in os.listdir(data_path):
        if file.endswith('.json') and 'brief' in file.lower():
            file_path = os.path.join(data_path, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if 'name' in data and 'brief' in data:
                            campaigns.append(data)
                    elif isinstance(data, list):
                        campaigns.extend(data)
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    # Load from CSV files
    for file in os.listdir(data_path):
        if file.endswith('.csv') and 'brief' in file.lower():
            file_path = os.path.join(data_path, file)
            try:
                df = pd.read_csv(file_path)
                # Handle different CSV formats
                if 'campaign_name' in df.columns and 'brief' in df.columns:
                    # Format: campaign_name, brief
                    for _, row in df.iterrows():
                        campaigns.append({
                            'name': str(row['campaign_name']),
                            'brief': str(row['brief']),
                            'campaign_id': str(row.get('campaign_id', '')),
                            'campaign_type': str(row.get('campaign_type', '')),
                            'cta': str(row.get('cta', ''))
                        })
                elif 'name' in df.columns and 'brief' in df.columns:
                    # Format: name, brief
                    for _, row in df.iterrows():
                        campaigns.append({
                            'name': str(row['name']),
                            'brief': str(row['brief'])
                        })
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    # Load from TXT files
    for file in os.listdir(data_path):
        if file.endswith('.txt') and 'brief' in file.lower():
            file_path = os.path.join(data_path, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    brief = f.read().strip()
                    # Use filename (without extension) as campaign name
                    name = os.path.splitext(file)[0].replace('_', ' ').title()
                    campaigns.append({
                        'name': name,
                        'brief': brief
                    })
            except Exception as e:
                print(f"Error loading {file}: {e}")
    
    return campaigns

def get_campaign_brief_by_name(name: str, data_dir: str = "data") -> str:
    """
    Get campaign brief text by campaign name.
    
    Args:
        name: Campaign name
        data_dir: Data directory path
        
    Returns:
        Campaign brief text or empty string if not found
    """
    campaigns = load_campaign_briefs(data_dir)
    for campaign in campaigns:
        if campaign.get('name') == name:
            return campaign.get('brief', '')
    return ''

def get_audience_csv_path(data_dir: str = "data") -> str:
    """
    Get the path to the audience CSV file.
    
    Args:
        data_dir: Data directory path
        
    Returns:
        Path to audience.csv file
    """
    return os.path.join(data_dir, "audience.csv")

def load_audience_data(data_dir: str = "data") -> pd.DataFrame:
    """
    Load audience data from CSV file in data folder.
    
    Args:
        data_dir: Data directory path
        
    Returns:
        DataFrame with audience data
    """
    csv_path = get_audience_csv_path(data_dir)
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        raise FileNotFoundError(f"Audience CSV not found at {csv_path}")

