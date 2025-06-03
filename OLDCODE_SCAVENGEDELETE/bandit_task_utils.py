# -*- coding: utf-8 -*-
"""
Created on Wed May  7 15:06:17 2025

@author: mm4114
"""
import os, glob
import time
import json
import threading
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import serial
from serial.tools import list_ports 
import numpy as np

@dataclass
class Mouse:
    mouseid : str = 'Dummy'
    variant : str = 'Base'
    stage : str = 'Hab'
    meritdemerit : list = field(default_factory=lambda : [])
    
class Session():
    pass 

class Stage():
    pass


        
