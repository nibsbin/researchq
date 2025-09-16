"""
Cyber Relevance Assessment Script

The goal of this tool is to automatically assess whether various ministries of different countries 
are direct stakeholders (i.e., responsible for or involved in) the country's cybersecurity ecosystem.

This script provides functions to:
1. Define Pydantic models for structured cybersecurity assessments
2. Run cybersecurity relevance assessments using the AutoRA sprayer
3. Process and save results in various formats
"""

import sys
import os
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from autora import sprayer


class CyberRelevanceLevel(str, Enum):
    """Level of cybersecurity involvement"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ConfidenceLevel(str, Enum):
    """Confidence in the assessment"""
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"


class CyberStakeholderAssessment(BaseModel):
    """Assessment of whether a ministry/department is a cybersecurity stakeholder"""    
    relevance_level: CyberRelevanceLevel = Field(
        description="Level of cybersecurity involvement (high/medium/low/none)"
    )
    confidence: ConfidenceLevel = Field(
        description="Confidence level of this assessment"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation for the assessment with citation reference after each claim."
    )


def load_country_data(data_file: str = '../data/ministries_of_energy_done_with_all_countries.xlsx') -> List[str]:
    """
    Load country data from Excel file.
    
    Args:
        data_file: Path to the Excel file containing country data
        
    Returns:
        List of country names
    """
    try:
        data = pd.read_excel(data_file)
        return data["COUNTRY"].tolist()
    except FileNotFoundError:
        print(f"Warning: Data file {data_file} not found. Using sample countries.")
        return ["USA", "Germany", "France", "Japan", "Canada"]
    except KeyError:
        print("Warning: 'COUNTRY' column not found in data. Using sample countries.")
        return ["USA", "Germany", "France", "Japan", "Canada"]


def create_word_sets(domain: str, countries: List[str]) -> Dict[str, List[str]]:
    """
    Create word sets for the spray function.
    
    Args:
        domain: The ministry domain (e.g., "energy", "health", "transport")
        countries: List of country names
        
    Returns:
        Dictionary of word sets for the sprayer
    """
    return {
        "domain": [domain],
        "country": countries
    }


def get_cyber_relevance_prompt() -> str:
    """
    Get the standard cybersecurity relevance assessment prompt.
    
    Returns:
        Formatted prompt string for cybersecurity stakeholder assessment
    """
    return "Is the department/ministry of {domain} in {country} a direct stakeholder (i.e., responsible for or involved in) the country's cybersecurity?"


async def run_cyber_assessment(
    domain: str,
    countries: List[str] = None,
    max_queries: Optional[int] = None,
    delay_seconds: float = 1.0,
    max_concurrent: int = 1
) -> pd.DataFrame:
    """
    Run cybersecurity stakeholder assessment for specified domain and countries.
    
    Args:
        domain: Ministry domain to assess (e.g., "energy", "health", "transport")
        countries: List of countries to assess. If None, loads from default data file
        max_queries: Maximum number of queries to run (useful for testing)
        delay_seconds: Delay between API calls
        
    Returns:
        DataFrame with assessment results
    """
    if countries is None:
        countries = load_country_data()
    
    word_sets = create_word_sets(domain, countries)
    prompt = get_cyber_relevance_prompt()
    
    print(f"Starting cybersecurity stakeholder assessment for {domain} ministry...")
    print(f"Assessing {len(countries)} countries")
    if max_queries:
        print(f"Limited to {max_queries} queries for testing")
    
    # Run the assessment using AutoRA sprayer
    result_df = await sprayer.spray(
        word_sets=word_sets,
        research_questions=[prompt],
        response_model=CyberStakeholderAssessment,
        max_queries=max_queries,
        max_concurrent=max_concurrent,
        delay_between_batches=delay_seconds
    )
    
    print(f"\nCompleted! Generated {len(result_df)} assessments")
    if 'parsing_success' in result_df.columns:
        success_rate = result_df['parsing_success'].mean()
        print(f"Successful parsing rate: {success_rate:.1%}")
    
    return result_df


def process_results(spray_output: pd.DataFrame) -> pd.DataFrame:
    """
    Process spray output to create a clean DataFrame with expanded structured data and prettified citations.
    
    Args:
        spray_output: Raw output from the sprayer
        
    Returns:
        Processed DataFrame with expanded structured data columns and prettified citations
    """
    import ast
    
    def safe_parse_citations(citations_str: str) -> List[Dict[str, Any]]:
        """Safely parse citations string from Python dictionary format."""
        if pd.isna(citations_str) or not citations_str:
            return []
        
        # If it's already a list, return it
        if isinstance(citations_str, list):
            return citations_str
        
        citations_str = str(citations_str).strip()
        
        try:
            # Use ast.literal_eval for Python dictionary strings
            return ast.literal_eval(citations_str)
        except (ValueError, SyntaxError):
            print(f"Warning: Could not parse citations: {citations_str[:100]}...")
            return []
    
    def format_citation(citation: Dict[str, Any], index: int) -> str:
        """Format a single citation into a human-readable string."""
        if not isinstance(citation, dict):
            return f"[{index}] Invalid citation format"
        
        # Extract citation information (excluding 'matched')
        url = citation.get('url', 'No URL')
        title = citation.get('title', 'No Title')
        snippet = citation.get('snippet', '')
        date = citation.get('date', '')
        last_updated = citation.get('last_updated', '')
        
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
        
        # Combine all parts
        formatted = f"[{index}] " + "\n    ".join(citation_parts)
        return formatted
    
    def prettify_citations(citations_str: str) -> str:
        """Convert citations string to prettified format."""
        citations = safe_parse_citations(citations_str)
        
        if not citations:
            return "No citations available"
        
        prettified = []
        for i, citation in enumerate(citations, 1):
            formatted_citation = format_citation(citation, i)
            prettified.append(formatted_citation)
        
        return "\n\n" + "\n\n".join(prettified)
    
    # Create a DataFrame from the processed results
    df = spray_output.copy()
    
    # Prettify enriched_citations if it exists
    if 'enriched_citations' in df.columns:
        df['enriched_citations'] = df['enriched_citations'].apply(prettify_citations)
    
    first_columns = df[['domain','country']]
    last_columns = df[['research_question', 'enriched_citations']]
    
    # Expand structured_data into separate columns if it exists
    if 'structured_data' in spray_output.columns:
        # Handle both Pydantic objects and dictionaries
        structured_series = spray_output['structured_data'].apply(
            lambda x: x.model_dump() if hasattr(x, 'model_dump') else x if isinstance(x, dict) else {}
        )
        structured_df = structured_series.apply(pd.Series)
        df = pd.concat([first_columns, structured_df, last_columns], axis=1)
    
    return df


def save_results(
    spray_output: pd.DataFrame, 
    base_filename: str = "cyber_relevance_results",
    output_dir: str = "."
) -> None:
    """
    Save spray results in both raw JSON and processed CSV formats.
    
    Args:
        spray_output: DataFrame from spray function
        base_filename: Base filename for output files
        output_dir: Directory to save files to
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save raw results to JSONL (JSON Lines format)
    json_filename = output_path / f"{base_filename}.jsonl"
    spray_output.to_json(json_filename, orient='records', lines=True)
    print(f"Raw results saved to {json_filename}")
    
    # Save processed results to CSV
    csv_filename = output_path / f"{base_filename}.csv"
    processed_df = process_results(spray_output)
    processed_df.to_csv(csv_filename, index=False)
    print(f"Processed results saved to {csv_filename}")


