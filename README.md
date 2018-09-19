# StabiHacks

Various utilities to deal with metadata and content provided by the Berlin State Library/Staatsbibliothek zu Berlin

## SBBget
* a [Python script](sbbget/sbbget.py) that is capable of downloading digitized media, the associated metadata, and its fulltext from Berlin State Library's digitized collections. 
* it also extracts images that have been detected by the OCR.
* its logic is based on the more or less unique PPN identifier used at the library.
* two PPN lists are shipped for demonstration purposes. more can be obtained at the Berlin State Library or the creator of the script.
* the script will create various folders below its current working directory, e.g.,
    * downloads (fulltexts, original digitizations etc.) are stored at: sbbget_downloads/download_temp/<PPN>
    * extracted images are stored at: sbbget_downloads/extracted_images/<PPN>
    * METS/MODS files are stored at: sbbget_downloads/download_temp/<PPN>/__metsmods/

## OAI-Analyzer
* [Python script](oai-analyzer/oai-analyzer.py) that downloads METS/MODS files via OAI-PMH and analyzes them
* the results of the analyses are saved locally for further processing in various formats, e.g. Excel, CSV, or sqlite


