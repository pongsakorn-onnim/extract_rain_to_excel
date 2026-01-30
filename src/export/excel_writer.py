import pandas as pd
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)

def export_to_excel(dfs: Dict[str, pd.DataFrame], output_path: Path):
    """
    Exports multiple DataFrames to a single Excel file with multiple sheets.
    Args:
        dfs: Dictionary where Key = Sheet Name, Value = DataFrame
        output_path: Destination path
    """
    try:
        # Ensure parent directory exists
        if not output_path.parent.exists():
            logger.info(f"Creating output directory: {output_path.parent}")
            output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing Excel to: {output_path}")
        
        # Use ExcelWriter context manager to write multiple sheets
        # engine='openpyxl' is required for writing .xlsx files
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet_name, df in dfs.items():
                logger.info(f"  > Writing sheet: {sheet_name} ({len(df)} rows)")
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info("Export completed successfully.")

    except Exception as e:
        logger.error(f"Failed to write Excel file: {e}")
        raise