# -*- coding: utf-8 -*-
"""
Created on Thu May 22 15:48:30 2025

@author: mxwll
"""

from copy import deepcopy
import os
import json
from dataclasses import dataclass
from lampyr.primatives import Mouse, Behavior, BehaviorSession
from lampyr.config import ConfigManager
import numpy as np
from lampyr.rigcontrol import ArduinoBanditRig_0, SerialMonitor
import time


class MouseManager():
    def __init__(self, config):
        self.mouse = None
        self.config = config
        
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
            self.mouse = None
        with open(self.path(mouseid), 'r') as f:
            mousedat = json.load(f)
        self.mouse = Mouse(**mousedat)

    def exists(self, mouseid):
        return os.path.exists(self.path(mouseid))
    
    def save(self):
        pass

class RigManager():
    def __init__(self, config):
        self.config = config
        self.rig = None
        self.connected = False
        
    def connect(self):
        print('Connecting to Arduino Rig...')
        rig = ArduinoBanditRig_0()
        print('Creating serial monitor thread...')
        rig.listen()
        print('Setting stored rig sipper calibration...')
        rig.reward.setsize(self.config.rig_sippercalibration)
        self.rig = rig
        self.connected = True
    
    def disconnect(self):
        print('Closing monitoring thread...')
        self.rig.abort()
        time.sleep(2)
        print('Disconnecting from Arduino Rig...')
        self.rig.close()
        self.connected = False
        
    def calibrate(self):
        if not self.connected:
            self.connect()
        def linreg(x,y):
            x = np.asarray(x)
            y = np.asarray(y)
            a, b = np.polyfit(x, y, 1)
            y_pred = a * x + b
            r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2)

            return a, b, r2
        
        def inputfloat(prompt):
            while True:
                val = input(prompt)
                try:
                    number = float(val)
                    break
                except ValueError:
                    print("Please enter a valid number.")
            return number
        
        def calib_disp(disp_size):
            disp_size=int(disp_size)
            self.rig.reward.setsize(disp_size)
            initial_value = inputfloat('INPUT CURRENT WATER LEVEL (ml): ')
            time.sleep(0.1)
            for i in range(20):
                self.rig.reward.give()
                time.sleep(0.4)
            dvol = (initial_value - inputfloat('NEW WATER LEVEL (ml):'))/20
            print(f'Reward Size: {disp_size} produces {str(dvol)[:10]} ml reward')
            return dvol
        
        while True:
            print('\nBEGINING CALIBRATION')
            dsizes = [20000,30000,50000]
            dvols = []
            for disp_size in dsizes:
                dvol = calib_disp(disp_size)
                dvols.append(dvol)
            slope, coeff, r2 = linreg(dsizes, dvols)
            if r2 < 0.9:
                print('Failed to produce linear regression. Repeating Calibration.')
                continue
            est_sipp = int((0.005 - coeff) / slope)
            print(f'Estimated correct reward size is {est_sipp}')
            print('Beginning dispenser test...')
            dvol = calib_disp(est_sipp)
            if abs(0.005 - dvol) < 0.0005:
                break
            else:
                print('Calibration failed. Repeating calibration.')
        print('Calibration success')
        print(f'Rig reward size is set to {est_sipp}')
        self.config.rig_sippercalibration = est_sipp


class Lampyr:
    def __init__(self):
        self.subdata = []
        self.name = 'Lampyr'
        
        self.config = ConfigManager()
        self.rigmanager = RigManager(self.config)
        self.mousemanager = MouseManager(self.config)
        self.behaviors = {c.__name__ : c for c in Behavior.get_children()}
        print('instantiated')
    
    @property
    def rig(self):
        return self.rigmanager.rig
    
    @property
    def mouse(self):
        return self.mousemanager.mouse
    
    def _number_of_parents(self, order = 0):
        return order + 1
    
    def run(self, behavior = None, **kwargs):
        if self.config.rig_lastcalibrated < 43200:
            print('Rig has not been calibrated in > 12 hours')
            return
        if not self.rigmanager.connected:
            self.rigmanager.connect()
        if self.mouse is not None:
            pass
        if behavior not in self.behaviors:
            raise KeyError('Not a valid behavior')
        behav = self.behaviors[behavior](parent = self,
                                         sessiondata = BehaviorSession(**kwargs)
                                         )
        behav.run()
        
    def close(self):
        self.rigmanager.disconnect()
        self.config.save()
        self.mouse.save()


if __name__ == '__main__':
    try:
        lamp = Lampyr()
    finally:
        lamp.close()
