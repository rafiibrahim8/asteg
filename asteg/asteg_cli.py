#!/usr/bin/python3
import argparse
import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, filtfilt

from asteg import __version__, VERSION_CODE

PULSE_DUR = 0.02                        # sec
META_LEN = 10                           # bytes
META_DURATION = PULSE_DUR * META_LEN    # 10 byte for metadata
AMP = 1000.0                            # amplitude of audio component. It is possible to use lower or higher amplitude. absolute, MAX = 32767.0
F_LIST = [17600,18000,18400,18800]*2    # freqency in which data will be encoded.
WINDOW = 200                            # it is the distance from center frequency for the filter in both positive and negative direction
THRESHOLD = 0.65 * AMP                  # threshold for a signal count as HIGH
ZONE_SIZE = 44                          # when de-stegging, this number of samples will average together to determine if a signal portion is binary 0 or 1

def secs_required(data, file_name:str = None):  # Calculating miniman length for audio file to embed all data
    l = len(data)+META_LEN
    if(file_name):                              # if user want to embed a file, then we need to embed the file name too
        l+=len(file_name)
    return l*PULSE_DUR

def generate_meta(data:bytes, file_name = None, is_enc = False):            # genarate metadata for putting at the begining of stegged file
    ret = bytearray('aSx'.encode())                                         # reserve, see README.md for more info
    [ret.append(b) for b in len(data).to_bytes(4,'big')]                       # adding payload length to metadata
    if(file_name!=None):                                                    # user is wanting to embed a file, we have to add filename in meta
        if(len(file_name)>127):
            raise ValueError('Maximum allowable file name length is 127')   # maximum allowed filename is 2^7 -1 = 127. Case we have 7 bit to encode the filename length
        ret.append((len(file_name)<<1 | (1 if is_enc else 0))& 0xFF)        # file name length (7-bit) + encryption flag (1-bit)
    else:                                                                   # user is wanting to embed text
        ret.append((1 if is_enc else 0))                                    # no need for file name length, just is_enc for if the text is encrypted
    ret.append(VERSION_CODE)                                                # adding version code of asteg to meta
    ret.append(0)                                                           # reserve, see README.md for more info
    return ret                                                              # returning the crafted metadata
	
def __tobits(b):    # converting a single byte to a list of bits
    return [b>>7 & 1, b>>6 & 1, b>>5 & 1, b>>4 & 1, b>>3 & 1, b>>2 & 1, b>>1 & 1, b & 1]

def tobits(data):                   # converting whole data (which is in bytes) into bits to embed into audio file
    if(isinstance(data, bytes)):     # checking if the data is actually it bytes, or we are in trouble
        for byte in data:           # converting each byte one-by-one
            yield __tobits(byte)
    else:
        raise TypeError             # Oh no! We wanted bytes got something else :(

def tobyte(bits:list):              # when de-stegging we have got bits, now we have to convert them back to byte
    ret = 0                         # return variable
    for b in bits:
        ret = (ret<<1) | (b & 1)    # appending each bit, (big-endian)
    return ret

def toint(bytes_):      # converting bytes to int
    return int.from_bytes(bytes(bytes_),'big') 

def to_str(bytes_):     # converting bytes to string 
    return bytes(bytes_).decode()

def __gen_one(bit, time = 0.010, s_rate = 44100, f = 1000, amp = 1.0):              # genarate a single signal (s_rate = sampling_rate, amp = amplitude)
    if(int(bit) == 0):                                                              # genarating no wave for binary 0 for specified time (usually PULSE_DUR)
        return np.zeros(int(time * s_rate))
    else:                                                                           # genarating sine wave of freqency f for binary 1 for specified time (usually PULSE_DUR)
        return amp*np.sin([2*np.pi*f*t/s_rate for t in range(int(time*s_rate))])

def gen_sig(data:bytes, duration = 0.010, s_rate = 44100, f:list=[18000,18500,19000,19500,18000,18500,19000,19500], amp = 1.0):     # genarate OOK signal for entire data
    dx = [np.zeros(0) for i in range(8)]                                                            # genarating empty array to append data later, data will be encoded in 8 different channel
    for d in tobits(data):                                                                          # going through whole data converted into bits                       
        for i in range(8):                                                                          # adding data to each channel
            dx[i]=np.append(dx[i],__gen_one(d[i],time=duration, s_rate=s_rate, f=f[i], amp=amp))    # appending data to previously created empty array
    return dx                                                                                       # returning the genarated signal

