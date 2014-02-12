from __future__ import division
import numpy as np
from scipy.integrate import simps, trapz
import scipy.io.wavfile as wv
from matplotlib import mlab
from matplotlib import pyplot

from PyQt4.QtGui import QImage

VERBOSE = False
DBFACTOR = 20
OUTPUT_MINIMUM = 0.01

def calc_db(peak, caldb, cal_peak):
    u"""20*log10(peak/cal_peak) + caldb"""
    try:
        pbdB = DBFACTOR * np.log10(peak/cal_peak) + caldb
    except ZeroDivisionError:
        print u'attempted division by zero:'
        print u'peak {}, caldb {}, calpeak {}'.format(peak, caldb, cal_peak)
        pbdB = np.nan
    return pbdB

def calc_noise(fft_vector, ix1,ix2):
    fft_slice = fft_vector[ix1:ix2]
    area = trapz(fft_slice)
    return area

def calc_spectrum(signal,rate):
    #calculate complex fft

    # pad with zeros?
    #padded_signal = np.zeros(len(signal*2))
    #padded_signal[:len(signal)] = signal
    #signal = padded_signal
    npts = len(signal)

    freq = np.arange(npts)/(npts/rate)
    freq = freq[:(npts/2)+1] #single sided
    #print('freq len ', len(freq))

    sp = np.fft.fft(signal)/npts
    sp = sp[:(npts/2)+1]
    #print('sp len ', len(sp))

    return freq, abs(sp.real)

def get_fft_peak(spectrum, freq, atfrequency=None):
    # find the peak values for spectrum
    if atfrequency is None:
        maxidx = spectrum.argmax(axis=0)
        f = freq[maxidx]
        spec_peak = np.amax(spectrum)
    else:
        f = atfrequency
        spec_peak = spectrum[freq==f]
    return spec_peak, f

def make_tone(freq,db,dur,risefall,samplerate, caldb=100, calv=0.1):
    """
    Produce a pure tone signal 

    :param freq: Frequency of the tone to be produced (Hz)
    :type freq: int
    :param db: Intensity of the tone in dB SPL
    :type db: int
    :param dur: duration (seconds)
    :type dur: float
    :param risefall: linear rise fall of (seconds)
    :type risefall: float
    :param samplerate: generation frequency of tone (Hz)
    :type samplerate: int
    :param caldb: Reference intensity (dB SPL). Together with calv, provides a reference point for what intensity equals what output voltage level
    :type caldb: int
    :param calv: Reference voltage (V). Together with calv, provides a reference point for what intensity equals what output voltage level
    :type calv: float
    """
    npts = dur * samplerate
    try:
        amp = (10 ** ((db-caldb)/DBFACTOR)*calv)

        if VERBOSE:
            print("current dB: {}, attenuation: {}, current frequency: {} kHz, AO Amp: {:.6f}".format(db, atten, freq/1000, amp))
            print("cal dB: {}, V at cal dB: {}".format(caldb, calv))

        rf_npts = risefall * samplerate
        #print('amp {}, freq {}, npts {}, rf_npts {}'
        # .format(amp,freq,npts,rf_npts))
    
        tone = amp * np.sin((freq*dur) * np.linspace(0, 2*np.pi, npts))
        #add rise fall
        if risefall > 0:
            tone[:rf_npts] = tone[:rf_npts] * np.linspace(0,1,rf_npts)
            tone[-rf_npts:] = tone[-rf_npts:] * np.linspace(1,0,rf_npts)
        
        timevals = np.arange(npts)/samplerate

        # in the interest of not blowing out the speakers I am going to set this to 5?
        if np.amax(abs(tone)) > 5:
            print("WARNING: OUTPUT VOLTAGE {:.2f} EXCEEDS MAXIMUM, RECALULATING".format(np.amax(abs(tone))))
            tone = tone/np.amax(abs(tone))

    except:
        print("WARNING: Unable to produce tone")
        tone = np.zeros(npts)
        timevals = np.arange(npts)/samplerate
        raise

    return tone, timevals


def spectrogram(source, nfft=512, overlap=90, window='hanning'):
    if isinstance(source, basestring):
        try:
            sr, wavdata = wv.read(source)
        except:
            print u"Problem reading wav file"
            raise
        wavdata = wavdata.astype(float)
    else:
        sr, wavdata = source
    duration = len(wavdata)/sr
    # mx = np.amax(wavdata)
    # wavdata = wavdata/mx
    if window == 'hanning':
        winfnc = mlab.window_hanning
    elif window == 'hamming':
        winfnc = np.hamming(nfft)
    elif window == 'blackman':
        winfnc = np.blackman(nfft)
    elif window == 'bartlett':
        winfnc = np.bartlett(nfft)
    elif window == None or window == 'none':
        winfnc = mlab.window_none

    noverlap = int(nfft*(float(overlap)/100))

    Pxx, freqs, bins = mlab.specgram(wavdata, NFFT=nfft, Fs=sr, noverlap=noverlap,
                                     pad_to=nfft*2, window=winfnc, detrend=mlab.detrend_none,
                                     sides='default', scale_by_freq=True)

    # convert to db scale for display
    spec = 10. * np.log10(Pxx)
    # spec = np.nan_to_num(spec)
    # remove -inf values from spec array
    spec[np.isneginf(spec)] = np.nan
    spec[np.isnan(spec)] = np.nanmin(spec)

    return spec, freqs, bins, duration
