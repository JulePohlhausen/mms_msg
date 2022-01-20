import itertools
import operator
from typing import List, Tuple

import numpy as np
import paderbox as pb
from scipy.signal import fftconvolve

from mms_msg import keys

from paderbox.array.sparse import SparseArray


def pad_sparse(original_source, offset, target_shape):
    padded = [
        SparseArray.from_array_and_onset(x_, offset_, target_shape)
        for x_, offset_ in zip(original_source, offset)
    ]

    assert len(padded) == len(original_source), (len(padded), len(original_source))
    for p in padded:
        assert p.shape == target_shape, (p.shape, target_shape)

    return padded


def anechoic_scenario_map_fn(
        example: dict,
        *,
        snr_range: tuple = (20, 30),
        normalize_sources: bool = True,
) -> dict:
    """
    Constructs the observation and scaled speech source signals for `example`
    for the single-channel no reverberation case.

    Args:
        example: Example dict to load
        snr_range: Range where SNR is sampled from for white microphone noise.
            This is deterministic; the rng is seeded with the example ID
        normalize_sources: If `True`, the source signals are mean-normalized
            before processing

    Returns:
        Dict with the following structure:
        ```python
        {
            'audio_data': {
                'observation': ndarray,
                'speechch_source': [ndarray, ndarray, ...],
                'speech_source': [ndarray, ndarray, ...],
                'noise_image': ndarray,
            }
        }
        ```
    """
    T = example[keys.NUM_SAMPLES][keys.OBSERVATION]
    s = example[keys.AUDIO_DATA][keys.ORIGINAL_SOURCE]
    offset = example[keys.OFFSET][keys.ORIGINAL_SOURCE]

    # In some databases (e.g., WSJ) the utterances are not mean normalized. This
    # leads to jumps when padding with zeros or concatenating recordings.
    # We mean-normalize here to eliminate these jumps
    if normalize_sources:
        s = [s_ - np.mean(s_) for s_ in s]

    # Scale the sources by log_weights. We have to determine the scale based on
    # the full signal (its standard deviation) and not just the cut out part
    scale = get_scale(example[keys.LOG_WEIGHTS], s)
    s = [s_ * scale_ for s_, scale_ in zip(s, scale)]

    # Move and pad speech source to the correct position, use sparse array
    speech_source = pad_sparse(s, offset, target_shape=T)

    # The mix is now simply the sum over the speech sources
    # mix = np.sum(speech_source, axis=0)
    mix = sum(speech_source, np.zeros(T, dtype=s[0].dtype))

    example[keys.AUDIO_DATA][keys.OBSERVATION] = mix
    example[keys.AUDIO_DATA][keys.SPEECH_SOURCE] = speech_source

    # Anechoic case: Speech image == speech source
    example[keys.AUDIO_DATA][keys.SPEECH_IMAGE] = speech_source

    # Add noise if snr_range is specified. RNG depends on example ID (
    # deterministic)
    add_microphone_noise(example, snr_range)

    return example


def get_scale(
        log_weights: List[float], signals: List[np.ndarray]
) -> np.ndarray:
    """
    Computes the normalized scales for all signals so that multiplying them with
    the scales gives a logarithmic ratio of log_weights.

    Note:
        We assume that the input signals have roughly the same scaling. We
        ignore the scaling of the input signals for computing the log_weights to
        eliminate estimation errors.

        For reference, these are the means of the standard deviations of the
        WSJ database at 8khz:
         - `cv_dev93`: 0.004037793712821765
         - `cv_dev93_5k`: 0.003991357421377814
         - `test_eval92`: 0.016388209061080895
         - `test_eval92_5k`: 0.01724772268374945
         - `test_eval93`: 0.00272367188875606
         - `test_eval93_5k`: 0.0028981842313541535
         - `train_si284`: 0.0061338699176127125
         - `train_si84`: 0.014455413654260894

    Args:
        log_weights: Target logarithmic weights
        signals: The signals to scale. They are used for normalization and to
            obtain the correct shape for the scales.

    Returns:
        Scale, in the same dimensions as `signals`, but as a numpy array.
    """
    assert len(log_weights) == len(signals), (len(log_weights), len(signals))
    log_weights = np.asarray(log_weights)

    # Note: scale depends on channel mode
    std = np.maximum(
        np.array([np.std(s, keepdims=True) for s in signals]),
        np.finfo(signals[0].dtype).tiny
    )

    # Bring into the correct shape
    log_weights = log_weights.reshape((-1,) + (1,) * signals[0].ndim)
    scale = 10 ** (log_weights / 20) / std

    # divide by 71 to ensure that all values are between -1 and 1 (WHY 71?)
    # TODO: find a good value for both WSJ and LibriSpeech
    scale /= 71

    return scale


