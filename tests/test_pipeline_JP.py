'''
Script to save VPC meetings to disk
25.04.2023 JP
'''
import mms_msg
import soundfile as sf
import os
from pathlib import Path
from collections import defaultdict
from paderbox.io import dump_json
from tqdm import tqdm
import numpy as np

np.random.seed(1234)

# define path to json file, input data folder, output folder
json_path = '/media/Daten/datasets/jsons/vpc_cutted.json'
input_path = '/media/Daten/datasets/VPC'
data_path = '/media/Daten/datasets/VPC_meeting_mix'
out_json_path = os.path.join(data_path, 'vpc_cutted_mix_all_utt_unique_spk.json')

# define random seed 
rng = '_rng1234'

# define audio params
sample_rate = 16000

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
                    overlap_conditions=overlap_conditions,
                    snr_min_max=(100, 100), 
                    within_chapter=False
                    )
dataset_names = db.dataset_names

database_dict = dict()    
examples = defaultdict(dict)
ex = defaultdict(dict)
for sub_set in dataset_names:
    dset = db.get_dataset(sub_set + rng)
    Path(os.path.join(data_path, sub_set)).mkdir(parents=True, exist_ok=True)

    temp = dict(dset.items())
    ex = defaultdict(dict)  
    for meeting in temp:
        ex[temp[meeting][0]] = temp[meeting][1]
    examples[sub_set] = ex

    # save meetings with unique speaker combis
    for idx in tqdm(range(len(dset)), desc=sub_set):
        ex = db.load_example(dset[idx])
        filename = os.path.join(data_path, sub_set, ex['example_id'] + '.wav')
        sf.write(filename, ex['audio_data']['observation'], sample_rate)
        
# finalize database dict
database_dict['datasets'] = examples
dump_json(database_dict, out_json_path)
print('Done!')