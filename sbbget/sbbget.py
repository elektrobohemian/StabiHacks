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

import shutil
import argparse
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import os
from PIL import Image
from time import gmtime, strftime, sleep
from datetime import datetime
import sys
import requests
import tarfile as TAR


def downloadData(currentPPN,downloadPathPrefix,metsModsDownloadPath):
    # static URL pattern for Stabi's digitized collection downloads
    # old version
    #metaDataDownloadURLPrefix = "http://digital.staatsbibliothek-berlin.de/metsresolver/?PPN="
    metaDataDownloadURLPrefix ="https://content.staatsbibliothek-berlin.de/dc/"
    # old
    tiffDownloadLink = "http://ngcs.staatsbibliothek-berlin.de/?action=metsImage&format=jpg&metsFile=@PPN@&divID=@PHYSID@&original=true"
    
    
    tiffDownloadLink="https://content.staatsbibliothek-berlin.de/dms/@PPN@/800/0/@PHYSID@.tif?original=true"

    saveDir=""
    pathToTitlePage=""

    # download the METS/MODS file first in order to find the associated documents
    #
    # old
    # currentDownloadURL = metaDataDownloadURLPrefix + currentPPN
    currentDownloadURL = metaDataDownloadURLPrefix + currentPPN+".mets.xml"
    # debug
    #print(currentDownloadURL)
    # todo: error handling
    # old version
    metsModsPath= metsModsDownloadPath+"/"+currentPPN+".xml"
    #metsModsPath= metsModsDownloadPath+"/"+currentPPN+".mets.xml"
    print(metsModsPath)
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

    # second, we will link the physical page to the logical as indicated in the original work
    # this information is stored in the following tag
    #<mets:smLink xmlns:xlink="http://www.w3.org/1999/xlink" xlink:to="PHYS_0433" xlink:from="LOG_0015"/>
    physID2logicalID = dict()
    smLinks = root.findall(
        ".//{http://www.loc.gov/METS/}smLink")
    for l in smLinks:
        physID2logicalID[l.attrib['{http://www.w3.org/1999/xlink}to']]=l.attrib['{http://www.w3.org/1999/xlink}from']
        print(l.attrib)

    print(physID2logicalID)
    #sys.exit(0)
    # find the image with the title page (if available)
    titlePage = root.findall(".//{http://www.loc.gov/METS/}div[@TYPE='title_page']")
    titlePageLogID=""
    if titlePage:
        titlePageLogID=titlePage[0].attrib['ID']
    else:
        if verbose and storeExtraTitlePageThumbnails:
            print("\tNo title page found. Using first image instead.")
    # if we have found a title page before, select the link to its physical page
    physTitlePageNodes=root.findall(".//{http://www.loc.gov/METS/}smLink[@{http://www.w3.org/1999/xlink}from='"+titlePageLogID+"']")
    titlePagePhysID=""
    if physTitlePageNodes:
        titlePagePhysID=physTitlePageNodes[0].attrib['{http://www.w3.org/1999/xlink}to']

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

            firstFileNode=True
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
                        currentPhysicalFile=fileID2physID[id]
                        currentLogicalID=physID2logicalID[currentPhysicalFile]
                        if not currentPhysicalFile in alreadyDownloadedPhysID:
                            isTitlePage=False
                            # check if the current image is the title page
                            if currentPhysicalFile==titlePagePhysID:
                                isTitlePage=True
                            if verbose:
                                if isTitlePage:
                                    print("Downloading to " + tiffDir+" (TITLE PAGE)")
                                else:
                                    print("Downloading to " + tiffDir)

                            if (not skipDownloads) or (forceTitlePageDownload and isTitlePage):
                                cleanedPhysID=currentPhysicalFile.replace("PHYS_","").zfill(8)
                                if not allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
                                    if verbose:
                                        print("Trying to get image for phys ID "+currentPhysicalFile+" file from: "+tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',cleanedPhysID))
                                    urllib.request.urlretrieve(tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',cleanedPhysID),tiffDir+"/"+currentPPN+".tif")
                                else:
                                    with open(tiffDir+"/"+currentPPN+".tif", 'wb') as f:
                                        if verbose:
                                            print("Trying to get image for phys ID "+currentPhysicalFile+" file from: "+tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',cleanedPhysID))
                                        resp = requests.get(tiffDownloadLink.replace('@PPN@',currentPPN).replace('@PHYSID@',cleanedPhysID), verify=False)
                                        f.write(resp.content)

                                # save the logical and physical ID for later usage separated by space
                                with open(tiffDir + "/" + currentPPN + ".txt", 'w') as f:
                                    f.write(currentLogicalID+" "+currentPhysicalFile+"\n")


                                masterTIFFpaths.append(tiffDir+"/"+currentPPN+".tif")
                                # open the freshly download TIFF and convert it to the illustration export file format
                                img = Image.open(tiffDir + "/" + currentPPN + ".tif")
                                img.save(tiffDir + "/" + currentPPN + illustrationExportFileType)

                                # store the title page separately if desired
                                if storeExtraTitlePageThumbnails:
                                    if isTitlePage:
                                        img.thumbnail(titlePageThumbnailSize)
                                        pathToTitlePage=downloadPathPrefix+"/" +"_TITLE_PAGE"+ illustrationExportFileType
                                        img.save(pathToTitlePage)
                                    else:
                                        # otherwise, take the first seen image as title page
                                        if firstFileNode:
                                            img.thumbnail(titlePageThumbnailSize)
                                            pathToTitlePage = downloadPathPrefix + "/" + "_TITLE_PAGE" + illustrationExportFileType
                                            img.save(pathToTitlePage)
                            alreadyDownloadedPhysID.append(currentPhysicalFile)
                            firstFileNode=False
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

    # extract illustrations found in ALTO files (only possible if the images have been downloaded before...)
    #illuID = 0
    if extractIllustrations and (not skipDownloads):
        if "PPN" not in saveDir:
            saveDir = "./" + savePathPrefix + "/"+currentPPN+"/"
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

    return pathToTitlePage

if __name__ == "__main__":
    downloadPathPrefix="."
    # in case the PPN list contains PPNs without "PPN" prefix, it will be added
    addPPNPrefix=True
    
    # STANDARD file download settings (will download images and fulltexts): retrievalScope=['TIFF','FULLTEXT'] 
    # please not the the the retrieval scope overrides all of the following settings.
    # if set to 'FULLTEXT', no images will be downloaded even if forceTitlePageDownload etc. is set.
    retrievalScope=['TIFF','FULLTEXT']
    # TODO: per Schalter steuern, default: FULLTEXT und PRESENTATION
    # <mets:fileGrp USE="THUMBS"
    # <mets:fileGrp USE="DEFAULT">
    # <mets:fileGrp USE="FULLTEXT">
    # <mets:fileGrp USE="PRESENTATION">
    
    # should illustration, found by the OCR, be extracted?
    extractIllustrations=True
    # determines file format for extracted images, if you want to keep max. quality use ".tif" instead
    illustrationExportFileType= ".jpg"
    # (recommended setting) create .tar files from the extracted illustrations and delete extracted illustrations afterwards
    # facilitating distribution as a much fewer files will be created. however, this will slow down processing because of
    # the packing overhead.
    createTarBallOfExtractedIllustrations=True
    # store title page thumbnails separately? (will be saved in illustrationExportFileType format) works only if skipDownloads=False or forceTitlePageDownload=True
    storeExtraTitlePageThumbnails=True
    # the maximum dimensions ot the thumbnail as a tuple (<width,height>) (aspect ratio remains intact)
    titlePageThumbnailSize=(512,512)
    # delete temporary files (will remove XML documents, OCR fulltexts and leave you alone with the extracted images
    deleteTempFolders=False
    # if True, downloaded full page TIFFs will be removed after illustration have been extracted (saves a lot of storage space)
    deleteMasterTIFFs=False
    # handy if a certain file set has been downloaded before and processing has to be limited to post-processing only
    skipDownloads=False
    # overrides skipDownloads to force the download of title pages (first pages will not be downloaded!)
    forceTitlePageDownload = True
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

    # for testing purposes we try a a collection of historical illustrated childrens' playbooks, some with OCR
    # this will download and create approx. 5,97 GB of test data (when limited to a 5 file download)
    # set a debug download limit for testing
    debugLimit=5
    i=0
    with open("../ppn_lists/diverse_ill_spielbuch.csv") as f:
        lines = f.readlines()
        for line in lines:
           ppns.append(line.replace("\n", "").replace("PPN",""))
           i+=1
           if i>=debugLimit:
               break
        f.close()

    # # a PPN list of Orbis pictus
    # ppns.append("PPN745459102")
    # ppns.append("770159389")
    # ppns.append("PPN770184375")

    print("Number of documents to be processed: " + str(len(ppns)))
    start = 0
    end = len(ppns)
    # in case of a prior abort of the script, try to resume from the last known state
    if os.path.isfile(logFileName):
        print("\nATTENTION! Log file found under %s. The script will try to continue processing. \nIf you want to restart, please remove the log file. \nThe script will continue in 15 seconds..."%logFileName)
        sleep(15)
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

    titlePagePaths=[]
    for i in range(start,end):
        sbbPrefix = "sbbget_downloads"
        downloadPathPrefix="download_temp"
        savePathPrefix="extracted_images"
        ppn = ppns[i]
        current_time = strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        with open(logFileName, 'a') as log_file:
            log_file.write(current_time + " " + ppn + " (Number: %d)" % (i) + "\n")

        if addPPNPrefix:
            if not ppn.startswith("PPN"):
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

        #debug
        #try:
        pathToTitlePage=downloadData(ppn,downloadPathPrefix,metsModsDownloadPath)
        if pathToTitlePage:
            titlePagePaths.append(pathToTitlePage)
        #except Exception as ex:
        #    template = "An exception of type {0} occurred. Arguments: {1!r}"
        #    message = template.format(type(ex).__name__, ex.args)
        #    errorFile.write(str(datetime.now()) + "\t" + ppn + "\t" + message + "\t" + downloadPathPrefix + "\t" + metsModsDownloadPath + "\n")

    errorFile.close()

    # write out paths to title pages
    titlePagePathsFile = open("title_pages.txt", "w")
    for path in titlePagePaths:
        titlePagePathsFile.write(path+"\n")
    titlePagePathsFile.close()

    endTime = str(datetime.now())

    print(summaryString + "\n")
    # daz new
    print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))
    if allowUnsafeSSLConnections_NEVER_USE_IN_PRODUCTION:
        print("Run without SSL certificate verification.")

    print("Done.")
