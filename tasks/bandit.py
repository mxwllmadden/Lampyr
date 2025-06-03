# -*- coding: utf-8 -*-
"""
Created on Wed May 14 15:02:23 2025

@author: mm4114
"""

import time
from dataclasses import dataclass, field
import random
from lampyr.primatives import Behavior
from lampyr.tasks.habituation import RewardedHabituationTask


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

    def loop(self):
        self.trial_state = 'iti1'
        while True:
            if self.stop_reason:
                break
            match self.trial_state:
                case _ if self.trial_state not in ('iti1', 'pretrial', 'trial', 'iti2'):
                    self.stoplog('finished')
                case 'iti1':
                    self.loop_iti1()
                case 'pretrial':
                    self.loop_pretrial()
                case 'trial':
                    self.loop_trial()
                case 'iti2':
                    self.loop_iti2()

    def loop_iti1(self):
        self.printlog('TS0s', 'ITI START')
        time.sleep(self.iti_dur)
        self.printlog('TS0e', 'ITI END')
        self.trial_state = 'pretrial'

    def loop_pretrial(self):
        pretrial_start = self.printlog('TS1e', 'PRETRIAL START')
        while True:
            time.sleep(0.001)
            if time.time() - pretrial_start < self.pretrial_hold_s:
                continue
            wheel_movement = abs(
                self.rig.wheel.movement_total_since(time.time()-2))
            if wheel_movement < self.pretrial_movementthresh_deg:
                break
        self.printlog('TS1e', 'PRETRIAL END')
        self.trial_state = 'trial'

    def loop_trial(self):
        trial_start = self.printlog('TS2s', 'TRIAL START')
        self.rig.play.begintrialtone()
        response = False
        while not response:
            resp = self.rig.wheel.movement_since(trial_start)
            if resp < 0 and abs(resp) > self.trial_responsethresholds_deg['Left']:
                self.printlog('LR', 'Leftward response detected')
                response = 'Left'
            elif resp > 0 and abs(resp) > self.trial_responsethresholds_deg['Right']:
                self.printlog('RR', 'Rightward response detected')
                response = 'Right'
            elif response is False and time.time() - trial_start > self.trial_responsewindow_s:
                self.printlog('NR', 'No response detected')
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
        self.printlog(f'RAND:{rand},THRESH:{probability}')
        if rand < probability:
            self.printlog('REWARD', 'Giving reward')
            self.rig.reward.give()
            self.rig.play.rewardtone()
            self.log_reward()
        else:
            self.printlog('NOREWARD', 'No reward given')
        self.printlog('TS2e', 'TRIAL END')
        self.trial_state = 'iti2'

    def loop_iti2(self):
        self.printlog('TS3s', 'ITI2 START')
        time.sleep(self.iti2_dur)
        self.printlog('TS3e', 'ITI2 END')
        self.trial_state = None


@dataclass
class BanditTask(Behavior):
    offtargetrewardprob: int = 10
    ontargetrewardprob: int = 80
    blockrewardsizerange: tuple = (6, 15)

    def loop(self):
        side = not random.randint(0, 1)
        blocknum = 0
        while True:
            if self.stop_reason:
                break
            blocksize = random.randint(*self.blockrewardsizerange)
            side = not side
            self.loop_block(side, blocksize, blocknum)
            blocknum += 1

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
                                    save=self.save,
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

