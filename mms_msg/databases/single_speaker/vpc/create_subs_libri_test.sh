#!/bin/bash

dset=/home/jule/datasets/VPC
libri_path=$dset/libri_test/wav

for file in "$libri_path"/*
do
  speaker_id="${file%%.*}"
  mkdir -p "$speaker_id"

  mv "$file" "$speaker_id"
done