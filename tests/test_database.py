from lazy_dataset.database import JsonDatabase
from collections import defaultdict
import os
import numpy as np

orig_data_path = "/media/Daten/datasets/VPC/"
json_path = "/media/Daten/datasets/VPC_meeting_mix/vpc_cutted_mix_all_utt_unique_spk.json"
# get VPC meeting mix data
db = JsonDatabase(json_path)
dataset_names = db.dataset_names

sample_rate = 16000

total_len = 0
total_dur = 0
for subset in dataset_names:
    # get mixed subset data
    dset = db.get_dataset(subset)
    num_meetings = len(dset)
    print(num_meetings)
    total_len += num_meetings

    utterances_mix = defaultdict(dict)
    duration = np.zeros(num_meetings)
    for idx in range(len(dset)):
        duration[idx] = dset[idx]["num_samples"]["observation"]/sample_rate/60

        utt_ids = dset[idx]['source_id']
        spkrs_list = dset[idx]['speaker_id']
        for speaker_id, utt_id in zip(spkrs_list, utt_ids):
            if speaker_id in utterances_mix.keys():
                if utt_id in utterances_mix[speaker_id].keys():
                    assert(f"Duplicate! At {subset}, speaker {speaker_id}, utterance {utt_id}.")
            utterances_mix[speaker_id][utt_id] = 1
    print(duration)
    total_dur += sum(duration)

    # compare to info from original dataset
    utt_file = os.path.join(orig_data_path, subset, 'utt2spk')
    with open(utt_file, 'r') as f:
        for line in f.readlines():
            utt_id, speaker_id = line.replace('\n', '').split(' ', maxsplit=1)
            if speaker_id in utterances_mix.keys():
                if not utt_id in utterances_mix[speaker_id]:
                    assert(f"Missing utterance! At {subset}, speaker {speaker_id}, utterance {utt_id}.")
            else:
                assert(f"Missing speaker! At {subset}, speaker {speaker_id}.")
print(total_len, total_dur/60)