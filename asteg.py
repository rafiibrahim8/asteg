#!/bin/python3
import argparse
import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, filtfilt

VERSION = 0.1
VERSION_CODE = 0

PULSE_DUR = 0.02 #sec
META_DURATION = PULSE_DUR*10
AMP = 1000.0 #absloute, MAX = 32767.0
F_LIST = [17600,18000,18400,18800]*2
WINDOW = 200
THRESHOLD = 650

def secs_required(d,fn:str=None):
	META_LEN = 10 #bytes
	l = len(d)+META_LEN
	if(fn):
		l+=len(fn)
	return l*PULSE_DUR

def get_meta(d:bytes,file_name=None,is_enc=False):
	ret = bytearray('aSx'.encode()) #reserve
	[ret.append(b) for b in len(d).to_bytes(4,'big')] #payload len
	if(file_name!=None):
		if(len(file_name)>127):
			raise ValueError('Maximum allowable file name length is 127')
		ret.append((len(file_name)<<1 | (1 if is_enc else 0))& 0xFF) #file name length + is enc
	else:
		ret.append((1 if is_enc else 0)) #just_is enc for text
	ret.append(VERSION_CODE) #version code
	ret.append(0) #reserve
	return ret
	
def __tobits(d):
    return [d>>7 & 1,d>>6 & 1,d>>5 & 1,d>>4 & 1,d>>3 & 1,d>>2 & 1,d>>1 & 1,d & 1]

def tobits(d):
    if(isinstance(d,bytes)):
        for b in d:
            yield __tobits(b)
    else:
        raise TypeError

def tobyte(bits:list):
    ret = 0
    for b in bits:
        ret = (ret<<1) | (b & 1)
    return ret

def toint(bytes_):
    return int.from_bytes(bytes(bytes_),'big')

def to_str(bytes_):
    return bytes(bytes_).decode()

def __gen_one(bit,time = 0.010, s_rate = 44100,f=1000,amp=1.0):
    if(int(bit) == 0):
        return np.zeros(int(time*s_rate))
    else:
        return amp*np.sin([2*np.pi*f*t/s_rate for t in range(int(time*s_rate))])

def gen_sig(data:bytes, duration = 0.010, s_rate = 44100,f:list=[18000,18500,19000,19500,18000,18500,19000,19500], amp=1.0):
    dx = [np.zeros(0) for i in range(8)]
    for l in tobits(data):
        for i in range(8):
            dx[i]=np.append(dx[i],__gen_one(l[i],time=duration,s_rate=s_rate,f=f[i],amp=amp))
    return dx

def __butter_bandstop(lowcut, highcut, fs, f_type,order):
    b, a = butter(order, [lowcut, highcut], btype=f_type,fs=fs)
    return b, a

def filter(data, lowcut=17500, highcut=20000, fs=44100, f_type = 'bandpass',order=7):
    b, a = __butter_bandstop(lowcut, highcut, fs, f_type, order)
    y = filtfilt(b, a, data)
    return np.array(y).astype('int16')

def determine_high_low(l):
    size = 44
    sliced = [l[i:i+size] for i in range(0,len(l),size)]
    if(len(sliced[-1])<size):
        sliced.remove(sliced[-1])
    maxes = []
    for s in sliced:
        maxes.append(np.max(s))
    avg = sum(maxes)/len(maxes)
    return 1 if avg>THRESHOLD else 0

def extract_data(channels:list):
    data_channels=[]
    for chnl in channels:
        for i in range(4):
            freq = F_LIST[i]
            data_channels.append(filter(chnl.get_array_of_samples(),freq-WINDOW,freq+WINDOW,chnl.frame_rate))
    
    dbytes = []
    symbol_num = int(len(data_channels[0])/(channels[0].frame_rate*PULSE_DUR)) # int((len(channels[0])/1000)/PULSE_DUR) #another formula 
    for i in range(symbol_num): 
        bits=[]
        for chnl in data_channels:
            bits.append(determine_high_low(chnl[int(44100*PULSE_DUR*i):int(44100*PULSE_DUR*(i+1))]))
        dbytes.append(tobyte(bits))
    
    return dbytes

