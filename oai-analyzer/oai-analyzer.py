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
# for time measurement
from datetime import datetime
import re
import os
import pickle
import urllib.request
import xml.etree.ElementTree as ET
import sqlite3
# OAI-PMH client library
from sickle import Sickle

# data science imports, the usual suspects
import numpy as np
import scipy as sp
import pandas as pd
import matplotlib as mpl
import matplotlib.cm as cm
import matplotlib.pyplot as plt

# general configuration

# enables verbose output during processing
verbose = True
# override locally stored temporary files, re-download files etc.; should be True during first run
forceOverride = False
# static URL pattern for Stabi's digitized collection downloads
metaDataDownloadURLPrefix = "http://digital.staatsbibliothek-berlin.de/metsresolver/?PPN="
# Berlin State Library internal setting
runningFromWithinStabi = False
# error log file name
errorLogFileName = "oai-analyzer_error.log"
# analysis path prefix
analysisPrefix = "analysis/"
# temporary downloads prefix
tempDownloadPrefix = "oai-analyzer_downloads/"
# file where all retrieved PPNs will be saved to
ppnFileName = analysisPrefix + "ppn_list.log"
# file where all retrieved *ambiguous* PPNs will be saved to
ambiguousPPNFileName = analysisPrefix + "ppn_ambiguous_list.csv"
# True if downloaded METS/MODS documents have to be kept after processing
keepMETSMODS=False
# file path for metadata record pickle
metadataRecordPicklePath = "save_120k_dc_all.pickle"
# DB-related settings (only interpreted if useSQLDB is True
useSQLDB=True
# path to the DB file
sqlDBPath=analysisPrefix+"oai-analyzer.db"

# do not change the following values
# XML namespace of MODS
modsNamespace = "{http://www.loc.gov/mods/v3}"

def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()


def isValidPPN(ppn):
    rePattern = "^PPN\d+[0-9X]?"
    p = re.compile(rePattern, re.IGNORECASE)
    if p.match(ppn):
        return True
    else:
        return False


def downloadMETSMODS(currentPPN):
    """
    Tries to download a METS/MODS file associated with a given PPN.
    ATTENTION! Should be surrounded by a try-catch statement as it does not handle network errors etc.
    :param currentPPN: The PPN for which the METS/MODS file shall be retrieved.
    :return: The path to the downloaded file.
    """
    # download the METS/MODS file first in order to find the associated documents
    currentDownloadURL = metaDataDownloadURLPrefix + currentPPN
    metsModsPath = tempDownloadPrefix + currentPPN + ".xml"
    if runningFromWithinStabi:
        proxy = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy)
        urllib.request.install_opener(opener)

    urllib.request.urlretrieve(currentDownloadURL, metsModsPath)
    return metsModsPath


def parseOriginInfo(child):
    """
    Parses an originInfo node and its children
    :param child: The originInfo child in the element tree.
    :return: A dict with the parsed information or None if the originInfo is invalid.
    """
    discardNode = True

    result = dict()
    result["publisher"] = ""
    # check if we can directly process the node
    if "eventType" in child.attrib:
        if child.attrib["eventType"] == "publication":
            discardNode = False
    else:
        # we have to check if the originInfo contains and edition node with "[Electronic ed.]" to discard the node
        children = child.getchildren()
        hasEdition = False
        for c in children:
            if c.tag == modsNamespace + "edition":
                hasEdition = True
                if c.text == "[Electronic ed.]":
                    discardNode = True
                else:
                    discardNode = False
        if not hasEdition:
            discardNode = False

    if discardNode:
        return None
    else:
        for c in child.getchildren():
            cleanedTag = c.tag.replace(modsNamespace, "")
            if cleanedTag == "place":
                result["place"] = c.find("{http://www.loc.gov/mods/v3}placeTerm").text.strip()
            if cleanedTag == "publisher":
                result["publisher"] = c.text.strip()
            # check for the most important date (see https://www.loc.gov/standards/mods/userguide/origininfo.html)
            if "keyDate" in c.attrib:
                result["date"] = c.text.strip()
    return result

