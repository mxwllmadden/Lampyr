# -*- coding: utf-8 -*-
"""
Created on Wed May 14 15:02:23 2025

@author: mm4114
"""

import time
from dataclasses import dataclass, field
import random
from lampyr.primatives import Trial, Task


@dataclass
class BanditTaskTrial(Behavior):
    # Parameters
    iti_dur: float = 1
    pretrial_hold_s: float = 2
    pretrial_movementthresh_deg: int = 5
    trial_responsewindow_s: float = 3
    trial_responsethresholds_deg: dict = field(default_factory=lambda: {'Left': 15,
                                                                        'Right': 15}
                                               )
    trial_rewardprobs_perc: dict = field(default_factory=lambda: {'Left': 100,
                                                                  'Right': 100,
                                                                  'None': 0}
                                         )
    iti2_dur: float = 2.5
    
    def setup(self):
        self.trial_state = 'iti1'

    def loop(self):
        match self.trial_state:
            case _ if self.trial_state not in ('iti1', 'pretrial', 'trial', 'iti2'):
                self.stop('finished')
            case 'iti1':
                self.loop_iti1()
            case 'pretrial':
                self.loop_pretrial()
            case 'trial':
                self.loop_trial()
            case 'iti2':
                self.loop_iti2()

    def loop_iti1(self):
        self.logevent('TS0s', 'ITI START')
        time.sleep(self.iti_dur)
        self.logevent('TS0e', 'ITI END')
        self.trial_state = 'pretrial'

    def loop_pretrial(self):
        pretrial_start = self.logevent('TS1e', 'PRETRIAL START')
        while True:
            time.sleep(0.001)
            if time.time() - pretrial_start < self.pretrial_hold_s:
                continue
            wheel_movement = abs(
                self.rig.wheel.movement_total_since(time.time()-2))
            if wheel_movement < self.pretrial_movementthresh_deg:
                break
        self.logevent('TS1e', 'PRETRIAL END')
        self.trial_state = 'trial'

    def loop_trial(self):
        trial_start = self.logevent('TS2s', 'TRIAL START')
        self.rig.play.begintrialtone()
        response = False
        while not response:
            resp = self.rig.wheel.movement_since(trial_start)
            if resp < 0 and abs(resp) > self.trial_responsethresholds_deg['Left']:
                self.logevent('LR', 'Leftward response detected')
                response = 'Left'
            elif resp > 0 and abs(resp) > self.trial_responsethresholds_deg['Right']:
                self.logevent('RR', 'Rightward response detected')
                response = 'Right'
            elif response is False and time.time() - trial_start > self.trial_responsewindow_s:
                self.logevent('NR', 'No response detected')
                response = 'None'
            else:
                time.sleep(0.0001)
                continue
        self.report['response'] == response
        self.report['response_delay'] == trial_start - time.time()
        if response == 'None':
            self.log_abstention()

        highestrewardprob = max(
            [prob for prob in self.trial_rewardprobs_perc.values()])
        probability = self.trial_rewardprobs_perc[response]/100
        if self.trial_rewardprobs_perc[response] == highestrewardprob:
            self.report['best_response'] = True
            self.log_merit()
        else:
            self.report['best_response'] = False
            self.log_demerit()
        rand = random.random()
        self.logevent(f'RAND:{rand},THRESH:{probability}')
        if rand < probability:
            self.logevent('REWARD', 'Giving reward')
            self.rig.reward.give()
            self.rig.play.rewardtone()
            self.log_reward()
        else:
            self.logevent('NOREWARD', 'No reward given')
        self.logevent('TS2e', 'TRIAL END')
        self.trial_state = 'iti2'

    def loop_iti2(self):
        self.logevent('TS3s', 'ITI2 START')
        time.sleep(self.iti2_dur)
        self.logevent('TS3e', 'ITI2 END')
        self.trial_state = None


@dataclass
class BanditTask(Behavior):
    offtargetrewardprob: int = 10
    ontargetrewardprob: int = 80
    blockrewardsizerange: tuple = (6, 15)
    
    def setup(self):
        self.side = not random.randint(0, 1)
        self.blocknum = 0

    def loop(self):
        blocksize = random.randint(*self.blockrewardsizerange)
        self.side = not self.side
        self.loop_block(self.side, blocksize, self.blocknum)
        self.blocknum += 1

    def loop_block(self, side: bool, blocksize: int, blocknumber: int):
        side_selection = {True: {'Left': self.offtargetrewardprob,
                                 'Right': self.ontargetrewardprob,
                                 'None': 0},
                          False: {'Left': self.ontargetrewardprob,
                                  'Right': self.offtargetrewardprob,
                                  'None': 0}
                          }
        tnum = 0
        blockrewards = 0
        while True:
            if 'reward' in self.stop_reason or 'serialabstention' in self.stop_reason:
                break
            trial = BanditTaskTrial(name=f'{self.__class__.__name__}_{tnum}',
                                    rig=self.rig,
                                    mouse=self.mouse,
                                    parent=self,
                                    properties=self.properties,
                                    trial_rewardprobs_perc=side_selection[side])
            trial.properties['trial_in_block'] = tnum
            trial.properties['trial_in_session'] = len(self.subdata)
            trial.properties['block_in_session'] = blocknumber
            # run trial
            trial.run()
            # evaluate blockswitch
            if trial.rewards:
                blockrewards += 1
            if blockrewards >= blocksize:
                break
            # close trial and receive data
            trialdata = trial.dump()
            del trial
            self.log_subdata(trialdata, report=True)
            # Prepare for next loop
            tnum += 1


@dataclass
class AlternatingSideResponseTask(BanditTask):
    offtargetrewardprob: int = 0
    ontargetrewardprob: int = 100

@dataclass
class AnyWheelResponseTask(Behavior):
    def loop(self):
        while True:
            if self.stop_reason:
                break
            trial = BanditTaskTrial(name=f'{self.__class__.__name__}_{len(self.subdata)}',
                                    rig=self.rig,
                                    mouse=self.mouse,
                                    save=self.save,
                                    properties=self.properties)
            trial.properties['trial_in_session'] = len(self.subdata)
            # run trial
            trial.run()
            # close trial and receive data
            trialdata = trial.dump()
            del trial
            self.log_subdata(trialdata)
