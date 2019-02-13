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
* a [Python script](oai-analyzer/oai-analyzer.py) that downloads METS/MODS files via OAI-PMH and analyzes them
* the results of the analyses are saved locally for further processing in various formats, e.g. Excel, CSV, or sqlite

## Fulltext Statistics
* a [Python script](fulltext-tools/fulltext_statistics.py) that retrieves all fulltexts from a SBBget created download directory and converts all files to raw text files
* alternatively the script can operate on the result file created by OAI-Analyzer and download ALTO files directly, from this perspective it serves as a Stabi fulltext corpus builder
* the script is based on [NLTK](http://www.nltk.org) which needs additional installation steps, i.e.:
    * install NLTK in your Python environment
    * when running the script, Python will ask you to install additional NLTK packages, the easiest way is to open a Python interpreter
    and run to launch NLTK's graphical installer:
    ```
    import nltk
    nltk.download()
    ```
    * further information can be found an [online book](http://www.nltk.org/book) that also gives an introduction into natural language processing

## Pica Plus

* a [Python script](pica_plus/processPicaPlus.py) that parses files in the Pica+ format as provided by the [GBV](https://www.gbv.de)
* the script lets you choose interesting fields (as stored in the _fieldsOfInterest_ list) and will output the contained data
* records will be separated by a *NEW_RECORD* string


* documentation of the Pica Plus format is only available in German here:
    * [general overview](https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/inhalt.shtml)
    * [list of fields](https://www.gbv.de/bibliotheken/verbundbibliotheken/02Verbund/01Erschliessung/02Richtlinien/01KatRicht/pica3.pdf)

