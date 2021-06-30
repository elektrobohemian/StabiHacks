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

import sys
import os
from datetime import datetime
import jsonpickle
import sqlite3
import csv
import re
from bokeh.io import output_file, show
from bokeh.plotting import figure, from_networkx
from bokeh.models import MultiLine, Circle
from bokeh.models.graphs import NodesAndLinkedEdges, EdgesAndLinkedNodes
from bokeh.models.tools import HoverTool
from bokeh.palettes import Spectral4
import networkx as nx

# enables verbose output during processing
verbose = True
# path to the sbbget temporary result files, e.g. "../sbbget/sbbget_downloads/download_temp" (the base path under which ALTO files are stored)
sbbGetBasePath="../sbbget/sbbget_downloads/download_temp/"
# path of the analysis results
analysisPath="./analysis/"
# path to the stopword list
stopwordFile="./stopwords_ger.txt"

def printLog(text):
    now = str(datetime.now())
    print("[" + now + "]\t" + text)
    # forces to output the result of the print command immediately, see: http://stackoverflow.com/questions/230751/how-to-flush-output-of-python-print
    sys.stdout.flush()

def createSupplementaryDirectories():
    if not os.path.exists(analysisPath):
        if verbose:
            print("Creating " + analysisPath)
        os.mkdir(analysisPath)

def setupDatabase(conn,cursor):
    cursor.execute('''DROP TABLE IF EXISTS media;''')
    cursor.execute('''CREATE TABLE media (ppn TEXT PRIMARY KEY, path TEXT NOT NULL, title_img TEXT);''')

    cursor.execute('''DROP TABLE IF EXISTS words;''')
    cursor.execute('''CREATE TABLE words (word_str TEXT);''')

    cursor.execute('''DROP TABLE IF EXISTS pages;''')
    cursor.execute('''CREATE TABLE pages (number INTEGER, path TEXT NOT NULL, rel_ppn TEXT NOT NULL, FOREIGN KEY (rel_ppn) REFERENCES media(ppn));''')

    cursor.execute('''DROP TABLE IF EXISTS word_pages;''')
    cursor.execute('''CREATE TABLE word_pages (rel_word TEXT, rel_number INTEGER, rel_ppn TEXT NOT NULL, FOREIGN KEY (rel_ppn) REFERENCES media(ppn), FOREIGN KEY (rel_word) REFERENCES words(word_str),FOREIGN KEY (rel_number) REFERENCES pages(number));''')
    conn.commit()


