# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 18:40:05 2025

@author: mm4114
"""

from lampyr.managers.abstract import AbstractManager

import h5py
import os
import numpy as np
import pickle
import json
from dataclasses import is_dataclass, asdict
from lampyr.primatives import Session, Mouse
from lampyr.config import Config
import shutil
import csv
import time


def savejson(fp, data, saveasis=True):
    if not saveasis:
        if is_dataclass(data):
            data = asdict(data)
    with open(fp, 'w') as f:
        json.dump(data, f, indent=2)
    return fp


def loadjson(fp):
    with open(fp, 'r') as f:
        return json.load(f)


def savepickle(fp, data):
    with open(fp, 'wb') as f:
        pickle.dump(data, f)
    return fp


def loadpickle(filepath):
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def loadh5(fp):
    def recursive_load(h5group):
        # Get the type hint saved by saveh5
        node_type = h5group.attrs.get('_type')
        if node_type == 'ndarray':
            return h5group['array'][()]
        elif node_type == 'scalar' or node_type == 'unknown_fallback_str':
            val = h5group.attrs['value']
            original_py_type = h5group.attrs.get('_original_py_type')

            # Attempt to convert back to original Python type
            if original_py_type == 'int':
                return int(val)
            elif original_py_type == 'float':
                return float(val)
            elif original_py_type == 'bool':
                # Handle boolean string conversion carefully
                if isinstance(val, str):
                    return val.lower() == 'true'
                return bool(val)  # For actual boolean values saved directly
            # Add more types if needed (e.g., complex, bytes)
            # elif original_py_type == 'str_fallback': # This means it was an unhandled type saved as string
            #     # You might want to log a warning here
            #     pass
            return val  # Default for string or if type conversion not handled

        elif node_type == 'dict':
            keys = list(h5group.keys())
            return {k: recursive_load(h5group[k]) for k in keys}
        elif node_type == 'list':  # List or tuple, using the explicit flag
            keys = list(h5group.keys())
            indices = sorted(int(k) for k in keys)
            # Ensure it's a contiguous list of indices for true list reconstruction
            if len(indices) == len(keys) and all(idx == i for i, idx in enumerate(indices)):
                return [recursive_load(h5group[str(i)]) for i in indices]
            else:
                # Fallback to dict if keys are not contiguous for a list
                print(f"Warning: List expected for group '{
                      h5group.name}', but keys are not contiguous. Loading as dictionary.")
                return {k: recursive_load(h5group[k]) for k in keys}
        else:
            # Fallback for old files or unexpected structures
            # If no '_type' attribute, try to guess based on existing children/attributes
            if 'array' in h5group:
                return h5group['array'][()]
            elif 'value' in h5group.attrs:
                return h5group.attrs['value']
            # Assume it's a group that might be a dict or list (try dict first for safety)
            else:
                keys = list(h5group.keys())
                # Try to guess if it's a list by checking if all keys are integer strings
                try:
                    parsed_keys = sorted(int(k) for k in keys)
                    if len(parsed_keys) > 0 and all(pk == i for i, pk in enumerate(parsed_keys)):
                        return [recursive_load(h5group[str(i)]) for i in parsed_keys]
                    else:
                        return {k: recursive_load(h5group[k]) for k in keys}
                except ValueError:  # Not all keys are integers, so definitely a dict
                    return {k: recursive_load(h5group[k]) for k in keys}

    with h5py.File(fp, mode='r') as file:
        if 'root' in file:
            return recursive_load(file['root'])
        else:
            print(f"Warning: 'root' group not found in HDF5 file: {
                  fp}. Returning None.")
            return None  # Or raise an error
    return fp


def saveh5(fp, data):
    def recursive_save(obj, h5group):
        if isinstance(obj, dict):
            h5group.attrs['_type'] = 'dict'  # Indicate it's a dictionary
            for k, v in obj.items():
                grp = h5group.create_group(str(k))
                recursive_save(v, grp)
        elif isinstance(obj, (list, tuple)):
            h5group.attrs['_type'] = 'list'  # Indicate it's a list/tuple
            for i, v in enumerate(obj):
                grp = h5group.create_group(str(i))
                recursive_save(v, grp)
        elif isinstance(obj, np.ndarray):
            h5group.attrs['_type'] = 'ndarray'  # Indicate it's an ndarray
            h5group.create_dataset('array', data=obj)
        # Added bool for explicit type saving
        elif isinstance(obj, (int, float, str, bool, np.number)):
            h5group.attrs['_type'] = 'scalar'
            h5group.attrs['value'] = obj
            # Store original Python type name for better reconstruction
            h5group.attrs['_original_py_type'] = type(obj).__name__
        else:
            # Fallback for unhandled types (e.g., set, complex, custom objects)
            # Save as string, mark as fallback
            h5group.attrs['_type'] = 'unknown_fallback_str'
            h5group.attrs['value'] = str(obj)
            h5group.attrs['_original_py_type'] = 'str_fallback'

    if is_dataclass(data):
        data = asdict(data)

    with h5py.File(fp, mode='w') as file:
        # Changed to pass data first
        recursive_save(data, file.create_group("root"))
    
    return fp


class DataHandler(AbstractManager):
    CONFIG_FAILSAFE_DEFAULT = {'sessions' : []}
    
    def start(self):
        """
        DataHandler startup. If this object is instantiated with a config file, 
        determine if backups and failsafes are enabled, then execute those methods.
        

        Returns
        -------
        None.

        """
        configured = self.config is not None
        haslampyr = self.lampyr is not None
        if not configured:
            return
        self.enable_failsafe = self.config.get(
            'lampyr.enable_saveload_failsafe') and haslampyr
        self.enable_localbackup = self.config.get(
            'lampyr.enable_local_mouse_backups') and haslampyr
        
        # Create required information for backups and cleanup
        self.local_save_dir = self.config._APP_DATA_DIR
        self.config_failsafe_data = self.config.load_extended_config('data_failsafe',
                                                        default=self.CONFIG_FAILSAFE_DEFAULT)
        # Check if
        m_dir_present = os.path.exists(self.config.get('lampyr.mice_directory'))
        if m_dir_present and self.enable_localbackup:
            self._output_func('Running mouse data local backup...')
            self._backupmice()
        if m_dir_present and self.enable_failsafe:
            self._output_func('Running failsafe cleanup...')
            self._runfailsafecleanup()
                    
    def _backupmice(self):
        if not self.enable_localbackup:
            return
        miceids, _ = self.lampyr_mouseidlist()
        for mouse in miceids:
            try:
                path_mousefile, path_historyfile = self.lampyr_mouseidtofilepaths(mouse)
                shutil.copy(path_mousefile,
                            self.config._APP_DATA_DIR)
                shutil.copy(path_historyfile,
                            self.config._APP_DATA_DIR)
                self._output_func(f'Created local backup of {mouse}.')
            except FileNotFoundError as e:
                self._output_func(f'FAILED TO BACK UP {mouse} due to FILE NOT FOUND')
            except PermissionError as e:
                self._output_func(f'FAILED TO BACK UP {mouse} due to PERMISSION DENIED')
            except Exception as e:
                self._output_func(f'FAILED TO BACK UP {mouse} due to UNEXPECTED ERROR')
                self._output_func(str(e))
    
    def _runfailsafecleanup(self):
        if not self.enable_failsafe:
            return
        failsafe = self.config.load_extended_config('data_failsafe',
                                                        default={'session' : []})
        failed_sessions = failsafe.get('session')
        for session in failed_sessions:
            if not isinstance(session, dict):
                self._output_func('DataHandler found an invalid session failsafe entry!!!')
                continue
            if not {'fps', 'target'} <= session:
                self._output_func('DataHandler found an invalid session failsafe entry!!!')
                self._output_func('You must manually inspect and register any remaining failed files.')
                continue
            for fp in session['fps']:
                shutil.copy(fp, session['target'])
                
    
    def logfailure(self, failure_type : str, fps : list, target : str):
        failures = self.config_failsafe.get(failure_type)
        failures.append({'fps' : fps,
                         'target' : target})
        self.config_failsafe.set(failure_type, failures)
    
    def savesessionfile(self, session : Session, folder : str):
        os.makedirs(folder, exist_ok=True)
        rigdata = session.rigdata
        np_rigdata = {}
        fps = []
        if rigdata is not None:
            for reporttype, reports in rigdata.items():
                np_rigdata[reporttype] = {}
                for datalabel, data in reports.items():
                    np_rigdata[reporttype][datalabel] = np.asarray(data)
            fp = saveh5(os.path.join(folder, f'{session.uniquesessionid}.lampyr.h5'),
                   np_rigdata)
            if fp is not None:
                fps.append(fp)
        data = asdict(session)
        data['rigdata'] = None
        fp = savejson(os.path.join(folder, f'{session.uniquesessionid}.lampyr.json'),
                 data)
        if fp is not None:
            fps.append(fp)
        return fps
    
    def loadsessionfile(self, folder : str, sessionid : str):
        if not os.path.exists(folder):
            raise FileExistsError('Folder not found')
        h5file = os.path.join(folder,
                              f'{sessionid}.lampyr.h5')
        jsonfile = os.path.join(folder,
                                f'{sessionid}.lampyr.json')
        if not os.path.exists(h5file) or not os.path.exists(jsonfile):
            raise FileExistsError(f'Session is invalid or does not exist. {
                                  h5file} or {jsonfile} not found.')
        sesh = Session(rigdata=loadh5(h5file))
        jsonobj = loadjson(jsonfile)
        for index, value in jsonobj.items():
            if index != 'endtime':
                sesh.__setattr__(index, value)
        sesh.endtime = jsonobj['endtime']
        return sesh
    
    def lampyr_savesession(self, session: Session):
        folder = os.path.join(self.config.get('lampyr.mice_directory'),
                              session.mouseid,
                              'lampyr_sessionhistory')
        try:
            self.savesessionfile(session, folder)
        except FileNotFoundError:
            if self.enable_failsafe:
                fps = self.savesessionfile(session, self.config.APP_DATA_DIR)
                self.logfailure('session', fps, folder)

    def lampyr_loadsession(self, mouseid: str, sessionid: str):
        folder = os.path.join(self.config.get('lampyr.mice_directory'),
                              mouseid,
                              'lampyr_sessionhistory')
        sesh = self.loadsessionfile(folder, sessionid)
        return sesh
    
    def mouseidlist(self, folder):
        folders = os.listdir(folder)
        mice = {}
        for mouseid in folders:
            mouse_fp = os.path.join(folder, mouseid,
                                    f'{mouseid}_mouse.lampyr.json')
            if os.path.exists(mouse_fp):
                mice[mouseid] = mouse_fp
        return list(mice.keys()), mice
    
    def lampyr_mouseidlist(self):
        folder = self.config.get('lampyr.mice_directory')
        return self.mouseidlist(folder)
    
    def mouseidtofilepath_mouse(self, mouseid, folder):
        return os.path.join(folder, mouseid, f'{mouseid}_mouse.lampyr.json')

    def mouseidtofilepath_history(self, mouseid, folder):
        return os.path.join(folder, mouseid, f'{mouseid}_history.lampyr.csv')
    
    def mouseidtofilepaths(self, mouseid, folder):
        return self.mouseidtofilepath_mouse(mouseid, folder),\
            self.mouseidtofilepath_history(mouseid, folder)
    
    def lampyr_mouseidtofilepaths(self, mouseid = None):
        if mouseid is None and self.lampyr is not None:
            mouseid = self.lampyr.mouse.mouseid
        if mouseid is None and self.lampyr is None:
            raise KeyError('mouseid is required if datahandler is not within a Lampyr instance')
        mice_dir = self.config.get('lampyr.mice_directory')
        return self.mouseidtofilepaths(mouseid, mice_dir)
    
    def savemousefile(self, folder, mouse):
        pass
    
    def loadmousefile(self, folder, mouseid):
        pass
    
    def lampyr_savemouse(self, mouse):
        pass
    
    def lampyr_loadmouse(self, mouseid):
        pass


class MouseManager(AbstractManager):
    def start(self):
        self.mouse = None
        if not self.exists('UNKNOWN_MOUSE'):
            self.create('UNKNOWN_MOUSE')
        self.mouse = self.load('UNKNOWN_MOUSE')

    def create(self, mouseid, **kwargs):
        mouse = Mouse(mouseid=mouseid, **kwargs)
        self.mouse = mouse
        self.save()

    def path_mouse(self, mouseid=None):
        if mouseid is None:
            mouseid = self.mouse.mouseid
        mice_dir = self.config.get('lampyr.mice_directory')
        return os.path.join(mice_dir, mouseid, f'{mouseid}_mouse.lampyr.json')

    def path_history(self, mouseid=None):
        if mouseid is None:
            mouseid = self.mouse.mouseid
        mice_dir = self.config.get('lampyr.mice_directory')
        return os.path.join(mice_dir, mouseid, f'{mouseid}_history.lampyr.csv')

    def load(self, mouseid):
        if not self.exists(mouseid):
            raise KeyError(f'Mouse {mouseid} does not exist')
        mouse_fp = self.path_mouse(mouseid)
        history_fp = self.path_history(mouseid)

        with open(mouse_fp, 'r') as f:
            mouse_data = json.load(f)

        mouse = Mouse(**mouse_data)
        mouse.mouseid = mouseid
        mouse.history.clear()

        if mouseid == 'UNKNOWN_MOUSE':
            return mouse

        if os.path.isfile(history_fp):
            with open(history_fp, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mouse.history.append(row)
        else:
            with open(history_fp, 'w', newline='') as f:
                pass

        self.mouse = mouse
        return mouse

    def save(self):
        if self.mouse is None:
            raise ValueError("No mouse loaded to save")

        mouse_fp = self.path_mouse()
        history_fp = self.path_history()

        os.makedirs(os.path.dirname(mouse_fp), exist_ok=True)

        mouse_data = asdict(self.mouse)
        mouse_data.pop('history', None)

        with open(mouse_fp, 'w') as f:
            json.dump(mouse_data, f, indent=4)

        if self.mouse.mouseid == 'UNKNOWN_MOUSE':
            return  # Skip saving history

        if self.mouse.history:
            all_keys = set()
            for entry in self.mouse.history:
                all_keys.update(entry.keys())
            all_keys = list(all_keys)

            with open(history_fp, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_keys)
                writer.writeheader()
                writer.writerows(self.mouse.history)
        else:
            with open(history_fp, 'w', newline='') as f:
                pass

    def exists(self, mouseid):
        return os.path.exists(self.path_mouse(mouseid))


if __name__ == '__main__':
    dhandler = DataHandler()
    
