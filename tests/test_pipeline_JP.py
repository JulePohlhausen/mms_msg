'''
Script to save VPC meetings to disk
25.04.2023 JP
'''
import mms_msg
import paderbox as pb
import soundfile as sf
import os
from pathlib import Path
from tqdm import tqdm

# define path to json file
json_path = '/media/Daten/datasets/jsons/vpc_cutted.json'

# define path to output folder
data_path = '/media/Daten/datasets/VPC_meeting_mix'

# define audio params
sample_rate = 16000
duration = 60*sample_rate

# define overlap and silence settings
overlap_conditions = {
    'max_concurrent_spk': 2,
    'p_silence': 0,
    'maximum_silence': 1,
    'maximum_overlap': 0,
}

# create meetings based on VPC test data
db = mms_msg.databases.meeting.vpc_meeting.AnechoicVPCMeeting(
                    source_json_path=json_path,
                    num_speakers=(3, 4), 
                    duration=duration, 
                    overlap_conditions=overlap_conditions,
                    snr_min_max=(100, 100), 
                    within_chapter=False
                    )
dataset_names = db.dataset_names

for sub_set in dataset_names:
    if 'test' in sub_set: # just use test set
        dset = db.get_dataset(sub_set)
        print('... saving ', sub_set)
        Path(os.path.join(data_path, sub_set)).mkdir(parents=True, exist_ok=True)
        for idx in tqdm(range(len(dset))):
            ex = db.load_example(dset[idx])
            filename = os.path.join(data_path, sub_set, ex['example_id'] + '.wav')
            sf.write(filename, ex['audio_data']['observation'], sample_rate)
print('Done!')

#database_dict = {'datasets': {dataset_name: dict(db.get_dataset(dataset_name).items(), desc=dataset_name) for dataset_name in dataset_names}}
#pb.io.dump(database_dict, os.path.join(data_path, 'vpc_mix.json'))