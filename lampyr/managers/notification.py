# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 18:44:53 2025

@author: mm4114
"""

from lampyr.managers.abstract import AbstractManager
from lampyr.primatives import NestedConfig
from lampyr.managers.data import loadjson, savejson

class NotificationManager(AbstractManager):
    def start(self):
        self.user = self.config.get('notifications.last_user')
        self.userdata = self.config.load_extended_config('users.json')
    
    def add_user(self, name, service, apiid):
        pass
        