@dataclass
class BanditTrainer(Behavior):
    task_stage : int = 0
    trials_experienced : int = 0
    training_update_rate : int = 50
    duration_min = 1500
    
    def task_paradigm(self):
        match self.task_stage:
            case 0:
                task = RewardedHabituationTask(name=f'RewardedHabituationTask_{len(self.subdata)}',
                                               rig=self.rig,
                                               mouse=self.mouse,
                                               save=self.save,
                                               properties=self.properties,
                                               serial_abstention_limit=10,
                                               reward_limit=self.reward_limit - self.rewards,
                                               subdata_limit=self.training_update_rate
                                               )
            case 1:
                task = AnyWheelResponseTask(name=f'AnyWheelResponseTask_Session{len(self.subdata)}',
                                            rig=self.rig,
                                            mouse=self.mouse,
                                            save=self.save,
                                            properties=self.properties,
                                            serial_abstention_limit=15,
                                            reward_limit=self.reward_limit - self.rewards,
                                            subdata_limit=self.training_update_rate,
                                            )
            case 2:
                task = AlternatingSideResponseTask(name=f'AlternatingSideResponseTask_Session{len(self.subdata)}',
                                                   rig=self.rig,
                                                   mouse=self.mouse,
                                                   save=self.save,
                                                   properties=self.properties,
                                                   serial_abstention_limit=15,
                                                   reward_limit=self.reward_limit - self.rewards,
                                                   subdata_limit=self.training_update_rate,
                                                   )
            case 3:
                task = BanditTask(name=f'BanditTaskTraining_Session{len(self.subdata)}',
                                  rig=self.rig,
                                  mouse=self.mouse,
                                  save=self.save,
                                  properties=self.properties,
                                  serial_abstention_limit=15,
                                  reward_limit=self.reward_limit - self.rewards,
                                  subdata_limit=self.training_update_rate,
                                  )
            case 4:
                task = BanditTask(name=f'BanditTask_Session{len(self.subdata)}',
                                  rig=self.rig,
                                  mouse=self.mouse,
                                  save=self.save,
                                  properties=self.properties,
                                  serial_abstention_limit=15,
                                  reward_limit=self.reward_limit - self.rewards,
                                  )
        return task
    
    def progress_stage(self):
        self.task_stage = 1
        self.merit = 0
        self.demerit = 0    
        self.participation = 0
        self.trials_experienced = 0
        self.abstention = 0
    
    def task_paradigm_progression(self, task):
        match self.task_stage:
            case 0:
                if self.trials_experienced > 250:
                    self.progress_stage()
                    # Add check for reliable licking
            case 1:
                if self.trials_experienced > 150:
                    self.progress_stage()
            case 2:
                if self.trials_experienced > 200:
                    self.progress_stage()
            case 3:
                if self.trials_experienced > 150:
                    self.progress_stage()
    
    def update_mouse(self):
        if self.mouse is not None:
            self.mouse.properties['bandit']['stage'] = self.task_stage
            self.mouse.properties['bandit']['merit'] = self.merit
            self.mouse.properties['bandit']['demerit'] = self.demerit   
            self.mouse.properties['bandit']['participation'] = self.participation
            self.mouse.properties['bandit']['trials_experienced'] += self.trials_experienced
            self.mouse.properties['bandit']['trials_experienced_total'] += self.trials_experienced

    def loop(self):
        if self.mouse is not None:
            if 'bandit' not in self.mouse.properties:
                self.mouse.properties['bandit'] = {'stage': 0,
                                                   'merit': 0,
                                                   'demerit': 0,
                                                   'participation' : 0,
                                                   'trials_experienced' : 0,
                                                   'reward_limit': 200,
                                                   'trials_experienced_total' : 0
                                                   }
            self.task_stage = self.mouse.properties['bandit']['stage']
            self.merit = self.mouse.properties['bandit']['merit']
            self.demerit = self.mouse.properties['bandit']['demerit']
            self.participation = self.mouse.properties['bandit']['participation']
            self.trials_experienced = self.mouse.properties['bandit']['trials_experienced']
            self.reward_limit = self.mouse.properties['bandit']['reward_limit']
        
        while True:
            if self.stop_reason:
                break
            task = self.task_paradigm()
            task.properties['task_in_session'] = len(self.subdata)
            task.run()
            
            if 'reward' in task.stop_reason:
                self.stoplog('reward')
            
            taskdata = task.dump()
            
            self.log_subdata(taskdata)
            self.trials_experienced += len(taskdata['subdata'])
            self.task_paradigm_progression(taskdata)
            del task
        self.update_mouse()
        self._printstate()


if __name__ == '__main__':
    from rigcontrol import ArduinoBanditRig_0
    import threading
    import winsound

    class ComputerSpeaker():
        def begintrialtone(self):
            threading.Thread(target=lambda: winsound.Beep(1000, 500)).start()

        def rewardtone(self):
            threading.Thread(target=lambda: winsound.Beep(4000, 500)).start()

        def punishtone(self):
            threading.Thread(target=lambda: winsound.Beep(100, 500)).start()

    try:
        rig = ArduinoBanditRig_0()
        rig.play = ComputerSpeaker()
        rig.listen()
        time.sleep(2)
        t = BanditTask(rig=rig, save=False,
                       subdata_limit=20,
                       blockrewardsizerange=(4, 7))
        t.run()
        t.dump()
        rig.play.punishtone()
        rig.abort()
    finally:
        rig.close()
        del rig
        del t
