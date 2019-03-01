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

import urllib.request
import os
from datetime import datetime
import requests
from PIL import Image

# the maximum dimensions ot the thumbnail as a tuple (<width,height>) (aspect ratio remains intact)
titlePageThumbnailSize=(512,512)
errorLogFileName="./addFirstPages_error.log"

startTime = str(datetime.now())

ppns=[]
titlePagesDirectory="C:\david.local\__datasets\\titlepages"
downloadLink="https://content.staatsbibliothek-berlin.de/dc/@PPN@-00000001/full/full/0/default.jpg"

with open("ppn_list_146000.csv") as f:
    lines = f.readlines()
    for line in lines:
        ppns.append(line.replace("\n", "").replace("PPN", ""))
    f.close()

errorFile = open(errorLogFileName, "w")

missingCount=0
for ppn in ppns:
    if not os.path.exists(titlePagesDirectory+"/PPN"+ppn+".jpg"):
        #print("Missing PPN"+ppn)
        missingCount+=1
        try:
            downloadedFile="./temp/PPN" + ppn + ".jpg"
            # skip already downloaded images
            if not os.path.exists(downloadedFile):
                with open(downloadedFile, 'wb') as f:
                    resp = requests.get(
                        downloadLink.replace('@PPN@', ppn),verify=False)
                    f.write(resp.content)
                # quick'n'dirty fix, a 34 byte file is an error
                statinfo = os.stat(downloadedFile)
                if statinfo.st_size<=34:
                    errorFile.write(str(datetime.now()) + "\t" + ppn + "\t" + "NOT EXISTENT" + "\n")
                    os.remove(downloadedFile)
                else:
                    img = Image.open(downloadedFile)
                    img.thumbnail(titlePageThumbnailSize)
                    img.save(downloadedFile)
        except Exception as ex:
            print("Error downloading " + ppn+".jpg")
            template = "An exception of type {0} occurred. Arguments: {1!r}"
            message = template.format(type(ex).__name__, ex.args)
            errorFile.write(str(datetime.now()) + "\t" + ppn + "\t" + message + "\n")

errorFile.close()
endTime = str(datetime.now())
print("Started at:\t%s\nEnded at:\t%s" % (startTime, endTime))
print("Missing PPNs: %i"%missingCount)