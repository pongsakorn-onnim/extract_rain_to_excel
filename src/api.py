"""
Public API for extract_rain_to_excel.
Exposes run_extraction() for use by other projects via sys.path import.
"""
import logging
import numpy as np
import pandas as pd
from pathlib import Path

from utils.config_loader import load_config
from core.raster_processor import RasterProcessor
from core.calculator import enrich_dataframe_with_metrics

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.yaml"


def run_extraction(init_year: int, init_month: int) -> dict[str, pd.DataFrame]:
    """
    Run zonal statistics extraction for the given init month.

    Returns {"Basin": df, "Region": df} without writing to disk.
    Each DataFrame has columns:
        MB_CODE/REG_CODE, MBASIN_T/FIRST_REGI,1
        init_month, lead_time, target_month, model,
        fcst_mean, normal_mean, anomaly, percent_anomaly
    """
    cfg = load_config(_CONFIG_PATH)
    cfg['run']['init_month'] = f"{init_year}{init_month:02d}"

    processor = RasterProcessor(cfg)
    results_by_zone: dict[str, list] = {"Basin": [], "Region": []}

    leads         = cfg['run']['leads']
    models_order  = cfg['models']['order']
    init_month_str = str(cfg['run']['init_month'])

    zones_config = {
        "Basin": {
            "path": Path(cfg['paths']['basin_shp']),
            "id":   cfg['zones']['basin']['id_field'],
            "name": cfg['zones']['basin']['name_field_th'],
        },
        "Region": {
            "path": Path(cfg['paths']['region_shp']),
            "id":   cfg['zones']['region']['id_field'],
            "name": cfg['zones']['region']['name_field_th'],
        },
    }

    for model_name in models_order:
        if model_name not in cfg['models']:
            continue
        model_cfg = cfg['models'][model_name]

        for lead in leads:
            target_date = processor.get_target_date(lead)
            logger.info(
                f"Extracting: {model_name} | Lead {lead} | {target_date.strftime('%Y-%m')}"
            )

            try:
                fcst_path   = processor._generate_fcst_path(model_name, model_cfg, target_date, lead)
                normal_path = processor._generate_normal_path(target_date)
            except Exception as e:
                logger.error(f"Path generation error: {e}")
                continue

            if not fcst_path.exists():
                logger.warning(f"Missing forecast file: {fcst_path.name}")
                continue

            has_normal = normal_path.exists()

            for zone_type, z_cfg in zones_config.items():
                df_fcst = processor.process_zonal_stats(
                    fcst_path, z_cfg['path'], z_cfg['id'], z_cfg['name']
                )
                if df_fcst.empty:
                    continue
                df_fcst = df_fcst.rename(columns={'mean': 'fcst_mean'})

                if has_normal:
                    df_normal = processor.process_zonal_stats(
                        normal_path, z_cfg['path'], z_cfg['id'], z_cfg['name']
                    )
                else:
                    df_normal = pd.DataFrame()

                if df_normal.empty:
                    df_normal = df_fcst[[z_cfg['id'], z_cfg['name']]].copy()
                    df_normal['normal_mean'] = np.nan
                else:
                    df_normal = df_normal.rename(columns={'mean': 'normal_mean'})

                df_merged = pd.merge(
                    df_fcst, df_normal, on=[z_cfg['id'], z_cfg['name']], how='left'
                )
                df_merged['init_month']  = init_month_str
                df_merged['lead_time']   = lead
                df_merged['target_month'] = target_date.strftime("%Y-%m")
                df_merged['model']       = model_name
                df_merged['zone_type']   = zone_type

                df_calculated = enrich_dataframe_with_metrics(
                    df_merged, fcst_col='fcst_mean', normal_col='normal_mean'
                )
                results_by_zone[zone_type].append(df_calculated)

    return {
        zone: pd.concat(data_list, ignore_index=True) if data_list else pd.DataFrame()
        for zone, data_list in results_by_zone.items()
    }


