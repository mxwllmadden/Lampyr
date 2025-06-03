# -*- coding: utf-8 -*-
"""
Created on Wed May  7 14:59:29 2025

@author: mm4114
"""

import argparse
import sys
from bandit_task_utils import *

sys.argv = ['bandit_task_v0.0.0.py',
            '014-000',
            '-s','hab']

WORKINGDIRECTORY = 'N:\\Maxwell\\Labwork\\Data_All\\'

def run_bandit_interactive():
    mouseid = input('MouseID: ')
    session = input('Session Type: ')
    
    run_bandit(mouseid = mouseid, session = session)

def run_bandit(interactive = True, **kwargs):
    pass
            
class Bandit():
    def __init__(self, mouse, session):
        self.mouse = mouse
        self.session = session
        self.ser_monitor = SerialMonitor()
    
    def run():
        pass


def bandit_parse():
    parser = argparse.ArgumentParser()
    
    # arguments
    parser.add_argument('mouseid',
                        type = str,
                        help = 'ID of the Mouse, include the hyphernm')
    parser.add_argument('-s', '--session',
                        required = True,
                        type = str,
                        help = 'Training Stage')
    
    kwargs = vars(parser.parse_args())
    
    run_bandit(interactive = False, **kwargs)

if __name__ == '__main__':
    bandit_parse()