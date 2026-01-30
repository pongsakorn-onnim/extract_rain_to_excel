import pandas as pd
import numpy as np

def calculate_anomaly(fcst_val: float, normal_val: float) -> float:
    """
    Calculates simple anomaly: Forecast - Normal
    """
    # Handle None/NaN cases if necessary, though pandas usually handles them
    if pd.isna(fcst_val) or pd.isna(normal_val):
        return np.nan
    return fcst_val - normal_val

def calculate_percent_anomaly(anomaly_val: float, normal_val: float) -> float:
    """
    Calculates percentage anomaly: (Anomaly / Normal) * 100
    Handles division by zero or near-zero normal values.
    """
    if pd.isna(anomaly_val) or pd.isna(normal_val):
        return np.nan
    
    # Avoid division by zero
    if normal_val == 0:
        return np.nan # Or 0, depending on business logic for dry areas
        
    return (anomaly_val / normal_val) * 100.0

def enrich_dataframe_with_metrics(df: pd.DataFrame, 
                                  fcst_col: str = 'fcst_mean', 
                                  normal_col: str = 'normal_mean') -> pd.DataFrame:
    """
    Vectorized calculation for the entire DataFrame.
    Much faster than looping through rows.
    """
    # 1. Anomaly
    df['anomaly'] = df[fcst_col] - df[normal_col]
    
    # 2. Percent Anomaly (Handle division by zero safely using numpy)
    # np.where(condition, value_if_true, value_if_false)
    df['percent_anomaly'] = np.where(
        df[normal_col] != 0, 
        (df['anomaly'] / df[normal_col]) * 100.0, 
        np.nan
    )
    
    return df