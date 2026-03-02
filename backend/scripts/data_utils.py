"""
Data file utilities for seeding scripts.

Resolves data file paths with R2 fallback:
1. Local: backend/data/<filename> (development, always preferred)
2. Remote: Download from Cloudflare R2 bucket (CI/CD or fresh clone)

Set SEED_DATA_R2_URL to enable R2 fallback (S3-compatible endpoint).
Set SEED_DATA_R2_ACCESS_KEY and SEED_DATA_R2_SECRET_KEY for authentication.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def get_data_path(filename: str) -> Path:
    """
    Get path to a data file, downloading from R2 if missing locally.

    Args:
        filename: Name of the file in backend/data/ (e.g. "spells.json")

    Returns:
        Path to the local file (either existing or freshly downloaded)

    Raises:
        FileNotFoundError: If file is missing locally and R2 is not configured
    """
    local_path = DATA_DIR / filename
    if local_path.exists():
        return local_path

    # Try downloading from R2
    r2_endpoint = os.getenv("SEED_DATA_R2_URL")
    if not r2_endpoint:
        raise FileNotFoundError(
            f"{filename} not found at {local_path} and SEED_DATA_R2_URL not set. "
            "Either place data files in backend/data/ or configure R2 credentials:\n"
            "  SEED_DATA_R2_URL=https://<account>.r2.cloudflarestorage.com\n"
            "  SEED_DATA_R2_ACCESS_KEY=<key>\n"
            "  SEED_DATA_R2_SECRET_KEY=<secret>"
        )

    access_key = os.getenv("SEED_DATA_R2_ACCESS_KEY", "")
    secret_key = os.getenv("SEED_DATA_R2_SECRET_KEY", "")
    bucket = os.getenv("SEED_DATA_R2_BUCKET", "realms-data")

    if not access_key or not secret_key:
        raise FileNotFoundError(
            f"{filename} not found locally and R2 credentials incomplete. "
            "Set SEED_DATA_R2_ACCESS_KEY and SEED_DATA_R2_SECRET_KEY."
        )

    logger.info(f"Downloading {filename} from R2 bucket '{bucket}'...")

    try:
        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, f"seed/{filename}", str(local_path))
        logger.info(f"Downloaded {filename} ({local_path.stat().st_size / 1024:.0f} KB)")
        return local_path

    except ImportError:
        raise FileNotFoundError(
            f"{filename} not found locally. Install boto3 to download from R2: pip install boto3"
        )
    except Exception as e:
        # Clean up partial download
        if local_path.exists():
            local_path.unlink()
        raise FileNotFoundError(f"Failed to download {filename} from R2: {e}") from e


def get_data_dir() -> Path:
    """
    Get the data directory path.
    For scripts that need to scan the whole directory (e.g. analyze_creature_datasets.py).

    Returns:
        Path to backend/data/

    Raises:
        FileNotFoundError: If the directory doesn't exist and R2 is not configured
    """
    if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
        return DATA_DIR

    raise FileNotFoundError(
        f"Data directory {DATA_DIR} is empty or missing. "
        "Place data files in backend/data/ or use get_data_path() "
        "to download individual files from R2."
    )
