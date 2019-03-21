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
import sys
from datetime import datetime
from PIL import Image
import json
import pickle
import zipfile



def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()

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
    debugLimit=1
    tempTarDir="./tmp/"
    verbose=True
    #tarFiles=findTARfiles("C:\david.local\__datasets\extracted_images\\")
    tarFiles = findTARfiles("/data2/sbbget/sbbget_downloads/extracted_images/")

    #general preparations
    if not os.path.exists(tempTarDir):
        if verbose:
            print("Creating " + tempTarDir)
        os.mkdir(tempTarDir)

    #

    numberOfExtractedIllustrations=0
    i=0
    noTarFiles=len(tarFiles)
    minExtract=1
    maxExtract=0

    histograms=[]

    printLog("Started processing...")
    startTime = str(datetime.now())

    for tarFile in tarFiles:
        i+=1

        if verbose:
            printLog("Processing %s" % tarFile)
        ppn=os.path.basename(tarFile).replace(".tar","")
        tarBall = TAR.open(tarFile, "r")

        members=tarBall.getmembers()
        numberOfExtractedIllustrations+=len(members)
        if len(members)<minExtract:
            minExtract=len(members)
        if len(members)>maxExtract:
            maxExtract=len(members)

        if i%1000==0:
            printLog("\n\nFound %i extracted illustrations in %i files of %i. Continuing..."%(numberOfExtractedIllustrations,i,noTarFiles))
            printLog("Min: %i; Max: %i\n"%(minExtract,maxExtract))

        # extraction
        if verbose:
            printLog("\t Extracting tar file...")
        jpgFiles=[]
        for member in members:
            #tarBall.extract(member,tempTarDir)
            if member.isreg():  # skip if the TarInfo is not files
                member.name = os.path.basename(member.name)  # remove the path by reset it
                jpgFiles.append(member.name)
                tarBall.extract(member, tempTarDir)

        # process the JPEG files
        if verbose:
            printLog("\t Processing JPEG files...")
        zipFile = zipfile.ZipFile(tempTarDir+ppn+"_histograms.zip", "w",compression=zipfile.ZIP_DEFLATED)

        for jpeg in jpgFiles:
            histogramDict=dict()
            histogramDict['ppn']=ppn
            histogramDict['extractName']=jpeg

            image = Image.open(tempTarDir + jpeg)
            histogram = image.histogram()
            histogramDict['redHistogram'] = histogram[0:256]
            histogramDict['blueHistogram'] = histogram[256:512]
            histogramDict['greenHistogram'] = histogram[512:768]
            image.close()

            pickleFile=tempTarDir + ppn + "_" + jpeg.replace(".", "_") + "_.pickle"
            pickle.dump(histogramDict, open(pickleFile,'wb'))
            zipFile.write(pickleFile)
            os.remove(pickleFile)

            jsonFile=tempTarDir+ppn+"_"+jpeg.replace(".","_")+"_.json"
            with open(jsonFile, "w") as write_file:
                json.dump(histogramDict, write_file)
            zipFile.write(jsonFile)
            os.remove(jsonFile)

        zipFile.close()

        # finally, remove the files again
        if verbose:
            printLog("\t Removing files...")
        for jpeg in jpgFiles:
            os.remove(tempTarDir+jpeg)

        #debug
        #if i>=debugLimit:
        #    break
    print("Total number of files: %i"%numberOfExtractedIllustrations)
    endTime = str(datetime.now())

    print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))