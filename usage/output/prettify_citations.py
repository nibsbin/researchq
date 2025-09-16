#!/usr/bin/env python3
"""
Prettify Citations Script

This script processes CSV files containing enriched_citations columns and creates
prettified versions with human-readable citation formatting.

Features:
- Processes all CSV files in the output directory
- Converts Python dict-formatted citations to human-readable format
- Creates new files with "_prettified" suffix
- Handles various citation formats gracefully (Python dicts, JSON, etc.)
- Preserves original files
"""

import pandas as pd
import json
import ast
from pathlib import Path
from typing import List, Dict, Any, Union
import re

def safe_parse_citations(citations_str: str) -> List[Dict[str, Any]]:
    """
    Safely parse citations string that might be in various formats.
    
    Args:
        citations_str: String representation of citations (Python dict string, etc.)
        
    Returns:
        List of citation dictionaries
    """
    if pd.isna(citations_str) or not citations_str:
        return []
    
    # If it's already a list, return it
    if isinstance(citations_str, list):
        return citations_str
    
    citations_str = str(citations_str).strip()
    
    # Try different parsing methods
    try:
        # Method 1: Python literal evaluation (for Python dict strings)
        return ast.literal_eval(citations_str)
    except (ValueError, SyntaxError):
        pass
    
    try:
        # Method 2: Handle edge cases with eval (be careful with this!)
        # Only use eval if the string looks like a Python list/dict
        if citations_str.startswith('[') and citations_str.endswith(']'):
            return eval(citations_str)
    except (ValueError, SyntaxError, NameError):
        pass
    
    try:
        # Method 3: JSON parsing as fallback
        return json.loads(citations_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    try:
        # Method 4: Handle malformed strings by fixing common issues
        # Replace None, True, False for JSON compatibility
        json_str = citations_str.replace("'", '"')
        json_str = re.sub(r'\bNone\b', 'null', json_str)
        json_str = re.sub(r'\bTrue\b', 'true', json_str)
        json_str = re.sub(r'\bFalse\b', 'false', json_str)
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If all parsing fails, return empty list
    print(f"Warning: Could not parse citations: {citations_str[:100]}...")
    return []

def format_citation(citation: Dict[str, Any], index: int) -> str:
    """
    Format a single citation into a human-readable string.
    
    Args:
        citation: Dictionary containing citation information
        index: Citation number (1-based)
        
    Returns:
        Formatted citation string
    """
    if not isinstance(citation, dict):
        return f"[{index}] Invalid citation format"
    
    # Extract citation information
    url = citation.get('url', 'No URL')
    title = citation.get('title', 'No Title')
    snippet = citation.get('snippet', '')
    date = citation.get('date', '')
    last_updated = citation.get('last_updated', '')
    matched = citation.get('matched', False)
    
    # Build formatted citation
    citation_parts = []
    
    # Add title and URL
    if title and title != 'No Title':
        citation_parts.append(f"**{title}**")
    
    if url and url != 'No URL':
        citation_parts.append(f"URL: {url}")
    
    # Add dates if available
    date_parts = []
    if date:
        date_parts.append(f"Published: {date}")
    if last_updated:
        date_parts.append(f"Updated: {last_updated}")
    if date_parts:
        citation_parts.append(" | ".join(date_parts))
    
    # Add snippet if available
    if snippet:
        # Clean up snippet (remove extra quotes, limit length)
        clean_snippet = snippet.strip().strip('"\'')
        if len(clean_snippet) > 150:
            clean_snippet = clean_snippet[:147] + "..."
        citation_parts.append(f"Snippet: {clean_snippet}")
    
    # Add match status
    match_status = "✓ Matched" if matched else "⚠ Not matched"
    citation_parts.append(match_status)
    
    # Combine all parts
    formatted = f"[{index}] " + "\n    ".join(citation_parts)
    return formatted

def prettify_citations(citations_str: str) -> str:
    """
    Convert citations string to prettified format.
    
    Args:
        citations_str: String representation of citations
        
    Returns:
        Prettified citations string
    """
    citations = safe_parse_citations(citations_str)
    
    if not citations:
        return "No citations available"
    
    prettified = []
    for i, citation in enumerate(citations, 1):
        formatted_citation = format_citation(citation, i)
        prettified.append(formatted_citation)
    
    return "\n\n" + "\n\n".join(prettified)

def process_csv_file(file_path: Path) -> None:
    """
    Process a single CSV file and create a prettified version.
    
    Args:
        file_path: Path to the CSV file to process
    """
    print(f"Processing {file_path.name}...")
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if enriched_citations column exists
        if 'enriched_citations' not in df.columns:
            print(f"  ⚠ No 'enriched_citations' column found in {file_path.name}")
            return
        
        # Create a copy for processing
        df_pretty = df.copy()
        
        # Apply prettification to enriched_citations column
        print(f"  📝 Prettifying {len(df)} citations...")
        df_pretty['enriched_citations_pretty'] = df['enriched_citations'].apply(prettify_citations)
        
        # Reorder columns to put prettified citations after original
        cols = list(df_pretty.columns)
        if 'enriched_citations_pretty' in cols:
            cols.remove('enriched_citations_pretty')
            # Insert after enriched_citations
            insert_idx = cols.index('enriched_citations') + 1
            cols.insert(insert_idx, 'enriched_citations_pretty')
            df_pretty = df_pretty[cols]
        
        # Create output filename
        output_path = file_path.parent / f"{file_path.stem}_prettified{file_path.suffix}"
        
        # Save prettified version
        df_pretty.to_csv(output_path, index=False)
        print(f"  ✓ Saved prettified version to {output_path.name}")
        
        # Show sample
        if len(df_pretty) > 0:
            print(f"  📊 Sample from {df_pretty.iloc[0]['country'] if 'country' in df_pretty.columns else 'first row'}:")
            sample_citations = df_pretty.iloc[0]['enriched_citations_pretty']
            # Show first 200 characters of prettified citations
            preview = sample_citations[:200] + "..." if len(sample_citations) > 200 else sample_citations
            print(f"    {preview}")
        
    except Exception as e:
        print(f"  ✗ Error processing {file_path.name}: {str(e)}")

def main():
    """
    Main function to process all CSV files in the output directory.
    """
    print("🎨 CSV Citations Prettifier")
    print("=" * 50)
    
    # Get the output directory
    output_dir = Path(__file__).parent
    
    # Find all CSV files
    csv_files = list(output_dir.glob("*.csv"))
    
    # Filter out already prettified files
    csv_files = [f for f in csv_files if "_prettified" not in f.name]
    
    if not csv_files:
        print("No CSV files found to process.")
        return
    
    print(f"Found {len(csv_files)} CSV files to process:")
    for file_path in csv_files:
        print(f"  - {file_path.name}")
    
    print("\n" + "=" * 50)
    
    # Process each file
    for file_path in csv_files:
        process_csv_file(file_path)
        print()
    
    print("=" * 50)
    print("✅ Citation prettification completed!")

if __name__ == "__main__":
    main()