def __butter_bandstop(lowcut, highcut, fs, f_type,order):                               # getting a and b value for butter bandstop filter for filtering signal
    b, a = butter(order, [lowcut, highcut], btype=f_type,fs=fs)
    return b, a

def filter(data, lowcut=17500, highcut=20000, fs=44100, f_type = 'bandpass',order=7):   # making the filter using previous a and b value
    b, a = __butter_bandstop(lowcut, highcut, fs, f_type, order)
    y = filtfilt(b, a, data)                                                            # filtering the data
    return np.array(y).astype('int16')                                                  # saving a bit of AudioSegment required 16 bit integer

def determine_high_low(l):                                              # determine if the portion of signal is binary 0 or 1
    ZONE_SIZE = 44                                                      # slice this portion of signal into zones. each zone having ZONE_SIZE samples.
    sliced = [l[i:i+ZONE_SIZE] for i in range(0, len(l), ZONE_SIZE)]    # slicing...
    if(len(sliced[-1]) < ZONE_SIZE):                                    # removing any zones has less then ZONE_SIZE
        sliced.remove(sliced[-1])
    maxes = []
    for s in sliced:                                                    # geting max values for each zone
        maxes.append(np.max(s))
    avg = sum(maxes) / len(maxes)                                       # averaging maxes for getting for determining the signal portion high or low
    return 1 if avg > THRESHOLD else 0                                

def extract_data(audio_channels:list):  # extract data from audio channel
    data_channels=[]                    # 8 data channel will be added here
    for channel in audio_channels:
        for i in range(4):              # we will get 4 data channel form each audio channel
            freq = F_LIST[i]            # each data channel has it's own freqency. selecting it to filter other signal
            data_channels.append(filter(channel.get_array_of_samples(),freq-WINDOW,freq+WINDOW,channel.frame_rate)) # filtering to get only signal for this data channel
    
    data_bytes = []                     # data in bytes extracted from audio
    symbol_num = int(len(data_channels[0])/(audio_channels[0].frame_rate*PULSE_DUR))                        # determining the number of bits embedded into the each data channel  
    # symbol_num = int((len(audio_channels[0])/1000)/PULSE_DUR) --------- another formula 

    for i in range(symbol_num): 
        bits=[]
        for channel in data_channels:
            bits.append(determine_high_low(channel[int(44100*PULSE_DUR*i):int(44100*PULSE_DUR*(i+1))]))     # getting data in bits from each data_channel, there is 8 data channel so we will get a byte for each i
        data_bytes.append(tobyte(bits))                                                                     # converting back to byte
    
    return data_bytes

def put(in_file, out_file, payload, is_file):               # embed data to audio
    if(is_file):                                            # user wants to embed file, reding it.
        with open(payload,'rb') as data_file:
            data = data_file.read()
            meta = generate_meta(data, file_name = payload) # getting meta to embed at the begaining and future de-stegging
    else:                                                   # user wants to embed text, just converting into bytes
        data = payload.encode()
        meta = generate_meta(data)                          # getting meta to embed at the begaining and future de-stegging
    
    to_embed = meta                                         # we will keep all data that will be embed into audio in variable to_embed
    to_embed.extend(data)                                   # adding data to to_embed
    if(is_file):
        to_embed.extend(payload.encode())                   # if user want's to embed file we need to save the file name too
    
    sound = AudioSegment.from_file(open(in_file,'rb'))      # reading the audio file, in which the data will be embedded

    if(secs_required(to_embed)>sound.duration_seconds):     # checking the length of the audio file is sufficient to embed all data
        print('Audio is too short in length. You need at least %.3fs of audio to embed this message.' %(secs_required(to_embed)))
        exit()
    
    encoded = gen_sig(bytes(to_embed), duration = PULSE_DUR, s_rate = sound.frame_rate, f=F_LIST, amp=AMP)  # encoding binary 0 and 1 into OOK signal

    s_channels = sound.split_to_mono()  # spliting audio channel to embed data to each channel

    for i in range(len(s_channels)):    # embedding data to each channel
        filtered = filter(data=s_channels[i].get_array_of_samples(),lowcut=17000,highcut=19500,fs=s_channels[i].frame_rate,f_type='bandstop')           # deleteing higher freqency component of audio, cause our data will be added here
        s_channels[i] = AudioSegment(filtered.tobytes(),frame_rate = s_channels[i].frame_rate,sample_width = filtered.dtype.itemsize,channels = 1)      # converting filtered value back to AudioSegment object for marging with our OOK signal
        for e in encoded[i*4 : (i+1)*4]:    # adding 4 channel of encoded data into each audio channel
            ex = e.astype('int16')          # AudioSegment required 16 bit integer
            s_channels[i]=s_channels[i].overlay(AudioSegment(ex.tobytes(),frame_rate=s_channels[i].frame_rate,sample_width = ex.dtype.itemsize,channels = 1))   # converting each encoded data channel to AudioSegment and marging with provided audio file

    new_sound = AudioSegment.from_mono_audiosegments(s_channels[0],s_channels[1])   # converting mono audio to usual stereo audio
    
    if(not out_file.endswith('.wav')):                                              # adding file extension if user misses
        out_file = out_file + '.wav'
    
    new_sound.export(open(out_file,'wb'),'wav').close()                             # exporting audio to new file