def add_microphone_noise(example: dict, snr_range: Tuple[int, int]):
    """
    Adds microphone noise to `example`. Uses the example ID in `example` for
    RNG seeding.

    Modifies `example` in place.

    Args:
        example: The example to add microphone noise to
        snr_range: Range for uniformly drawing SNR. If `None`, no noise is
            added.
    """
    if snr_range is not None:
        # TODO: Handle cut signals, segment offset
        example_id = example[keys.EXAMPLE_ID]
        rng = pb.utils.random_utils.str_to_random_generator(example_id)
        example[keys.SNR] = snr = rng.uniform(*snr_range)

        rng = pb.utils.random_utils.str_to_random_generator(example_id)
        mix = example[keys.AUDIO_DATA][keys.OBSERVATION]
        n = get_white_noise_for_signal(mix, snr=snr, rng_state=rng)
        example[keys.AUDIO_DATA][keys.NOISE_IMAGE] = n
        mix += n
        example[keys.AUDIO_DATA][keys.OBSERVATION] = mix


def multi_channel_scenario_map_fn(
        example,
        *,
        snr_range: tuple = (20, 30),
        normalize_sources: bool = False,
        add_speech_reverberation_early=True,
        add_speech_reverberation_tail=True,
        early_rir_samples: int = int(8000 * 0.05),  # 50 milli seconds
        details=False,
        channel_slice=None,
        squeeze_channels=True,
):
    """
    Modified copy of the scenario_map_fn from sms_wsj.

    This will care for convolution with RIR and also generate noise.
    The random noise generator is fixed based on example ID. It will
    therefore generate the same SNR and same noise sequence the next time
    you use this DB.

    Args:
        compute_scale_on_padded_signals:
        num_channels:
        details:
        early_rir_samples:
        normalize_sources:
        example: Example dictionary.
        snr_range: required for noise generation
        sync_speech_source: pad and/or cut the source signal to match the
            length of the observations. Considers the offset.
        add_speech_reverberation_early:
        add_speech_reverberation_tail:
            Calculate the speech_reverberation_tail signal.

    Returns:
        Dict with the following structure:
        ```python
        {
            'audio_data': {
                'observation': array,
                'speech_source': [SparseArray, ...],
                'original_source': [array, ...],
                'speech_image': [SparseArray, ...],
                'noise_image': array,

                # If add_original_reverberated=True
                'original_reverberated': [array, ...],

                # If add_speech_reverberation_early==True
                'speech_reverberation_early: [SparseArray, ...],
                'original_reverberation_early: [SparseArray, ...],

                # If add_speech_reverberation_tail==True
                'speech_reverberation_tail: [SparseArray, ...],
                'original_reverberation_tail': [SparseArray, ...],

                # If add_reverberation_direct==True
                'original_reverberation_direct': [array, ...],
                'speech_reverberation_direct': [SparseArray, ...],
            }
        }
        ```
    """
    audio_data = example[keys.AUDIO_DATA]
    h = audio_data[keys.RIR]  # Shape (K, D, T)

    # Estimate start sample first, to make it independent of channel_mode
    rir_start_sample = np.array([get_rir_start_sample(h_k) for h_k in h])

    if channel_slice is not None:
        h = h[:, channel_slice, :]

    _, D, rir_length = h.shape

    # Use 50 milliseconds as early rir part, excluding the propagation delay
    #    (i.e. "rir_start_sample")
    assert isinstance(early_rir_samples, int), (type(early_rir_samples), early_rir_samples)
    rir_stop_sample = rir_start_sample + early_rir_samples

    # Compute the shifted offsets that align the convolved signals with the
    # speech source
    # This is Jahn's heuristic to be able to still use WSJ alignments.
    rir_offset = [
        offset_ - rir_start_sample_
        for offset_, rir_start_sample_ in zip(
            example[keys.OFFSET][keys.ORIGINAL_SOURCE], rir_start_sample)
    ]

    # The two sources have to be cut to same length
    K = len(example[keys.SPEAKER_ID])
    T = example[keys.NUM_SAMPLES][keys.OBSERVATION]
    s = audio_data[keys.ORIGINAL_SOURCE]

    # In some databases (e.g., WSJ) the utterances are not mean normalized. This
    # leads to jumps when padding with zeros or concatenating recordings.
    # We mean-normalize here to eliminate these jumps
    if normalize_sources:
        s = [s_ - np.mean(s_) for s_ in s]

    def get_convolved_signals(h):
        """Convolve the scaled signals `s` with the RIRs in `h`. Returns
        the (unpadded) convolved signals with offsets and the padded convolved
        signals"""
        assert len(s) == len(h), (len(s), len(h))
        x = [
            fftconvolve(s_[..., None, :], h_, axes=-1)
            for s_, h_ in zip(s, h)
        ]

        assert len(x) == len(example[keys.NUM_SAMPLES][keys.ORIGINAL_SOURCE])
        for x_, T_ in zip(x, example[keys.NUM_SAMPLES][keys.ORIGINAL_SOURCE]):
            assert x_.shape == (D, T_ + rir_length - 1), (
                x_.shape, D, T_ + rir_length - 1)

        assert len(x) == len(rir_offset) == K
        return x

    # Speech source is simply the shifted and padded original source signals
    audio_data[keys.SPEECH_SOURCE] = pad_sparse(
        audio_data[keys.ORIGINAL_SOURCE],
        example[keys.OFFSET][keys.ORIGINAL_SOURCE],
        target_shape=(T,),
    )

    # Compute the reverberated signals
    audio_data[keys.ORIGINAL_REVERBERATED] = get_convolved_signals(h)

    # Scale s with log_weights before convolution
    scale = get_scale(
        example[keys.LOG_WEIGHTS],
        audio_data[keys.ORIGINAL_REVERBERATED]
    )

    def apply_scale(x):
        return [x_ * scale_ for x_, scale_ in zip(x, scale)]

    audio_data[keys.ORIGINAL_REVERBERATED] = apply_scale(
        audio_data[keys.ORIGINAL_REVERBERATED]
    )

    audio_data[keys.SPEECH_IMAGE] = pad_sparse(
        audio_data[keys.ORIGINAL_REVERBERATED], rir_offset, (D, T))
    example[keys.NUM_SAMPLES][keys.ORIGINAL_REVERBERATED] = [
        a.shape[-1] for a in audio_data[keys.ORIGINAL_REVERBERATED]
    ]
    example[keys.OFFSET][keys.ORIGINAL_REVERBERATED] = rir_offset

    if add_speech_reverberation_early:
        # Obtain the early reverberation part: Mask the tail reverberation by
        # setting everything behind the RIR stop sample to zero
        h_early = h.copy()
        for i in range(h_early.shape[0]):
            h_early[i, ..., rir_stop_sample[i]:] = 0

        # Compute convolution
        audio_data[keys.ORIGINAL_REVERBERATION_EARLY] = apply_scale(
            get_convolved_signals(h_early)
        )
        audio_data[keys.SPEECH_REVERBERATION_EARLY] = pad_sparse(
            audio_data[keys.ORIGINAL_REVERBERATION_EARLY], rir_offset, (D, T))

        if details:
            audio_data[keys.RIR_EARLY] = h_early

    if add_speech_reverberation_tail:
        # Obtain the tail reverberation part: Mask the early reverberation by
        # setting everything before the RIR stop sample to zero
        h_tail = h.copy()
        for i in range(h_tail.shape[0]):
            h_tail[i, ..., :rir_stop_sample[i]] = 0

        # Compute convolution
        audio_data[keys.ORIGINAL_REVERBERATION_TAIL] = apply_scale(
            get_convolved_signals(h_tail)
        )
        audio_data[keys.SPEECH_REVERBERATION_TAIL] = pad_sparse(
            audio_data[keys.ORIGINAL_REVERBERATION_TAIL], rir_offset, (D, T))

        if details:
            audio_data[keys.RIR_TAIL] = h_tail

    clean_mix = sum(audio_data[keys.SPEECH_IMAGE], np.zeros((D, T), dtype=s[0].dtype))
    audio_data[keys.OBSERVATION] = clean_mix
    add_microphone_noise(example, snr_range)
    return example


