# -*- coding: utf-8 -*-
"""
Created on Tue Jan  6 17:18:16 2026

@author: mm4114
"""
import inspect, hashlib, json
import pandas as pd
import numpy as np
from pathlib import Path

from lampyr.analysis.data import SegmentReference, TraceExtractionProfile
from lampyr.analysis.traces import dynamic_trace_extraction

from typing import Iterable, List, Callable, Dict

def longtidy_multidynamictraceextraction(
        data,
        segments: Iterable[SegmentReference],
        events: Iterable[str],
        extraction_profiles: Iterable[TraceExtractionProfile],
        expose_reports: List[str] = None,
        expose_properties: List[str] = None,
        expose_segmentattr: List[str] = None,
        custom_exposures: Dict[str, Callable] = None,
        perprofilekwargs: dict = None,
        **kwargs):
    def seg2segkey(s): return f'{s.animal}_{s.session}_{s.segment}'
    exposures = (['segkey', 'animal', 'session', 'segment'] +
                 (expose_reports or []) +
                 (expose_properties or []) +
                 (expose_segmentattr or []) +
                 (custom_exposures or []))
    # Construct segment info dataframe
    segment_dict = {e: [] for e in exposures}
    expose_reports = expose_reports or []
    expose_properties = expose_properties or []
    expose_segmentattr = expose_segmentattr or []
    custom_exposures = custom_exposures or {}
    for segref in segments:
        segment_dict['segkey'].append(seg2segkey(segref))
        segment_dict['animal'].append(segref.animal)
        segment_dict['session'].append(segref.session)
        segment_dict['segment'].append(segref.segment)
        seg_obj = data.get_segment(segref)
        for report in expose_reports:
            segment_dict[report].append(seg_obj['reports'][report])
        for prop in expose_properties:
            segment_dict[prop].append(seg_obj['properties'][prop])
        for attr in expose_segmentattr:
            segment_dict[attr].append(seg_obj[attr])
        for expname, expcallable in custom_exposures.items():
            segment_dict[expname].append(expcallable(seg_obj))
    segment_info = pd.DataFrame(segment_dict)
    segment_info['segkey'] = segment_info['segkey'].astype('string')
    segment_info['animal'] = segment_info['animal'].astype('category')
    segment_info['session'] = segment_info['session'].astype('category')
    segment_info['segment'] = segment_info['segment'].astype('string')

    profile_dfs = []
    for profile in extraction_profiles:
        if (perprofilekwargs is not None and 
            profile.profile_name in perprofilekwargs):
            profilekwargs = {**kwargs,
                             **perprofilekwargs[profile.profile_name]}
        else:
            profilekwargs = kwargs.copy()
        t, sig, _ = dynamic_trace_extraction(data,
                                             segments=segments,
                                             events=events,
                                             extraction_profile=profile,
                                             **profilekwargs)
        n_segs, len_t = sig.shape
        t_long = np.tile(t, n_segs)
        sig_long = sig.flatten()
        seg_keys = np.repeat(segment_dict['segkey'], len_t)
        profile_df = pd.DataFrame({'time': t_long,
                                  'value': sig_long,
                                   'signal': profile.profile_name,
                                   'segkey': seg_keys})
        profile_dfs.append(profile_df)
    traceframe = pd.concat(profile_dfs, ignore_index=True)
    traceframe = traceframe.merge(segment_info, on='segkey', how='left')
    return traceframe, segment_info

def load_parquet(path: str | Path) -> pd.DataFrame | None:
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_parquet(path, engine="pyarrow")


def save_parquet(path: str | Path, df: pd.DataFrame, overwrite: bool = False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        raise FileExistsError(path)

    df.to_parquet(path, engine="pyarrow", compression="snappy")


def ltdataset(cachefile):
    cachefile = Path(cachefile)
    cachefile.parent.mkdir(parents=True, exist_ok=True)

    def decorator(func):
        def wrapper(*args, force_reload = False, **kwargs):
            # Load metadata
            if cachefile.exists():
                with open(cachefile, "r") as f:
                    meta = json.load(f)
            else:
                meta = {}

            fid = func.__name__
            uid = hashlib.sha256(inspect.getsource(func).encode()).hexdigest()
            uid_main = f"{fid}_{uid}_main.parquet"
            uid_meta = f"{fid}_{uid}_meta.parquet"
            main_path = cachefile.parent / uid_main
            meta_path = cachefile.parent / uid_meta

            if fid in meta:
                old = meta[fid]
                if (old.get("uid") == uid and main_path.exists()
                    and meta_path.exists() and not force_reload):
                    df_main = load_parquet(main_path)
                    df_meta = load_parquet(meta_path)
                    if df_main is not None and df_meta is not None:
                        return df_main, df_meta
                else:
                    # Function changed → delete old parquets if exist
                    for old_file in [old.get("uid_main", ""), old.get("uid_meta", "")]:
                        old_path = cachefile.parent / old_file
                        if old_path.exists():
                            old_path.unlink()

            # Run function and save
            df_main, df_meta = func(*args, **kwargs)
            save_parquet(main_path, df_main, overwrite=True)
            save_parquet(meta_path, df_meta, overwrite=True)

            meta[fid] = {"uid": uid, "uid_main": uid_main, "uid_meta": uid_meta}
            with open(cachefile, "w") as f:
                json.dump(meta, f, indent=2)

            return df_main, df_meta

        return wrapper
    return decorator
