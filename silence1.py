import os
import numpy
import scipy.io.wavfile as wf
from pydub import AudioSegment
import sys
import streamlit as st
import time
from time import sleep
import base64
from PIL import Image






def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    '''
    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms
    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0  # ms
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
        trim_ms += chunk_size

    return trim_ms

class VoiceActivityDetection:

    def __init__(self):
        self.__step = 160
        self.__buffer_size = 160 
        self.__buffer = numpy.array([],dtype=numpy.int16)
        self.__out_buffer = numpy.array([],dtype=numpy.int16)
        self.__n = 0
        self.__VADthd = 0.
        self.__VADn = 0.
        self.__silence_counter = 0

    # Voice Activity Detection
    # Adaptive threshold
    def vad(self, _frame):
        frame = numpy.array(_frame) ** 2.
        result = True
        threshold = 0.1
        thd = numpy.min(frame) + numpy.ptp(frame) * threshold
        self.__VADthd = (self.__VADn * self.__VADthd + thd) / float(self.__VADn + 1.)
        self.__VADn += 1.

        if numpy.mean(frame) <= self.__VADthd:
            self.__silence_counter += 1
        else:
            self.__silence_counter = 0

        if self.__silence_counter > 20:
            result = False
        return result

    # Push new audio samples into the buffer.
    def add_samples(self, data):
        self.__buffer = numpy.append(self.__buffer, data)
        result = len(self.__buffer) >= self.__buffer_size
        # print('__buffer size %i'%self.__buffer.size)
        return result

    # Pull a portion of the buffer to process
    # (pulled samples are deleted after being
    # processed
    def get_frame(self):
        window = self.__buffer[:self.__buffer_size]
        self.__buffer = self.__buffer[self.__step:]
        # print('__buffer size %i'%self.__buffer.size)
        return window

    # Adds new audio samples to the internal
    # buffer and process them
    def process(self, data):
        if self.add_samples(data):
            while len(self.__buffer) >= self.__buffer_size:
                # Framing
                window = self.get_frame()
                # print('window size %i'%window.size)
                if self.vad(window):  # speech frame
                	self.__out_buffer = numpy.append(self.__out_buffer, window)
                # print('__out_buffer size %i'%self.__out_buffer.size)

    def get_voice_samples(self):
        return self.__out_buffer

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

RAWDATAPATH = "/Users/ishitasaluja/Desktop/ac/output1.wav"


image = Image.open('optum.png')
st.image(image)
st.title("Silence Removal Model")

def main():
    filein = st.file_uploader("Choose a file", type=['MP3', 'WAV'])
    
    fileout = RAWDATAPATH
    if st.button("Remove Silence"):
        if filein is not None:
            st.audio(filein, format='wav')
            sound = AudioSegment.from_wav(filein)
            sound = sound.set_channels(1)
            sound.export("output.wav", format="wav")

            
            wav = wf.read("output.wav")
            sr = wav[0]
            c0 = wav[1]

            vad = VoiceActivityDetection()
            vad.process(c0)
            voice_samples = vad.get_voice_samples()
            wf.write(fileout,sr,voice_samples)
            # Trimming in case there is something else to remove
            sound = AudioSegment.from_file(fileout, format="wav")
            start_trim = detect_leading_silence(sound)
            end_trim = detect_leading_silence(sound.reverse())

            duration = len(sound)
            trimmed_sound = sound[start_trim:duration-end_trim]
            trimmed_sound.export(fileout, format="wav")
            st.markdown(get_binary_file_downloader_html(fileout, 'output file without silence'), unsafe_allow_html=True)

#python silenceRemoval.py path/to/in.wav path/to/out.wav

main()