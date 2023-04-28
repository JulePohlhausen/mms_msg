## Generating meetings with VPC data

The VPC data should have 4 main subfolders containing audio: libri_dev; libri_test; vctk_dev; vctk_test.
We decided to use just the test folders, hence you can skip step 1.

1. Run `create_subs_libri_test.sh` with your individual path to the VPC data (`dset`).
    This will create subfolders as for libri_dev.

2. Optional: run VAD with sb/recipes/LibriParty/VAD/inference_VPC.py, it cuts silences at the beginning and end and saves the cutted wavs:

    ```
    python inference_VPC.py -j /path/to/output/vpc.json -d /path/to/VPC
    ```
3. Create a description of the (cutted) VPC data with mms_msg/mms_msg/databases/single_speaker/vpc/create_json.py:

    ```
    python create_json.py -d /path/to/VPC -j /path/to/output/vpc.json -a wav_cutted
    ```

4. Use the class-based interface: `class AnechoicVPCMeeting()`.
    An example is given at test_pipeline_JP.py, just adjust the path definitions.
