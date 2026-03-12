# -*- coding: utf-8 -*-
"""
Created on Wed Oct 29 00:51:12 2025

@author: Maxwell
"""

import pickle
import numpy as np

with open('all_rois_traces.pkl', 'rb') as file:
    data = pickle.load(file)
