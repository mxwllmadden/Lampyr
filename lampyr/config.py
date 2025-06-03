# -*- coding: utf-8 -*-
"""
Created on Tue May 27 21:43:43 2025

@author: mm4114
"""
import os
import json

DEFAULT_CONFIG = {'lampyr': {'configured': False,
                             'mice_directory': 'N:/Maxwell/Labwork/Data_All'},
                  'rig': {'calibrated': 0,
                          'sipper_calib': 40000}
                  }
WDIR = os.path.join(os.getenv('LOCALAPPDATA'), 'lampyr')
CONFIG_FILE = os.path.join(WDIR,'config.json')

def load():
    os.makedirs(WDIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    else:
        config = DEFAULT_CONFIG
    return config

def save(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)