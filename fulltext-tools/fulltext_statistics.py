# Copyright 2018 David Zellhoefer
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

import sys
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import urllib.request
from urllib.parse import urlparse
import zipfile

import nltk as nltk

# enables verbose output during processing
verbose = False
# path to the sbbget temporary result files, e.g. "../sbbget/sbbget_downloads/download_temp" (the base path under which ALTO files are stored)
sbbGetBasePath="../sbbget/sbbget_downloads/download_temp/"
# Berlin State Library internal setting
runningFromWithinStabi = False
# analysis path prefix
analysisPrefix = "analysis/"
# if set to onlineMode, the tool will not try to use local files, instead it will check for an Excel file stored at oaiAnalyzerResultFile and download ALTO files
onlineMode=True
oaiAnalyzerResultFile="../_datasets/analyticaldf.xlsx"
# True if downloaded ALTO documents have to be kept after processing
keepALTO=False
# analysis path prefix
analysisPrefix = "analysis/"
# temporary downloads prefix
tempDownloadPrefix = "fulltext_download/"
# True if ALTO download should be resumed
resumeAltoDownloads=True

# error log file name
errorLogFileName = "fulltext_statistics_error.log"

# constants, do not change
PARSING_ERROR=1
EMPTY_TEXT=2
NO_ALTO=3
NO_ERROR=-1

def errorCodeAsText(errorCode):
    if errorCode==PARSING_ERROR:
        return "PARSING_ERROR"
    if errorCode==EMPTY_TEXT:
        return "EMPTY_TEXT"
    if errorCode==NO_ALTO:
        return "NO_ALTO"

def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()

def createSupplementaryDirectories():
    if not os.path.exists(analysisPrefix):
        if verbose:
            print("Creating " + analysisPrefix)
        os.mkdir(analysisPrefix)
    if not os.path.exists(tempDownloadPrefix):
        if verbose:
            print("Creating " + tempDownloadPrefix)
        os.mkdir(tempDownloadPrefix)

def downloadALTO(ppn,url):
    """
    Tries to download an ALTO XML file from a given url.
    ATTENTION! Should be surrounded by a try-catch statement as it does not handle network errors etc.
    :param url: The URL from which the ALTO file shall be retrieved.
    :return: The path to the downloaded file.
    """
    # download the ALTO file first in order to find the associated documents
    # 1) get the file name from the URL
    a = urlparse(url)
    fileName=os.path.basename(a.path)
    # 2) download

    altoPath = tempDownloadPrefix + fileName
    if runningFromWithinStabi:
        proxy = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy)
        urllib.request.install_opener(opener)

    urllib.request.urlretrieve(url, altoPath)
    return altoPath

def parseALTO(docPath):
    # parse the ALTO candidate file
    # text conversion is based on https://github.com/cneud/alto-ocr-text/blob/master/alto_ocr_text.py
    namespace = {'alto-1': 'http://schema.ccs-gmbh.com/ALTO',
                 'alto-2': 'http://www.loc.gov/standards/alto/ns-v2#',
                 'alto-3': 'http://www.loc.gov/standards/alto/ns-v3#'}
    rawText=""
    try:
        tree = ET.parse(docPath)
        root = tree.getroot()
        xmlns = root.tag.split('}')[0].strip('{')
    except ET.ParseError:
        #printLog("\t\tParse error @ "+docPath)
        return (None,PARSING_ERROR)
    if root.tag.endswith("alto"):
        for lines in tree.iterfind('.//{%s}TextLine' % xmlns):
            rawText+="\n"
            for line in lines.findall('{%s}String' % xmlns):
                text = line.attrib.get('CONTENT') + ' '
                rawText +=text
        #printLog("\t\t>%s< (%s)"%(rawText,docPath))
        if rawText:
            return (rawText,NO_ERROR)
        else:
            return (None,EMPTY_TEXT)
    else:
        return (None,NO_ALTO)

def creatStatisticFiles(statFilePath, resultTxt):
    statFile = open(statFilePath, "w")
    # standard NLP workflow
    # 1) tokenize the text
    tokens = nltk.word_tokenize(resultTxt)
    nltkText=nltk.Text(tokens)
    # 2) normalize tokens
    words = [w.lower() for w in tokens]
    # 3) create vocabulary
    vocab = sorted(set(words))

    # calculate token frequencies
    fdist = nltk.FreqDist(nltkText)
    fTxt=""
    for (word,freq) in fdist.most_common(100):
        fTxt+=str(word)+"\t"+str(freq)+"\n"
    statFile.write(fTxt)
    statFile.close()


