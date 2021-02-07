#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  6 22:35:28 2021

@author: Jan Koehler
"""

class FftData:
    def __init__(self, frequencies):
        """
        ctor initialize from single measurement
        """
        self.timestamps = []
        self.frequencies = frequencies
        self.data = []
        
    def append_dataset(self, timestamp, dataset):
        """
        Append dataset from timestamp
        """
        self.timestamps.append(timestamp)
        self.data.append(dataset)
        
    def append_data(self, timestamps, data):
        """
        Append a collection of datasets
        """
        self.data += data
    
    def append_fftdata(self, fftdata):
        """
        Append data of Type FftData
        """
        self.timestamps += fftdata.timestamps
        self.data += fftdata.data
    
    def save(self, filename):
        """
        Save data to file
        """
        import pickle
        file = open(filename, 'wb')
        pickle.dump([self.timestamps, self.frequencies, self.data], file)
        file.close()
    
    def load(self, filename):
        """
        Load data from file
        """
        import pickle
        file = open(filename, 'rb')
        self.timestamps, self.frequencies, self.data = pickle.load(file)
        file.close()

    def select_fft(self, threshold, fmin, fmax):
        """
        return those fft, that have values above threshold in [fmin, fmax]
        """
        from numpy import array
        datasets = []
        mask = (self.frequencies > fmin)*(self.frequencies < fmax)

        for t, d in zip(self.timestamps, self.data):
            if array(d)[mask].max() > threshold:
                datasets.append( (t, d) )
        return datasets
        
    def select_frequency(self, fmin, fmax):
        """
        return a timeseries of a frequency range
        """
        from numpy import array
        mask = (self.frequencies > fmin)*(self.frequencies < fmax)
        data = array(self.data).T[mask]
        return self.timestamps, data.sum(axis=0)
        
    def plot_time_fft(self, logcolor=False):
        """
        Create a 2D density plot with FFT intensity over time and frequencies
        """        
        import pylab
        from matplotlib.colors import LogNorm
        fig = pylab.figure(figsize=(20, 10))
        ax1 = fig.subplots()
        data = pylab.array(self.data).T
        colornorm = None
        if logcolor:
            colornorm = LogNorm(1, data.max())
        mesh = ax1.pcolormesh(self.timestamps, self.frequencies/1e3, data, norm=colornorm)
        fig.colorbar(mesh, ax=ax1)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("f [kHz]")
        ax1.set_title(self.timestamps[0].strftime("%Y-%m-%d %H:%M:%S"))
        return fig
    
    def plot_ffts(self, threshold, fmin=20e3, fmax=500e3):
        """
        plot those fft, that have values above threshold in [fmin, fmax]
        """
        import pylab
        fig = pylab.figure(figsize=(20, 10))
        ax1 = fig.subplots()
        ax1.set_title(self.timestamps[0].strftime("%Y-%m-%d %H:%M:%S"))
        ax1.grid()
        ax1.set_xlabel("f [kHz]")
        ax1.set_yscale('log')
        for t, d in self.select_fft(threshold, fmin, fmax):
            label = t.strftime("%H:%M:%S")
            ax1.plot(self.frequencies/1e3, d, label=label)
        ax1.legend()
        return fig
    
    def find_maximum(self, threshold, fmin=20e3, fmax=500e3):
        """
        Return maximum above threshold in [fmin, fmax]
        If none exists, None is retuned
        """
        from numpy import array
        mask = (self.frequencies > fmin)*(self.frequencies < fmax)
        data = array(self.data).T[mask]
        if data.max() > threshold:
            fmax_index = data.max(axis=1).argmax()
            return self.frequencies[mask][fmax_index], data.max()
        else:
            return None



        