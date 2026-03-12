# -*- coding: utf-8 -*-
"""
Created on Mon Sep 15 09:57:23 2025

@author: mm4114
"""

from lampyr.managers import DataHandler

dh = DataHandler()

print(dh.lampyr_mouseidtofilepaths('014-005'))
mouse = dh.lampyr_loadmouse('014-005')

for session in mouse.history:
    sessionid = session['id']
    try:
        print(dh.lampyr_loadsession('014-005', sessionid))
    except FileExistsError as e:
        pass