# -*- coding: utf-8 -*-
"""
Created on Mon May 26 16:49:26 2025

@author: mm4114
"""
import time
from dataclasses import dataclass
import random
from lampyr.primatives import Behavior

@dataclass
class HabituationTrial(Behavior):
    prerewardduration: int = 5
    maxpostrewardduration: int = 5
    minpostrewardduration: int = 2

    def loop(self):
        self.printlog('TS0s', 'Trial Start')
        time.sleep(self.prerewardduration)
        rewardtime = self.printlog('REWARD', 'Reward given')
        self.rig.play.rewardtone()
        self.rig.reward.give()
        licked = self.loop_lickmonitor()
        if not licked:
            self.log_abstention()
            self.printlog('No lick detected')
        else:
            self.log_merit()
            print('Reward was licked')
        self.printlog('TS0e', 'Trial End')
        self.stoplog('finished')
    
    def loop_lickmonitor(self):
        slick = time.time()
        lastlicktest = time.time()
        licked = False
        while time.time() - slick < self.maxpostrewardduration:
            if self.rig.licks.since(lastlicktest):
                print('lick!')
                licked = True
            lastlicktest = time.time()
            if licked == True and time.time() - slick > self.minpostrewardduration:
                break
            time.sleep(0.01)
        return licked


@dataclass
class RewardedHabituationTask(Behavior):
    serial_abstention_limit : int = 25
    reward_limit : int = 200
    
    def loop(self):
        while True:
            if self.stop_reason:
                break
            trial = HabituationTrial(name=f'{self.name}_Trial{len(self.subdata)}',
                                     rig=self.rig,
                                     mouse=self.mouse,
                                     save=self.save,
                                     properties=self.properties,
                                     prerewardduration=random.randint(1, 5),
                                     maxpostrewardduration=45)
            trial.run()
            trialdata = trial.dump()
            self.log_subdata(trialdata)
            del trial

    def evaluate_trial(self, trial):
        pass