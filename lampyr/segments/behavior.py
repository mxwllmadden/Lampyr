# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 17:21:59 2025

@author: mm4114
"""
from dataclasses import dataclass, field
import time
from copy import deepcopy
from typing import Callable, List, Literal
from abc import ABC, abstractmethod

from lampyr.primatives import Mouse, Session, uniqueid
from lampyr.segments.abstract import Segment

@dataclass
class BehaviorSegment(Segment):
    """
    Behavior segments adds as setup loop configuration that respects session stopconditions
    and supports tag and class based overrides by mouse

    Also adds:
        PROPERTIES
        REPORTS
        TAGS
    """
    # Context
    properties: dict = field(default_factory=dict)  # Inherited from parents
    tags: List[str] = field(default_factory=list)  # Inherited from parents
    # Describe the results of the segment
    reports: dict = field(default_factory=dict)

    # Reasons for stopping the session
    stop_reasons: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self._checkoverrides()
        

    def _configure(self):
        super()._configure()
        self._parent_inheritproperties_combine += ['tags']

    def execute(self):
        self.setup()
        while True:
            self.stop_reasons += self.session.evaluatestopconditions()
            if self.stop_reasons:
                break
            self.loop()
    
    @abstractmethod
    def setup(self):
        pass
        
    @abstractmethod
    def loop(self):
        pass

    def finish(self):
        self.stop_reasons.append('finished')
    
    def log_merit(self, increment=1):
        if self.session:
            self.session.merit += increment
            self.log_participation(increment)
            self.log_debug(f'Merit +{increment} → {self.session.merit}.')

    def log_demerit(self, increment=1):
        if self.session:
            self.session.demerit += increment
            self.log_participation(increment)
            self.log_debug(f'Demerit +{increment} → {self.session.demerit}.')

    def log_abstention(self, increment=1):
        if self.session:
            self.session.abstention += increment
            self.session.serial_abstention += increment
            self.log_debug(
                f'Abstention +{increment} → {self.session.abstention}.')
            self.log_debug(
                f'SerialAbstention +{increment} → {self.session.serial_abstention}.')

    def log_participation(self, increment=1):
        if self.session:
            self.session.participation += increment
            self.session.serial_abstention = 0
            self.log_debug(
                f'Participation +{increment} → {self.session.participation}. SerialAbstention reset.')

    def log_reward(self, increment=1):
        if self.session:
            self.session.rewards += increment
            self.log_debug(f'Reward +{increment} → {self.session.rewards}.')

    def log_trial(self, increment=1):
        if self.session:
            self.session.trial += increment
            self.log_debug(f'Trial +{increment} → {self.session.trial}.')

    def create_report(self, key, value):
        if key in self.reports:
            self.log_warning(f'Overwrote {key} as {value}. This is not recommended behavior.')
        self.reports[key] = value

    def _applyoverrides(self, overrides: dict):
        for param, val in overrides.items():
            if hasattr(self, param):
                setattr(self, param, val)

    def _checkoverrides(self):
        if self.mouse is None:
            return
        if 'all' in self.mouse.mouse_behav_param_overrides:
            overrides = self.mouse.mouse_behav_param_overrides['all']
            self.log_debug(f'Applying {len(overrides)} overrides')
            self._applyoverrides(overrides)
        if self.slug in self.mouse.mouse_behav_param_overrides:
            overrides = self.mouse.mouse_behav_param_overrides[self.slug]
            self.log_debug(f'Applying {len(overrides)} overrides associated with ' +
                          f'{self.slug} slug')
            self._applyoverrides(overrides)
        for tag in self.tags:
            if tag in self.mouse.mouse_behav_param_overrides:
                overrides = self.mouse.mouse_behav_param_overrides[tag]
                self.log_debug(f'Applying {len(overrides)} overrides associated with ' +
                              f'{tag} tag')
                self._applyoverrides(overrides)
                
@dataclass
class Task(BehaviorSegment):
    """
    Implements methods for trawling for trial data and extracting aggregate information
    """


@dataclass
class Trial(BehaviorSegment):
    """
    Implements event registration and interaction with rig and session to record actions
    """
    event_definitions: dict = field(default_factory=dict)
    event_records: list = field(default_factory=list)
    _events: dict = field(default_factory=dict)

    def register_event(self, name: str,
                       callback: Callable = lambda *args, **kwargs: None,
                       description: str = None):
        if name in self._events:
            raise RuntimeError(f'{name} already exists')
        self._events[name] = callback
        self.event_definitions[name] = {'description': description,
                                        'callback': callback.__repr__()}

    def trigger_event(self, event, *args, **kwargs):
        if event not in self._events:
            self.log_error(f'Attempted to trigger <{
                           event}> which is not a registered event.')
            return
        t = self.log_debug(f'Event <{event}> has been triggered')
        try:
            self._events[event](self, *args, **kwargs)
        except TypeError:
            self.log_error(f'Failed to trigger <{
                           event}> due to incorrect arguments. Event callbacks should accept segment as first argument then *args **kwargs.')
        self.event_records.append({'time': t,
                                   'event': event,
                                   'args': args,
                                   'kwargs': kwargs})
        self.session.eventlist.append({'segment': self.uniqueid,
                                       'time': t,
                                       'event': event,
                                       'args': args,
                                       'kwargs': kwargs})
        return t
    
    def execute(self):
        self.setup()
        while True:
            if self.stop_reasons:
                break
            self.loop()
        self.log_trial()
        
    def _configure(self):
        super()._configure()
        self._dump_reducetorepresentations += ['event_definitions']
