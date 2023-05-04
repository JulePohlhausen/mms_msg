from lazy_dataset.database import JsonDatabase
from paderbox.io.data_dir import database_jsons
from mms_msg.sampling.environment.scaling import UniformScalingSampler
from mms_msg.sampling.pattern.meeting import MeetingSampler
from mms_msg.sampling.pattern.meeting.overlap_sampler import UniformOverlapSampler
from mms_msg.sampling.environment.noise import UniformSNRSampler
from mms_msg.sampling.source_composition import sample_utterance_composition
from mms_msg.databases.single_speaker.vpc import VPC
from .database import AnechoicMeetingDatabase

OVERLAP_SETTINGS = {
    'no_ov': {
        'max_concurrent_spk': 2,
        'p_silence': 1,
        'maximum_silence': 3 * 16000,
        'maximum_overlap': 0,
    },
    'medium_ov': {
        'max_concurrent_spk': 2,
        'p_silence': 0.1,
        'maximum_silence': 3 * 16000,
        'maximum_overlap': 1 * 16000,
    },
    'high_ov': {
        'max_concurrent_spk': 2,
        'p_silence': 0.01,
        'maximum_silence': 3 * 16000,
        'maximum_overlap': 4 * 16000,
        'hard_minimum_overlap': 2 * 16000,
    }
}

def AnechoicVPCMeeting(source_json_path=database_jsons / 'vpc.json',
                               duration=120 * 16000, overlap_conditions='medium_ov', num_speakers=(5, 6, 7, 8),
                               snr_min_max=(20, 30), max_weight=5, within_chapter=True):
    """
    Meetings based on the VPC test data.

    Args:
        source_json_path: Path to the JSON file created for the VPC data
        duration: Minimal duration of each meeting (in samples). The sampling of new utterances is stopped once the meeting
                  length exceeds this value
        overlap_conditions: Specifies the overlap scenario, either via pre-defined scenarios or custom values
            either str or dict of overlap settings
        num_speakers: Number of speakers per meeting. Any permitted number of speakers needs to be listed.
        snr_min_max: Gives each utterance a different SNR, sampled from a uniform distribution between `snr_min` and `snr_max`
        max_weight: Gives each utterance a different log_weight, sampled from a uniform distribution between 
            0 and `max_weight` and mean-normalized
        within_chapter: If true, ensures that utterances of each speaker in a meeting are sampled from
            the same chapter such that the acoustic properties (e.g. recording device) don't differ
    Returns:
        Database object containing configurations for anechoic VPC meetings
    """
    if isinstance(overlap_conditions, str):
        try:
            overlap_conditions = OVERLAP_SETTINGS[overlap_conditions]
        except:
            raise KeyError(f'No settings defined for overlap scenario {overlap_conditions}') from None
    if within_chapter:
        scenario_key = ('speaker_id')
    else:
        scenario_key = None
    source_database = VPC(source_json_path, scenario_key=scenario_key)
    overlap_sampler = UniformOverlapSampler(**overlap_conditions)
    meeting_sampler = MeetingSampler(duration, overlap_sampler=overlap_sampler)
    snr_sampler = UniformSNRSampler(snr_min_max[0], snr_min_max[1])
    scaling_sampler = UniformScalingSampler(max_weight=max_weight)
    composition_sampler = 'unique'
    #composition_sampler = sample_utterance_composition
    return AnechoicMeetingDatabase(source_database=source_database,
                                   num_speakers=num_speakers,
                                   meeting_sampler=meeting_sampler,
                                   scaling_sampler=scaling_sampler,
                                   snr_sampler=snr_sampler,
                                   composition_sampler=composition_sampler,
                                   )