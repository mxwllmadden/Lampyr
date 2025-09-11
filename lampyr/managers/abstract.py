# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 18:40:48 2025

@author: mm4114
"""
from lampyr.config import Config

class AbstractManager():
    def __init__(self, lampyr = None, config = None):
        if lampyr is not None:
            self.config = lampyr.config
            self._input_func = lampyr._input_func
            self._output_func = lampyr._output_func
            self.lampyr = lampyr
        if lampyr is None:
            if config is not None:
                self.config = config
            else:
                self.config = Config()
            self._input_func = input
            self._output_func = print
            self.lampyr = None
            
        self.start()
    
    def start(self):
        pass