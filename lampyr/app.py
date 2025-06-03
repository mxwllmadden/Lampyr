# -*- coding: utf-8 -*-
"""
Created on Wed May 14 15:02:02 2025

@author: mm4114
"""

import argparse
import time
import os
import numpy as np
import lampyr
from lampyr import primatives, rigcontrol, Lampyr
from lampyr.tasks import bandit, habituation
from lampyr.rigcontrol import ArduinoBanditRig_0, SerialMonitor

def list_behaviors():
    print('-'*10+'Behaviors'+'-'*10)
    print(*sorted(primatives.BehaviorParadigm.get_children()), sep='\n')

def run_command(args, config, rig):
    behavs = {c.__name__ : c for c in primatives.Behavior.get_children()}
    if args.behavior not in behavs:
        print('Behavior not found')
        return
    mouse = args.mouse
    if mouse is not None:
        mouse = primatives.Mouse.load(os.path.join(config['lampyr']['mice_directory'], args.mouse))
        if mouse is None:
            mouse = primatives.Mouse(mouseid=args.mouse)
    mybehav = behavs[args.behavior](rig = rig, mouse = mouse)
    mybehav.run()
    mouse.save(os.path.join(config['lampyr']['mice_directory'],mouse.mouseid))

def rig_command(args, config, rig):
    pass

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

def rig_calibration(config, rig):
    def calib_disp(disp_size):
        disp_size=int(disp_size)
        rig.reward.setsize(disp_size)
        initial_value = inputfloat('INPUT CURRENT WATER LEVEL (ml): ')
        time.sleep(0.1)
        for i in range(20):
            rig.reward.give()
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
        print(f'Beginning dispenser test...')
        dvol = calib_disp(est_sipp)
        if abs(0.005 - dvol) < 0.0005:
            break
        else:
            print('Calibration failed. Repeating calibration.')
    print('Calibration success')
    print(f'Rig reward size is set to {est_sipp}')
    config['rig']['sipper_calib'] = est_sipp
    config['rig']['calibrated'] = time.time()

def rig_setup(config):
    print('Connecting to Arduino Rig...')
    rig = ArduinoBanditRig_0(SerialMonitor(115200))
    rig.listen()
    sipper_calib = config['rig']['sipper_calib']
    rig.reward.setsize(sipper_calib)
    print('Connected!')
    return rig

def main():
    parser = argparse.ArgumentParser(prog = 'lampyr')
    subparsers = parser.add_subparsers(dest = 'command')
    
    #standard cwurm commands
    subparsers.add_parser('list')
    subparsers.add_parser('info')
    subparsers.add_parser('setup')
    
    #rig commands
    rigparser = subparsers.add_parser('rig')
    rig_subparsers = rigparser.add_subparsers(dest='rig_command')
    rig_calib_parser = rig_subparsers.add_parser('calibrate')
    rig_calib_parser.add_argument('-c', '--check', action='store_true', help = 'Test current calibration')
    rig_subparsers.add_parser('set')
    
    #cwurm run X
    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('behavior')
    run_parser.add_argument('-m', '--mouse')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_behaviors()
        return
    
    config = lampyr.config.load()
    rig = rig_setup(config)
    try:
        if args.command == 'rig' and args.rig_command == 'calibrate':
            rig_calibration(config, rig)
            return
        if time.time() - config['rig']['calibrated'] > 64800:
            print('WARNING! Rig has not been calibrated in more than 18 hours. Run lampyr rig calibrate')
            return
        if args.command == 'rig' and args.rig_command != 'calibrate':
            rig_command(args, config, rig)
        if args.command == 'run':
            run_command(args, config, rig)
    finally:
        lampyr.config.save(config)
        rig.abort()
        rig.close()

if __name__ == "__main__":
    main()