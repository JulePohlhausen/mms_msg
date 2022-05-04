from mms_msg.sampling.utils.rng import get_rng_example


def sample_uniform_snr(example, *, snr_range=(20, 30)):
    if len(snr_range) != 2:
        raise ValueError(f'Invalid snr_range={snr_range}')
    example['snr'] = float(
        get_rng_example(example, 'snr').uniform(*snr_range, size=1)
    )
    return example