if __name__ == "__main__":
    onlineModePossible=False
    if os.path.exists(oaiAnalyzerResultFile):
        onlineModePossible=True
    else:
        printLog("Could not find %s as input for online mode. Application will exit."%oaiAnalyzerResultFile)
        raise SystemExit

    createSupplementaryDirectories()

    # open error log
    errorFile = open(errorLogFileName, "w")

    if (not onlineMode) and onlineModePossible:
        fulltextFilePaths = []
        # check all subdirectories startings with PPN as each PPN stands for a different medium
        dirsPerPPN = dict()
        ppnDirs=[]
        for x in os.listdir(sbbGetBasePath):
            if x.startswith("PPN"):
                dirsPerPPN[x]=[]
                ppnDirs.append(x)

        # browse all directories below sbbGetBasePath and search for *_FULLTEXT directories
        # and associate each with its PPN
        for ppn in ppnDirs:
            for dirpath, dirnames, files in os.walk(sbbGetBasePath+ppn):
                for name in files:
                    if dirpath.endswith("_FULLTEXT"):
                        # if we found a fulltext directory, only add XML files, i.e., the ALTO candidate files
                        if name.endswith(".xml") or name.endswith(".XML"):
                            fulltextFilePaths.append(os.path.join(dirpath, name))
                            dirsPerPPN[ppn].append(os.path.join(dirpath, name))


        printLog("Found %i ALTO candidate files for further processing."%len(fulltextFilePaths))
        for ppn in dirsPerPPN:
            textPerPPN=""
            for file in dirsPerPPN[ppn]:
                r=parseALTO(file)
                error=r[1]
                if(error<0):
                    resultTxt=r[0]
                    if resultTxt:
                        txtFilePath=file.replace(".xml", ".txt")
                        statFilePath=file.replace(".xml", "_stats.txt")
                        txtFile = open(txtFilePath, "w")

                        txtFile.write(resultTxt)
                        txtFile.close()

                        creatStatisticFiles(statFilePath,resultTxt)
                        textPerPPN+=resultTxt+"\n"
                else:
                    if verbose:
                        printLog("\tParsing problem (%s): %s" % (errorCodeAsText(error),file))
                    errorFile.write("Discarded %s.\tNo ALTO root element found OR parsing error.\n" % file)
            txtFile=open(sbbGetBasePath+ppn+"/fulltext.txt","w")
            txtFile.write(textPerPPN)
            txtFile.close()

            creatStatisticFiles(sbbGetBasePath+ppn+"/fulltext_stats.txt",textPerPPN)
    else:
        # online mode relying on an Excel file placed at oaiAnalyzerResultFile
        printLog("Using online mode.")
        printLog("\tRead METS/MODS analysis table from: " +oaiAnalyzerResultFile)
        rawDF = pd.read_excel(oaiAnalyzerResultFile)
        # select only the records with available altoPaths
        df=rawDF[rawDF.altoPaths.notnull()]
        # 1) iterate over the dataframe to find out how many URLs will have to be processed
        countURLs=0
        downloadedAltoFiles=0
        for index, row in df.iterrows():
            countURLs+=len(row['altoPaths'].split(";"))
        printLog("\tFound a total of %i ALTO file URLs."%countURLs)

        # check if there is a resume file, create it or read it
        resumeFilePath=tempDownloadPrefix+"/_resume.log"
        processedPPNs=[]
        if os.path.exists(resumeFilePath):
            resumeFile = open(resumeFilePath, "r")
            for line in resumeFile:
                processedPPNs.append(line.replace("\n",""))
            resumeFile.close()
            resumeFile = open(resumeFilePath, "a+")
        else:
            resumeFile = open(resumeFilePath, "w")

        firstNonResumablePPN=False
        # download and process all ALTO files
        for index, row in df.iterrows():
            urls=row['altoPaths'].split(";")
            ppn=row['ppn']
            skip=False
            if resumeAltoDownloads:
                # if resume mode is on and we have downloaded the ALTO files for this PPN before, skip processing...
                if ppn in processedPPNs:
                    #print("Skipped %s."%ppn)
                    skip=True
                else:
                    if not firstNonResumablePPN:
                        printLog("\tStarting with PPN: %s"%ppn)
                        firstNonResumablePPN=True

            if not skip:
                textPerPPN = ""
                for url in urls:
                    try:
                        # debug
                        # ppn="PPN74616453X"
                        currentALTO = downloadALTO(ppn,url)
                        downloadedAltoFiles+=1
                    except Exception as ex:
                        template = "An exception of type {0} occurred. Arguments: {1!r}"
                        message = template.format(type(ex).__name__, ex.args)
                        errorFile.write(url + "\t" + message + "\n")

                    if os.path.exists(currentALTO):

                        r = parseALTO(currentALTO)

                        # remove the ALTO file after processing
                        if not keepALTO:
                            os.remove(currentALTO)

                        error = r[1]
                        if (error < 0):
                            resultTxt = r[0]
                            if resultTxt:
                                #txtFilePath = file.replace(".xml", ".txt")
                                #statFilePath = file.replace(".xml", "_stats.txt")
                                #txtFile = open(txtFilePath, "w")

                                #txtFile.write(resultTxt)
                                #txtFile.close()

                                #creatStatisticFiles(statFilePath, resultTxt)
                                textPerPPN += resultTxt + "\n"
                        else:
                            if verbose:
                                printLog("\tParsing problem (%s): %s" % (errorCodeAsText(error), currentALTO))
                            errorFile.write("Discarded %s.\tNo ALTO root element found OR parsing error.\n" % currentALTO)

                        # I am alive! output
                        # BUG: percentage is not correct -> mixes files with URLs, downloadedAltoFiles works on files, countURLs on URLS!
                        if downloadedAltoFiles%10000==0:
                            percent=(float(downloadedAltoFiles)/float(countURLs))*100
                            printLog("\t\tProcessed %i ALTO files (%f %%)."%(downloadedAltoFiles,percent))
                fulltextPath=tempDownloadPrefix + ppn + "_fulltext.txt"
                txtFile = open(fulltextPath, "w")
                txtFile.write(textPerPPN)
                txtFile.close()
                # zip current fulltext file and remove
                zip = zipfile.ZipFile(fulltextPath.replace(".txt",".zip"), 'w')
                zip.write(fulltextPath, compress_type=zipfile.ZIP_DEFLATED)
                zip.close()
                os.remove(fulltextPath)
            # add PPN to resume list
            resumeFile.write(ppn + "\n")

        resumeFile.close()

     # finally, clean up
    errorFile.close()
    printLog("Done.")