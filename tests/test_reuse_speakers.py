from lazy_dataset.database import JsonDatabase
import numpy as np
import matplotlib.pyplot as plt

# get VPC meeting mix data
json_path = '/media/Daten/datasets/jsons/vpc_cutted_mix.json'
db = JsonDatabase(json_path)
dataset_names = db.dataset_names

fig, ax = plt.subplots(2, 2)
cnt = 0
for subset in dataset_names:
    if 'test' in subset: # just use test set

        # get subset data
        dset = db.get_dataset(subset)

        # find first reuse
        sources = []
        speakers = []
        num_reuse = np.zeros(len(dset))
        num_used = np.zeros(len(dset))
        num_speakers = np.zeros(len(dset))
        for idx in range(len(dset)):
            ex = dset[idx]
            sources.extend(ex['audio_path']['original_source'])
            speakers.extend(set(ex['speaker_id']))

            num_used[idx] = len(set(sources))
            num_reuse[idx] = len(sources) - len(set(sources))

            num_speakers[idx] = len(set(speakers))

        perc_used = num_used / len(dset)
        perc_reused = num_reuse / len(dset)

        # determine num meetings to cover 80% of whole dataset
        num_sub = 0.8*len(dset)
        idx_cover = np.argmax(num_used >= num_sub)
        print(f"{subset}: covers 80% after {idx_cover} meetings")

        # determine num meetings to cover all speakers of whole dataset
        idx_cover = np.argmax(num_speakers >= max(num_speakers))
        print(f"{subset}: covers all speakers after {idx_cover} meetings")

        ax[cnt, 0].plot(num_used)
        ax[cnt, 0].plot([0, len(dset)], num_sub*np.ones(2), 'r--')
        ax[cnt, 0].set_xlabel('meetings')
        ax[cnt, 0].set_ylabel('used sentences')
        ax2 = ax[cnt, 0].twinx()
        color = 'tab:green'
        ax2.plot(num_speakers, color)
        ax2.set_ylabel('used speakers', color=color)
        ax2.tick_params(axis='y', labelcolor=color)

        ax[cnt, 1].plot(num_reuse)
        ax[cnt, 1].set_xlabel('meetings')
        ax[cnt, 1].set_ylabel('reused sentences')
        cnt += 1

plt.tight_layout()
plt.savefig('vpc_cutted_reuse.png')