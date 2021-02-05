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
        if not self.uc_if:
            print("No uc IF defined")
            return None
        if self.uc_if.mode != "fft":
            self.uc_if.set_mode("fft")
        timestamps = []
        freq = self.uc_if.fft_axis()
        data = []
        if self.verbose > 2:
            print("Starting {} seconds of data collection".format(length_seconds))
        ts_start = time.time()
        while ts_start + length_seconds > time.time():
            dataset = self.uc_if.read_valid_dataset()
            if dataset:
                timestamps.append(datetime.datetime.now())
                data.append(dataset)
        return timestamps, freq, data

    def watch_fft(self, threshold, fmin=20e3, fmax=500e3):
        """
        continously watches for frequencies above threshold
        fmin, fmax define the min/max frequency in Hz to consider
        """
        from numpy import array
        while True:
            timestamps, freq, data = self.record_fft_data(10)
            mask = (freq > fmin)*(freq < fmax)
            maxvalue = array(data).T[mask].max()
            if maxvalue > threshold:
                if self.verbose:
                    print("Found maximum: {}".format(maxvalue))
                args = ([timestamps, freq, data ], threshold, fmin, fmax)
                self.save_executer.submit(save_fft_data, *args)
                #save_fft_data([timestamps, freq, data], threshold, fmin, fmax)


def save_fft_data(fftdata, threshold, fmin, fmax):
    """
    save data as figure and pickle
    """
    import pickle
    timestamps, freq, data = fftdata
    filename = timestamps[0].strftime("%Y-%m-%d_%H%M%S")
    file = open(filename+".pickle", 'wb')
    pickle.dump(fftdata, file)
    file.close()
    fig = plot_time_fft_data((timestamps, freq, data), False)
    fig.savefig(filename+"_time_fft.png")
    fig = plot_fft_data(fftdata, threshold, fmin, fmax)
    fig.savefig(filename+"_fft.png")

def plot_time_fft_data(fftdata, logcolor=False):
    """
    Plot 2D Frequqncy data - return Figure
    """
    time, freq, data = fftdata
    import pylab
    from matplotlib.colors import LogNorm
    fig = pylab.figure(figsize=(20, 10))
    ax1 = fig.subplots()
    data = pylab.array(data).T
    colornorm = None
    if logcolor:
        colornorm = LogNorm(1, data.max())
    mesh = ax1.pcolormesh(time, freq/1e3, data, norm=colornorm)
    fig.colorbar(mesh, ax=ax1)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("f [kHz]")
    ax1.set_title(time[0].strftime("%Y-%m-%d %H:%M:%S"))
    return fig

def plot_fft_data(fftdata, threshold, fmin=20e3, fmax=500e3):
    """
    """
    timestamps, freq, data = fftdata
    mask = (freq > fmin)*(freq < fmax)
    import pylab
    fig = pylab.figure(figsize=(20, 10))
    ax1 = fig.subplots()
    ax1.set_title(timestamps[0].strftime("%Y-%m-%d %H:%M:%S"))
    ax1.grid()
    ax1.set_xlabel("f [kHz]")
    #ax1.set_ylim(bottom=1)
    ax1.set_yscale('log')
    for i in range(len(data)):
        dataset = pylab.array(data[i])[mask]
        if dataset.max() > threshold:
            label = timestamps[i].strftime("%H:%M:%S")
            ax1.plot(freq[mask]/1e3, dataset, label=label)
    ax1.legend()
    return fig

if __name__ == "__main__":
    DATAPROC = BatData(BatUcIF("/dev/ttyACM0"))
    DATAPROC.watch_fft(12)
