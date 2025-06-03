# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 16:46:19 2025

@author: mm4114
"""

import sys, serial, argparse, time, glob, os, threading, queue
import json
from pathlib import Path
from serial.tools import list_ports
from dataclasses import dataclass, field, asdict

sys.argv = ['bandit_task_v0.0.0.py',
            '-m', '014-000',
            '-wd', r'N:\Maxwell\Labwork\Data_All']
BAUD_RATES = [9600, 115200]

def run_bandit(interactive = False, **kwargs):
    state = ProgramState(**kwargs)
    mouse = get_mouse(mouseid = state.mouseid,
                      workingdir = state.workingdir)
    return
    bandit = BanditTask(mouse, state.behavior_stage)
    bandit.report()
    if interactive:
        state = manual_parameter_edits(state, mouse)
    bandit.run()
    
    
# PROGRAM STATE, OPERATION, AND DATA
@dataclass
class ProgramState:
    mouseid : str = None
    workingdir : str = None
    behavior_stage_override : str = None
    newmouse : bool = False

@dataclass
class Mouse:
    mouseid : str = 'Dummy'
    variant : str = 'Base'
    stage : str = 'Hab'
    meritdemerit : list = field(default_factory=lambda : [])

def get_mouse(mouseid, workingdir):
    mpath = os.path.join(workingdir, mouseid)
    mdatpath = os.path.join(mpath,f'{mouseid}_data.json.cwurm')
    session_data = glob.glob(os.path.join(mpath,'*.h5.cwurm'))
    if not os.path.exists(mdatpath):
        with open(mdatpath, 'w') as file:
            mouse = Mouse()
            json.dump(asdict(mouse),file, indent=2)
    else:
        with open(mdatpath, 'r') as file:
            mdat = json.load(file)
            mouse = Mouse(**mdat)
    return mouse
        
@dataclass
class SessionData:
    serialinputs : list = field(default_factory=lambda : [])
    
# THE ACTUAL BANDIT TASK AND ALL VARIANTS
# TRANSITIONS BETWEEN BANDIT SESSION TYPES HANDLED BY BANDIT TASK

class BanditTask:
    variants = {'Base' : {'stages' : []}
                }
    def __init__(self, mouse, task_stage = None, variant = 'Base'):
        self.task_stage = task_stage
        self.state = 'Idle'
        
        self.session_start = time.time()
        self.trial_start = time.time()
        self.stage_start = time.time()
    
    def run(max_trials = 100):
        pass

class Bandit_Session:
    def __init__(self):
        pass
    
    def run(self):
        trial = Bandit_Trial(self.trial_params())
    
    def trial_params(self):
        pass
    
    def check_transitions(self):
        pass
    
class Bandit_Session_Habituation(Bandit_Session):
    def __init__(self):
        pass
    
class Bandit_Session_AnyResponse(Bandit_Session):
    def __init__(self):
        pass

class Bandit_Session_AlternatingSideResponse(Bandit_Session):
    def __init__(self):
        pass

@dataclass
class Bandit_Trial:
    pretrial_dur: int = 3
    pretrial_still_dur_sec: int = 2
    pretrial_still_penalty: int = 1
    pretrial_still_threshold_deg: int = 5
    trial_start_tone_hz: int = 4000
    reward: bool = True
    rewarded_responses: tuple = (-15, 15)
    reward_probabilities: tuple = (80, 10)
    reward_tone_hz: int = 10000
    trial_start_time = None
    
    def run(self):
        self.trial_start = time.time()
        # PretrialLoop
        while True:
            pass

# HARDWARE INTERACTION AND CONTROL
class SerialMonitor:
    def __init__(self):
        self.ser = None
        self.find_device()
        
    def find_device(self):
        if self.ser is not None:
            print('DEVICE SERIAL OVERWRITE ATTEMPTED!!!! SOMETHING IS WRONG!!!!')
            return
        ports = list_ports.comports()
        ports = [p for p in ports if 'Arduino' in p.description]
        for port in ports:
            print(f'Identified potential Arduino device: {port.description}')
            for baud in BAUD_RATES:
                print(f'Attempting to connect with baud {baud}')
                with serial.Serial(port.device, baud, timeout = 1) as ser:
                    time.sleep(2)
                    ser.write(bytes([255]))
                    response = ser.readline().decode(errors='ignore').strip()
                if response == bytes([255]):
                    print('Successful serial connection established')
                    self.ser = serial.Serial(port.device, baud, timeout = 1)
                    return
        raise serial.SerialException('No compatible arduino device found')
    
    def listen(self, queue):
        self.serial_queue
        theading.Thread(target = self._listener, daemon = True).start()

# ALL INTERACTION WITH USER
def manual_parameter_edits(state, mouse):
    
    return state

def setup(**kwargs):
    state = ProgramState(interactive = True, **kwargs)

def bandit_parse():
    parser = argparse.ArgumentParser()
    
    # arguments
    parser.add_argument('-m','--mouseid',
                        required = True,
                        type = str,
                        help = 'ID of the Mouse')
    parser.add_argument('-wd', '--workingdir',
                        type = str,
                        help = '')
    parser.add_argument('-s', '--behavior_stage',
                        type = str,
                        help = 'Training Stage')
    parser.add_argument('--newmouse',
                        action = 'store_true',
                        help = 'If specified creates mouse if it does not exist')
    
    args = vars(parser.parse_args())
    
    run_bandit(**args)

if __name__ == '__main__':
    bandit_parse()