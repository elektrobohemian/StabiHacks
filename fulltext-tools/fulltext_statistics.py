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

import nltk as nltk

# enables verbose output during processing
verbose = True
# path to the sbbget temporary result files, e.g. "../sbbget/sbbget_downloads/download_temp" (the base path under which ALTO files are stored)
sbbGetBasePath="../sbbget/sbbget_downloads/download_temp/"
# analysis path prefix
analysisPrefix = "analysis/"
# error log file name
errorLogFileName = "fulltext_statistics_error.log"


def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()

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
        return None
    if root.tag.endswith("alto"):
        for lines in tree.iterfind('.//{%s}TextLine' % xmlns):
            rawText+="\n"
            for line in lines.findall('{%s}String' % xmlns):
                text = line.attrib.get('CONTENT') + ' '
                rawText +=text
        return rawText
    else:
        return None

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

    # open error log
    errorFile = open(errorLogFileName, "w")

    printLog("Found %i ALTO candidate files for further processing."%len(fulltextFilePaths))
    for ppn in dirsPerPPN:
        textPerPPN=""
        for file in dirsPerPPN[ppn]:
            resultTxt=parseALTO(file)
            if resultTxt:
                txtFilePath=file.replace(".xml", ".txt")
                statFilePath=file.replace(".xml", "_stats.txt")
                txtFile = open(txtFilePath, "w")

                txtFile.write(resultTxt)
                txtFile.close()

                creatStatisticFiles(statFilePath,resultTxt)
                textPerPPN+=resultTxt+"\n"

            else:
                errorFile.write("Discarded %s.\tNo ALTO root element found OR parsing error.\n" % file)
        txtFile=open(sbbGetBasePath+ppn+"/fulltext.txt","w")
        txtFile.write(textPerPPN)
        txtFile.close()

        creatStatisticFiles(sbbGetBasePath+ppn+"/fulltext_stats.txt",textPerPPN)

     # finally, clean up
    errorFile.close()
    printLog("Done.")