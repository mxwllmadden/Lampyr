# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 12:58:45 2025

@author: mm4114
"""
from dataclasses import dataclass, field
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import Header, Footer, Input, RichLog, Switch, Placeholder, \
    ContentSwitcher, Button, Label, Select
from lampyr import Lampyr
from lampyr.behaviors import bandit
from time import time
import threading
from typing import Callable
import math
from importlib import resources as impres
from os import path
import art



@dataclass
class LampyrGuiState():
    lampyr: Lampyr = field(default_factory=Lampyr)
    lampyr_running: bool = False
    report_func: Callable = lambda x: None

    def refresh(self):
        self.lampyr.close()
        self.lampyr = Lampyr(_output_func=self.report_func)
    

def title(container, title: str):
    container.border_title = title
    return container


def flatten_dict(d, parent=""):
    for k, v in d.items():
        path = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            yield from flatten_dict(v, path)
        else:
            yield path, v


class LampyrApp(App):
    """A Textual app to run manage a lampyr rig."""

    title = 'Lampyr'
    CSS_PATH = impres.files(
        'lampyr').joinpath("interfaces\\textual_tui\\app.tcss")

    def __init__(self):
        self.state = LampyrGuiState()
        super().__init__()

    def on_mount(self) -> None:
        self.theme = 'solarized-light'

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.title = 'Lampyr'
        config = self.state.lampyr.config
        yield Header()
        with Horizontal(id='top'):
            with Vertical():
                yield Label(art.text2art(config.get('rig.name'), font='small'))
                with VerticalScroll():
                    for conf, val in flatten_dict(config._config):
                        yield Label(f'{conf}: {val}')
            with Vertical():
                yield Label('Current Rig Configuration')
                yield Select.from_values(["NOTIMPLEMENTED"],
                                         prompt='Rig Configuration')
                yield Label('Current User')
                yield Select.from_values(["NOTIMPLEMENTED"],
                                         prompt='Current User')
                yield Label('')
                yield Button("Run Calibration for Current Rig Config", id='calib',
                             classes='centeralign')
        yield Label('')
        with title(Horizontal(id='mid', classes='bordered'), 'Behavior Control'):
            yield Select.from_values(['test'],
                                     prompt='Mouse')
            yield Select.from_values(['test'],
                                     prompt='Behavior')
            yield Button("RUN", disabled=True)
        yield Label('')
        with title(Vertical(id='bot', classes='bordered'), 'Terminal'):
            twindow = RichLog(id='terminal')
            self.state.report_func = twindow.write
            yield twindow
            yield Input(id='terminalinput')
        self.state.refresh()

    def action_quit(self) -> None:
        self.exit()

    @on(Input.Submitted, '#terminalinput')
    def on_entry(self, event: Input.Submitted) -> None:
        self.query_one(RichLog).write(event.value)
        event.input.clear()
        self.state.refresh()
        t = threading.Thread(target=self.state.lampyr.run,
                             args=('HabituationTrial',))
        t.start()

    @on(Button.Pressed, '#calib')
    def on_calibbutton(self, event: Button.Pressed) -> None:
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pass


if __name__ == "__main__":
    app = LampyrApp()
    app.run()
