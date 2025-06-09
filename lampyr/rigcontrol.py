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


class ArduinoBanditRig_0:
    class _Measure():
        def __init__(self, parent):
            self.data = parent.data

    class _Control():
        def __init__(self, parent):
            self.serial = parent.serial

    class Wheel(_Measure):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.home()

        def movement_total_since(self, time):
            components = self.movement_components_since(time)
            return components[1] - components[0]

        def movement_since(self, time):
            return sum(self.data.get_reportvals_since('R', time))/4096*360

        def movement_components_since(self, time):
            sum_positive = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x > 0)/4096*360
            sum_negative = sum(x for x in self.data.get_reportvals_since('R', time)
                               if x < 0)/4096*360
            return sum_negative, sum_positive

        def angle(self):
            return self.movement_since(self.home_t)

        def home(self):
            self.home_t = time.time()

    class Lick(_Measure):
        def since(self, time):
            lickdat = self.data.get_reportvals_since('L', time)
            lcount = 0
            for l1, l2 in zip(lickdat,lickdat[1:]):
                if l1 < 512 and l2 > 512:
                    lcount += 1
            return lcount

    class Speaker(_Control):
        def begintrialtone(self):
            self.serial._writeserial('b')

        def rewardtone(self):
            self.serial._writeserial('r')

        def punishtone(self):
            self.serial._writeserial('p')

    class Sipper(_Control):
        def give(self):
            self.serial._writeserial('g')
        
        def setsize(self, size : int):
            self.serial._writeserial('w')
            self.serial._writeserial(f'{size}\n')

    def __init__(self, customserialmonitor=None):
        if customserialmonitor is None:
            self.serial = SerialMonitor(115200)
        else:
            self.serial =  customserialmonitor
        self.data = self.serial.data
        self.wheel = self.Wheel(self)
        self.licks = self.Lick(self)
        self.play = self.Speaker(self)
        self.reward = self.Sipper(self)

    def listen(self):
        self.serial.listen()
        time.sleep(1)
        self.serial.purge()

    def abort(self):
        self.serial.abort()

    def close(self):
        self.serial.close()


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
        return reports['report_value'][-ind-1:]

    def get_report_snippet(self, start_unixtime, end_unixtime):
        result = {}
        for reporttype, data in self.reports.items():
            result[reporttype] = {'unix_time': [],
                                  'arduino_time': [], 'report_value': []}
            for tu, ta, v in zip(data['unix_time'], data['arduino_time'], data['report_value']):
                if start_unixtime <= tu <= end_unixtime:
                    result[reporttype]['unix_time'].append(tu)
                    result[reporttype]['arduino_time'].append(ta)
                    result[reporttype]['report_value'].append(v)
        return result


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
        time.sleep(2)
        self.ser.reset_input_buffer()
        self.ser.flush()

    def listen(self):
        thread = threading.Thread(target=self._listen)
        thread.start()
        time.sleep(2)

    def purge(self):
        with self.data.lock:
            self.data.log = []
            self.data.reports = defaultdict(lambda: {'unix_time': [],
                                                     'arduino_time': [],
                                                     'report_value': []}
                                            )

    def _listen(self):
        time.sleep(1)
        self.ser.reset_input_buffer()
        self.ser.flush()
        while not self.abort_flag:
            try:
                self._readserial()
            except Exception as error:
                print(f'WARNING! Unknown serial read error occurred. {error}')
            time.sleep(0.001)

        self.abort_flag = False

    def _readserial(self):
        responses = []
        while self.ser.in_waiting > 0:
            try:
                response = self.ser.readline().decode().strip()
            except UnicodeDecodeError as error:
                print(error)
                print('WARNING: UnicodeDecodeError detected. If this reoccurs, restart your script!!!!')
                break
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


if __name__ == '__main__':
    try:
        rig = ArduinoBanditRig_0(SerialMonitor(115200))
        rig.listen()
        rig.play.begintrialtone()
        rig.reward.setsize(100)
        time.sleep(0.01)
        rig.reward.setsize(200)
        time.sleep(0.01)
        rig.reward.setsize(42424)
        for i in range(100):
            rig.reward.give()
            rig.play.rewardtone()
            time.sleep(0.8)
        t = time.time()
        time.sleep(2)
        rig.abort()
        print('R', rig.data.get_reportvals_since('R', t))
        print('T', rig.data.get_reportvals_since('T', -1))
        print('W', rig.data.get_reportvals_since('W', -1))
        print('G', rig.data.get_reportvals_since('G', -1))
    finally:
        rig.abort()
        rig.serial.close()
