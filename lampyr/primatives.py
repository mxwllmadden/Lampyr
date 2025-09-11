# -*- coding: utf-8 -*-
"""
Created on Tue Jun 24 11:33:55 2025

@author: mm4114
"""

from dataclasses import dataclass, field
import time
from copy import deepcopy
from typing import List
import random

def uniqueid(type, name = None):
    uid = f'{type}_'
    if name is not None:
        uid += f'{name}_'
    uid += f'created{round(time.time())}_{random.randint(0, 999999):06d}'
    return uid

@dataclass
class Mouse:
    mouseid: str = '014-000'
    mouse_behav_param_overrides: dict = field(default_factory=dict)
    paradigm: str = None
    properties: dict = field(default_factory=dict)
    history: List = field(default_factory=list)

@dataclass
class Session:
    # Session limits and minimums
    merit_limit: int = None
    merit_min: int = None
    merit: int = 0
    demerit_limit: int = None
    demerit_min: int = None
    demerit: int = 0
    duration_limit: int = None
    duration_min: int = None
    duration: float = None
    trial_limit: int = None
    trial_min: int = None
    trial: int = 0
    reward_limit: int = None
    reward_min: int = None
    rewards: int = 0
    abstention_limit: int = None
    abstention_min: int = None
    abstention: int = 0
    participation_limit: int = None
    participation_min: int = None
    participation: int = 0
    serial_abstention_limit: int = None
    serial_abstention_min: int = None
    serial_abstention: int = 0
    
    # General information
    starttime: float = field(default_factory=time.time)
    endtime: float = None
    uniquesessionid : str = field(default_factory=lambda : uniqueid('session'))
    
    # Mouseid
    mouseid : str = None
    mouseid_unique : str = None
    
    # Segment records
    root : str = None
    segmentlist : list = field(default_factory=list)
    segments : dict = field(default_factory = dict)
    
    # Session Events and rig data
    eventlist : List = field(default_factory=list)
    rigdata : dict = None
    
    def __setattr__(self, key, value):
        if hasattr(self, "endtime") and self.endtime is not None:
            raise RuntimeError(f"Cannot modify '{key}'; session is finalized.")
        super().__setattr__(key, value)
    
    def lock(self):
        self.endtime = time.time()
    
    def __repr__(self):
        fields = [
            ("merit", self.merit_min, self.merit_limit, self.merit),
            ("demerit", self.demerit_min, self.demerit_limit, self.demerit),
            ("duration", self.duration_min, self.duration_limit, round(self.duration,2)),
            ("trial", self.trial_min, self.trial_limit, self.trial),
            ("reward", self.reward_min, self.reward_limit, self.rewards),
            ("abstention", self.abstention_min, self.abstention_limit, self.abstention),
            ("participation", self.participation_min, self.participation_limit, self.participation),
            ("serial_abstention", self.serial_abstention_min, self.serial_abstention_limit, self.serial_abstention),
        ]
        msg = ''
        for name, min_val, max_val, val in fields:
            msg += f"{name:22}: {str(val):6} (Min: {str(min_val):6} Max: {str(max_val):6})\n"
        msg += f"{'starttime':22}: {self.starttime}\n"
        msg += f"{'endtime':22}: {self.endtime}\n"
        msg += f"{'uniquesessionid':22}: {self.uniquesessionid}\n"
        msg += f"{'mouseid':22}: {self.mouseid}\n"
        msg += f"{'mouseid_unique':22}: {self.mouseid_unique}\n"
        return msg
    
    def extract_reports(self):
        pass
    
    def search(self, root = None, 
               type = None, types = None,
               slug = None, slugs = None,
               _seglist = None):
        if _seglist is None:
            _seglist = []
        if root is None:
            root = self.root
        segment = self.segments[root]
        
        def search_filter(singleton, multioption, target):
            if singleton is None and multioption is None:
                return True
            if not isinstance(target, (list, tuple, set)):
                target = [target]
            if singleton is not None:
                if singleton not in target:
                    return False
            if multioption is not None:
                for option in multioption:
                    if option in target:
                        return True
                return False
            return True
        
        valid = search_filter(type, types, segment['segment_type'])
        valid = valid and search_filter(slug, slugs, segment['slug'])
        if valid:
            _seglist.append(root)
        for subseg in segment['subdata']:
            _ = self.search(subseg, 
                            type, types, 
                            slug, slugs,
                            _seglist = _seglist)
        return _seglist
    
    def searchself(self, root, *args, **kwargs):
        all_finds = []
        for segment in root.subdata:
            all_finds += self.search(segment,*args, **kwargs)
        return all_finds

    def evaluatestopconditions(self):
        stops = []
        if self.endtime is None:
            self.duration = (time.time() - self.starttime) / 60
        duration = self.duration
        
        # Reward limits are privileged to avoid senarios where water restriction is broken
        if self.reward_limit is not None:
            if self.rewards >= self.reward_limit:
                stops.append('reward')
        
        # All minimum requirements must be met before limits are tested
        if self.trial_min is not None:
            if self.trial < self.trial_min:
                return stops
        if self.duration_min is not None:
            if duration < self.duration_min:
                return stops
        if self.participation_min is not None:
            if self.participation < self.participation_min:
                return stops
        if self.merit_min is not None:
            if self.merit < self.merit_min:
                return stops
        if self.demerit_min is not None:
            if self.demerit < self.demerit_min:
                return stops
        if self.abstention_min is not None:
            if self.abstention < self.abstention_min:
                return stops
        if self.serial_abstention_min is not None:
            if self.serial_abstention < self.serial_abstention_min:
                return stops
        
        # Test all limits and report reasons for stop
        if self.trial_limit is not None:
            if self.trial >= self.trial_limit:
                stops.append('trial')
        if self.duration_limit is not None:
            if duration >= self.duration_limit:
                stops.append('duration')
        if self.merit_limit is not None:
            if self.merit >= self.merit_limit:
                stops.append('merit')
        if self.demerit_limit is not None:
            if self.demerit >= self.demerit_limit:
                stops.append('demerit')
        if self.participation_limit is not None:
            if self.participation >= self.participation_limit:
                stops.append('participation')
        if self.abstention_limit is not None:
            if self.abstention >= self.abstention_limit:
                stops.append('abstention')
        if self.serial_abstention_limit is not None:
            if self.serial_abstention >= self.serial_abstention_limit:
                stops.append('serialabstention')
        return stops



