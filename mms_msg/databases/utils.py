from pathlib import Path
import paderbox as pb


def get_dataset_name_and_rng(dataset_name):
    if 'rng' in dataset_name:
        try:
            dataset_name, seed = dataset_name.split('_rng')
        except ValueError:
            raise ValueError(
                f'Expected "<original_dataset_name>_rng[seed]" '
                f'(e.g., train_si284_rng), not {dataset_name}'
            ) from None

        if seed != '':
            rng = int(seed)
        else:
            rng = True
    else:
        rng = False
    return dataset_name, rng


def check_audio_files_exist(
        database_dict,
        speedup=None,
):
    """
    Verifies all files denoted in a dabatase_dict as paths actually exist.
    No structure for the database_dict is assumed. It will just search for all
    string values ending with a certain file type (e.g. wav).
    """

    def path_exists(path):
        return Path(path).exists()

    def body(file_key_path):
        file, key_path = file_key_path
        assert path_exists(file), (file, key_path)

    def condition_fn(file):
        extensions = ('.wav', '.wv2', '.wv1', '.flac')
        return isinstance(file, (str, Path)) and str(file).endswith(extensions)

    to_check = pb.utils.nested.flatten(
        database_dict,
    )
    # Use path as key to drop duplicates
    to_check = {entry: key for key, entry in to_check.items() if condition_fn(entry)}

    assert len(to_check) > 0, (
        f'Expect at least one wav file. '
        f'It is likely that the database folder is empty '
        f'and the greps did not work. to_check: {to_check}'
    )

    if speedup and 'thread' == speedup:
        import os
        from multiprocessing.pool import ThreadPool

        # Use this number because ThreadPoolExecutor is often
        # used to overlap I/O instead of CPU work.
        # See: concurrent.futures.ThreadPoolExecutor
        # max_workers = (os.cpu_count() or 1) * 5

        # Not sufficiently benchmarked both, this is more conservative.
        max_workers = (os.cpu_count() or 1)

        with ThreadPool(max_workers) as pool:
            for _ in pool.imap_unordered(
                body,
                to_check.items()
            ):
                pass

    elif speedup is None:
        for file, key_path in to_check.items():
            assert path_exists(file), (file, key_path)
    else:
        raise ValueError(speedup, type(speedup))

