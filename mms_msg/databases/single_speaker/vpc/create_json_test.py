from pathlib import Path
from create_json import create_json, read_speakers_vctk, read_speakers_libri, get_transcription

database_path = "/home/jule/datasets/VPC"
json_path = "vpc.json"

#read_speakers_vctk(Path(database_path).absolute()  / 'vctk_dev' / 'SPEAKERS.txt')
print(read_speakers_libri(Path(database_path).absolute()))
#get_transcription(Path(database_path).absolute(), set='libri')

#create_json(Path(database_path).absolute(), True)