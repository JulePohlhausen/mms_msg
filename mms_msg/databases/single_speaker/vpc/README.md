## Generating meetings with VPC data

The VPC data should have 4 main subfolders  containing audio: libri_dev; libri_test; vctk_dev; vctk_test.

1. Run `create_subs_libri_test.sh` with your individual path to the VPC data (`dset`).
    This will create subfolders as for libri_dev.

2. Create a description of the VPC data:

    ```
    python create_json.py -d /path/to/VPC -j /path/to/output/vpc.json
    ```

3. (Optional: run VAD)

4. Use the class-based interface: `class AnechoicVPCMeeting()`.
    An example is given at test_pipeline_JP.py.