def get_white_noise_for_signal(
        time_signal,
        *,
        snr,
        rng_state: np.random.RandomState = np.random
):
    """
    Args:
        time_signal:
        snr: SNR or single speaker SNR.
        rng_state: A random number generator object or np.random
    """
    noise_signal = rng_state.normal(size=time_signal.shape)

    power_time_signal = np.mean(time_signal ** 2, keepdims=True)
    power_noise_signal = np.mean(noise_signal ** 2, keepdims=True)
    current_snr = 10 * np.log10(power_time_signal / power_noise_signal)

    factor = 10 ** (-(snr - current_snr) / 20)

    noise_signal *= factor
    return noise_signal


def get_rir_start_sample(h, level_ratio=1e-1):
    """Finds start sample in a room impulse response.

    Selects that index as start sample where the first time
    a value larger than `level_ratio * max_abs_value`
    occurs.

    If you intend to use this heuristic, test it on simulated and real RIR
    first. This heuristic is developed on MIRD database RIRs and on some
    simulated RIRs but may not be appropriate for your database.

    If you want to use it to shorten impulse responses, keep the initial part
    of the room impulse response intact and just set the tail to zero.

    Params:
        h: Room impulse response with Shape (num_samples,)
        level_ratio: Ratio between start value and max value.

    >>> get_rir_start_sample(np.array([0, 0, 1, 0.5, 0.1]))
    2
    """
    assert level_ratio < 1, level_ratio
    if h.ndim > 1:
        assert h.shape[0] < 20, h.shape
        h = np.reshape(h, (-1, h.shape[-1]))
        return np.min(
            [get_rir_start_sample(h_, level_ratio=level_ratio) for h_ in h]
        )

    abs_h = np.abs(h)
    max_index = np.argmax(abs_h)
    max_abs_value = abs_h[max_index]
    # +1 because python excludes the last value
    larger_than_threshold = abs_h[:max_index + 1] > level_ratio * max_abs_value

    # Finds first occurrence of max
    rir_start_sample = np.argmax(larger_than_threshold)
    return rir_start_sample



