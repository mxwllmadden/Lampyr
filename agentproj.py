# -*- coding: utf-8 -*-
"""
Created on Fri Sep 12 13:39:58 2025

@author: mm4114
"""
from lampyr.primatives import Session
from lampyr.behaviors.bandit import RandomBanditStage
from lampyr.rigs.rigcontrol import SerialData
from collections import deque
import lampyr
import time
import math
import random

original_timesleep = time.sleep
original_timetime = time.time

def dummy_time_factory():
    t = 0
    def dummy_time():
        nonlocal t
        t += 1
        return t
    return dummy_time

def dummy_timesleep(val):
    pass


time.sleep = dummy_timesleep
time.time = dummy_time_factory()

class Agent:
    def __init__(self, window_size=5, exploration_coefficient = 1):
        self.exploration_coefficient = exploration_coefficient
        self.window_size = window_size
        self.history = deque(maxlen=window_size)  # stores (arm, reward)
        self.total_pulls = 0
        self.last_choice = None
        self.rewarded = False
        self.num_arms = 2  # fixed to 2 choices

    def stimulus(self):
        # Before choosing a new action, update history from last choice and reward
        if self.last_choice is not None:
            # Append previous choice and reward info to history
            reward_val = 1 if self.rewarded else 0
            self.history.append((self.last_choice, reward_val))
            self.total_pulls += 1
        
        self.rewarded = False  # reset reward flag for next round
        
        # Count pulls and sum rewards for each arm in sliding window
        counts = [0] * self.num_arms
        rewards = [0.0] * self.num_arms
        
        for arm, reward in self.history:
            counts[arm] += 1
            rewards[arm] += reward
        
        total_counts = sum(counts)
        if total_counts == 0:
            # No history yet, choose arm 0
            self.last_choice = 0
            return
        
        ucb_values = [0.0] * self.num_arms
        
        for arm in range(self.num_arms):
            if counts[arm] == 0:
                # Encourage exploration by setting UCB to infinity if arm never tried
                ucb_values[arm] = float('inf')
            else:
                avg_reward = rewards[arm] / counts[arm]

                exploration = math.sqrt(self.exploration_coefficient * math.log(total_counts) / counts[arm])
                ucb_values[arm] = avg_reward + exploration
        
        # Choose arm with highest UCB
        self.last_choice = int(ucb_values.index(max(ucb_values)))
        

    def response(self):
        """Return response as -20 or 20 depending on last choice."""
        if self.last_choice is None:
            return random.choice([-20,20])
        return 20 if self.last_choice == 1 else -20

    def reward(self):
        self.rewarded = True


class SoftwareRig:
    class _DummyComponent():
        def __init__(self, parent):
            self.agent = parent.agent

    class Wheel(_DummyComponent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.home()

        def movement_total_since(self, time):
            return 0

        def movement_since(self, time):
            return self.agent.response()

        def movement_components_since(self, time):
            return 0, 0

        def angle(self):
            return self.movement_since(self.home_t)

        def home(self):
            pass

    class Lick(_DummyComponent):
        def since(self, time):
            return 1

    class Speaker(_DummyComponent):
        def begintrialtone(self):
            self.agent.stimulus()

        def rewardtone(self):
            self.agent.reward()

        def punishtone(self):
            pass

    class Sipper(_DummyComponent):
        def give(self):
            pass

        def setsize(self, size: int):
            pass

    def __init__(self, agent=None):
        self.data = SerialData()
        self.agent = Agent()
        self.wheel = self.Wheel(self)
        self.licks = self.Lick(self)
        self.play = self.Speaker(self)
        self.reward = self.Sipper(self)

    def listen(self):
        pass

    def abort(self):
        pass

    def close(self):
        pass
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_experiment(params):
    window_size, exploration_coefficient = params

    class CustomRig(SoftwareRig):
        def __init__(self):
            self.data = SerialData()
            self.agent = Agent(window_size=window_size, exploration_coefficient=exploration_coefficient)
            self.wheel = self.Wheel(self)
            self.licks = self.Lick(self)
            self.play = self.Speaker(self)
            self.reward = self.Sipper(self)
    
    sesh = Session(trial_limit=1000000,
                   duration_limit=float('inf'),
                   reward_limit=float('inf'))
    
    RandomBanditStage(_verbose=False, session=sesh, rig=CustomRig()
                      ).run()
    
    avg_merit = sesh.merit / sesh.participation
    print(f"Window size: {window_size}, Exploration coeff: {exploration_coefficient:.2f}, Avg merit: {avg_merit:.4f}")
    return (window_size, exploration_coefficient, avg_merit)

def main():
    window_sizes = list(range(1, 13))  # 1 to 12 inclusive
    exploration_coeffs = np.arange(0.1, 5.1, 0.5)  # 0.1 to 5.0 step 0.5

    param_grid = [(w, e) for w in window_sizes for e in exploration_coeffs]
    total_jobs = len(param_grid)
    completed_jobs = 0
    results = []
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(run_experiment, params): params for params in param_grid}
        for future in as_completed(futures):
            completed_jobs += 1
            print(f"Completed {completed_jobs}/{total_jobs} jobs")
            res = future.result()
            results.append(res)

    # Convert results to a 2D matrix for plotting
    rewards_matrix = np.zeros((len(window_sizes), len(exploration_coeffs)))

    # Map params back to indices
    w_index = {w: i for i, w in enumerate(window_sizes)}
    e_index = {e: i for i, e in enumerate(exploration_coeffs)}

    for w, e, avg_r in results:
        i = w_index[w]
        j = e_index[e]
        rewards_matrix[i, j] = avg_r

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(10, 7))
    cax = ax.matshow(rewards_matrix, cmap='viridis', origin='lower')

    # Set axis ticks and labels
    ax.set_xticks(np.arange(len(exploration_coeffs)))
    ax.set_yticks(np.arange(len(window_sizes)))
    ax.set_xticklabels([f"{e:.1f}" for e in exploration_coeffs], rotation=45)
    ax.set_yticklabels([str(w) for w in window_sizes])

    ax.set_xlabel('Exploration Coefficient')
    ax.set_ylabel('Window Size')
    ax.set_title('Average Reward Heatmap')

    # Add colorbar
    fig.colorbar(cax, label='Avg Reward')

    plt.tight_layout()
    plt.show()

    # Print best parameters for convenience
    best = max(results, key=lambda x: x[2])
    print(f"\nBest performance at window size={best[0]}, exploration coefficient={best[1]:.2f} with avg reward={best[2]:.4f}")

    return results

if __name__ == "__main__":
    main()