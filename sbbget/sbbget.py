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

import shutil
import argparse
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import os
from PIL import Image
from time import gmtime, strftime
from datetime import datetime

import requests
import tarfile as TAR


def downloadData(currentPPN,downloadPathPrefix,metsModsDownloadPath):
    # static URL pattern for Stabi's digitized collection downloads
    metaDataDownloadURLPrefix = "http://digital.staatsbibliothek-berlin.de/metsresolver/?PPN="
    tiffDownloadLink = "http://ngcs.staatsbibliothek-berlin.de/?action=metsImage&format=jpg&metsFile=@PPN@&divID=@PHYSID@&original=true"

    # download the METS/MODS file first in order to find the associated documents
    currentDownloadURL = metaDataDownloadURLPrefix + currentPPN
    # todo: error handling
    metsModsPath= metsModsDownloadPath+"/"+currentPPN+".xml"
    if runningFromWithinStabi:
        proxy = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy)
        urllib.request.install_opener(opener)

    if not allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
        urllib.request.urlretrieve(currentDownloadURL,metsModsPath)
    # daz: TODO JPG-Wandlung der Vollseiten-TIFFs automatisieren und dokumentieren
    else:
        with open(metsModsPath, 'wb') as f:
            resp = requests.get(currentDownloadURL, verify=False)
            f.write(resp.content)

    # STANDARD file download settings
    retrievalScope=['TIFF','FULLTEXT']
    # TODO: per Schalter steuern, default: FULLTEXT und PRESENTATION
    # <mets:fileGrp USE="THUMBS"
    # <mets:fileGrp USE="DEFAULT">
    # <mets:fileGrp USE="FULLTEXT">
    # <mets:fileGrp USE="PRESENTATION">

    # parse the METS/MODS file
    tree = ET.parse(metsModsPath)
    root = tree.getroot()

    fileID2physID=dict()
    # first, we have to build a dict mapping various IDs to physical pages
    for div in root.iter('{http://www.loc.gov/METS/}div'):
        for fptr in div.iter('{http://www.loc.gov/METS/}fptr'):
            #print(fptr.tag,fptr.attrib)
            fileID2physID[fptr.attrib['FILEID']]=div.attrib['ID']
            #print(fptr.attrib['FILEID'],fileID2physID[fptr.attrib['FILEID']])

    # a list of downloaded TIFF files
    alreadyDownloadedPhysID=[]
    # a dict of paths to ALTO fulltexts (id->download dir)
    altoPaths=dict()

    # a list of downloaded image paths in order to remove them if needed (controled by deleteMasterTIFFs)
    masterTIFFpaths=[]

    # we are only interested in fileGrp nodes below fileSec...
    for fileSec in root.iter('{http://www.loc.gov/METS/}fileSec'):
        for child in fileSec.iter('{http://www.loc.gov/METS/}fileGrp'):
            currentUse=child.attrib['USE']

            # which contains file nodes...
            for fileNode in child.iter('{http://www.loc.gov/METS/}file'):
            # embedding FLocat node pointing to the URLs of interest
                id = fileNode.attrib['ID']
                downloadDir="./"+downloadPathPrefix + "/" + id
                saveDir= "./" + savePathPrefix + "/" + id
                # only create need sub directories
                if currentUse in retrievalScope :
                    if not os.path.exists(downloadDir):
                        if verbose:
                            print(downloadDir)
                        os.mkdir(downloadDir)

                if 'TIFF' in retrievalScope:
                    # try to download TIFF first
                    downloadDir = "./" + downloadPathPrefix + "/" + id
                    saveDir = "./" + savePathPrefix + "/"
                    tiffDir=downloadDir.replace(currentUse,'TIFF')
                    if not os.path.exists(tiffDir):
                        os.mkdir(tiffDir)
                    try:
                        if not fileID2physID[id] in alreadyDownloadedPhysID:
                            if verbose:
                                print("Downloading to " + tiffDir)
                            if not skipDownloads:
                                # TODO  JPG-Wandlung der Vollseiten-TIFFs automatisieren und dokumentieren
                                if not allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
                                    urllib.request.urlretrieve(tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',fileID2physID[id]),tiffDir+"/"+currentPPN+".tif")
                                else:
                                    with open(tiffDir+"/"+currentPPN+".tif", 'wb') as f:
                                         resp = requests.get(tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',fileID2physID[id]), verify=False)
                                         f.write(resp.content)
                                masterTIFFpaths.append(tiffDir+"/"+currentPPN+".tif")
                                # open the freshly download TIFF and convert it to the illustration export file format
                                img = Image.open(tiffDir + "/" + currentPPN + ".tif")
                                img.save(tiffDir + "/" + currentPPN + illustrationExportFileType)
                            alreadyDownloadedPhysID.append(fileID2physID[id])
                    except urllib.error.URLError:
                        print("Error downloading " + currentPPN+".tif")

                if currentUse in retrievalScope : # e.g., TIFF or FULLTEXT
                    for fLocat in fileNode.iter('{http://www.loc.gov/METS/}FLocat'):
                        if (fLocat.attrib['LOCTYPE'] == 'URL'):
                            if verbose:
                                print("Processing "+id)
                            href=fLocat.attrib['{http://www.w3.org/1999/xlink}href']
                            rawPath=urlparse(href).path
                            tokens=rawPath.split("/")
                            outputPath=tokens[-1]

                            if verbose:
                                print("\tSaving to: " + downloadDir + "/" + outputPath)
                            try:
                                if not skipDownloads:
                                    if allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
                                        with open(downloadDir + "/" + outputPath, 'wb') as f:
                                            resp = requests.get(href, verify=False)
                                            f.write(resp.content)
                                    else:
                                        urllib.request.urlretrieve(href, downloadDir+"/"+outputPath)
                                if currentUse=='FULLTEXT':
                                    altoPaths[id]=[downloadDir,outputPath]
                            except urllib.error.URLError:
                                print("\tError processing "+href)

    # extract illustrations found in ALTO files
    #illuID = 0
    if extractIllustrations:
        # create a .tar file for the extracted illustrations
        tarBallPath = saveDir + currentPPN + ".tar"
        tarBall = None
        if createTarBallOfExtractedIllustrations:
            tarBall = TAR.open(tarBallPath, "w")

        for key in altoPaths:
            tiffDir=altoPaths[key][0].replace('FULLTEXT','TIFF')+"/"+altoPaths[key][1].replace(".","_")+"/"
            tiffDir="."+tiffDir[1:-1]
            if not os.path.exists(tiffDir):
                os.mkdir(tiffDir)
                if verbose:
                    print("Creating "+tiffDir)
            if verbose:
                print("Processing ALTO XML in: "+altoPaths[key][0]+"/"+altoPaths[key][1])
            tree = ET.parse(altoPaths[key][0]+"/"+altoPaths[key][1])
            root = tree.getroot()




            for e in root.findall('.//{http://www.loc.gov/standards/alto/ns-v2#}PrintSpace'):
                for el in e:
                    if el.tag in consideredAltoElements:
                        illuID=el.attrib['ID']
                        #if verbose:
                        #print("\tExtracting "+illuID)
                        h=int(el.attrib['HEIGHT'])
                        w=int(el.attrib['WIDTH'])
                        if h > 150 and w > 150:
                            if verbose:
                                print("Saving image to: "+saveDir + key.split("_")[1] + "_" +illuID + illustrationExportFileType)
                            entry = {"WIDTH" : w, "HEIGHT": h, "LABEL" : key.split("_")[1]}
                            dimensions.append(entry)
                            hpos=int(el.attrib['HPOS'])
                            vpos=int(el.attrib['VPOS'])
                            #print(altoPaths[key])
                            #print(altoPaths[key][0].replace('FULLTEXT','TIFF')+"/"+currentPPN+'.tif')
                            img=Image.open(altoPaths[key][0].replace('FULLTEXT','TIFF')+"/"+currentPPN+'.tif')
                            if verbose:
                                print("\t\tImage size:",img.size)
                                print("\t\tCrop range:", h, w, vpos, hpos)
                            # (left, upper, right, lower)-tuple.
                            img2 = img.crop((hpos, vpos, hpos+w, vpos+h))

                            extractedIllustrationPath=saveDir + key.split("_")[1] + "_" +illuID + illustrationExportFileType
                            img2.save(extractedIllustrationPath)
                            if createTarBallOfExtractedIllustrations:
                                tarBall.add(extractedIllustrationPath)
                                os.remove(extractedIllustrationPath)

                        else:
                            if verbose:
                                print("Image is too small: processing skipped.")
        if createTarBallOfExtractedIllustrations:
            tarBall.close()

    if deleteMasterTIFFs:
        for masterTiff in masterTIFFpaths:
            os.remove(masterTiff)

    if deleteTempFolders:
        shutil.rmtree('sbb/download_temp', ignore_errors=True)
        if not os.path.exists("sbb/download_temp"):
            if verbose:
                print("Deleted temporary folders.")


if __name__ == "__main__":
    downloadPathPrefix="."
    # in case the PPN list contains PPNs without "PPN" prefix, it will be added
    addPPNPrefix=True
    # should illustration, found by the OCR, be extracted?
    extractIllustrations=True
    # determines file format for extracted images, if you want to keep max. quality use ".tif" instead
    illustrationExportFileType= ".jpg"
    # (recommended setting) create .tar files from the extracted illustrations and delete extracted illustrations afterwards
    # facilitating distribution as a much fewer files will be created. however, this will slow down processing because of
    # the packing overhead.
    createTarBallOfExtractedIllustrations=True
    # delete temporary files (will remove XML documents, OCR fulltexts and leave you alone with the extracted images
    deleteTempFolders=False
    # if True, downloaded full page TIFFs will be removed after illustration have been extracted (saves a lot of storage space)
    deleteMasterTIFFs=True
    # handy if a certain file set has been downloaded before and processing has to be limited to post-processing only
    skipDownloads=False
    # enables verbose output during processing
    verbose=True
    # determines which ALTO elements should be extracted
    consideredAltoElements=['{http://www.loc.gov/standards/alto/ns-v2#}Illustration']#,'{http://www.loc.gov/standards/alto/ns-v2#}GraphicalElement']

    # setting this variable to true will disable SSL certificate verification - USE AT YOUR OWN RISK!
    allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION=False
    # Berlin State Library internal setting
    runningFromWithinStabi=False
    # Stabi internal setup variants, may vary depending on the sub-net of the machine
    # dev Windows: allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION=True   runningFromWithinStabi=True
    # dev Linux:   allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION=False   runningFromWithinStabi=True

    # path to the log file which also stores information if the script run has been canceled and it should be resumed (in case of a large amount of downloads)
    # if you want to force new downloads, just delete this file
    logFileName = 'ppn_log.log'
    # error log file name
    errorLogFileName="sbbget_error.log"

    ppns = []
    dimensions = []


    if allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
        print("ATTENTION! SSL certificate verification is disabled. Do not use in production.")

    startTime = str(datetime.now())

    # a PPN list for testing purposes (some with OCR)
    with open("test_ppn_list.txt") as f:
         lines = f.readlines()
         for line in lines:
            ppns.append(line.replace("\n", ""))
         f.close()

    # a PPN list with fulltexts
    # with open('OCR-PPN-Liste.txt') as f:
    #      lines = f.readlines()
    #      lines.pop(0)
    #      for line in lines:
    #          line_split = line.split(' ')
    #          ppn_cleaned = line_split[len(line_split) - 1].rstrip().replace('PPN', '')
    #          ppns.append(ppn_cleaned)
    #
    #      f.close()

    # a PPN list containing the Wegehaupt Digital collection
    # with open("wegehaupt_digital.txt") as f:
    #      lines = f.readlines()
    #      for line in lines:
    #          ppns.append(line.replace("\n",""))
    #      f.close()

    print("Number of documents to be processed: " + str(len(ppns)))
    start = 0
    end = len(ppns)
    # in case of a prior abort of the script, try to resume from the last known state
    if os.path.isfile(logFileName):
        with open(logFileName, 'r') as log_file:
            log_entries = log_file.readlines()
            start = len(log_entries)
    else:
        with open(logFileName, 'w') as log_file:
            pass

    # demo stuff - please remove if you want to work on real data
    #ppns=["3308099233"]#,"609921959"]
    #end = len(ppns)
    # end demo

    summaryString=""

    errorFile = open(errorLogFileName, "w")

    for i in range(start,end):
        sbbPrefix = "sbbget_downloads"
        downloadPathPrefix="download_temp"
        savePathPrefix="extracted_images"
        ppn = ppns[i]
        current_time = strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        with open(logFileName, 'a') as log_file:
            log_file.write(current_time + " " + ppn + " (Number: %d)" % (i) + "\n")

        if addPPNPrefix:
            ppn="PPN"+ppn

        if not os.path.exists(sbbPrefix+"/"):
            if verbose:
                print("Creating "+sbbPrefix+"/")
            os.mkdir(sbbPrefix+"/")

        downloadPathPrefix= sbbPrefix + "/" + downloadPathPrefix
        savePathPrefix = sbbPrefix + "/" + savePathPrefix

        summaryString = "\nSUMMARY"
        if not os.path.exists(downloadPathPrefix+"/"):
            if verbose:
                print("Creating "+downloadPathPrefix+"/")
            os.mkdir(downloadPathPrefix+"/")
        downloadPathPrefix=downloadPathPrefix+"/"+ppn

        summaryString += "\n\tDownloads (fulltexts, original digitizations etc.) were, e.g., stored at: "+downloadPathPrefix
        if not os.path.exists(downloadPathPrefix+"/"):
            if verbose:
                print("Creating "+downloadPathPrefix+"/")
            os.mkdir(downloadPathPrefix+"/")

        if not os.path.exists(savePathPrefix+"/"):
            if verbose:
                print("Creating "+savePathPrefix+"/")
            os.mkdir(savePathPrefix+"/")
        savePathPrefix=savePathPrefix+"/"+ppn
        if not os.path.exists(savePathPrefix+"/"):
            if verbose:
                print("Creating "+savePathPrefix+"/")
            os.mkdir(savePathPrefix+"/")
        summaryString += "\n\tExtracted images were, e.g., stored at: " + savePathPrefix

        metsModsDownloadPath=downloadPathPrefix + "/__metsmods/"
        if not os.path.exists(metsModsDownloadPath):
            if verbose:
                print("Creating " + metsModsDownloadPath)
            os.mkdir(metsModsDownloadPath)
        summaryString += "\n\tMETS/MODS files were, e.g., stored at: " + metsModsDownloadPath

        try:
            downloadData(ppn,downloadPathPrefix,metsModsDownloadPath)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments: {1!r}"
            message = template.format(type(ex).__name__, ex.args)
            errorFile.write(str(datetime.now()) + "\t" + ppn + "\t" + message + "\t" + downloadPathPrefix + "\t" + metsModsDownloadPath + "\n")

    errorFile.close()

    endTime = str(datetime.now())

    print(summaryString + "\n")
    # daz new
    print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))
    if allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
        print("Run without SSL certificate verification.")

    print("Done.")