def put(in_file, out_file, payload, is_file):
    if(is_file):
        with open(payload,'rb') as data_file:
            data = data_file.read()
            meta = get_meta(data,payload)
    else:
        data = payload.encode()
        meta = get_meta(data)
    
    to_embed = meta
    to_embed.extend(data)
    if(is_file):
        to_embed.extend(payload.encode())
    
    sound = AudioSegment.from_file(open(in_file,'rb'))

    if(secs_required(to_embed)>sound.duration_seconds):
        print('Audio is too short in length. You need at least %.3fs of audio to embed this message.' %(secs_required(to_embed)))
        exit
    
    encoded = gen_sig(bytes(to_embed),duration=PULSE_DUR,s_rate=sound.frame_rate,f=F_LIST,amp=AMP)

    s_channels = sound.split_to_mono()

    for i in range(len(s_channels)):
        filtered = filter(data=s_channels[i].get_array_of_samples(),lowcut=17000,highcut=19500,fs=s_channels[i].frame_rate,f_type='bandstop')
        s_channels[i] = AudioSegment(filtered.tobytes(),frame_rate = s_channels[i].frame_rate,sample_width = filtered.dtype.itemsize,channels = 1)
        for e in encoded[i*4 : (i+1)*4]:
            ex = e.astype('int16')
            s_channels[i]=s_channels[i].overlay(AudioSegment(ex.tobytes(),frame_rate=s_channels[i].frame_rate,sample_width = ex.dtype.itemsize,channels = 1))

    new_sound = AudioSegment.from_mono_audiosegments(s_channels[0],s_channels[1])
    
    if(not out_file.endswith('.wav')):
        out_file = out_file + '.wav'
    
    new_sound.export(open(out_file,'wb'),'wav').close()

def extract(in_file):
    if(not in_file.endswith('.wav')):
        print('This program can desteg from wav format only. Your filename is',in_file) #this program only save in wav format
        exit()
    sound = AudioSegment.from_wav(open(in_file,'rb'))
    sound_channels = sound.split_to_mono()

    meta_samples_len = int(sound.frame_rate*META_DURATION)
    sliced_channels = [chnl.get_sample_slice(0,meta_samples_len) for chnl in sound_channels]
    meta = extract_data(sliced_channels)
    payload_len = int.from_bytes(meta[3:7],'big')
    file_name_len = meta[7]>>1
    if(to_str(meta[:2])!='aS'):
        print('Error: The file',in_file,"doesn't contain steg data.")
        exit()
    data_samples_len = int(sound.frame_rate*PULSE_DUR*(payload_len+file_name_len))
    sliced_channels = [chnl.get_sample_slice(meta_samples_len,data_samples_len+meta_samples_len) for chnl in sound_channels]
    data = extract_data(sliced_channels)
    if(file_name_len==0): #text type 
        print(to_str(data))
    else:
        file_name = to_str(data[len(data)-file_name_len:])
        with open(file_name,'wb') as towrite:
            towrite.write(bytearray(data[:len(data)-file_name_len]))
        print('Extracted file:',file_name)
    
    # is_enc = (meta[7] & 1) == 1
    # version = meta[8]
    # print(payload_len,file_name_len,is_enc,version)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Adding secret to audio.',add_help=False)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p','--put',action='store_true',dest='is_put',help='Embed file/message to the input file.')
    group.add_argument('-x','--extract',action='store_false',dest='is_put',help='Extract file/messgae from the input file.')

    parser.add_argument('-i','--input',required=True,dest='in_file',metavar='FILE',help='The input file to to process.')
    parser.add_argument('-o','--output',required=False,dest='out_file',metavar='FILE',help='The destination file name. Reqired considered if embedding.')
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-f','--file',dest='s_file',metavar='FILE',help='Will embed the provided file inside input file.')
    group.add_argument('-t','--text',dest='s_text',metavar='message',help='Will embed the text provided.')
    
    parser.add_argument('-v','--version',help='Prints version information.',action='version',version= 'v'+str(VERSION))
    parser.add_argument('-h','--help', help='Show this help message and exit.',action='help')

    args = parser.parse_args()
    
    if(args.is_put and args.s_file==None and args.s_text==None):
        parser.error('-t/--text or -f/--file FILE is required when -p/--put')
    
    if(args.is_put and args.out_file==None):
        parser.error('-o/--output FILE is required when -p/--put')

    if(args.is_put):
        isFile = True
        pload = args.s_file
        if(args.s_file == None):
            isFile = False
            pload = args.s_text
        put(args.in_file, args.out_file, pload, isFile)
    else:
        extract(args.in_file)