def display_sample_results(df: pd.DataFrame, num_samples: int = 3) -> None:
    """
    Display sample results from the assessment.
    
    Args:
        df: DataFrame with assessment results
        num_samples: Number of sample results to display
    """
    print("\n" + "="*60)
    print("SAMPLE RESULTS")
    print("="*60)
    
    sample_df = df.head(num_samples)
    
    for i, (_, row) in enumerate(sample_df.iterrows()):
        print(f"\n--- {row.get('country', 'Unknown')} ---")
        
        if row.get('parsing_success', False):
            # Try to get structured data
            if 'structured_data' in row and row['structured_data']:
                assessment = row['structured_data']
                if hasattr(assessment, 'model_dump'):
                    assessment = assessment.model_dump()
                
                print(f"Relevance Level: {assessment.get('relevance_level', 'N/A')}")
                print(f"Confidence: {assessment.get('confidence', 'N/A')}")
                
                explanation = assessment.get('explanation', '')
                if explanation:
                    print(f"Explanation: {explanation[:150]}...")
            else:
                print("Structured data not available")
        else:
            error = row.get('parsing_error', 'Unknown error')
            print(f"Parsing Error: {error}")
    
    if len(df) > num_samples:
        print(f"\n... and {len(df) - num_samples} more countries assessed")


async def run_test_assessment(domain: str = "health", test_countries: List[str] = None) -> pd.DataFrame:
    """
    Run a quick test assessment with limited queries.
    
    Args:
        domain: Domain to test
        test_countries: Countries to test. If None, uses default test countries
        
    Returns:
        DataFrame with test results
    """
    if test_countries is None:
        test_countries = ["Afghanistan", "Germany"]
    
    print(f"Running test assessment for {domain} ministry in {test_countries}")
    
    result_df = await run_cyber_assessment(
        domain=domain,
        countries=test_countries,
        max_queries=2,  # Limit for testing
        delay_seconds=0.5  # Faster for testing
    )
    
    display_sample_results(result_df)
    return result_df


# Example usage and main function
async def main():
    """
    Main function demonstrating usage of the cyber relevance assessment tools.
    """
    print("Cyber Relevance Assessment Tool")
    print("=" * 40)
    
    # Run a test assessment
    test_results = await run_test_assessment("telecommunications", ["Afghanistan", "USA"])
    
    # Save test results
    save_results(test_results, "test_cyber_assessment", "output")
    
    print("\nTest completed! Check the 'output' directory for results.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())