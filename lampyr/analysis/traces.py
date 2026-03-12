# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 14:26:35 2026

@author: mm4114
"""
import numpy as np

from scipy.interpolate import interp1d

from lampyr.primatives import Session
from lampyr.analysis.data import SegmentReference, TraceReference, MultiSessionDataset, TraceExtractionProfile
from lampyr.analysis.time import TimeTranslator, create_dynamictimearray, create_dynamictimearray_2d
from lampyr.analysis.segments import extract_event_times_multiple

from typing import Iterable, Literal, Union, List, Tuple


def determine_ideal_samplerate(event_times,
                               extraction_profile: TraceExtractionProfile,
                               mode: Literal['mean', 'median'] = 'mean'):
    diffs = np.diff(event_times, axis=1)
    if mode == 'mean':
        elapsed = diffs.mean(axis=0)
    elif mode == 'median':
        elapsed = np.median(diffs, axis=0)

    samples = extraction_profile.samplerate * elapsed
    ideal_samplerate = [int(round(s))
                        if not np.isnan(s) else 1
                        for s in samples]
    return ideal_samplerate


def timeconversion_bulk(data: MultiSessionDataset,
                        sessionids: Iterable[str],
                        event_times,
                        source_time,
                        target_time):
    converted_times = np.empty(event_times.shape)
    timeconverters = {}
    for ind, sessionid in enumerate(sessionids):
        if sessionid not in timeconverters:
            translator = TimeTranslator(data.sessionsbyid[sessionid],
                                        target=target_time,
                                        source=source_time,
                                        kind='linear',
                                        fill_value='extrapolate')
            timeconverters[sessionid] = translator
        nt = timeconverters[sessionid].convert(event_times[ind, :])
        converted_times[ind, :] = nt

    return converted_times


def dynamic_trace_extraction(data,
                             segments: Iterable[SegmentReference],
                             events: Iterable[str],
                             extraction_profile: TraceExtractionProfile,
                             samples: List[Union[int, None]] = None,
                             event_pseudotimes: List[Union[int, None]] = None,
                             baseline_range: Tuple[float, float] = None,
                             padding=False,
                             pad_start=2,
                             pad_end=6):
    event_times = extract_event_times_multiple(data, segments, events)
    if np.isnan(event_times).sum() > 0:
        raise KeyError('Was not able to find all events in all segments')
    if padding:
        event_times_padded = np.empty((len(segments), len(events)+2))
        event_times_padded[:, 1:-1] = event_times
        event_times_padded[:, 0] = event_times[:, 0] - pad_start
        event_times_padded[:, -1] = event_times[:, -1] + pad_end
        event_times = event_times_padded
    samples_ideal = determine_ideal_samplerate(
        event_times, extraction_profile)
    if samples is None:
        samples = samples_ideal
    samples = [s if s is not None else i
               for s, i in zip(samples, samples_ideal)]
    if len(samples)+1 != event_times.shape[1]:
        raise ValueError('Length of samples must be length of events -1\n' +
                         f'samples is currently {len(samples)}\n' +
                         f'events is currently {event_times.shape[1]}')
    # Time conversion...if required
    if extraction_profile.time_type != 'unix_time':
        event_times = timeconversion_bulk(data,
                                          [seg.session for seg in segments],
                                          event_times,
                                          'unix_time',
                                          extraction_profile.time_type
                                          )
    tarr = create_dynamictimearray_2d(event_times, samples)
    trace_references = [TraceReference(seg.session,
                                       row,
                                       extraction_profile.time_type)
                        for seg, row in zip(segments, tarr)]
    result_arr = np.empty((tarr.shape))
    for ind, ref in enumerate(trace_references):
        result_arr[ind, :] = data.get_trace(ref, extraction_profile)

    # Take the event times and calculate average time distance between events
    diffs = np.empty((event_times.shape[1]))
    diffs[0] = 0
    diffs[1:] = np.diff(event_times, axis=1).mean(axis=0)
    pseudoeventtimes_ideal = np.cumsum(diffs)
    pseudoeventtimes_ideal = [float(e) for e in pseudoeventtimes_ideal]

    if event_pseudotimes is None:
        event_pseudotimes = pseudoeventtimes_ideal
    event_pseudotimes = [e if e is not None else i
                         for e, i in zip(event_pseudotimes,
                                         pseudoeventtimes_ideal)
                         ]

    pseudotime = create_dynamictimearray(event_pseudotimes, samples)

    if baseline_range is not None:
        bl_mask = ((pseudotime > baseline_range[0]) &
                   (pseudotime < baseline_range[1]))
        result_arr = result_arr - result_arr[:, bl_mask
                                             ].mean(axis=1)[:, np.newaxis]

    info = {'event_times': event_times,
            'samples_ideal': samples_ideal,
            'pseudoeventtimes_ideal': pseudoeventtimes_ideal
            }

    return pseudotime, result_arr, info


class SessionInterpolatedTraceExtractor:
    def __init__(self, session: Session, time_type):
        print('SessionInterpolatedTraceExtractor is depreciated')
        self.time_type = time_type
        self.rigdata = {}
        self.rigdata_linear = {}
        self.rigdata_raw = session.rigdata
        for rdat, rdict in session.rigdata.items():
            if rdat == 'SyncStream':
                continue
            t = rdict[time_type]
            v = rdict['report_value']

            self.rigdata[rdat] = interp1d(
                t, v, kind='nearest',
                bounds_error=False, fill_value=np.nan
            )

            self.rigdata_linear[rdat] = interp1d(
                t, v, kind='linear',
                bounds_error=False, fill_value=np.nan
            )

    def extract(self, rig_data: str, time_array: np.ndarray, mode="nearest"):
        if mode == "nearest":
            return self.rigdata[rig_data](time_array)
        elif mode == "linear":
            return self.rigdata_linear[rig_data](time_array)
        else:
            raise ValueError(f"Unknown interpolation mode: {mode}")

    def extract_windowed_dynamic(self, rig_data: str, time_array: np.ndarray,
                                 mode="mean", fill=np.nan):
        t_data = self.rigdata_raw[rig_data][self.time_type]
        v_data = self.rigdata_raw[rig_data]['report_value']

        n = len(time_array)
        left_window = np.empty(n)
        right_window = np.empty(n)

        # edges
        left_window[0] = (time_array[1] - time_array[0])/2
        right_window[0] = left_window[0]
        left_window[-1] = (time_array[-1] - time_array[-2]) / 2
        right_window[-1] = left_window[-1]

        # interior points
        left_window[1:-1] = (time_array[1:-1] - time_array[:-2]) / 2
        right_window[1:-1] = (time_array[2:] - time_array[1:-1]) / 2

        out = np.full(n, fill)
        for i, ti in enumerate(time_array):
            mask = (t_data >= ti - left_window[i]
                    ) & (t_data <= ti + right_window[i])
            if not mask.any():
                continue
            if mode == "mean":
                out[i] = np.nanmean(v_data[mask])
            elif mode == "sum":
                out[i] = np.nansum(v_data[mask])
            elif mode == "count":
                out[i] = np.sum(~np.isnan(v_data[mask]))
            elif mode == "rate":
                out[i] = np.sum(~np.isnan(v_data[mask])) / \
                    (left_window[i] + right_window[i])
            else:
                raise ValueError(f"Unknown mode: {mode}")
        return out
