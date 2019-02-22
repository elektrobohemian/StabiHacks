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

import sys
import os
from datetime import datetime

# add fields of interest to the following list, only this field will be extracted

# general overview of Pica + fields (in German) is available under https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/inhalt.shtml

# 028B  2. Verfasser und weitere (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/3000.pdf)
# 021B  Hauptsachtitel bei j-Sätzen (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/4004.pdf)
# 033A  Ort und Verlag (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/4030.pdf)
# 019@  Erscheinungsland (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/1700.pdf)
# run time for the full 2018 set
# Started at:	2019-02-20 12:37:25.704093
# Ended at:	2019-02-20 15:40:56.240565

# the paths to the files to be analyzed
picaPlusFilePaths=["""C:\david.local\cbs\\vollabzug\iln11_001_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_002_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_003_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_004_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_005_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_006_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_007_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_008_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_009_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_010_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_011_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_012_20180103.pp""","""C:\david.local\cbs\\vollabzug\iln11_013_20180103.pp"""]
#picaPlusFilePaths=["./analysis/test_large.pp"]

# toggles textual output
createTextOutput=True
# analysis path prefix
#analysisPrefix = "analysis/"
analysisPrefix="""C:\david.local\cbs\\analysis\\"""
# path to the created text file
outputTextFilePathSuffix="out.txt"
# a map of language to text output path and file handler
outputTextFilePaths={"eng":[analysisPrefix+"/eng_"+outputTextFilePathSuffix,None],"ger":[analysisPrefix+"/ger_"+outputTextFilePathSuffix,None],"lat":[analysisPrefix+"/lat_"+outputTextFilePathSuffix,None],"fre":[analysisPrefix+"/fre_"+outputTextFilePathSuffix,None],"ita":[analysisPrefix+"/ita_"+outputTextFilePathSuffix,None],"spa":[analysisPrefix+"/spa_"+outputTextFilePathSuffix,None],"por":[analysisPrefix+"/por_"+outputTextFilePathSuffix,None],"dut":[analysisPrefix+"/dut_"+outputTextFilePathSuffix,None],"swe":[analysisPrefix+"/swe_"+outputTextFilePathSuffix,None],"dan":[analysisPrefix+"/dan_"+outputTextFilePathSuffix,None],"nor":[analysisPrefix+"/nor_"+outputTextFilePathSuffix,None],"ice":[analysisPrefix+"/ice_"+outputTextFilePathSuffix,None],"fry":[analysisPrefix+"/fry_"+outputTextFilePathSuffix,None],"None":[analysisPrefix+"/"+outputTextFilePathSuffix,None]}
# path to the statistics file
statisticsFilePath=analysisPrefix+"/statistics.txt"

# the fields of interest indicate the fields that have to be extracted, please note that 003@ and 010@ must not be removed because these fields contain
# the unique ID of the records and its language
fieldsOfInterest=['003@','028A','028B','021A','021B','033A','010@','019@']
# enables verbose output during processing
verbose = True

def createSupplementaryDirectories():
    if not os.path.exists(analysisPrefix):
        if verbose:
            print("Creating " + analysisPrefix)
        os.mkdir(analysisPrefix)

def handle021a(tokens):
    """
    Processes the 021A (Hauptsachtitel) field. Currently, only subfield a and d are supported.
    For details (in German), see: https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/4000.pdf
    :param tokens: a list of tokens of the field 021A
    :return:
    """
    hauptsachtitel=""
    zusaetze=""
    for token in tokens:
        if token.startswith("a"):
            hauptsachtitel=token[1:].replace("@","").strip()
        elif token.startswith("d"):
            z=token[1:].replace("@","").split(";")
            z = list(map(str.strip, z))
            zusaetze=" ".join(z).strip()


    return(hauptsachtitel+" "+zusaetze)

def handle028a(tokens):
    """
    Processes the 028A (1. Verfasser) field. Currently, only subfield a and d are supported.
    For details (in German), see: https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/3000.pdf
    :param tokens: a list of tokens of the field 028A
    :return: a tuple in form of (<family name, first name>,<gnd id, if available>)
    """
    familyName=""
    firstName=""
    gnd=""
    for token in tokens:
        if token.startswith("a"):
            familyName=token[1:].strip()+", "
        elif token.startswith("d"):
            firstName=token[1:].strip()
        # GND id
        elif token.startswith("0"):
            gnd=token[1:].strip()

    return((familyName+firstName,gnd))

