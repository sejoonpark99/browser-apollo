"""
CSV Domain Loader for Browser Automation
Loads domains from CSV file and formats them for Apollo.io input
"""

import pandas as pd
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def load_domains(path: str) -> str:
    """
    Load domains from CSV file and return as newline-separated string

    Args:
        path: Path to CSV file with 'domain' column

    Returns:
        Newline-separated string of domains

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        KeyError: If 'domain' column is missing
        ValueError: If CSV is empty or invalid
    """
    try:
        df = pd.read_csv(path)

        if "domain" not in df.columns:
            raise KeyError("CSV file must contain a 'domain' column")

        # Clean and filter domains
        domains = df["domain"].dropna().astype(str).str.strip()
        domains = domains[domains != ""]  # Remove empty strings

        if len(domains) == 0:
            raise ValueError("No valid domains found in CSV file")

        logger.info(f"Loaded {len(domains)} domains from {path}")
        return "\n".join(domains)

    except FileNotFoundError:
        logger.error(f"CSV file not found: {path}")
        raise
    except Exception as e:
        logger.error(f"Error loading domains from {path}: {str(e)}")
        raise


def load_domains_list(path: str) -> List[str]:
    """
    Load domains from CSV file and return as list

    Args:
        path: Path to CSV file with 'domain' column

    Returns:
        List of domain strings
    """
    domains_str = load_domains(path)
    return domains_str.split("\n")


def validate_domain(domain: str) -> bool:
    """
    Basic domain validation

    Args:
        domain: Domain string to validate

    Returns:
        True if domain appears valid
    """
    import re

    # Basic domain regex pattern
    pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    return bool(re.match(pattern, domain.strip()))


def create_sample_csv(path: str, domains: List[str]) -> None:
    """
    Create a sample CSV file with domains for testing

    Args:
        path: Output CSV file path
        domains: List of domains to include
    """
    df = pd.DataFrame({"domain": domains})
    df.to_csv(path, index=False)
    logger.info(f"Created sample CSV with {len(domains)} domains at {path}")


# Sample domains for testing
SAMPLE_DOMAINS = [
    "bloomreach.com",
    "klaviyo.com",
    "shopify.com",
    "stripe.com",
    "slack.com",
]

if __name__ == "__main__":
    # Create sample CSV for testing
    create_sample_csv("domains.csv", SAMPLE_DOMAINS)

    # Test loading
    domains_str = load_domains("domains.csv")
    print(f"Loaded domains:\n{domains_str}")

    # Test validation
    for domain in SAMPLE_DOMAINS:
        is_valid = validate_domain(domain)
        print(f"{domain}: {'✓' if is_valid else '✗'}")
