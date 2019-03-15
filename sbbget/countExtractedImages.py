# Copyright 2019 David Zellhoefer
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tarfile as TAR


def findTARfiles(path):
    # a list for the tar files
    tarFilePaths=[]
    for root, dirs, files in os.walk(path):
        for file_ in files:
            if file_.endswith(".tar"):
                # debug
                # print(os.path.join(root, file_))
                tarFilePaths.append(os.path.join(root, file_))
    return tarFilePaths


if __name__ == '__main__':
    tarFiles=findTARfiles('/Users/david/src/__datasets/OCR_image_extracts/extracted_images/')

    numberOfExtractedIllustrations=0
    i=0
    noTarFiles=len(tarFiles)
    minExtract=1
    maxExtract=0
    for tarFile in tarFiles:
        tarBall = TAR.open(tarFile, "r")
        members=tarBall.getmembers()
        numberOfExtractedIllustrations+=len(members)
        if len(members)<minExtract:
            minExtract=len(members)
        if len(members)>maxExtract:
            maxExtract=len(members)
        i+=1
        if i%1000==0:
            print("Found %i extracted illustrations in %i files of %i. Continuing..."%(numberOfExtractedIllustrations,i,noTarFiles))
            print("Min: %i; Max: %i"%(minExtract,maxExtract))
        #debug
        #print("%i members in %s"%(len(members),tarFile))
    print("Total number of files: %i"%numberOfExtractedIllustrations)