if __name__ == "__main__":
    startTime = str(datetime.now())

    txtFile=None
    if createTextOutput:
        createSupplementaryDirectories()
        for language in outputTextFilePaths:
            f=open(outputTextFilePaths[language][0],"w",encoding="utf-8")
            outputTextFilePaths[language][1]=f

    # histogram of found languages
    languageHist=dict()
    numberOfRecords=0

    # process all Pica+ files sequentially
    for picaPlusFile in picaPlusFilePaths:
        with open(picaPlusFile, "rb") as f:
            byte = f.read(1)
            i = 0
            unicodeHot = False
            lastUnicodeMarker = None
            last = None
            fieldSeparator = False

            currentLine = ""
            # encoding is indicated in 001U as "0utf8"

            ppn = ""
            language="None"
            while byte != b"":
                # Do stuff with byte.

                byte = f.read(1)
                # debug (print all seen bytes)
                # print(str(byte)+"\t"+str(int.from_bytes(byte,sys.byteorder)))
                i += 1

                # if in unicode processing mode, compose 2 byte unicode character
                if unicodeHot:
                    bytestream = last + lastUnicodeMarker + byte
                    currentLine = currentLine[:-1] + bytestream.decode('utf-8', "replace")

                # if we find a \r\n, we have a new line
                if (byte == b'\n' and last == b'\r') or (byte == b'\x1e' and last == b'\n'):
                    #print(currentLine)
                    # split must be based on b'\x1f'
                    currentLine = currentLine.replace("\x1e", "")
                    #tokens = currentLine.replace('\x1f', "\t").split("\t")
                    tokens = currentLine.split("\t")
                    # remove whitespaces etc.
                    tokens=list(map(str.strip, tokens))
                    #TODO remove @ in certain sub-fields because it is used as a sorting indicator in PICA+
                    #['028A', 'dPaul\x1faCelan\x1f9131811533\x1fdPaul\x1faCelan\x1fE1920\x1fF1970\x1f0gnd/118519859']


                    if tokens[0] in fieldsOfInterest:
                        outputLine=""
                        subtokens=tokens[1].split('\x1f')
                        if tokens[0]=="010@":
                            # 010@  Sprache (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/1500.pdf)
                            language=str(subtokens[0][1:])
                            if not language in languageHist:
                                languageHist[language]=1
                            else:
                                languageHist[language]=languageHist[language]+1
                        elif tokens[0]=="003@":
                            # 003@ the ID of the record (the PPN number)
                            # override the last seen PPN in case we have to deal with a new record
                            ppn=str(subtokens[0])
                        elif tokens[0]=="021A":
                            # 021A  Hauptsachtitel (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/4000.pdf)
                            r=handle021a(subtokens)
                            outputLine=ppn + '\t' +tokens[0] + '\t' + r
                        elif tokens[0]=="028A":
                            # 028A  1. Verfasser (siehe https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/3000.pdf)
                            r=handle028a(subtokens)
                            # if a GND is has been found add it to the name following after @
                            if r[1]:
                                outputLine=ppn + '\t' +tokens[0] + '\t' + r[0] + '@' +r[1]
                            else:
                                outputLine = ppn + '\t' + tokens[0] + '\t' + r[0]
                        else:
                            outputLine=ppn + "\t" +tokens[0]+"\t"+str(subtokens)

                        if verbose:
                            print(outputLine)

                        if createTextOutput:
                            if language in outputTextFilePaths:
                                outputTextFilePaths[language][1].write(outputLine+"\n")
                            else:
                                outputTextFilePaths["None"][1].write(outputLine + "\n")
                    currentLine = ""

                # if we find a space followed by \xlf, we have found a field separator
                if byte == b'\x1f' and last == b' ':
                    # currentLine = currentLine +"\t"
                    byte = b'\t'

                # if we find a \n followed by \x1d, we have found a record separator
                if byte == b'\x1d' and last == b'\n':
                    if verbose:
                        print("*NEW_RECORD*")
                    numberOfRecords+=1
                    language="None"

                # take care of 2 byte unicode characters, toggle unicode processing mode, see above
                # TODO handling of ß
                if byte == b'\xcc':
                    unicodeHot = True
                    lastUnicodeMarker = byte
                else:
                    if byte:
                        last = byte
                    else:
                        last = b' '
                    # ignore output for \r
                    if not byte == b'\r':
                        if not byte == b'\n':
                            if byte:
                                if not unicodeHot:
                                    currentLine = currentLine + byte.decode('utf-8',
                                                                            "replace")  # see https://docs.python.org/3/howto/unicode.html#the-unicode-type
                                else:
                                    unicodeHot = False

    if createTextOutput:
        for language in outputTextFilePaths:
            outputTextFilePaths[language][1].close()

    sumOfLanguageRecords=0
    for language in languageHist:
        sumOfLanguageRecords+=languageHist[language]

    endTime = str(datetime.now())

    print("\nStarted at:\t%s\nEnded at:\t%s" % (startTime, endTime))
    print("Found languages : %s" % languageHist.keys())
    print("Language available in %i of %i records."%(sumOfLanguageRecords,numberOfRecords))

    f = open(statisticsFilePath, "w", encoding="utf-8")
    f.write("\nStarted at:\t%s\nEnded at:\t%s\n" % (startTime, endTime))
    f.write("Found languages : %s\n" % languageHist.keys())
    f.write("Language available in %i of %i records.\n"%(sumOfLanguageRecords,numberOfRecords))
    f.close()