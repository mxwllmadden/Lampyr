# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 17:32:31 2025

@author: mm4114
"""

from dataclasses import dataclass
from lampyr.segments.abstract import Segment

@dataclass
class ControlSegment(Segment):
    pass

@dataclass
class Shaper(ControlSegment):
    def execute(self):
        pass

@dataclass
class ScopedSegment(ControlSegment):
    pass