def parseTitleInfo(child):
    result = dict()
    result["title"]=""
    result["subTitle"]=""

    for c in child.getchildren():
        cleanedTag = c.tag.replace(modsNamespace, "")
        result[cleanedTag]=c.text.strip()

    return result

def parseLanguage(child):
    result = dict()
    result["language"]=""

    for c in child.getchildren():
        cleanedTag = c.tag.replace(modsNamespace, "")
        if cleanedTag=="languageTerm":
            result["language"]=c.text.strip()

    return result

def parseName(child):
    result=dict()
    role=""
    name=""
    for c in child.getchildren():
        cleanedTag = c.tag.replace(modsNamespace, "")
        if cleanedTag=="role":
            for c2 in c.getchildren():
                ct=c2.tag.replace(modsNamespace, "")
                if ct=="roleTerm":
                    role=c2.text.strip()
        elif cleanedTag=="displayForm":
            name=c.text.strip()
    result[role]=name
    return result

def parseAccessCondition(child):
    result = dict()
    result["access"]=child.text.strip()
    return result

def processMETSMODS(currentPPN, metsModsPath):
    """
    Processes a given METS/MODS file.
    :param currentPPN: the current PPN
    :param metsModsPath: path to the METS/MODS file

    :return: A dataframe with the parsing results.
    """
    # parse the METS/MODS file
    tree = ET.parse(metsModsPath)
    root = tree.getroot()
    # only process possibly interesting nodes, i.e.,
    nodesOfInterest = ["originInfo", "titleInfo", "language", "name", "accessCondition"]

    # stores result dicts created by various parsing function (see below)
    resultDicts=[]
    # master dictionary, later used for the creation of a dataframe
    masterDict={'publisher':"",'place':"",'date':"",'title':"",'subTitle':"",'language':"",'aut':"",'rcp':"",'fnd':"",'access':""}
    # find all mods:mods nodes
    for modsNode in root.iter(modsNamespace + 'mods'):
        for child in modsNode:
            # strip the namespace
            cleanedTag = child.tag.replace(modsNamespace, "")
            #print(cleanedTag)
            #print(child)
            if cleanedTag in nodesOfInterest:
                if cleanedTag == "originInfo":
                    r = parseOriginInfo(child)
                    if r:
                        resultDicts.append(r)
                elif cleanedTag=="titleInfo":
                    r = parseTitleInfo(child)
                    if r:
                        resultDicts.append(r)
                elif cleanedTag=="language":
                    r = parseLanguage(child)
                    if r:
                        resultDicts.append(r)
                elif cleanedTag=="name":
                    r = parseName(child)
                    if r:
                        resultDicts.append(r)
                elif cleanedTag=="accessCondition":
                    r = parseAccessCondition(child)
                    if r:
                        resultDicts.append(r)
        # we are only interested in the first occuring mods:mods node
        break
    # copy results to the master dictionary
    for result in resultDicts:
        for key in result:
            masterDict[key]=[result[key]]
    masterDict["ppn"]=[currentPPN]
    return pd.DataFrame(data=masterDict)

