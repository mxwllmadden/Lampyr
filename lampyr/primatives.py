# -*- coding: utf-8 -*-
"""
Created on Thu May 15 15:23:06 2025

@author: mm4114
"""
from dataclasses import dataclass, field, asdict
import time
import os
from datetime import datetime
from collections import defaultdict
from copy import deepcopy
import json
import glob
from typing import Callable


@dataclass
class Mouse:
    mouseid: str = '014-000'

    # All below are organized by classname
    mouse_behav_param_overrides: dict = field(default_factory=lambda: {})
    properties: dict = field(default_factory=lambda: {})
    history: list = field(default_factory=lambda: [])


@dataclass
class BehaviorSession:
    merit_limit: int = None
    merit: int = 0
    demerit_limit: int = None
    demerit: int = 0
    duration_limit: int = None
    duration_min: int = None
    duration: float = None
    trial_limit: int = None
    trial_min: int = None
    trial: int = 0
    reward_limit: int = None
    rewards: int = 0
    abstention_limit: int = None
    abstention: int = 0
    participation: int = 0
    participation_limit: int = None
    serial_abstention_limit: int = None
    serial_abstention: int = 0

    starttime: float = field(default_factory=time.time)
    endtime: float = field(default_factory=time.time)

    def evaluatestopconditions(self):
        stops = []
        self.duration = time.time() - self.starttime
        if self.reward_limit is not None:
            if self.rewards >= self.reward_limit:
                stops.append('reward')

        if self.duration_min is not None:
            if self.duration / 60 < self.duration_min:
                return stops
        if self.trial_min is not None:
            if self.trial < self.trial_min:
                return stops

        if self.trial_limit is not None:
            if self.trial >= self.trial_limit:
                stops.append('trial')
        if self.duration_limit is not None:
            if self.duration / 60 >= self.duration_limit:
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