def run_obs_diff_batch_extraction(init_year: int, init_month: int) -> pd.DataFrame:
    """
    Batch extraction of obs-diff data for all past months covered by the report.
    - Non-January report: Jan … (init_month-1) of init_year
    - January report:     Jan … Dec of (init_year-1)

    Returns a DataFrame with columns:
        model, obs_year, obs_month, REG_CODE, FIRST_REGI,
        obs_mean, fcst_mean, anomaly, percent_anomaly
    """
    cfg = load_config(_CONFIG_PATH)

    if init_month == 1:
        past_months = [(init_year - 1, m) for m in range(1, 13)]
    else:
        past_months = [(init_year, m) for m in range(1, init_month)]

    fcst_root    = Path(cfg['paths']['fcst_root'])
    obs_dir      = Path(cfg['paths']['obs_monthly_raster_dir'])
    tmd_fcst_dir = Path(cfg['paths']['tmd_fcst_raster_dir'])
    region_shp   = Path(cfg['paths']['region_shp'])

    processor = RasterProcessor(cfg)
    id_col    = cfg['zones']['region']['id_field']
    name_col  = cfg['zones']['region']['name_field_th']

    fcst_path_map = {
        "HII":  lambda yyyymm: fcst_root / yyyymm / "OM" / f"rain_fcst_hii_{yyyymm}.asc",
        "TMD":  lambda yyyymm: tmd_fcst_dir / yyyymm / f"rain_tmd_fcst_{yyyymm}.asc",
        "OM_W": lambda yyyymm: fcst_root / yyyymm / "OM" / f"OM_WFCST_{yyyymm}.asc",
    }

    results = []

    for obs_year, obs_month in past_months:
        yyyymm   = f"{obs_year}{obs_month:02d}"
        obs_path = obs_dir / str(obs_year) / f"o_th{yyyymm}.asc"

        if not obs_path.exists():
            logger.warning(f"Obs raster missing: {obs_path}")
            continue

        df_obs = processor.process_zonal_stats(obs_path, region_shp, id_col, name_col)
        if df_obs.empty:
            continue
        df_obs = df_obs.rename(columns={"mean": "obs_mean"})

        for model, path_fn in fcst_path_map.items():
            fcst_path = path_fn(yyyymm)
            if not fcst_path.exists():
                logger.warning(f"Fcst raster missing: {fcst_path}")
                continue

            df_fcst = processor.process_zonal_stats(fcst_path, region_shp, id_col, name_col)
            if df_fcst.empty:
                continue
            df_fcst = df_fcst.rename(columns={"mean": "fcst_mean"})

            df = pd.merge(df_obs, df_fcst, on=[id_col, name_col])
            df["model"]     = model
            df["obs_year"]  = obs_year
            df["obs_month"] = obs_month
            df["anomaly"]   = df["obs_mean"] - df["fcst_mean"]
            df["percent_anomaly"] = np.where(
                df["fcst_mean"] != 0,
                (df["anomaly"] / df["fcst_mean"]) * 100,
                np.nan,
            )
            results.append(df)

    if not results:
        return pd.DataFrame()

    col_order = ["model", "obs_year", "obs_month", id_col, name_col,
                 "obs_mean", "fcst_mean", "anomaly", "percent_anomaly"]
    df_all = pd.concat(results, ignore_index=True)
    return df_all[[c for c in col_order if c in df_all.columns]]


_REGION_NAME_MAP = {
    "ภาคเหนือ":               "เหนือ",
    "ภาคตะวันออกเฉียงเหนือ":  "ตะวันออกเฉียงเหนือ",
    "ภาคกลาง":                "กลาง",
    "ภาคตะวันออก":            "ตะวันออก",
    "ภาคใต้ฝั่งตะวันออก":    "ใต้ฝั่งตะวันออก",
    "ภาคใต้ฝั่งตะวันตก":     "ใต้ฝั่งตะวันตก",
}


def run_obs_diff_extraction(model: str, year: int, month: int) -> dict:
    """
    Fallback for group 2.10.1-2.10.3 obs-diff tables when senior's Excel is missing.
    Extracts obs and fcst zonal means (region) at lead 0, computes diff and pct.

    model: "HII", "TMD", or "OM_W"
    Returns: {thai_region_short_name: {"anomaly": float, "percent": float}}
      anomaly = obs - fcst (mm)
      percent = (obs - fcst) / fcst * 100
    """
    cfg = load_config(_CONFIG_PATH)

    yyyymm = f"{year}{month:02d}"
    fcst_root   = Path(cfg['paths']['fcst_root'])
    obs_dir     = Path(cfg['paths']['obs_monthly_raster_dir'])
    tmd_fcst_dir = Path(cfg['paths']['tmd_fcst_raster_dir'])
    region_shp  = Path(cfg['paths']['region_shp'])

    obs_path = obs_dir / str(year) / f"o_th{yyyymm}.asc"

    if model == "HII":
        fcst_path = fcst_root / yyyymm / "OM" / f"rain_fcst_hii_{yyyymm}.asc"
    elif model == "TMD":
        fcst_path = tmd_fcst_dir / yyyymm / f"rain_tmd_fcst_{yyyymm}.asc"
    elif model == "OM_W":
        fcst_path = fcst_root / yyyymm / "OM" / f"OM_WFCST_{yyyymm}.asc"
    else:
        logger.error(f"run_obs_diff_extraction: unsupported model '{model}'")
        return {}

    if not obs_path.exists():
        logger.warning(f"Obs raster not found: {obs_path}")
        return {}
    if not fcst_path.exists():
        logger.warning(f"Fcst raster not found: {fcst_path}")
        return {}

    processor = RasterProcessor(cfg)
    id_col   = cfg['zones']['region']['id_field']    # REG_CODE
    name_col = cfg['zones']['region']['name_field_th']  # FIRST_REGI

    df_obs  = processor.process_zonal_stats(obs_path,  region_shp, id_col, name_col)
    df_fcst = processor.process_zonal_stats(fcst_path, region_shp, id_col, name_col)

    if df_obs.empty or df_fcst.empty:
        logger.warning(f"run_obs_diff_extraction: empty zonal stats for {model} {yyyymm}")
        return {}

    df_obs  = df_obs.rename(columns={"mean": "obs_mean"})
    df_fcst = df_fcst.rename(columns={"mean": "fcst_mean"})
    df = pd.merge(df_obs, df_fcst, on=[id_col, name_col])

    result = {}
    for _, row in df.iterrows():
        raw_name = str(row[name_col]).strip()
        name     = _REGION_NAME_MAP.get(raw_name, raw_name.removeprefix("ภาค"))
        obs_val  = float(row["obs_mean"])
        fcst_val = float(row["fcst_mean"])
        anomaly  = obs_val - fcst_val
        pct      = (anomaly / fcst_val * 100) if fcst_val != 0 else float("nan")
        result[name] = {"anomaly": anomaly, "percent": pct}

    return result