def convertSickleRecordsToDataFrame(sickleRecords):
    availableKeys = dict()
    # check for all keys present in the previously downloaded dataset
    for i, r in enumerate(sickleRecords):
        for k in r.keys():
            if not k in availableKeys:
                availableKeys[k] = 1
            else:
                availableKeys[k] = availableKeys[k] + 1

    # print(availableKeys)

    # create a dictionary for the records
    values = dict()
    # take the keys as they have found within the downloaded OAI records
    keys = availableKeys.keys()
    # for every metadata field, create an empty array as the content of the dictionary filed under the key 'k'
    for k in keys:
        values[k] = []
    # in addition, store the PPN (the SBB's unique identifier for digitized content)
    values["PPN"] = []

    # under circumstances the identifier field of the DC records might be ambiguous, these records are listed here
    ambiguousPPNRecords = []

    # iterate over all saved records
    for record in sickleRecords:
        # we cannot iterate over the keys of record.metadata directly because not all records cotain the same fields,...
        for k in keys:
            # thus we check if the metadata field 'k' has been created above
            if k in values:
                # append the metadata fields to the dictionary created above
                # if the metadata field 'k' is not available input "None" instead
                if k in record:
                    value = record.get(k)[0]
                    if value:
                        if value.isdigit():
                            value = int(value)
                        else:
                            # p27 value=value.encode('ISO-8859-1')
                            # value = value.encode('ISO-8859-1').decode("utf-8", "backslashreplace")
                            pass
                    values[k].append(value)
                    # get the PPN and fix issues with it
                    if k == "identifier":
                        if len(record["identifier"]) > 1:
                            # sometimes there is more than one identifier provided
                            # check if it is a valid PPN
                            candidates = [str(record.get(k)[0]), str(record.get(k)[1])]
                            candidateIndex = 0
                            candidateCount = 0
                            i = 0
                            for c in candidates:
                                if c.startswith("PPN"):
                                    candidateIndex = i
                                    candidateCount += 1
                                else:
                                    i += 1
                            ppn = str(record.get(k)[1])

                            if candidateCount >= 1:
                                # print("\tCANDIDATE CONFLICT SOLVED AS: " + candidates[candidateIndex])
                                # print("\t\t" + str(record.get(k)[0]))
                                # print("\t\t" + str(record.get(k)[1]))
                                ambiguousPPNRecords.append(candidates)
                                ppn = candidates[0]
                        else:
                            ppn = str(record.get(k)[0])
                        values["PPN"].append(ppn)
                else:
                    values[k].append(np.nan)
    # create a data frame
    df = pd.DataFrame(values)
    df['date'] = pd.to_numeric(df['date'], errors='ignore', downcast='integer')

    return (df, ambiguousPPNRecords)


def createSupplementaryDirectories():
    if not os.path.exists(analysisPrefix):
        if verbose:
            print("Creating " + analysisPrefix)
        os.mkdir(analysisPrefix)
    if not os.path.exists(tempDownloadPrefix):
        if verbose:
            print("Creating " + tempDownloadPrefix)
        os.mkdir(tempDownloadPrefix)