@dataclass
class Behavior:
    # Metadata
    name: str = None
    mouse_overrides: bool = True
    tags: list = field(default_factory=list)
    frozen: bool = False
    istrial: bool = True
    save: bool = False

    # Data (peristant)
    mouse: Mouse = None
    sessiondata: BehaviorSession = None

    # Data (this behavior session)
    # report of the events of a trial
    reports: dict = field(default_factory=dict)
    debuglog: list = field(default_factory=list)
    eventlog: list = field(default_factory=list)  # Log all events
    datalog: list = field(default_factory=list)  # Log all edits to Data
    rigdata: list = None
    starttime: float = None
    endtime: float = None
    stop_reasons: list = field(default_factory=list)
    # Log outputs of any sub Behaviors
    subdata: list = field(default_factory=list)

    # Properties
    labels: dict = field(default_factory=dict)  # context for the trial
    name: str = None
    log: list = field(default_factory=list)
    # report of the events of a trial
    report: dict = field(default_factory=dict)
    subdata: list = field(default_factory=lambda: [])

    # Control
    rig: object = None
    parent: object = None
    parent_number : int = 0
    output_func: Callable = print

    @classmethod
    def get_children(cls):
        children = set()
        for subclass in cls.__subclasses__():
            children.add(subclass)
            children.update(subclass.get_children())
        return children

    def _applyoverrides(self, overrides: dict):
        for param, val in overrides.items():
            if param in self.__dict__:
                self.__dict__[param] = val
                self.logdebug(f'{param} was set to {val}')

    def __post_init__(self):
        if self.mouse is not None and self.mouse_overrides:
            if 'all' in self.mouse.mouse_behav_param_overrides:
                overrides = self.mouse.mouse_behav_param_overrides['all']
                self.logdebug(f'Applying {len(overrides)} overrides')
                self._applyoverrides(overrides)
            if self.__class__.__name__ in self.mouse.mouse_behav_param_overrides:
                overrides = self.mouse.mouse_behav_param_overrides[self.__class__.__name__]
                self.logdebug(f'Applying {len(overrides)} behavior overrides')
                self._applyoverrides(overrides)
            for tag in self.tags:
                if tag in self.mouse.mouse_behav_param_overrides:
                    overrides = self.mouse.mouse_behav_param_overrides[tag]
                    self.logdebug(f'Applying {len(overrides)} associated with ' +
                                  f'{tag} overrides')
                    self._applyoverrides(overrides)
        if self.parent is not None:
            try:
                order = self.parent.parent_number + 1
            except:
                order = 1
        else:
            order = 0
        self.parent_number = order

        if self.parent is not None:
            if self.name is None:
                self.name = (self.parent.name +
                             f'_subbehavior{len(self.parent.subdata)}_' +
                             self.__class__.__name__)
            if self.mouse is None:
                self.mouse = self.parent.mouse
            if self.sessiondata is None:
                self.sessiondata = self.parent.sessiondata
            if self.rig is None:
                self.rig = self.parent.rig
        if self.name is None:
            self.name = self.__class__.__name__

    def run(self):
        if self.frozen:
            raise RuntimeError(f'Attempted to run {self.name} more than once.\n' +
                               'Behavior objects must never be run twice.')
        self.logdebug(f'BEGIN: {self.name}')
        self.starttime = time.time()
        self.setup()
        while True:
            stops = self.sessiondata.evaluatestopconditions()
            if stops:
                self.stop(stops)
            if self.stop_reasons:
                break
            self.loop()
        self.endtime = time.time()
        if self.istrial:
            self.logtrial()
        self.rigdata = self.rig.data.get_report_snippet(self.starttime,
                                                        self.endtime)
        self.logdebug(f'END: {self.name}')
        self.frozen = True
        
        return self.dump()

    def setup(self):
        pass

    def loop(self):
        raise NotImplementedError('Failed to implement self.loop()')
    
    def output(self, *msgs):
        for msg in msgs:
            self.output_func(self.parent_number*'\t' + msg)

    def logdebug(self, *msgs):
        t = time.time()
        for msg in msgs:
            self.debuglog.append((t, msg))
            self.output(msg)
        return t

    def logevent(self, *msgs):
        t = time.time()
        for msg in msgs:
            self.eventlog.append((t, msg))
        self.output(msg)
        return t

    def logsessiondata(self, *msgs):
        t = time.time()
        for msg in msgs:
            self.datalog.append((t, msg))
        self.output(msg)
        return t

    def stop(self, *stopreasons):
        t = time.time()
        for stop in stopreasons:
            self.stop_reasons.append(stop)
            self.logdebug(f'STOP:{stop}')
        return t
    
    def report(self, report : str, value):
        self.reports[report] = value
        self.logdebug(f'Set report: {report} to {value}')

    def logtrial(self, increment=1):
        self.sessiondata.trial += increment
        self.logsessiondata(f'Incremented session trials by {increment}')

    def logreward(self, increment=1):
        self.sessiondata.rewards += increment
        self.logsessiondata(f'Incremented session reward by {increment}')

    def logmerit(self, increment=1):
        self.sessiondata.merit += increment
        self.logsessiondata(f'Incremented session merit by {increment}')
        self.logparticipation(increment)

    def logdemerit(self, increment=1):
        self.sessiondata.demerit += increment
        self.logsessiondata(f'Incremented session demerit by {increment}')
        self.logparticipation(increment)

    def logparticipation(self, increment=1):
        self.sessiondata.participation += increment
        self.logsessiondata(
            f'Incremented session participation by {increment}')
        self.sessiondata.serial_abstention = 0

    def logabstention(self, increment=1):
        self.sessiondata.abstention += increment
        self.logsessiondata(f'Incremented session abstentions by {increment}')
        self.sessiondata.serial_abstention += increment

    def dump(self):
        all_data = {key: val for key, val in self.__dict__.items()
                    if key not in ['rig', 'mouse', 'parent', 'output_func', 'sessiondata']}
        all_data['session'] = deepcopy(self.sessiondata.__dict__)
        all_data['mouse'] = 'No Mouse'
        if self.mouse is not None:
            all_data['mouse'] = self.mouse.mouseid
        if self.parent is not None:
            self.parent.subdata.append(all_data)
        return all_data

class Task(Behavior):
    istrial : bool = False

class Trial(Behavior):
    istrial : bool = True