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

@dataclass
class Mouse:
    mouseid : str = '014-000'
    
    # All below are organized by classname
    mouse_behav_param_overrides : dict = field(default_factory = lambda : {})
    properties : dict = field(default_factory= lambda : {})
    history : list = field(default_factory = lambda : [])

@dataclass
class Behavior:
    # Premature Exits/Limits
    merit_limit : int = None
    merit : int = 0
    demerit_limit : int = None
    demerit : int = 0
    duration_limit : int = None
    duration_min : int = None
    duration : float = None
    subdata_limit : int = None
    subdata_count : int = 0
    reward_limit : int = None
    rewards : int = 0
    abstention_limit : int = None
    abstention : int = 0
    participation : int = 0
    participation_limit : int = None
    serial_abstention_limit : int = None
    serial_abstention : int = 0
    
    stop_reason : list = field(default_factory=lambda:[])
    
    # Default properties
    starttime : float = field(default_factory = lambda : time.time())
    endtime : float = field(default_factory = lambda : time.time())
    
    # Properties
    name : str = None
    log: list = field(default_factory=lambda: [])
    properties : dict = field(default_factory = lambda : {}) #context for the trial
    report : dict = field(default_factory = lambda : defaultdict(lambda : None)) #report of the events of a trial
    subdata : list = field(default_factory = lambda : [])
    
    # Control
    rig: any = None
    
    # Administrative/high level properties
    mouse: Mouse = None
    save: bool = True
    savedir : str = field(default_factory = lambda : os.path.join(os.getenv('LOCALAPPDATA'), 'Bandit'))
    filename : str = None
    
    @classmethod
    def get_children(cls):
        children = set()
        for subclass in cls.__subclasses__():
            children.add(subclass)
            children.update(subclass.get_children())
        return children
    
    def run(self):
        if self.name is None:
            self.name = self.__class__.__name__
        self.printlog(f'RUNNING {self.name}')
        if self.mouse is not None:
            if self.__class__ in self.mouse.mouse_behav_param_overrides:
                overrides = self.mouse.mouse_behav_param_overrides[self.name]
                self.printlog('MOUSE HAS OVERRIDES LOGGED')
                for param, val in overrides.items():
                    if param in self.__dict__:
                        self.__dict__[param] = val
                        self.printlog(f'OVERRIDE: {param} IS NOW {val}')
        self.starttime = time.time()
        self.loop()
        self.endtime = time.time()
        self.duration = self.endtime - self.endtime
        self.printlog(f'FINISHED {self.name}')
    
    def loop(self):
        raise NotImplementedError('Failed to implement self.loop()')
    
    def printlog(self, *msgs):
        t = time.time()
        for msg in msgs:
            self.log.append((t, msg))
        print(msg)
        return t
    
    def stoplog(self, stopreason, msg = None):
        t = time.time()
        self.stop_reason.append(stopreason)
        if msg is not None:
            self.printlog(f'STOP:{stopreason}', msg)
        return t
    
    def _printstate(self):
        print('-'*50)
        print(f'MERIT: {self.merit} / {self.merit_limit}')
        print(f'DEMERIT: {self.demerit} / {self.demerit_limit}')
        print(f'REWARD: {self.rewards} / {self.reward_limit}')
        print(f'PARTICIPATION: {self.participation} / {self.participation_limit}')
        print(f'ABSTENTION: {self.abstention} / {self.abstention_limit}')
        print(f'SERIAL ABSTENTION: {self.serial_abstention} / {self.serial_abstention_limit}')
        print(f'SUBDATA: {len(self.subdata)} / {self.subdata_limit}')
        print(f'DURATION: {self.duration} / {self.duration_limit}')
        print('-'*50)
    
    def log_subdata(self, data, report = False):
        self.subdata.append(data)
        self.subdata_count = len(self.subdata)
        self.log_merit(data['merit'])
        self.log_demerit(data['demerit'])
        self.log_reward(data['rewards'])
        self.log_abstention(data['abstention'])
        self.log_serialabstention(data['abstention'])
        self.evaluatestopconditions()
        if report:
            self._printstate()
        
        
    def evaluatestopconditions(self):
        self.duration = time.time() - self.starttime
        if self.reward_limit is not None:
            if self.rewards >= self.reward_limit:
                self.stoplog('reward', f'Number of rewards given has reached limit of {self.reward_limit}')
        if self.duration_min is not None:
            if self.duration < self.duration_min:
                return
        if self.subdata_limit is not None:
            if self.subdata_count >= self.subdata_limit:
                self.stoplog('subdata',f'Reached limit of {self.subdata_limit} tasks')
        if self.duration_limit is not None:
            if self.duration >= self.duration_limit:
                self.stoplog('duration',f'Run duration has exceeded limit of {self.duration_limit} seconds')
        if self.merit_limit is not None:
            if self.merit >= self.merit_limit:
                self.stoplog('merit', f'Number of merits has reached target of {self.merit_limit}')
        if self.demerit_limit is not None:
            if self.demerit >= self.demerit_limit:
                self.stoplog('demerit',f'Number of demerits has reached limit of {self.demerit_limit}')
        if self.participation_limit is not None:
            if self.participation >= self.participation_limit:
                self.stoplog('participation', f'Number of participations has reached limit of {self.participation_limit}')
        if self.abstention_limit is not None:
            if self.abstention >= self.abstention_limit:
                self.stoplog('abstention', f'Number of abstentions has reached limit of {self.abstention_limit}')
        if self.serial_abstention_limit is not None:
            if self.serial_abstention >= self.serial_abstention_limit:
                self.stoplog('serialabstention',f'Number of serial abstentions has reached limit of {self.serial_abstention_limit}')
    
    def log_reward(self, increment = 1):
        self.rewards += increment
        
    def log_merit(self, increment = 1):
        self.merit += increment
        self.participation += increment
    
    def log_demerit(self, increment = 1):
        self.demerit += increment
        self.participation += increment
    
    def log_abstention(self, increment = 1):
        self.abstention += increment
    
    def log_serialabstention(self, increment = 1):
        if increment:
            self.serial_abstention += 1
        else:
            self.serial_abstention = 0
    
    def dump(self):
        if self.save:
            savefilepath = self.savedir
            filename = '_'.join([self.name,
                                datetime.fromtimestamp(self.starttime).strftime("%Y-%m-%d_%H-%M-%S")])
            filename += '.behav.lmp'
            self.printlog(f'SAVED: {self.name}',
                          f'\tTO ...{savefilepath[-40:]}',
                          f'\tAS {filename}')
            self.filename = filename
            self.savedir = savefilepath
        else:
            self.printlog(f'WARNING: Autosave is disabled for {self.name}')
        all_data = {key: val for key, val in self.__dict__.items()
                    if key not in ['rig', 'mouse', 'parent', 'lampyr']}
        if self.mouse is not None:
            all_data['mouse'] = self.mouse.mouseid
        if self.rig is not None:
            all_data['rig'] = self.rig.data.get_report_snippet(self.starttime, self.endtime)
        if not self.save:
            return all_data
        
        os.makedirs(savefilepath, exist_ok=True)
        
        with open(os.path.join(savefilepath,filename),'w') as file:
            json.dump(all_data, file, indent=2)
        
        return all_data