if __name__ == "__main__":
    # connect to a metadata repository
    sickle = Sickle('http://digital.staatsbibliothek-berlin.de/oai')
    records = sickle.ListRecords(metadataPrefix='oai_dc', set='DC_all')

    createSupplementaryDirectories()

    errorFile = open(errorLogFileName, "w")
    savedRecords = []

    if forceOverride:
        printLog("Starting OAI record download...")
        # initialize some variables for counting and saving the metadata records
        savedDocs = 0
        # 2:15 h for 100k
        maxDocs = 120000  # 100 is just for testing, for more interesting results increase this value to 1000. ATTENTION! this will also take more time for reading data.

        # save the records locally as we don't want to have to rely on a connection to the OAI-PMH server all the time
        # iterate over all records until maxDocs is reached
        # ATTENTION! if you re-run this cell, the contents of the savedRecords array will be altered!
        try:
            for record in records:
                # check if we reach the maximum document value
                if savedDocs < maxDocs:
                    savedDocs = savedDocs + 1
                    # save the current record to the "savedRecords" array
                    savedRecords.append(record.metadata)
                    if savedDocs % 1000 == 0:
                        printLog("Downloaded %d of %d records." % (savedDocs, maxDocs))
                # if so, end the processing of the for-loop
                else:
                    break  # break ends the processing of the loop
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments: {1!r}"
            message = template.format(type(ex).__name__, ex.args)
            errorFile.write(message + "\n")

        printLog("Finished OAI download of " + str(len(savedRecords)) + " records.")
        pickle.dump(savedRecords, open(metadataRecordPicklePath, "wb"))

    # if savedRecords is empty, we have to load the data from the file system
    if not savedRecords:
        if os.path.exists(metadataRecordPicklePath):
            printLog("Restoring metadata records from " + metadataRecordPicklePath)
            savedRecords = pickle.load(open(metadataRecordPicklePath, "rb"))
            printLog("Done.")
        else:
            printLog("Could not depickle metadata records. Re-run with forceOverride option.")

    results = convertSickleRecordsToDataFrame(savedRecords)
    df = results[0]
    ambiguousPPNs = results[1]

    # save PPN list
    df["PPN"].to_csv(ppnFileName, sep=';', index=False)

    # test ambiguous PPNs and save results to a separate file
    printLog("Testing ambiguous PPNs.")
    ambigPPNFile = open(ambiguousPPNFileName, "w")
    ambigPPNFile.write("PPN_1;RESULT_1;PPN_2;RESULT_2;COMMENTS\n")
    for testPPNs in ambiguousPPNs:
        line = ""
        for ppn in testPPNs:
            # could it be a PPN?
            # if ppn.startswith("PPN"):
            #    line+=ppn+";"+"OK;"
            # else:
            #    line += ppn + ";" + "NO!;"
            line += ppn + ";" + str(isValidPPN(ppn)) + ";"
        line += "\n"
        ambigPPNFile.write(line)
    ambigPPNFile.close()

    # process all retrieved PPNs
    ppns = df["PPN"].values.tolist()
    #debug
    #ppns = df["PPN"].values.tolist()[0:1000]


    forceOverridePossible=False
    if os.path.exists(analysisPrefix + "analyticaldf.xlsx"):
        forceOverridePossible=True

    if forceOverride and forceOverridePossible:
    #if True:
        printLog("Processing METS/MODS documents.")
        resultDFs=[]
        processedDocs=0
        maxDocs=len(ppns)
        for ppn in ppns:
            currentMETSMODS = None
            processedDocs+=1
            if processedDocs % 100 == 0:
                printLog("\tProcessed %d of %d METS/MODS documents." % (processedDocs, maxDocs))
            try:
                # debug
                #ppn="PPN74616453X"
                currentMETSMODS = downloadMETSMODS(ppn)
            except Exception as ex:
                template = "An exception of type {0} occurred. Arguments: {1!r}"
                message = template.format(type(ex).__name__, ex.args)
                errorFile.write(ppn + "\t" + message + "\n")
            if currentMETSMODS:
                currentDF=processMETSMODS(ppn, currentMETSMODS)
                #debug
                #currentDF.to_csv(analysisPrefix + "debug.csv",sep=';',index=False)
                resultDFs.append(currentDF)
                #raise (SystemExit)
                if not keepMETSMODS:
                    os.remove(currentMETSMODS)

        analyticalDF=pd.concat(resultDFs,sort=False)
        # store the results permanently
        analyticalDF.to_csv(analysisPrefix + "analyticaldf.csv",sep=';',index=False)
        analyticalDF.to_excel(analysisPrefix + "analyticaldf.xlsx", index=False)

        if useSQLDB:
            conn=sqlite3.connect(sqlDBPath)
            analyticalDF.to_sql("oai_results",conn,if_exists='replace')
    else:
        printLog("Read METS/MODS analysis table from: "+analysisPrefix + "analyticaldf.xlsx")
        analyticalDF=pd.read_excel(analysisPrefix + "analyticaldf.xlsx")

    print(analyticalDF.columns)

    ocrPPNs=[]
    # read in OCR'ed PPNs
    with open('../_datasets/ocr_ppn_list.txt') as f:
        lines = f.readlines()
        lines.pop(0)
        for line in lines:
            line_split = line.split(' ')
            ppn_cleaned = "PPN"+line_split[len(line_split) - 1].rstrip()
            ocrPPNs.append(ppn_cleaned)
    f.close()

    # create a dataframe from the OCR PPN list
    ocrDF=pd.DataFrame({"ppn":ocrPPNs})

    # join the two dataframes to discover all documents that got OCR'ed
    joinedDF=pd.merge(analyticalDF,ocrDF,on='ppn')

    printLog("Rows in analyticalDF: %i"%len(analyticalDF.index))
    printLog("Rows in ocrDF: %i" % len(ocrDF.index))
    printLog("Rows in joinedDF: %i" % len(joinedDF.index))

    joinedDF.to_excel(analysisPrefix + "joinedDF.xlsx", index=False)

    # finally, clean up
    errorFile.close()
    print("Done.")
