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
import sys
from datetime import datetime
import pickle
import zipfile

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans

import matplotlib.pyplot as plt

from PIL import Image

def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()

def findZipFiles(path):
    # a list for the tar files
    zipFilePaths=[]
    for root, dirs, files in os.walk(path):
        for file_ in files:
            if file_.endswith(".zip"):
                # debug
                # print(os.path.join(root, file_))
                zipFilePaths.append(os.path.join(root, file_))
    return zipFilePaths

if __name__ == '__main__':
    debugLimit=1
    verbose=True
    outputDir= "./analysis/"

    #general preparations
    if not os.path.exists(outputDir):
        if verbose:
            print("Creating " + outputDir)
        os.mkdir(outputDir)

    startTime = str(datetime.now())

    zipFiles=findZipFiles("./tmp/")

    printLog("Processing histogram files...")
    histograms=[]

    # data science structures
    ppnList=[]
    nameList=[]
    combinedHistograms=[]
    for zipFile in zipFiles:
        with zipfile.ZipFile(zipFile, 'r') as myzip:
            members=myzip.namelist()
            for member in members:
                with myzip.open(member) as myfile:
                    histDict=pickle.load(myfile)
                    histograms.append(histDict)

                    # fill the DS data structures
                    ppnList.append(histDict['ppn'])
                    nameList.append(histDict['extractName'])
                    combinedHistograms.append(histDict['redHistogram']+histDict['blueHistogram']+histDict['greenHistogram'])
    printLog("Number of combined histograms: %i of length: %i"%(len(combinedHistograms),len(combinedHistograms[0])))

    printLog("Clustering...")
    X=np.array(combinedHistograms)
    numberOfClusters=20
    kmeans = MiniBatchKMeans(n_clusters=numberOfClusters, random_state = 0, batch_size = 6)
    kmeans=kmeans.fit(X)
    #labels_

    printLog("Creating report files...")
    htmlFiles=[]
    for i in range(0,numberOfClusters):
        htmlFile=open(outputDir+str(i)+".html", "w")
        htmlFile.write("<html><body>\n")
        #htmlFile.write("<h1>Cluster "+str(i)+"</h1>\n")
        htmlFile.write("<img src='"+str(i)+".png' width=200 />") # cluster center histogram will created below
        htmlFiles.append(htmlFile)
    # image directory must be relative to the directory of the html files
    imgBaseDir="./sbbget_downloads/extracted_images/"
    for i, label in enumerate(kmeans.labels_):
        htmlFiles[label].write("<img height=200 src='"+imgBaseDir+ppnList[i]+"/"+nameList[i]+"' />\n")

    # close the HTML files
    for h in htmlFiles:
        h.write("</body></html>\n")
        h.close()

    # create the summarization main HTML page
    htmlFile = open(outputDir+"_main.html", "w")
    htmlFile.write("<html><body>\n")
    for i in range(0, numberOfClusters):
        htmlFile.write("<iframe src='./"+str(i)+".html"+"' height=400 ><p>Long live Netscape!</p></iframe>")
    htmlFile.write("</body></html>\n")
    htmlFile.close()


    # debug
    #image = Image.open("./red.png")
    #histogram = image.histogram()
    #histogramDict=dict()
    #histogramDict['redHistogram'] = histogram[0:256]
    #histogramDict['blueHistogram'] = histogram[256:512]
    #histogramDict['greenHistogram'] = histogram[512:768]
    #image.close()

    # save the cluster center histograms
    printLog("Rendering %i cluster center histograms..."%len(kmeans.cluster_centers_))

    for j, histogram in enumerate(kmeans.cluster_centers_):
        plt.figure(0)
        # clean previous plots
        plt.clf()
        plt.title("Cluster %i"%j)
        #red
        for i in range(0, 256):
            plt.bar(i, histogram[i],color='red', alpha=0.3)
        # blue
        for i in range(256, 512):
            plt.bar(i-256, histogram[i], color='blue', alpha=0.3)
        # green
        for i in range(512, 768):
            plt.bar(i-512, histogram[i], color='green', alpha=0.3)
        #debug
        #plt.show()
        plt.savefig(outputDir+str(j)+".png")


    df=pd.DataFrame.from_dict(histograms)
    df.to_hdf(outputDir+"histogramData.h5","rgb_histograms")

    endTime = str(datetime.now())
    print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))
#favorite_color = pickle.load( open( "save.p", "rb" ) )