# -*- coding: utf-8 -*-
"""
Created on Wed May 14 15:02:37 2025

@author: mm4114
"""

import threading
from serial.tools import list_ports
import serial
from dataclasses import dataclass, field
from collections import defaultdict
import time


@dataclass
class SerialData:
    lock: threading.Lock = field(default_factory=lambda: threading.Lock())
    log: list = field(default_factory=lambda: [])
    reports: dict = field(default_factory=lambda: defaultdict(
        lambda: {'unix_time': [],
                 'arduino_time': [],
                 'report_value': []}
    )
    )

    def get_reportvals_since(self, reporttype, unixtime):
        reports = self.reports[reporttype]
        ind = 0
        for ind, t in enumerate(reversed(reports['unix_time'])):
            if t < unixtime:
                break
        if ind == 0:
            return []
        return reports['report_value'][-ind:]


class SerialMonitor:
    def __init__(self, baud, timeout=1):
        self.baud = baud
        self.timeout = timeout
        self.find_device()
        self.timeout = timeout
        self.data = SerialData()
        self.abort_flag = False
        self.threadlock = threading.Lock()

    def abort(self):
        self.abort_flag = True

    def close(self):
        self.ser.close()

    def find_device(self):
        ports = list_ports.comports()
        ports = [p for p in ports if 'Arduino' in p.description]
        port = ports[0]
        self.ser = serial.Serial(port.device, self.baud, timeout=self.timeout)

    def listen(self):
        thread = threading.Thread(target=self._listen)
        thread.start()

    def purge(self):
        with self.data.lock:
            self.data.log = []
            self.data.reports = defaultdict(lambda: {'unix_time': [],
                                                     'arduino_time': [],
                                                     'report_value': []}
                                            )

    def _listen(self):
        self.ser.reset_input_buffer()
        while not self.abort_flag:
            self._readserial()
            time.sleep(0.001)

        self.abort_flag = False

    def _readserial(self):
        responses = []
        while self.ser.in_waiting > 0:
            
            response = self.ser.readline().decode().strip()
            response = response.split('\t')
            # print(response)
            if len(response) == 3:
                try:
                    timestamp = int(response[0])
                    event_type = str(response[1])
                    value = int(response[2])
                    responses.append(
                        (time.time(), [timestamp, event_type, value]))
                except ValueError as e:
                    print(f"ValueError processing data: {response} - {e}")
            else:
                print(f"Received unexpected data format: {response}")
        self.data.log += responses
        for unix_time, (arduino_time, report_type, report_value) in responses:
            self.data.reports[report_type]['unix_time'].append(unix_time)
            self.data.reports[report_type]['arduino_time'].append(arduino_time)
            self.data.reports[report_type]['report_value'].append(report_value)
        return responses

    def _writeserial(self, cmd):
        self.ser.write(cmd.encode())


class ArduinoBandit_0:
    class _Measure():
        def __init__(self, parent):
            self.data = parent.data

    class _Control():
        def __init__(self, parent):
            self.serial = parent.serial

    class Wheel(_Measure):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.home = time.time()
        
        def movement_since(self, time):
            return sum(self.data.get_reportvals_since('R', time))/4000*360
        
        def movement_components_since(self, time):
            sum_positive = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x > 0)/4000*360
            sum_negative = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x < 0)/4000*360
            return sum_negative, sum_positive
        
        def angle(self):
            return self.movement_since(self.home)
        
        def home(self):
            self.home = time.time()

    class Lick(_Measure):
        pass

    class Speaker(_Control):
        def tone1(self):
            self.serial._writeserial('b')
            
        def tone2(self):
            self.serial._writeserial('r')
        
        def tone3(self):
            self.serial._writeserial('p')

    class Sipper(_Control):
        pass

    def __init__(self, serialmonitor):
        import winsound
        self.serial = serialmonitor
        self.data = serialmonitor.data
        self.wheel = self.Wheel(self)
        self.licks = self.Lick(self)
        self.play = self.Speaker(self)

    def listen(self):
        self.serial.listen()
        time.sleep(1)
        self.serial.purge()

    def abort(self):
        self.serial.abort()
    
    def close(self):
        self.serial.close()

class DummyBandit_0():
    class KeyboardWheel():
        def __init__(self):
            self.home = time.time()
        
        def movement_since(self, time):
            return sum(self.data.get_reportvals_since('R', time))/4000*360
        
        def movement_components_since(self, time):
            sum_positive = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x > 0)/4000*360
            sum_negative = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x < 0)/4000*360
            return sum_negative, sum_positive
        
        def angle(self):
            return self.movement_since(self.home)
        
        def home(self):
            self.home = time.time()

    class ComputerSpeaker():
        def tone1(self):
            self.serial._writeserial('b')
            
        def tone2(self):
            self.serial._writeserial('r')
        
        def tone3(self):
            self.serial._writeserial('p')

    def __init__(self):
        self.wheel = self.KeyboardWheel(self)
        self.licks = self.Lick(self)
        self.play = self.ComputerSpeaker(self)

    def listen(self):
        self.serial.listen()
        time.sleep(1)
        self.serial.purge()

    def abort(self):
        self.serial.abort()

try:
    rig = ArduinoBandit_0(SerialMonitor(115200))
    rig.listen()
    t = time.time()
    for i in range(2000):
        time.sleep(0.01)
        print(rig.wheel.movement_components_since(t))
    rig.abort()
finally:
    rig.serial.close()