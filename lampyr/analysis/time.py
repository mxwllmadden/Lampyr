# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 14:26:35 2026

@author: mm4114
"""
import time

import numpy as np

from scipy.interpolate import interp1d

from lampyr.primatives import Session

from typing import Iterable, Union

def createtimereporter():
    start = time.time()

    def report(prefix):
        nonlocal start
        now = time.time()
        dur = now - start
        print(f'{prefix} ({dur:.1f} sec)')
        start = now
    return report

def create_dynamictimearray(points: Iterable[Union[float, int]],
                            samples: Iterable[int]):
    points = np.array(points, dtype=float)
    samples = np.array(samples, dtype=int)
    if len(points) - 1 != len(samples):
        raise ValueError("samples must have one less element than points")
    stretched = []
    for i in range(len(samples)):
        # Create linearly spaced points between consecutive points
        seg = np.linspace(points[i], points[i+1], samples[i], endpoint=False)
        stretched.append(seg)

    # Append the last point
    stretched.append([points[-1]])
    return np.concatenate(stretched)

def create_dynamictimearray_2d(points_2d: np.ndarray,
                               samples: Iterable[int]):
    newdim = sum(samples) + 1
    newarray = np.empty((points_2d.shape[0], newdim))
    for r, row  in enumerate(points_2d):
        newarray[r,:] = create_dynamictimearray(row, samples)
    return newarray

class TimeTranslator:
    def __init__(self, session: Session,
                 target=None,
                 source=None,
                 kind='linear',
                 fill_value='extrapolate'):
        self.default_source = source
        self.default_target = target
        self._kind = kind
        self._fill_value = fill_value
        self._syncstream = session.rigdata['SyncStream'].copy()
        self._translators = {}

    def _convert(self, arg, source, target):
        if (source, target) not in self._translators:
            self._translators[(source, target)] = interp1d(
                self._syncstream[source],
                self._syncstream[target],
                kind=self._kind,
                fill_value=self._fill_value)
        return self._translators[(source, target)](arg)

    def convert(self, value, source=None, target=None):
        source = source or self.default_source
        target = target or self.default_target
        if source is None or target is None:
            raise ValueError('Source or Target not specified')
        return self._convert(value, source, target)