def extract(in_file):                                                                               # extracting data from steg audio
    if(not in_file.endswith('.wav')):                                                               # file should end with .wav extension
        print('This program can de-steg from wav format only. Your filename is',in_file)            #this program only save in wav format
        exit()
    sound = AudioSegment.from_wav(open(in_file,'rb'))                                               # reading file
    sound_channels = sound.split_to_mono()                                                          # we need data from each audio channel

    meta_samples_len = int(sound.frame_rate * META_DURATION)                                        # to de-steg we need to read meta, to read meta we need to know how long our meta is
    sliced_channels = [channel.get_sample_slice(0,meta_samples_len) for channel in sound_channels]  # slicing length of meta from each channel
    meta = extract_data(sliced_channels)                                                            # extracting meta
    
    if(to_str(meta[:2])!='aS'):                                                                     # checking if the audio has steg data bases on flag. See README.md for more info
        print('Error: The file',in_file,"doesn't contain steg data.")                               # exiting because no steg data is on this audio
        exit()
    payload_len = int.from_bytes(meta[3:7],'big')                                                   # getting payload length from meta
    file_name_len = meta[7]>>1                                                                      # getting file name length from meta
    
    data_samples_len = int(sound.frame_rate*PULSE_DUR*(payload_len+file_name_len))                  # calculating how long in the audio our data exists
    sliced_channels = [channel.get_sample_slice(meta_samples_len,data_samples_len+meta_samples_len) for channel in sound_channels]    # slicing audio channel to the length our audio file contain steg data
    data = extract_data(sliced_channels)                                                            # extracing data
    if(file_name_len==0):                                                                           # file name length is 0, that means text type data was embedded
        print(to_str(data))                                                                         # printing text type data
    else:                                                                                           # a file was embedded 
        file_name = to_str(data[(len(data) - file_name_len):])                                      # extracing file name at the end of data
        with open(file_name,'wb') as towrite:                                                       # writing file
            towrite.write(bytearray(data[:len(data)-file_name_len]))
        print('Extracted file:',file_name)
    
    # is_enc = (meta[7] & 1) == 1
    # version = meta[8]
    # print(payload_len,file_name_len,is_enc,version)

def main():
    parser = argparse.ArgumentParser(description='Adding secret to audio.',add_help=False)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p','--put',action='store_true',dest='is_put',help='Embed file/message to the input file.')
    group.add_argument('-x','--extract',action='store_false',dest='is_put',help='Extract file/message from the input file.')

    parser.add_argument('-i','--input',required=True,dest='in_file',metavar='FILE',help='The input file to to process.')
    parser.add_argument('-o','--output',required=False,dest='out_file',metavar='FILE',help='The destination file name. Reqired considered if embedding.')
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-f','--file',dest='s_file',metavar='FILE',help='Will embed the provided file inside input file.')
    group.add_argument('-t','--text',dest='s_text',metavar='message',help='Will embed the text provided.')
    
    parser.add_argument('-v','--version',help='Prints version information.',action='version',version= 'v'+ __version__)
    parser.add_argument('-h','--help', help='Show this help message and exit.',action='help')

    args = parser.parse_args()
    
    if(args.is_put and args.s_file==None and args.s_text==None):
        parser.error('-t/--text or -f/--file FILE is required when -p/--put')
    
    if(args.is_put and args.out_file==None):
        parser.error('-o/--output FILE is required when -p/--put')

    if(args.is_put):
        isFile = True
        payload = args.s_file
        if(args.s_file == None):                            # cheking if user wants to put file or text
            isFile = False
            payload = args.s_text
        put(args.in_file, args.out_file, payload, isFile)
    else:
        extract(args.in_file)

if __name__ == "__main__":
    main()

