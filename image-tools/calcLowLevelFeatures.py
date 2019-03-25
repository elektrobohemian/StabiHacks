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
import warnings
import json
import pickle
import zipfile

from sklearn.cluster import MiniBatchKMeans
from skimage.feature import hog
import numpy as np
import webcolors



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

# based on https://stackoverflow.com/questions/9694165/convert-rgb-color-to-english-color-name-like-green-with-python
# the following two methods are taken from the answer by "fraxel"
def closest_colour(requested_colour):
    min_colours = {}
    for key, name in webcolors.css3_hex_to_names.items():
        r_c, g_c, b_c = webcolors.hex_to_rgb(key)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        min_colours[(rd + gd + bd)] = name
    return min_colours[min(min_colours.keys())]

def get_colour_name(requested_colour):
    try:
        closest_name = actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        closest_name = closest_colour(requested_colour)
        actual_name = None
    return actual_name, closest_name
# end of fraxel's code

# taken from https://www.pyimagesearch.com/2014/05/26/opencv-python-k-means-color-clustering/
def centroid_histogram(clt):
    # grab the number of different clusters and create a histogram
    # based on the number of pixels assigned to each cluster
    numLabels = np.arange(0, len(np.unique(clt.labels_)) + 1)
    (hist, _) = np.histogram(clt.labels_, bins=numLabels)

    # normalize the histogram, such that it sums to one
    hist = hist.astype("float")
    hist /= hist.sum()

    # return the histogram
    return hist
# end


if __name__ == '__main__':
    # as we expect large files, ignor DecompressionBombWarning from Pillow
    warnings.simplefilter('ignore', Image.DecompressionBombWarning)

    # number of clusters for the k-means dominant color algorithm
    numberOfDominantColorClusters = 7  # (7 seems to be a good compromise)

    debugLimit=1
    tempTarDir="./lowLevelFeatures/"
    verbose=True
    tarFiles=findTARfiles("C:\david.local\__datasets\extracted_images.test\\")
    #tarFiles = findTARfiles("/data2/sbbget/sbbget_downloads/extracted_images/")

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
        zipFile = zipfile.ZipFile(tempTarDir+ppn+"_lowlevelfeats.zip", "w",compression=zipfile.ZIP_DEFLATED)

        for jpeg in jpgFiles:
            histogramDict=dict()
            histogramDict['ppn']=ppn
            histogramDict['extractName']=jpeg

            # open an image an convert it to RGB because we don't want to cope with RGB/RGBA conversions later on
            image = Image.open(tempTarDir + jpeg).convert('RGB')
            histogram = image.histogram()
            histogramDict['redHistogram'] = histogram[0:256]
            histogramDict['blueHistogram'] = histogram[256:512]
            histogramDict['greenHistogram'] = histogram[512:768]

            # HOG feature (https://scikit-image.org/docs/dev/api/skimage.feature.html#skimage.feature.hog)
            fd = hog(image, orientations=8, pixels_per_cell=(16, 16),cells_per_block=(1, 1), multichannel=True,block_norm='L2-Hys')
            histogramDict['HOG']=fd.tolist()

            # dominant color detection
            # scale the image down to speed up later processing (alas, this assumption has not been validated yet...)
            w = h = 256
            size = w, h
            image.thumbnail(size)
            # created a numpy array from the input image
            arr = np.array(image)
            # reshape the image for the clustering algorithm
            pix = arr.reshape((arr.shape[0] * arr.shape[1], 3))

            # find the clusters as specified above
            clt = MiniBatchKMeans(n_clusters=numberOfDominantColorClusters)
            clt.fit(pix)
            histogramDict['dominantColors']=[]
            histogramDict['dominantColorsRGB'] = []
            for centroid in np.round(clt.cluster_centers_, 0):
                actual_name, closest_name = get_colour_name(centroid)
                histogramDict['dominantColors'].append(closest_name)
                histogramDict['dominantColorsRGB'].append(centroid.astype(int).tolist())
                #print("\nActual colour name:", actual_name, ", closest colour name:", closest_name)
            #hist = centroid_histogram(clt)
            #print(hist)


            # finally, close the image
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