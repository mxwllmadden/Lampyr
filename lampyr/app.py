# -*- coding: utf-8 -*-
"""
Created on Wed May 14 15:02:02 2025

@author: mm4114
"""

import click
import time
import os
import numpy as np
from lampyr import config, Lampyr
from lampyr.primatives import Task, Trial
from lampyr.tasks import habituation 
from lampyr.rigcontrol import ArduinoBanditRig_0, SerialMonitor

@click.group()
def cli():
    pass

@cli.command()
def list():
    click.echo('-'*20+'TASKS'+'-'*20)
    for behav in Task.get_children():
        click.echo(behav.__name__)
    click.echo('-'*20+'TRIALS'+'-'*20)
    for behav in Trial.get_children():
        click.echo(behav.__name__)

@cli.group()
@click.pass_context
def rig(ctx):
    ctx.obj = Lampyr()
    @ctx.call_on_close
    def cleanup():
        ctx.obj.close()
        
@rig.command()
@click.pass_obj
def calibrate(ctx):
    ctx.rigmanager.calibrate()

@cli.group()
def mouse():
    pass

@mouse.command()
@click.argument('mouseid')
@click.option('--merit_limit', '-ml', type=int, required=False)
@click.option('--demerit_limit', '-dml', type=int, required=False)
@click.option('--duration_limit', '-dl', type=int, required=False)
@click.option('--trial_limit', '-tl', type=int, required=False)
@click.option('--reward_limit', '-rl', type=int, required=False)
@click.option('--abstention_limit', '-al', type=int, required=False)
@click.option('--participation_limit', '-pl', type=int, required=False)
@click.option('--serial_abstention_limit', '-sal', type=int, required=False)
@click.option('--duration_min', '-dm', type=int, required=False)
@click.option('--trial_min', '-tm', type=int, required=False)
def run(mouseid, **kwargs):
    lampyr = Lampyr()
    try:
        lampyr.mousemanager.load(mouseid)
        lampyr.run(**kwargs)
    finally:
        lampyr.close()

@cli.command()
@click.argument('behavior')
@click.option('--merit_limit', '-ml', type=int, required=False)
@click.option('--demerit_limit', '-dml', type=int, required=False)
@click.option('--duration_limit', '-dl', type=int, required=False)
@click.option('--trial_limit', '-tl', type=int, required=False)
@click.option('--reward_limit', '-rl', type=int, required=False)
@click.option('--abstention_limit', '-al', type=int, required=False)
@click.option('--participation_limit', '-pl', type=int, required=False)
@click.option('--serial_abstention_limit', '-sal', type=int, required=False)
@click.option('--duration_min', '-dm', type=int, required=False)
@click.option('--trial_min', '-tm', type=int, required=False)
def run(behavior, **kwargs):
    lampyr = Lampyr()
    try:
        lampyr.run(behavior, **kwargs)
    finally:
        lampyr.close()