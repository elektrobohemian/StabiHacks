# Copyright 2021 David Zellhoefer
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
from time import sleep
import jsonpickle


import nltk as nltk
from flair.data import Sentence
from flair.models import SequenceTagger
import torch

# enables verbose output during processing
verbose = True
# path to the sbbget temporary result files, e.g. "../sbbget/sbbget_downloads/download_temp" (the base path under which ALTO files are stored)
sbbGetBasePath="../sbbget/sbbget_downloads/download_temp/"
#sbbGetBasePath="../sbbget/sbbget_downloads.div_spielebuecher/download_temp/"
# Berlin State Library internal setting
runningFromWithinStabi = False
# analysis path prefix
#analysisPrefix = "analysis/"
# if set to onlineMode, the tool will not try to use local files, instead it will check for an Excel file stored at
# oaiAnalyzerResultFile (created by oai-analyzer.py) and download ALTO files
onlineMode=False
oaiAnalyzerResultFile="../_datasets/analyticaldf.xlsx"
# True if downloaded ALTO documents have to be kept after processing
keepALTO=False
# temporary downloads prefix
tempDownloadPrefix = "fulltext_download/"
# True if ALTO download should be resumed
resumeAltoDownloads=True

# use flair NLP, recommended with available CUDA GPU
useFlairNLP=True
# the model to be used by flair, e.g.:
# ner English
# ner-multi English, German, Dutch and Spanish
# de-ner German
flairModel="de-ner"

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
    #if not os.path.exists(analysisPrefix):
    #    if verbose:
    #        print("Creating " + analysisPrefix)
    #    os.mkdir(analysisPrefix)
    if onlineMode:
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
    if verbose:
        print("\tCreating statistics file at: "+statFilePath)
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

def createNERFiles(statFilePath, resultTxt, tagger):
    if verbose:
        print("\tCreating named entity recognized file at: "+statFilePath)
    statFile = open(statFilePath, "w")
    try:
        sentence = Sentence(resultTxt)
        # predict NER tags
        tagger.predict(sentence)
    except RuntimeError as err:
        print("Runtime error: {0}".format(err))
        print("Failed at: "+statFilePath) 
    
    taggedStr=sentence.to_tagged_string()
    details=sentence.to_dict(tag_type='ner')
    statFile.write(taggedStr)
    statFile.close()
    return (taggedStr,details)


if __name__ == "__main__":
    onlineModePossible=False

    startTime = str(datetime.now())
    if os.path.exists(oaiAnalyzerResultFile):
        printLog("Online mode not possible due to missing OAI-Analyzer file at: "+oaiAnalyzerResultFile)
        onlineModePossible=True
    else:
        printLog("Could not find %s as input for online mode. Application will exit."%oaiAnalyzerResultFile)
        onlineModePossible=False

    createSupplementaryDirectories()

    if useFlairNLP:
        if not torch.cuda.is_available():
            print("WARNING: flair-based NLP is enabled but no GPU is available. This will slow down processing considerably! Processing will continue in 30 seconds.")
            sleep(30)
        print("Using flair model: "+flairModel)

    if onlineMode:
        print("WARNING: Operating in online mode. The script will not use local files. Processing will continue in 30 seconds.")
        sleep(30)
    else:
        print("Processing local files from: "+sbbGetBasePath)

    # open error log
    errorFile = open(errorLogFileName, "w")

    if (not onlineMode): #and onlineModePossible:
        printLog("Using offline mode.")
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

        totalFiles=len(fulltextFilePaths)
        printLog("Found %i ALTO candidate files for further processing."%totalFiles)
        
        if useFlairNLP:
            nerModel=SequenceTagger.load(flairModel)
            print("Flair model loaded.")

        processCounter=0
        for ppn in dirsPerPPN:
            textPerPPN=""
            nerTextPerPPN=""
            nerDicts=[]
            print("Processing PPN: "+ppn)
            for file in dirsPerPPN[ppn]:
                processCounter+=1
                print("Processing file %i of %i (total files over all PPNs)"%(processCounter,totalFiles))

                r=parseALTO(file)
                error=r[1]
                if(error<0):
                    resultTxt=r[0]
                    if resultTxt:
                        txtFilePath=file.replace(".xml", "_raw.txt")
                        statFilePath=file.replace(".xml", "_stats.txt")
                        nerFilePath=file.replace(".xml", "_ner.txt")
                        nerDetailFilePath=file.replace(".xml", "_ner_details.txt")
                        nerDetailJSONFilePath=file.replace(".xml", "_ner_details.json")
                        txtFile = open(txtFilePath, "w")

                        txtFile.write(resultTxt)
                        txtFile.close()

                        creatStatisticFiles(statFilePath,resultTxt)
                        if useFlairNLP:
                            r=createNERFiles(nerFilePath,resultTxt,nerModel)
                            nerTextPerPPN+=r[0]+"\n"
                            nerDicts.append(r[1])

                            nerDetailFile=open(nerDetailFilePath,"w")
                            nerDetailFile.write(str(r[1]))
                            nerDetailFile.close()

                            nerDetailJSONFile=open(nerDetailJSONFilePath,"w")
                            nerDetailJSONFile.write(jsonpickle.encode(r[1], unpicklable=False))
                            nerDetailJSONFile.close()
                        textPerPPN+=resultTxt+"\n"
                else:
                    if verbose:
                        printLog("\tParsing problem (%s): %s" % (errorCodeAsText(error),file))
                    errorFile.write("Discarded %s.\tNo ALTO root element found OR parsing error: %s\n" % (file,errorCodeAsText(error)))
            txtFile=open(sbbGetBasePath+ppn+"/fulltext.txt","w")
            txtFile.write(textPerPPN)
            txtFile.close()
            if useFlairNLP:
                txtFile=open(sbbGetBasePath+ppn+"/fulltext_ner.txt","w")
                txtFile.write(nerTextPerPPN)
                txtFile.close()

                txtFile=open(sbbGetBasePath+ppn+"/fulltext_ner_details.txt","w")
                txtFile.write("Used model: "+flairModel+"\n"+str(nerDicts))
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
    endTime = str(datetime.now())
    print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))
    printLog("Done.")