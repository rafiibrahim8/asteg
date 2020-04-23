# asteg
#### Steganography : Hiding text or file inside an audio

# DESCRIPTION
This program can be used for hiding text or a file inside an audio file. The program utilizes the high-frequency component of an audio file to embed its payload. Which is almost undetectable with the human ear. You will never notice any drop in audio quality.

# USES
###### Hiding 'Hello World!' inside infile.mp3. The resulten file is outfile.wav
#### 
```sh
$ python3 asteg.py -p -o outfile.wav -i infile.mp3 -t 'Hello world!'
```
###### Hiding secret.odt inside infile.mp3. The resulten file is outfile.wav
#### 
```sh
$ python3 asteg.py -p -o outfile.wav -i infile.mp3 -f secret.odt
```

# META
The data is formated frist before embeding inside the audio. Frist a 10 byte header is added at the begaining of the data. The header format is as follows:
| Number of Bytes| Description |
| ------ | ------ |
| 2 | 'aS' Always|
| 1 | <Reserved> |
| 4 | Payload length |
| 1 | Length for filename for file embedding (7bit) + encription flag (1bit)|
| 1 | Version of used program |
| 1 | <Reserved> |

# DEPENDENCY
  - pydub
  - numpy
  - scipy

# CURRENT LIMITATIONS

  - Does not support encription. (Has plan to add)
  - Genarates uncompressed wav file. Which is too big.


