# -*- coding: utf-8 -*-
"""
Created on Mon May 26 16:49:26 2025

@author: mm4114
"""
import time
from dataclasses import dataclass
import random
from lampyr.primatives import Task, Trial

@dataclass
class HabituationTrial(Trial):
    prerewardduration: int = 5
    maxpostrewardduration: int = 5
    minpostrewardduration: int = 2
    def loop(self):
        self.logevent('TS0s', 'Trial Start')
        time.sleep(self.prerewardduration)
        rewardtime = self.logevent('REWARD', 'Reward given')
        self.rig.play.rewardtone()
        self.rig.reward.give()
        licked = self.loop_lickmonitor()
        if not licked:
            self.logabstention()
            self.logevent('No lick detected')
        else:
            self.logmerit()
            self.logevent('Reward was licked')
        self.logevent('TS0e', 'Trial End')
        self.stop('finished')
    
    def loop_lickmonitor(self):
        slick = time.time()
        lastlicktest = time.time()
        licked = False
        while time.time() - slick < self.maxpostrewardduration:
            if self.rig.licks.since(lastlicktest):
                self.logevent('lick!')
                licked = True
            lastlicktest = time.time()
            if licked == True and time.time() - slick > self.minpostrewardduration:
                break
            time.sleep(0.01)
        return licked


@dataclass
class RewardedHabituationTask(Task):
    def loop(self):
        trial = HabituationTrial(parent = self,
                                 prerewardduration=random.randint(5, 15),
                                 maxpostrewardduration=45)
        trial.run()
        del trial