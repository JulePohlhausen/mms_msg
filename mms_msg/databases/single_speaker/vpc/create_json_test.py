from pathlib import Path
from create_json import read_speakers_vctk

database_path = "/media/Daten/datasets/VPC"

read_speakers_vctk(Path(database_path).absolute()  / 'vctk_dev' / 'speaker-info.txt')