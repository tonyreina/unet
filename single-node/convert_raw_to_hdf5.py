#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

import os
import nibabel as nib
import numpy as np
from tqdm import tqdm
import glob
import h5py

import argparse

parser = argparse.ArgumentParser(
               description="Convert Decathlon raw Nifti data "
               "(http://medicaldecathlon.com/) "
               "files to Numpy data files",
               add_help=True)

parser.add_argument("--data_path",
                    default="../../data/decathlon/Task01_BrainTumour/",
                    help="Path to the raw BraTS datafiles")
parser.add_argument("--save_path",
                    default="../../data/decathlon/",
                    help="Folder to save Numpy data files")
parser.add_argument("--resize", type=int, default=128,
                    help="Resize height and width to this size. "
                    "Original size = 240")
parser.add_argument("--split", type=float, default=0.85,
                    help="Train/test split ratio")

args = parser.parse_args()

print("Converting Decathlon raw Nifti data files to training and testing" \
        " Numpy data files.")
print(args)

save_dir = os.path.join(args.save_path, "{}x{}/".format(args.resize, args.resize))

# Create directory
try:
    os.makedirs(save_dir)
except OSError:
    if not os.path.isdir(save_dir):
        raise

# Check for existing numpy train/test files
check_dir = os.listdir(save_dir)
for item in check_dir:
    if item.endswith(".h5"):
        os.remove(os.path.join(save_dir, item))
        print("Removed old version of {}".format(item))


imgList = glob.glob(os.path.join(args.data_path, "imagesTr", "*.nii.gz"))
mskList = [w.replace("imagesTr", "labelsTr") for w in imgList]

numFiles = len(imgList)
np.random.seed(816)
idxList = np.arange(numFiles)
np.random.shuffle(idxList)
trainList = idxList[:np.int(numFiles*args.split)]
testList = idxList[np.int(numFiles*args.split):]

def crop_center(img,cropx,cropy,cropz):
    if len(img.shape) == 4:
        x,y,z,c = img.shape
    else:
        x,y,z = img.shape

    startx = x//2-(cropx//2)
    starty = y//2-(cropy//2)
    startz = z//2-(cropz//2)

    # Let's just take the entire z slices since
    # we are doing 2D anyway.
    if len(img.shape) == 4:
        return img[startx:startx+cropx,starty:starty+cropy,:,:]
    else:
        return img[startx:startx+cropx,starty:starty+cropy,:]

def normalize_img(img):

    for channel in range(img.shape[3]):
        img[:,:,:,channel] = (img[:,:,:,channel] - np.mean(img[:,:,:,channel])) / np.std(img[:,:,:,channel])

    return img

filename = os.path.join(save_dir, "decathlon_brats.h5")
hdf_file = h5py.File(filename, "w")

# Save training set images
print("Step 1 of 4. Save training images.")
first = True
for idx in tqdm(trainList):

    img = np.array(nib.load(imgList[idx]).dataobj)
    img = crop_center(img, args.resize, args.resize, args.resize)
    img = normalize_img(img)

    img = np.swapaxes(np.array(img),0,-2)
    num_rows = img.shape[0]

    if first:
        first = False
        img_train_dset = hdf_file.create_dataset("imgs_train",
                         img.shape,
                         maxshape=(None, img.shape[1],
                         img.shape[2], img.shape[3]),
                         dtype=float)
        img_train_dset[:] = img
    else:
        row = img_train_dset.shape[0] # Count current dataset rows
        img_train_dset.resize(row+num_rows, axis=0) # Add new row
        img_train_dset[row:(row+num_rows), :] = img # Insert data into new row


# Save testing set images

print("Step 2 of 4. Save testing images.")
first = True
for idx in tqdm(testList):

    # Nibabel should read the file as X,Y,Z,C
    img = np.array(nib.load(imgList[idx]).dataobj)
    img = crop_center(img, args.resize, args.resize, args.resize)
    img = normalize_img(img)

    img = np.swapaxes(np.array(img),0,-2)
    num_rows = img.shape[0]

    if first:
        first = False
        img_test_dset = hdf_file.create_dataset("imgs_test",
                         img.shape,
                         maxshape=(None, img.shape[1],
                         img.shape[2], img.shape[3]),
                         dtype=float)
        img_test_dset[:] = img
    else:
        row = img_test_dset.shape[0] # Count current dataset rows
        img_test_dset.resize(row+num_rows, axis=0) # Add new row
        img_test_dset[row:(row+num_rows), :] = img # Insert data into new row

# Save training set masks
print("Step 3 of 4. Save training masks.")
first = True
for idx in tqdm(trainList):

    msk = np.array(nib.load(mskList[idx]).dataobj)
    msk = crop_center(msk, args.resize, args.resize, args.resize)

    msk[msk > 1] = 1 # Combine all masks
    msk = np.expand_dims(np.swapaxes(np.array(msk),0,-2), -1)
    num_rows = msk.shape[0]

    if first:
        first = False
        msk_train_dset = hdf_file.create_dataset("msks_train",
                         msk.shape,
                         maxshape=(None, msk.shape[1],
                         msk.shape[2], msk.shape[3]),
                         dtype=float)
        msk_train_dset[:] = msk
    else:
        row = msk_train_dset.shape[0] # Count current dataset rows
        msk_train_dset.resize(row+num_rows, axis=0) # Add new row
        msk_train_dset[row:(row+num_rows), :] = msk # Insert data into new row

# Save training set masks

print("Step 4 of 4. Save testing masks.")
first = True
for idx in tqdm(testList):

    msk = np.array(nib.load(mskList[idx]).dataobj)
    msk = crop_center(msk, args.resize, args.resize, args.resize)

    msk[msk > 1] = 1 # Combine all masks
    msk = np.expand_dims(np.swapaxes(np.array(msk),0,-2), -1)
    num_rows = msk.shape[0]

    if first:
        first = False
        msk_test_dset = hdf_file.create_dataset("msks_test",
                         msk.shape,
                         maxshape=(None, msk.shape[1],
                         msk.shape[2], msk.shape[3]),
                         dtype=float)
        msk_test_dset[:] = msk
    else:
        row = msk_test_dset.shape[0] # Count current dataset rows
        msk_test_dset.resize(row+num_rows, axis=0) # Add new row
        msk_test_dset[row:(row+num_rows), :] = msk # Insert data into new row

print("Finished processing.")
print("HDF5 saved to {}".format(filename))