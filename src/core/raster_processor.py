import pandas as pd
import rasterio
import numpy as np
from rasterstats import zonal_stats
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import logging

# ใช้ logger เดียวกับโปรเจค
logger = logging.getLogger(__name__)

class RasterProcessor:
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the RasterProcessor with configuration dictionary.
        
        Args:
            config: The loaded configuration dictionary.
        """
        self.config = config
        self.fcst_root = Path(config['paths']['fcst_root'])
        self.normal_root = Path(config['paths']['normal30y_ascii_dir'])
        
        # เตรียม Date object สำหรับ Init Month
        init_str = str(config['run']['init_month']) # "202602"
        self.init_date = datetime.strptime(init_str, "%Y%m")

    def get_target_date(self, lead: int) -> datetime:
        """
        Calculates the target month based on init_month + lead time.
        Handles year rollover automatically.
        """
        # Logic: บวกเดือนเพิ่มไปใน date object
        # หมายเหตุ: การบวกเดือนใน python ต้องระวัง แต่วิธีที่ง่ายคือคำนวณปี/เดือนใหม่เอง
        month_new = self.init_date.month + lead
        year_new = self.init_date.year + (month_new - 1) // 12
        month_new = (month_new - 1) % 12 + 1
        return datetime(year_new, month_new, 1)

    def _generate_fcst_path(self, model_key: str, model_cfg: Dict, target_date: datetime, lead: int) -> Path:
        """
        Generates the absolute path for a forecast raster file.
        Adjusts logic based on HII vs OneMap structure if needed.
        """
        # โครงสร้าง Path: .../OM/{init_yyyymm}/OM/{filename}
        # หมายเหตุ: ตามที่คุณระบุ path จะเข้าไปที่ .../OM/202602/OM เสมอ ไม่ว่า lead จะเป็นเท่าไหร่
        # ไฟล์ข้างในจะเปลี่ยนชื่อตาม target date
        
        init_str = self.init_date.strftime("%Y%m")
        target_str = target_date.strftime("%Y%m")
        
        # Base folder path
        base_dir = self.fcst_root / init_str / "OM"
        
        # Filename construction
        prefix = model_cfg['filename']['prefix'] # e.g. "OM_MFCST_"
        ext = model_cfg['filename']['ext']       # ".asc"
        filename = f"{prefix}{target_str}{ext}"
        
        return base_dir / filename

    def _generate_normal_path(self, target_date: datetime) -> Path:
        """Generates path for 30-year normal file (based on Month only)."""
        month_str = target_date.strftime("%m") # "02"
        cfg = self.config['normal30y']['filename']
        filename = f"{cfg['prefix']}{month_str}{cfg['suffix']}{cfg['ext']}"
        return self.normal_root / filename

    def process_zonal_stats(self, raster_path: Path, shapefile_path: Path, 
                          id_col: str, name_col: str) -> pd.DataFrame:
        """
        Computes zonal statistics (mean) for a given raster and shapefile.
        Returns a DataFrame with [ID, Name, Mean_Value].
        """
        if not raster_path.exists():
            logger.warning(f"Raster not found: {raster_path}")
            return pd.DataFrame() # Return empty if file missing

        logger.info(f"Processing zonal stats for: {raster_path.name}")
        
        # ใช้ rasterstats.zonal_stats
        # stats="mean" คือสิ่งที่เราต้องการ
        # nodata value จะถูกอ่านจาก header .asc อัตโนมัติ
        stats = zonal_stats(
            str(shapefile_path),
            str(raster_path),
            stats="mean",
            geojson_out=False
        )
        
        # Load shapefile attributes separately to merge
        # (ใช้ geopandas อ่านเฉพาะ column ที่จำเป็นเพื่อความเร็ว)
        import geopandas as gpd
        gdf = gpd.read_file(shapefile_path, include_fields=[id_col, name_col])
        
        # Create Result DataFrame
        df_result = pd.DataFrame(stats)
        df_result[id_col] = gdf[id_col]
        df_result[name_col] = gdf[name_col]
        
        # Rename 'mean' to something meaningful later, 
        # but here we return raw stats structure
        return df_result[['mean', id_col, name_col]]

    def run_extraction(self):
        """
        Orchestrates the whole extraction process for all leads and models.
        (This will be expanded in the next step to loop through everything)
        """
        pass