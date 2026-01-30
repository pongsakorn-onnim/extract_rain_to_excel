import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Union

# ตั้งค่า Logging เบื้องต้น (สามารถย้ายไปตั้งค่า global ที่ main.py ภายหลังได้)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Loads configuration from a YAML file.

    This function safely reads a YAML file and returns its content as a dictionary.
    It uses pathlib for file handling and standard logging for status updates.

    Args:
        config_path (Union[str, Path]): The path to the .yaml configuration file.
            Can be a string or a pathlib.Path object.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration parameters.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the file contains invalid YAML syntax.
        Exception: For any other unexpected errors during file reading.
    """
    # Ensure config_path is a Path object
    path_obj = Path(config_path)

    if not path_obj.exists():
        error_msg = f"Configuration file not found at: {path_obj.resolve()}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        with path_obj.open("r", encoding="utf-8") as f:
            # use safe_load to prevent arbitrary code execution
            config_data = yaml.safe_load(f)
            
        logger.info(f"Successfully loaded configuration from {path_obj.name}")
        return config_data

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
        raise

if __name__ == "__main__":
    # Smoke test: Try to load the config if this script is run directly
    # Assumes the script is run from project root or src/utils
    # Adjust relative path as needed for testing
    try:
        test_path = Path("../../configs/config.yaml") # Adjust based on where you run this
        if test_path.exists():
            cfg = load_config(test_path)
            print("Config loaded successfully keys:", cfg.keys())
        else:
            print(f"Test skipped: {test_path} not found.")
    except Exception as e:
        print(f"Test failed: {e}")