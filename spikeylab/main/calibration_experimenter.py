import os
import logging
import numpy as np

from spikeylab.tools.util import create_unique_path
from spikeylab.main.protocol_acquisition import Experimenter
from spikeylab.stim.factory import CCFactory
from spikeylab.stim.types.stimuli_classes import PureTone
from spikeylab.io.players import FinitePlayer
from spikeylab.stim.stimulusmodel import StimulusModel
from spikeylab.tools.audiotools import spectrogram, calc_spectrum, get_fft_peak, calc_db
from spikeylab.data.dataobjects import AcquisitionData

USE_FFT = False

class CalibrationExperimenter(Experimenter):
    def __init__(self, signals):
        Experimenter.__init__(self, signals)

        self.group_name = 'calibration_test_1'

        self.player = FinitePlayer()

        self.stimulus = StimulusModel()
        CCFactory.init_stim(self.stimulus)
        self.protocol_model.insertNewTest(self.stimulus, 0)

        # add in a tone at the calibration frequency and intensity
        control_stim = StimulusModel()
        self.control_tone = PureTone()
        control_stim.insertComponent(self.control_tone)
        self.protocol_model.insertNewTest(control_stim, 0)

        save_data = True

    def set_save_params(self, folder=None, name=None):
        """Folder and filename where raw experiment data will be saved to

        :param savefolder: folder for experiment data
        :type savefolder: str
        :param samename: filename template, without extention for individal experiment files
        :type savename: str
        """
        if folder is not None:
            self.savefolder = folder
        if name is not None:
            self.savename = name

    def stash_calibration(self, attenuations, freqs, frange, calname):
        self.calibration_vector = attenuations
        self.calibration_freqs = freqs
        self.calibration_frange = frange
        self.calname = calname

    def apply_calibration(self, apply_cal):
        self.apply_cal = apply_cal

    def set_duration(self, dur):
        self.stimulus.data(self.stimulus.index(0,0)).setDuration(dur)

    def set_reps(self, reps):
        self.stimulus.setRepCount(reps)

    def _initialize_run(self):
        self.calibration_frequencies = []
        self.calibration_indexes = []

        self.current_dataset_name = self.group_name
        self.datafile.init_group(self.current_dataset_name, mode='calibration')
        self.datafile.init_data(self.current_dataset_name, mode='calibration',
                                dims=(self.stimulus.traceCount(), self.stimulus.repCount()),
                                nested_name='fft_peaks')
        self.datafile.init_data(self.current_dataset_name, mode='calibration',
                                dims=(self.stimulus.traceCount(), self.stimulus.repCount()),
                                nested_name='vmax')

        info = {'samplerate_ad': self.player.aisr}
        self.datafile.set_metadata(self.current_dataset_name, info)

        logger = logging.getLogger('main')
        logger.info('calibration dataset %s' % self.current_dataset_name)

        self.player.set_aochan(self.aochan)
        self.player.set_aichan(self.aichan)

        self.control_tone.setDuration(self.stimulus.data(self.stimulus.index(0,0)).duration())
        self.control_tone.setRisefall(self.stimulus.data(self.stimulus.index(0,0)).risefall())
        print 'setting calibration frequency', self.calf
        self.control_tone.setFrequency(self.calf)
        self.control_tone.setIntensity(self.caldb)
        self.calpeak = None
        self.trace_counter = -1 # initialize to -1 instead of 0

        if self.apply_cal:
            self.protocol_model.setCalibration(self.calibration_vector, self.calibration_freqs, self.calibration_frange)
        else:
            self.protocol_model.setCalibration(None, None, None)

    def _initialize_test(self, test):
        self.peak_avg = []
        return

    def _process_response(self, response, trace_info, irep):
        freq, spectrum = calc_spectrum(response, self.player.aisr)

        f = trace_info['components'][0]['frequency'] #only the one component (PureTone)
        db = trace_info['components'][0]['intensity']
        # print 'f', f, 'db', db
        
        # spec_max, max_freq = get_fft_peak(spectrum, freq)
        spec_peak_at_f = spectrum[freq == f]
        if len(spec_peak_at_f) != 1:
            print u"COULD NOT FIND TARGET FREQUENCY ",f
            print 'target', f, 'freqs', freq
            spec_peak_at_f = np.array([-1])
            # self._halt = True
        peak_fft = spec_peak_at_f[0]

        # vmax = np.amax(abs(response))
        vmax = np.sqrt(np.mean(pow(response,2)))*1.414 #rms

        if self.trace_counter >= 0:
            if irep == 0:
                if db == self.caldb:
                    self.calibration_frequencies.append(f)
                    self.calibration_indexes.append(self.trace_counter)
                self.trace_counter +=1
                self.peak_avg = []

            self.datafile.append(self.current_dataset_name, spec_peak_at_f, 
                                 nested_name='fft_peaks')
            self.datafile.append(self.current_dataset_name, np.array([vmax]), 
                                 nested_name='vmax')
            self.datafile.append_trace_info(self.current_dataset_name, trace_info)

            self.signals.response_collected.emit(self.aitimes, response)
            self.signals.calibration_response_collected.emit((f, db), spectrum, freq, peak_fft, vmax)
        
        # calculate resultant dB and emit
        if USE_FFT:
            self.peak_avg.append(peak_fft)
        else:
            self.peak_avg.append(vmax)
        if irep == self.nreps-1:
            mean_peak = np.mean(self.peak_avg)
            if f == self.calf and db == self.caldb and self.trace_counter == -1:
                # this always is the first trace
                self.calpeak = mean_peak
                self.trace_counter +=1
            else:
                resultdb = calc_db(mean_peak, self.calpeak) + self.caldb
                self.signals.average_response.emit(f, db, resultdb)

    def process_calibration(self, save=True):
        """processes the data gathered in a calibration run (does not work if multiple
            calibrations), returns resultant dB"""
        print 'process the calibration'

        vfunc = np.vectorize(calc_db)

        if USE_FFT:
            peaks = np.mean(abs(self.datafile.get('fft_peaks')), axis=1)
        else:
            peaks = np.mean(abs(self.datafile.get('vmax')), axis=1)

        # print 'calibration frequencies', self.calibration_frequencies
        # cal_index = self.calibration_indexes[self.calibration_frequencies.index(self.calf)]
        # cal_peak = peaks[cal_index]
        # cal_vmax = vmaxes[cal_index]

        # print 'vfunc inputs', vmaxes, self.caldb, cal_vmax

        resultant_dB = vfunc(peaks, self.calpeak) * -1 #db attenuation

        print 'calibration frequences', self.calibration_frequencies, 'indexes', self.calibration_indexes
        print 'attenuations', resultant_dB

        calibration_vector = resultant_dB[self.calibration_indexes].squeeze()
        # save a vector of only the calibration intensity results
            # delete the data saved to file thus far.
        self.datafile.delete_group(self.current_dataset_name)
        return resultant_dB, '', self.calf
