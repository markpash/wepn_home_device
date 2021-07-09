import pyaudio
import wave
import numpy as np
import pylab
import os
import sys
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../../'
sys.path.append(up_dir)
from lcd import LCD as LCD
from PIL import Image
from PIL import ImageDraw
import time
import matplotlib.pyplot as plt
lcd = LCD()
lcd.set_lcd_present(1)



channels = 2
def record(side):

    chunk = 1024  # Record in chunks of 1024 samples
    chunk = 4*2048  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    fs = 44100  # Record at 44100 samples per second
    fs = 16000  # Record at 44100 samples per second
    seconds = 5
    filename = "output_"+side+".wav"

    p = pyaudio.PyAudio()  # Create an interface to PortAudio

    print("*"*25)
    print("*"*25)
    print('Recording ' + side)

    stream = p.open(format=sample_format,
                    input_device_index = 1,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True)

    frames = []  # Initialize array to store frames

    # Store data in chunks for 3 seconds
    for i in range(0, int(fs / chunk * seconds)):
        data = stream.read(chunk)
        frames.append(data)

    # Stop and close the stream 
    stream.stop_stream()
    stream.close()
    # Terminate the PortAudio interface
    p.terminate()
    soundplot(data)

    print('Finished recording '+ side)
    print("*"*25)
    print("*"*25)
    depth = p.get_sample_size(sample_format)
    frame_bytes = b''.join(frames)
    # Save the recorded data as a WAV file
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(depth)
    wf.setframerate(fs)
    wf.writeframes(frame_bytes)
    wf.close()
    return depth, fs, frame_bytes

def soundplot(chunk):
    data = np.fromstring(chunk,dtype=np.int16)

    times = np.linspace(
        0, # start
        len(data) / 44100,
        num = len(data)
    )
    fig = plt.figure(1, figsize=(240,240), dpi=10)
      
    # title of the plot
    plt.title("Sound Wave")
      
    # label of x-axis
    plt.xlabel("Time")
     
    # actual ploting
    plt.plot(times, data)
      
    # you can also save
    # the plot using
    #plt.savefig("filename.png")
    #img = Image.open("filename.png")
    fig.canvas.draw()
    img = Image.frombytes('RGB',
        fig.canvas.get_width_height(), fig.canvas.tostring_rgb())
    im1 = img.resize((240,240))
    lcd.show_image(im1)

def save_wav_channel(fn, depth, fs, sdata, channel):
    '''
    Take Wave_read object as an input and save one of its
    channels into a separate .wav file.
    '''
    # Read data
    #nch   = wav.getnchannels()
    #depth = wav.getsampwidth()
    #wav.setpos(0)
    #sdata = wav.readframes(wav.getnframes())

    # Extract channel data (24-bit data not supported)
    typ = { 1: np.uint8, 2: np.uint16, 4: np.uint32 }.get(depth)
    if not typ:
        raise ValueError("sample width {} not supported".format(depth))
    print ("Extracting channel {} out of {} channels, {}-bit depth".format(channel+1, channels, depth*8))
    data = np.fromstring(sdata, dtype=typ)
    ch_data = data[channel::channels]

    # Save channel to a separate file
    outwav = wave.open(fn, 'w')
    #outwav.setparams(wav.getparams())
    outwav.setnchannels(1)
    outwav.setsampwidth(depth)
    outwav.setframerate(fs)
    outwav.writeframes(ch_data.tostring())
    outwav.close()
print("-"*25)
print("-"*25)
print("Cover right microphone, say 'left'")
input("Press enter when ready")
depth, fs, frame_bytes = record("left")
save_wav_channel('left.wav', depth, fs, frame_bytes, 0)
print("-"*25)
print("Cover left microphone, say 'right'")
input("Press enter when ready")
depth, fs, frame_bytes = record("right")
save_wav_channel('right.wav', depth, fs, frame_bytes, 1)
print("-"*25)
print("don't cover any microphone, say 'both'")
input("Press enter when ready")
depth, fs, frame_bytes = record("both")
print("-"*25)
print("-"*25)