if __name__ == "__main__":

    createSupplementaryDirectories()

    startTime = str(datetime.now())

    printLog("SQlite database will be stored at: "+analysisPath+'ner_analysis.db')
    db_connection = sqlite3.connect(analysisPath+'ner_analysis.db')
    db_cur = db_connection.cursor()

    setupDatabase(db_connection,db_cur)

    nerFilePaths = dict()
    statsFilePaths= dict()
    dirsPerPPN = dict()
    ppnDirs=[]
    # check all subdirectories startings with PPN as each PPN stands for a different medium
        
    for x in os.listdir(sbbGetBasePath):
        if x.startswith("PPN"):
            dirsPerPPN[x]=[]
            ppnDirs.append(x)

    # browse all directories below sbbGetBasePath and search for *_FULLTEXT directories
    # and associate each with its PPN
    for ppn in ppnDirs:
        for dirpath, dirnames, files in os.walk(sbbGetBasePath+ppn):
            for name in files:
                if dirpath.endswith("_FULLTEXT"):
                    # if we found a fulltext directory, only add JSON and stats files created by fulltext_analysis.py
                    if name.endswith(".json") or name.endswith(".JSON"):
                        if not ppn in nerFilePaths:
                            nerFilePaths[ppn]=[]
                        nerFilePaths[ppn].append(os.path.join(dirpath, name))
                        dirsPerPPN[ppn].append(os.path.join(dirpath, name))
                    elif name.endswith("_stats.txt") or name.endswith("_stats.TXT"):
                        if not ppn in statsFilePaths:
                            statsFilePaths[ppn]=[]
                        statsFilePaths[ppn].append(os.path.join(dirpath, name))

    totalFiles=0
    for ppn in nerFilePaths:
        totalFiles+=len(nerFilePaths[ppn])
    totalStatsFiles=0
    for ppn in statsFilePaths:
        totalStatsFiles+=len(statsFilePaths[ppn])
    printLog("Found %i JSON and %i stats files for further processing."%(totalFiles,totalStatsFiles))
    

    stopwords=open(stopwordFile, 'r').read()
    wordFrequencies=dict()
    cleanWordFrequencies=dict()
    wordsInPPN=dict()

    # regular expression for page number detection
    page_pattern=re.compile("FILE_\d\d\d\d")
    # only consider words with the following characteristics for the cleaned CSV and the DB:
    # min. 3 characters
    # a minimum frequency of 2
    # not starting with numbers
    # starting with Unicode word characters
    # does not start with punctuations
    punctuations = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''
    pattern = re.compile("^(\D\w)")
    pattern2=re.compile("^[\!\(\)\-\[\]\{\};:\'\,\.\/\=—•■✓€]")

    wordsInDatabase=0

    for ppn in statsFilePaths:
        # add the PPN to the database, only add title page if it is available, otherwise it will be set to NULL
        title_img=sbbGetBasePath+ppn+"/"+"_TITLE_PAGE.jpg"
        if not os.path.exists(title_img):
            title_img=None
        db_cur.execute("INSERT INTO media VALUES(:ppn,:path,:title_img);",{"ppn":ppn,"path":sbbGetBasePath+ppn,"title_img":title_img})
        db_connection.commit()

        for currentFile in statsFilePaths[ppn]:
            page_match=page_pattern.search(currentFile)
            currentPage=-1
            if page_match:
                # we are only interested in the number part, thus the +5 (skip FILE_)
                currentPage=int(currentFile[page_match.start()+5:page_match.end()])

            with open(currentFile) as csvfile:
                csv_reader = csv.reader(csvfile, delimiter='\t')
                for row in csv_reader:
                    # only add words that are no stopwords
                    word=row[0]
                    freq=int(row[1])
                    if not word.lower() in stopwords:
                        if not word in wordFrequencies:
                            wordFrequencies[word]=freq
                            # update database accordingly
                            if not pattern2.match(word) and len(word)>2:
                                if pattern.match(word):
                                    cleanWordFrequencies[word]=freq
                                    db_cur.execute("INSERT INTO words VALUES(:new_word);",{"new_word":word})
                                    wordsInDatabase+=1
                                    head_tail = os.path.split(currentFile)
                                    thumbnailPath=head_tail[0].replace("FULLTEXT","TIFF")+"/"+ppn+".jpg"

                                    db_cur.execute("INSERT INTO pages VALUES(:pg_number,:path,:rel_ppn);",{"pg_number":currentPage,"rel_ppn":ppn,"path":thumbnailPath})
                                    db_cur.execute("INSERT INTO word_pages VALUES(:rel_word,:rel_number,:rel_ppn);",{"rel_word":word,"rel_number":currentPage,"rel_ppn":ppn})
                        else:
                            wordFrequencies[word]+=freq
                            
                            # update the DB
                            if not pattern2.match(word) and len(word)>2:
                                if pattern.match(word):
                                    cleanWordFrequencies[word]+=freq
                                    head_tail = os.path.split(currentFile)
                                    thumbnailPath=head_tail[0].replace("FULLTEXT","TIFF")+"/"+ppn+".jpg"
                                    
                                    db_cur.execute("INSERT INTO pages VALUES(:pg_number,:path,:rel_ppn);",{"pg_number":currentPage,"rel_ppn":ppn,"path":thumbnailPath})
                                    db_cur.execute("INSERT INTO word_pages VALUES(:rel_word,:rel_number,:rel_ppn);",{"rel_word":word,"rel_number":currentPage,"rel_ppn":ppn})  

                        if not word in wordsInPPN:
                            wordsInPPN[word]=[]
                        if not ppn in wordsInPPN[word]:
                            wordsInPPN[word].append(ppn)   
                        db_connection.commit()
    
    printLog("Found %i distinct raw words (of which %i are cleaned in database)."%(len(wordFrequencies.keys()),wordsInDatabase))

    with open(analysisPath+'wordFrequencies.csv', 'w') as csvfile:
        csv_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["WORD","FREQUENCY","PPNs"])
        for word, freq in sorted(wordFrequencies.items()):
            csv_writer.writerow([word,freq,";".join(wordsInPPN[word])])

    
    with open(analysisPath+'wordFrequencies_CLEAN.csv', 'w') as csvfile:
        csv_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["WORD","FREQUENCY","PPNs"])
        for word, freq in sorted(cleanWordFrequencies.items()):
            if not pattern2.match(word) and len(word)>2 and freq>1:
                if pattern.match(word):
                    csv_writer.writerow([word,freq,";".join(wordsInPPN[word])])
    #print(wordsInPPN)



    # filePath="/Users/david/src/python/StabiHacks/sbbget/sbbget_downloads.div_spielebuecher/download_temp/PPN745143385/FILE_0005_FULLTEXT/00000005_ner_details.json"


    # jsonStr = open(filePath, 'r').read()
    # thawed = jsonpickle.decode(jsonStr)

    # print(thawed)
    # print(thawed.keys())

    # print("\nEntities:")

    # for ent in thawed["entities"]:
    #     print(ent)

    # create a graph of the following form
    #               /- page 1
    #       |-PPN 1----- ...
    # word -|       \- page n
    #       |
    #       |-PPN 2--- ...
    #
    printLog("Creating word-page graph...")
    word_ppn_pages=dict()

    query1='''SELECT * from words ORDER BY word_str;'''
    
    availableWords=[]
    # get all available words
    #for row in db_cur.execute(query1):
    #    availableWords.append(row[0])
    
    # limit the analysis to the top-100 most frequent words
    sorted_keys = sorted(cleanWordFrequencies, key=cleanWordFrequencies.get, reverse=True)
    availableWords=sorted_keys[:100]

    cnt_words=len(availableWords)
    for i,word in enumerate(availableWords):
        word_ppn_pages[word]=dict()
        if verbose:
            print("\t%s (%i of %i)"%(word,i,cnt_words))
        for row in db_cur.execute("SELECT DISTINCT wp.rel_word,wp.rel_number,wp.rel_ppn,p.path FROM word_pages wp INNER JOIN pages p ON rel_number=p.\"number\" AND wp.rel_ppn=p.rel_ppn WHERE rel_word LIKE :new_word;",{"new_word":word}):
            # word - page - ppn - thumbnail path
            # ('Alma', 22, 'PPN745158323', '../sbbget/sbbget_downloads.div_spielebuecher/download_temp/PPN745158323/FILE_0022_TIFF/PPN745158323.jpg')
            page=row[1]
            ppn=row[2]
            path=row[3]
            if ppn not in word_ppn_pages[word]:
                word_ppn_pages[word][ppn]=[]
            word_ppn_pages[word][ppn].append((page,path))
        # debug
        if i>500:
            break
    

    class Thing(object):
        def __init__(self, name, children):
            self.name = name
            self.children=children
    class Leaf(object):
        def __init__(self, name, value):
            self.name=name
            self.value=value

    G = nx.Graph()
    obj=Thing("test",[])
    mainNode="main"
    #G.add_node(mainNode)
    for word in word_ppn_pages:
        word_obj=Thing(word,[])
        G.add_node(word)
        G.nodes[word]['name'] = word
        G.nodes[word]['alpha'] = 1.0
        G.nodes[word]['size'] = 10
        #G.add_edge(mainNode,word)
        for ppn in word_ppn_pages[word]:
            ppnThing=Thing(ppn,[])
            G.add_node(ppn)
            G.nodes[ppn]['name']=ppn
            G.nodes[ppn]['alpha'] = 0.6
            G.nodes[ppn]['size'] = 8
            G.add_edge(word,ppn)
            for page, path in word_ppn_pages[word][ppn]:
                pageThing=Leaf(path,page)
                ppnThing.children.append(pageThing)
                G.add_node(str(page))
                G.add_edge(ppn,str(page))
                G.nodes[str(page)]['name']=str(page)
                G.nodes[str(page)]['alpha'] = 0.2
                G.nodes[str(page)]['size'] = 5
            word_obj.children.append(ppnThing)
        obj.children.append(word_obj)
    
    # degree-based scaling as seen at https://melaniewalsh.github.io/Intro-Cultural-Analytics/Network-Analysis/Making-Network-Viz-with-Bokeh.html
    # degrees = dict(nx.degree(G))
    # nx.set_node_attributes(G, name='degree', values=degrees)
    # number_to_adjust_by = 5
    # adjusted_node_size = dict([(node, degree+number_to_adjust_by) for node, degree in nx.degree(G)])
    # nx.set_node_attributes(G, name='adjusted_node_size', values=adjusted_node_size)

    plot = figure(title="Graph visualization", toolbar_location="below")
    node_hover_tool = HoverTool(tooltips=[("index", "@index"), ("name", "@name")])
    plot.add_tools(node_hover_tool)
    graph_renderer = from_networkx(G, nx.spring_layout, scale=4, center=(0,0))
    
    graph_renderer.node_renderer.glyph = Circle(size="size", fill_color=Spectral4[0],fill_alpha="alpha")
    graph_renderer.node_renderer.hover_glyph = Circle(size=15, fill_color=Spectral4[1])

    graph_renderer.edge_renderer.glyph = MultiLine( line_alpha=0.8, line_width=1)
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color=Spectral4[1], line_width=5)

    plot.renderers.append(graph_renderer)


    output_file(analysisPath+"networkx_graph.html")
    show(plot)
    
    jsonExport=open(analysisPath+"test.json","w")
    jsonExport.write(jsonpickle.encode(obj, unpicklable=False))
    jsonExport.close()
    printLog("\nDone.")

    db_connection.close()

    endTime = str(datetime.now())
    print("\nStarted at:\t%s\nEnded at:\t%s" % (startTime, endTime))
    printLog("Done.")
