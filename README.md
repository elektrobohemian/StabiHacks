# StabiHacks

Various utilities to deal with metadata and content provided by the Berlin State Library/Staatsbibliothek zu Berlin

## SBBget
* a [Python script](sbbget.py) that is capable of downloading digitized media, the associated metadata, and its fulltext. 
* it also extracts images that have been detected by the OCR.
* its logic is based on the more or less unique PPN identifier used at the library.
* two PPN lists are shipped for demonstration purposes. more can be obtained at the Berlin State Library or the creator of the script.
* the script will created various folder below its working directory, e.g.,
    * downloads (fulltexts, original digitizations etc.) are stored at: sbbget_downloads/download_temp/<PPN>
    * extracted images are stored at: sbbget_downloads/extracted_images/<PPN>
    * METS/MODS files are stored at: sbbget_downloads/download_temp/<PPN>/__metsmods/



