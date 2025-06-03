# -*- coding: utf-8 -*-
"""
Created on Thu May 22 15:48:30 2025

@author: mxwll
"""

from lampyr import config
from copy import deepcopy
import os
import json
from dataclasses import dataclass
from lampyr.primatives import Mouse


class Manager:
    def __init__(self, config):
        self.config = config


class ConfigManager:
    DEFAULT_CONFIG = {'lampyr': {'configured': False,
                                 'mice_directory': 'N:/Maxwell/Labwork/Data_All'},
                      'rig': {'calibrated': 0,
                              'sipper_calib': 40000}
                      }
    WDIR = os.path.join(os.getenv('LOCALAPPDATA'), 'lampyr')
    CONFIG_FILE = os.path.join(WDIR, 'config.json')

    def __init__(self):
        self.wdir = self.WDIR
        self.config_file = self.CONFIG_FILE
        self.load()
    
    @property
    def config(self):
        if self._config is None:
            self._config = self.load()
        return deepcopy(self._config)
    
    @property
    def configured(self):
        return self._config['lampyr']['configured']
    
    @configured.setter
    def configured(self, value : bool):
        if not isinstance(value, bool):
            raise KeyError('Value must be bool')
        self._config['lampyr']['configured'] = value

    @property
    def micedir(self):
        return self._config['lampyr']['mice_directory']

    @micedir.setter
    def micedir(self, value):
        if not isinstance(value, str):
            raise KeyError('Value must be string')
        self._config['lampyr']['mice_directory'] = value

    def load(self):
        os.makedirs(self.wdir, exist_ok=True)
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self._config = config
            return
        self._config = deepcopy(self.DEFAULT_CONFIG)

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)


class MouseManager(Manager):
    def list(self):
        folders = os.listdir(self.config.micedir)
        mice = {}
        for mouseid in folders:
            mousedatafilepath = os.path.join(self.config.micedir,
                                             mouseid,
                                             f'{mouseid}.mouse.lmp'
                                             )
            if os.path.exists(mousedatafilepath):
                mice[mouseid] = mousedatafilepath
        return list(mice.keys()), mice

    def create(self, mouseid):
        pass

    def path(self, mouseid):
        return os.path.join(self.config.config['lampyr']['mice_directory'],
                            mouseid,
                            f'{mouseid}.mouse.lmp')

    def load(self, mouseid):
        if not self.exists(mouseid):
            return None
        with open(self.path(mouseid), 'r') as f:
            mousedat = json.load(f)
        self.mouse = Mouse(**mousedat)

    def exists(self, mouseid):
        return os.path.exists(self.path(mouseid))


class RunManager(Manager):
    pass


class DataManager(Manager):
    pass


class Lampyr:
    def __init__(self):
        # Should take behavior and mouse and run everything then do file cleanup
        self.config = ConfigManager()
        self.mouse = MouseManager(self.config)
        self.run = RunManager(self.config)

    def clean(self):
        pass


if __name__ == '__main__':
    lamp = Lampyr()
    lamp.config.micedir = r'C:\Users\mxwll\Huda NAS Maxwell Folder\Labwork\Data_All'
    lamp.config.save()
    print(lamp.mouse.list()[0])
