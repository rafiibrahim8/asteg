# asteg
#### Steganography : Hiding text or file inside an audio

# DESCRIPTION
This program can be used for hiding text or a file inside an audio file. The program utilizes the high-frequency component of an audio file to embed its payload. Which is almost undetectable with the human ear. You will never notice any drop in audio quality.
# INSTALLATION
From a command line enter the command to install asteg
```
pip install asteg
```
You need to have python 3 installed. asteg won't run on python 2.
# USES
###### Hiding 'Hello World!' inside infile.mp3. The resultant file is outfile.wav
#### 
```sh
$ asteg -p -o outfile.wav -i infile.mp3 -t 'Hello world!'
```
###### Hiding secret.odt inside infile.mp3. The resultant file is outfile.wav
#### 
```sh
$ asteg -p -o outfile.wav -i infile.mp3 -f secret.odt
```

# META
The data is formatted first before embedding inside the audio. First a 10 byte header is added at the beginning of the data. The header format is as follows:
| Number of Bytes| Description |
| ------ | ------ |
| 2 | 'aS' Always|
| 1 | <Reserved> |
| 4 | Payload length |
| 1 | Length for filename for file embedding (7bit) + encryption flag (1bit)|
| 1 | Version of used program |
| 1 | <Reserved> |

# DEPENDENCY
  - pydub
  - numpy
  - scipy

# CURRENT LIMITATIONS

  - Does not support encryption. (Has plan to add)
  - Generates uncompressed wav file. Which is too big.


