from pathlib import Path
from mms_msg.databases.single_speaker.vpc.create_json import read_speakers_vctk, read_speakers_libri, get_transcription, get_vad_info, create_json

#database_path = "/home/jule/datasets/VPC"
database_path = "/media/Daten/datasets/VPC"
json_path = "vpc.json"

#read_speakers_vctk(Path(database_path).absolute()  / 'vctk_dev' / 'SPEAKERS.txt')
#print(read_speakers_libri(Path(database_path).absolute()))
#get_transcription(Path(database_path).absolute(), set='libri')
#get_vad_info(Path(database_path).absolute(), set='vctk')

create_json(Path(database_path).absolute(), True)