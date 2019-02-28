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

import numpy as np
import pandas as pd
import time
pd.set_option('display.width', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 40)
pd.set_option('display.notebook_repr_html', True)



import urllib # to read from URLs
from datetime import datetime # for time measurement
import sys
import pickle


# OAI
from sickle import Sickle


def printLog(text):
    now=str(datetime.now())
    print("["+now+"]\t"+text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()


runningFromWithinStabi=False
# main PPN harvesting
savedRecords=[]

if runningFromWithinStabi:
    proxy = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy)
    urllib.request.install_opener(opener)

# create OAI-PMH reader pointing to the Stabi OAI-PMH endpoint of the digitzed collections
sickle = Sickle('http://digital.staatsbibliothek-berlin.de/oai')
records = sickle.ListRecords(metadataPrefix='oai_dc', set='DC_all')

if True:
    printLog("Starting OAI-PMH record download...")
    # initialize some variables for counting and saving the metadata records
    savedDocs=0

    maxDocs=146000 # 100 is just for testing, for more interesting results increase this value to 1000. ATTENTION! this will also take more time for reading data.

    # save the records locally as we don't want to have to rely on a connection to the OAI-PMH server all the time
    # iterate over all records until maxDocs is reached
    # ATTENTION! if you re-run this cell, the contents of the savedRecords array will be altered!
    for record in records:
        # check if we reach the maximum document value
        if savedDocs<maxDocs:
            savedDocs=savedDocs+1
            # save the current record to the "savedRecords" array
            savedRecords.append(record.metadata)
            if savedDocs%10000==0:
                printLog("Downloaded %d of %d records."%(savedDocs,maxDocs))
        # if so, end the processing of the for-loop
        else:
            break # break ends the processing of the loop

    printLog("Finished OAI-PMH download of "+str(len(savedRecords))+" records.")
    pickle.dump( savedRecords, open( "save_120k_dc_all.pickle", "wb" ) )


availableKeys = dict()

# check for all keys present in the previously downloaded dataset
for i, r in enumerate(savedRecords):
    for k in r.keys():
        if not k in availableKeys:
            availableKeys[k] = 1
        else:
            availableKeys[k] = availableKeys[k] + 1

print(availableKeys)

# create a dictionary for the records
values = dict()
# take the keys as they have found within the downloaded OAI records
keys = availableKeys.keys()
# for every metadata field, create an empty array as the content of the dictionary filed under the key 'k'
for k in keys:
    values[k] = []
# in addition, store the PPN (the SBB's unique identifier for digitized content)
values["PPN"] = []

# iterate over all saved records
for record in savedRecords:
    # we cannot iterate over the keys of record.metadata directly because not all records cotain the same fields,...
    for k in keys:
        # thus we check if the metadata field 'k' has been created above
        if k in values:
            # append the metadata fields to the dictionary created above
            # if the metadata field 'k' is not available input "None" instead
            # values[k].append(record.get(k,["None"])[0].encode('ISO-8859-1'))
            if k in record:
                value = record.get(k)[0]
                if value:
                    if value.isdigit():
                        value = int(value)
                    else:
                        # p27 value=value.encode('ISO-8859-1')
                        # value=value.encode('ISO-8859-1').decode("utf-8", "backslashreplace")
                        value = value
                values[k].append(value)
                # get the PPN
                if k == "identifier":
                    # if len(record["identifier"])>1:
                    #    ppn=str(record.get(k)[1])
                    # else:
                    #    ppn=str(record.get(k)[0])
                    ppn = ""
                    for r in record["identifier"]:
                        if r.startswith("PPN"):
                            ppn = r
                            break
                    values["PPN"].append(ppn)
            else:
                values[k].append(np.nan)
# create a data frame from the values
df = pd.DataFrame(values)
df['date'] = pd.to_numeric(df['date'], errors='ignore', downcast='integer')

# save everything:
# 1) an Excel file with all columns
# 2) a one-column "CSV" with found PPNs compatible with sbbget.py
df.to_excel("./ppn_records_%i.xlsx"%len(savedRecords))
df.PPN.to_csv("./ppn_list_%i.csv"%len(savedRecords),index=False)
printLog("Done.")