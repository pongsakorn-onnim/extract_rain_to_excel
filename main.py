import logging
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Import modules we created
from src.utils.config_loader import load_config
from src.core.raster_processor import RasterProcessor
from src.core.calculator import enrich_dataframe_with_metrics
from src.export.excel_writer import export_to_excel

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """
    Parses command line arguments.
    Allows overriding config values for flexibility.
    """
    parser = argparse.ArgumentParser(description="Extract rainfall data to Excel.")
    
    # Argument: --init (Optional)
    parser.add_argument(
        "--init", 
        type=str, 
        help="Init month in YYYYMM format (e.g., 202603). Overrides config.yaml."
    )
    
    return parser.parse_args()

def main():
    # 0. Parse Arguments
    args = parse_arguments()

    # 1. Load Configuration
    config_path = Path("configs/config.yaml")
    cfg = load_config(config_path)
    
    # --- Override Config with CLI Args if provided ---
    if args.init:
        logger.info(f"Overriding init_month from CLI: {args.init}")
        cfg['run']['init_month'] = args.init
    # -------------------------------------------------
    
    processor = RasterProcessor(cfg)
    
    # [Point 1] เปลี่ยนตัวเก็บผลลัพธ์เป็น Dictionary แยกตามประเภทโซน (Basin/Region)
    results_by_zone = {
        "Basin": [],
        "Region": []
    }
    
    # 2. Setup Loop Parameters
    init_month_str = str(cfg['run']['init_month'])
    leads = cfg['run']['leads']
    models_order = cfg['models']['order']
    
    # Define Zoning to process
    zones_config = {
        "Basin": {
            "path": Path(cfg['paths']['basin_shp']),
            "id": cfg['zones']['basin']['id_field'],
            "name": cfg['zones']['basin']['name_field_th']
        },
        "Region": {
            "path": Path(cfg['paths']['region_shp']),
            "id": cfg['zones']['region']['id_field'],
            "name": cfg['zones']['region']['name_field_th']
        }
    }

    models_order = cfg['models']['order']
    leads = cfg['run']['leads']
    init_month_str = str(cfg['run']['init_month'])

    logger.info(f"Starting extraction for Init Month: {init_month_str}")

    # --- MAIN LOOP: วนตามไฟล์ (Model/Lead) เป็นหลัก ---
    for model_name in models_order:
        if model_name not in cfg['models']: continue
        model_cfg = cfg['models'][model_name]
        
        for lead in leads:
            target_date = processor.get_target_date(lead)
            logger.info(f"Processing: {model_name} | Lead: {lead} | Target: {target_date.strftime('%Y-%m')}")
            
            # 1. เตรียม Path ของไฟล์ Raster (ทำแค่ครั้งเดียวต่อ 1 ไฟล์)
            try:
                fcst_path = processor._generate_fcst_path(model_name, model_cfg, target_date, lead)
                normal_path = processor._generate_normal_path(target_date)
            except Exception as e:
                logger.error(f"Path generation error: {e}")
                continue

            # Check existence once
            has_fcst = fcst_path.exists()
            has_normal = normal_path.exists()

            if not has_fcst:
                logger.warning(f"  > Forecast file missing: {fcst_path.name}")
                continue # ถ้าไม่มีไฟล์หลัก ก็ข้ามไปเลย ไม่ต้องไปทำ Zone

            # --- INNER LOOP: วนตาม Zone (Basin -> Region) ---
            # ใช้ไฟล์ Raster ชุดเดิมที่เตรียมไว้ข้างบน
            for zone_type, z_cfg in zones_config.items():
                logger.info(f"    > Extracting {zone_type}...") # ปิดไว้ก็ได้เดี๋ยวรก Terminal

                # A. Calc Forecast
                df_fcst = processor.process_zonal_stats(fcst_path, z_cfg['path'], z_cfg['id'], z_cfg['name'])
                if df_fcst.empty: continue
                df_fcst = df_fcst.rename(columns={'mean': 'fcst_mean'})

                # B. Calc Normal
                if has_normal:
                    df_normal = processor.process_zonal_stats(normal_path, z_cfg['path'], z_cfg['id'], z_cfg['name'])
                else:
                    df_normal = pd.DataFrame() # Empty

                # Handle missing normal case
                if df_normal.empty:
                    df_normal = df_fcst[[z_cfg['id']]].copy()
                    df_normal['normal_mean'] = np.nan
                else:
                    df_normal = df_normal.rename(columns={'mean': 'normal_mean'})

                # C. Merge & Metadata
                df_merged = pd.merge(df_fcst, df_normal, on=[z_cfg['id'], z_cfg['name']], how='left')
                
                df_merged['init_month'] = init_month_str
                df_merged['lead_time'] = lead
                df_merged['target_month'] = target_date.strftime("%Y-%m")
                df_merged['model'] = model_name
                df_merged['zone_type'] = zone_type

                # D. Calc Metrics
                df_calculated = enrich_dataframe_with_metrics(
                    df_merged, fcst_col='fcst_mean', normal_col='normal_mean'
                )

                # E. Store Result ใส่กระเป๋าใครกระเป๋ามัน
                results_by_zone[zone_type].append(df_calculated)

    # 4. Export Result (เหมือนเดิมเป๊ะ)
    dfs_to_export = {}
    base_cols = ['zone_type', 'init_month', 'model', 'lead_time', 'target_month']
    metric_cols = ['fcst_mean', 'normal_mean', 'anomaly', 'percent_anomaly']

    for zone, data_list in results_by_zone.items():
        if data_list:
            df_zone = pd.concat(data_list, ignore_index=True)
            cols = base_cols + [c for c in df_zone.columns if c not in base_cols + metric_cols] + metric_cols
            valid_cols = [c for c in cols if c in df_zone.columns]
            dfs_to_export[zone] = df_zone[valid_cols]

    if dfs_to_export:
        output_filename = cfg['output']['excel_name'].replace("{init_month}", init_month_str)
        output_path = Path(cfg['output']['extract_dir']) / output_filename
        export_to_excel(dfs_to_export, output_path)
        logger.info(f"=== JOB FINISHED: {output_path} ===")
    else:
        logger.warning("No data processed.")

if __name__ == "__main__":
    main()