def combine_speaker_signals(example):
    # Group everything by speaker
    grouped_example = {}
    extra = {}

    # Whitelists
    combine_equal = (
        'speaker_id',
        'gender',
    )
    combine_list = (
        'transcription',
        'kaldi_transcription',
    )
    combine = combine_equal + combine_list
    remove = (
        'log_weights',
        'audio_path.rir',
        'source_position',
        'source_dataset',
    )
    blacklist = (
        'sensor_positions',
        'room_dimensions',
        'example_id',
        'num_speakers',
        'sound_decay_time',
        'sensor_position',
    )
    speaker_ids = example[keys.SPEAKER_ID]
    key_fn = operator.itemgetter(0)
    for k, v in pb.utils.nested.flatten(example).items():
        if k in combine:
            if k in combine_equal:
                def _combine(x):
                    assert pb.utils.misc.all_equal(x), x
                    return x[0]
            elif k in combine_list:
                _combine = list
            else:
                assert False, 'Can never happen'

            assert len(speaker_ids) == len(v), (k, len(speaker_ids), len(v))
            grouped_example[k] = [
                _combine(values)
                for _, values in itertools.groupby(sorted(zip(speaker_ids, v), key=key_fn), key=key_fn)
            ]
        elif k in remove:
            # Don't add to grouped example
            pass
        elif k in blacklist:
            extra[k] = v
        else:
            raise RuntimeError(f'key {k} neither in whitelist nor blacklist')