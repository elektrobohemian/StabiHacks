# What is a PPN and Why is it Helpful?

Most of the systems of the Berlin State Library are built around an identifier, the so-called [PPN 
(PICA production number)](https://lhclz.gbv.de/hermes/gbvhelp/en/en-12.html). This ID is central to most processes
of the library as it is basically used as a unique ID for all sorts of metadata records and thus media.
 For instance, if you know a PPN of an object, you can order it, or, in case of digitized media, inspect it with different viewers, 
 download its fulltext, or simply download its metadata in METS/MODS format.
 
 In the following examples, we will use the PPN PPN334378124X.
 ## Using PPNs with OAI-PMH
 
 The traditional endpoint in the library world is the [OAI-PMH protocol](https://www.openarchives.org/OAI/openarchivesprotocol.html)
 that can be used to download different metadata.
 The roughest but easiest format to parse is [Dublin Core](http://dublincore.org/). 
 To download the metadata in Dublin Core format for the aforementioned PPN, visit

 https://digital.staatsbibliothek-berlin.de/oai?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai%3Adigital.staatsbibliothek-berlin.de%3APPN334378124X


The more elegant approach to obtain metadata is using the [METS/MODS file format](https://www.loc.gov/standards/mods/presentations/mets-mods-morgan-ala07/).
The main advantage over Dublin Core is that the content of each element has been specified much stricter.
Furthermore, the files also contain links to different manifestations of each digitized object and the OCR full-text (if available).

http://digital.staatsbibliothek-berlin.de/oai/?verb=GetRecord&metadataPrefix=mets&identifier=oai%3Adigital.staatsbibliothek-berlin.de%3APPN334378124X

## Using PPNs with IIIF

The [International Image Interoperability Framework/IIIF](https://iiif.io/) defines different APIs to facilitate
image access. IIIF is built around so-called manifests in JSON format.
For instance, the manifest of the sample PPN can be accessed via https://content.staatsbibliothek-berlin.de/dc/PPN334378124X-00000001/info.json .

The interaction with IIIF is based on URLs, e.g., to download the full-sized image in JPEG format, you can use the following URL:

https://content.staatsbibliothek-berlin.de/dc/PPN334378124X-00000001/full/1200,/0/default.jpg

## Using PPNs to View A File in the Berlin State Library Image Viewer

If you want to inspect a medium with the Berlin State Library image view, you can simoly visit:

http://digital.staatsbibliothek-berlin.de/werkansicht/?PPN=PPN334378124X

## Using PPNs with the OPAC (stabikat)

If you want to obtain the PPN in our main catalog, see http://stabikat.de/DB=1/PPN?PPN=334378124X . 
If the PPN refers to an "analog" medium, you could start the loaning process from here.
Please note that you __must not use the PPN prefix__ in these URLs.

