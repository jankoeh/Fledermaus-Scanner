#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 21:52:07 2021

@author: pi
"""

OPERATION_MODES = {
        "raw" : b"0",
        "fft" : b"1",
        "freq" : b"2"
        }

class BatUcIF:
    """
    IF class for uC via serial device
    """
    separator = b"#EOD"
    samples = 2048
    sample_rate = 500e3
    mode = None
    def __init__(self, port, baudrate=115200):
        import serial
        self.serial_if = serial.Serial(port, baudrate)
        print("Opened serial port:", self.serial_if.name)

    def read_dataset(self):
        """
        Read data until separator or invalid value
        return data as list of ints
        """
        data = []
        while True:
            line = self.serial_if.readline()
            if self.separator in line:
                #print("Separator",line)
                break
            else:
                try:
                    data.append(int(line))
                except ValueError:
                    print("Invalid data found:", line)
                    break
        return data

    def read_valid_dataset(self, tries=10):
        """
        Returns only datasets with correct number of samples
        tries - defines the number of tries to obtain a dataset
        """
        datalen = 0
        if self.mode == "raw":
            datalen = self.samples
        elif self.mode == "fft":
            datalen = self.samples/2
        else:
            print("Invalid mode set")
            return None
        while tries > 0:
            tries -= 1
            data = self.read_dataset()
            if len(data) == datalen:
                return data

    def flush_read_buffer(self):
        """
        probably not neccessary
        """
        self.serial_if.read_all()
        self.serial_if.read_all()

    def fft_axis(self):
        """
        return fft frequency axis in Hz
        """
        import numpy as np
        return np.arange(0, self.samples/2)/self.samples*self.sample_rate
    def data_axis(self):
        """
        return raw data axis in seconds
        """
        import numpy as np
        return np.arange(0, self.samples)/self.sample_rate

    def set_mode(self, mode):
        """
        Set mode according to OPERATION_MODES dict
        """
        from time import sleep
        if mode not in OPERATION_MODES.keys():
            print("Invalid mode", mode)
            return
        self.mode = mode
        self.serial_if.write(OPERATION_MODES[self.mode])
        print("Setting mode", mode)
        sleep(0.5)
        self.flush_read_buffer()


class BatData:
    """
    Data processing class
    """
    verbose = 1
    def __init__(self, uc_if=None):
        from concurrent.futures import ThreadPoolExecutor
        self.uc_if = uc_if
        self.save_executer = ThreadPoolExecutor(5) #save data in separate threads

    def record_fft_data(self, length_seconds=10):
        """
        Record 10 seconds of fft valid datasets
        """
        import time
        import datetime
        from fft_data import FftData
        if not self.uc_if:
            print("No uc IF defined")
            return None
        if self.uc_if.mode != "fft":
            self.uc_if.set_mode("fft")
        data = FftData(self.uc_if.fft_axis())
        if self.verbose > 2:
            print("Starting {} seconds of data collection".format(length_seconds))
        ts_start = time.time()
        while ts_start + length_seconds > time.time():
            dataset = self.uc_if.read_valid_dataset()
            if dataset:
                data.append_dataset(datetime.datetime.now(), dataset)
        return data

    def watch_fft(self, threshold, fmin=20e3, fmax=500e3):
        """
        continously watches for frequencies above threshold
        fmin, fmax define the min/max frequency in Hz to consider
        """
        from numpy import array
        while True:
            data = self.record_fft_data(10)
            maxdata = data.find_maximum(threshold, fmin, fmax)
            if maxdata:
                if self.verbose:
                    print("{} Found maximum: {}Hz {}".format(data.timestamps[0], maxdata[0]/1e3, maxdata[1]))
                args = (data, threshold, fmin, fmax)
                #self.save_executer.submit(save_fft_data, *args)
                save_fft_data(*args)


def save_fft_data(data, threshold, fmin, fmax):
    """
    save data as figure and pickle
    """
    import pylab
    import pickle
    filename = data.timestamps[0].strftime("%Y-%m-%d_%H%M%S")
    data.save(filename+".pickle")
    fig = data.plot_time_fft(False)
    fig.savefig(filename+"_time_fft.png")
    pylab.close(fig)
    fig = data.plot_ffts(threshold, fmin, fmax)
    fig.savefig(filename+"_fft.png")
    pylab.close(fig)


if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')
    DATAPROC = BatData(BatUcIF("/dev/ttyACM0"))
    DATAPROC.watch_fft(12, 18e3)
