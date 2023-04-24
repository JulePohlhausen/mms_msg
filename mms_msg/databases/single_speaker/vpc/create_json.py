import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import click

from mms_msg.databases.utils import check_audio_files_exist
from paderbox.io.audioread import audio_length
from paderbox.io import dump_json


def read_speakers_libri(database_path):
    sub_dict = defaultdict(dict)
    spk2gender = defaultdict(dict)

    subsets = {'libri_test', 'libri_dev'}
    for subset in subsets:
        filepath = database_path  / subset
        gen_file = filepath / 'spk2gender'
        with open(gen_file, 'r') as f:
            for line in f.readlines():
                speaker_id, gender = line.replace('\n', '').split(' ', maxsplit=1)
                spk2gender[speaker_id] = \
            'male' if gender == 'm' else 'female'

        utt_file = filepath / 'utt2spk'
        with open(utt_file, 'r') as f:
            for line in f.readlines():
                wav_id, speaker_id = line.replace('\n', '').split(' ', maxsplit=1)
                sub_dict[subset + '|' + wav_id]['speaker_id'] = speaker_id
                sub_dict[subset + '|' + wav_id]['gender'] = spk2gender[speaker_id]

    return sub_dict

def read_speakers_vctk(filepath):
    sub_dict = defaultdict(dict)
    for line in filepath.read_text().splitlines():
        speaker_id, gender, subset = [
            segment.strip() for segment in line.split(' ')]
        sub_dict[subset + '|' + speaker_id]['speaker_id'] = speaker_id
        sub_dict[subset + '|' + speaker_id]['gender'] = \
            'male' if gender == 'm' else 'female'

    return sub_dict


def get_example_dict(in_tuple, transcription):
    audio_file, sub_dict, subset_id = in_tuple
    audio_id = audio_file.stem

    example_dict = {
        'audio_path': {"observation": str(audio_file)},
        'transcription': transcription[audio_id],
        'num_samples': audio_length(str(audio_file), unit='samples'),
    }

    example_dict.update(sub_dict)
    return subset_id, audio_id, example_dict


def get_transcription(database_path, set='vctk'):
    transcription = defaultdict(dict)
    filepaths = {database_path  / (set + '_dev') / 'text',
                database_path  / (set + '_test') / 'text'}

    for filepath in filepaths:
        with open(filepath, 'r') as f:
            for line in f.readlines():
                wav_id, text = line.replace('\n', '').split(' ', maxsplit=1)
                transcription[wav_id] = text.strip()

    return transcription


def get_audio_files(sub_dict, database_path, identifier):
    for segment, sub_dict in sub_dict.items():
        subset, speaker_id = segment.split('|')
        file_path = database_path / subset / 'wav' / speaker_id
        subset_id = subset.strip()
        for x in file_path.glob(f'*.{identifier}'):
            yield x, sub_dict, subset_id            


def read_subset(database_path, sub_dict_libri, sub_dict_vctk, wav):
    database = dict()
    examples = defaultdict(dict)
    identifier = 'wav' if wav else 'flac'
    subsets = {'libri', 'vctk'}
    for subset in subsets:
        transcription = get_transcription(database_path, set=subset)
        if subset == 'libri':
            audio_files = get_audio_files(sub_dict_libri, database_path, identifier)
        else:
            audio_files = get_audio_files(sub_dict_vctk, database_path, identifier)
        with ThreadPoolExecutor(os.cpu_count()) as ex:
            for subset_id, example_id, example_dict in ex.map(
                    partial(get_example_dict, transcription=transcription),
                    audio_files
            ):
                examples[subset_id][example_id] = example_dict

        database['datasets'] = examples
    return database

def create_json(database_path, wav):
    # data from librispeech 
    sub_dict_libri = read_speakers_libri(database_path)

    # data from vctk
    sub_dict_vctk = read_speakers_vctk(database_path / 'vctk_dev' / 'SPEAKERS.txt')
    database = read_subset(database_path, sub_dict_libri, sub_dict_vctk, wav)
    return database


@click.command()
@click.option(
    '--json-path', '-j', default='vpc.json',
    help=''
)
@click.option(
    '--database-path', '-d',
    help='Path to the folder containing the VPC test data',
)
@click.option(
    '--wav', default=True,
    help='Defines whether to look for wav or flac files. '
         'If True only wav files are written to the json '
         'otherwise only flac files are used',
    is_flag=True
)

def main(json_path, database_path, wav):
    database = create_json(Path(database_path).absolute(), wav)
    print('Check that all wav files in the json exists.')
    check_audio_files_exist(database, speedup='thread')
    print('Finished check. Write json to disk:')
    dump_json(database, Path(json_path),
              create_path=True,
              indent=4,
              ensure_ascii=False
              )


if __name__ == '__main__':
    main()
