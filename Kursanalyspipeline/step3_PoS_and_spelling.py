import sys
import string
import requests
import html
import xml.etree.ElementTree as XML
import json
import time
import socket

from timeit import default_timer as timer

##############################
### check system arguments ###
##############################
doSpell = 0
logging = 0
useCache = 0
tagAllTogether = 1
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-s":
        doSpell = 1
    elif sys.argv[i] == "-ns":
        doSpell = 0
    elif sys.argv[i] == "-log":
        logging = 1
    elif sys.argv[i] == "-cache":
        useCache = 1
    elif sys.argv[i] == "-sendAll":
        tagAllTogether = 1
    elif sys.argv[i] == "-sendEach":
        tagAllTogether = 0
    else:
        print ("\nReads JSON from stdin, adds part-of-speech tagging, prints JSON to stdout.")
        print ("\nusage options:")
        print ("     -s          do spelling error correction and part-of-speech tagging")
        print ("     -ns         no spelling, just tagging")
        print ("     -log        log debug data to " + sys.argv[0] + ".log")
        print ("     -sendAll    PoS-tag all goal texts at once (one call to Granska)")
        print ("     -sendEach   PoS-tag each goal separately (many calls to Granska)")
        print ("     -cache      use a local cache of sentences already tagged\n")
        sys.exit(0)


#################
#### Logging ####
#################
logF = ""
if logging:
    logF = open(sys.argv[0] + ".log", "w")

def log(s):
    if logging:
        logF.write(s)
        logF.write("\n")
        logF.flush()

###############
#### Cache ####
###############
cache = {}
newReqsNotInFile = 0
totNew=0
totHits=0
WHEN_TO_WRITE=500
if useCache:
    log("load cached data")
    cacheFile = sys.argv[0] + ".cache"

    cache = {}
    try:
        f = open(cacheFile)
        cache = json.load(f)
        f.close()
    except:
        cache = {}

    log(str(len(cache.keys())) + " cached items found.")

########################################################
#### Granska stuff (part-of-speech, lemma, spelling ####
########################################################

###########################################################################
# Does part-of-speech tagging.                                          ###
# returns list of lists (one per sentence) of {w:word, t:tag, l:lemma}  ###
###########################################################################
def posParseAndSpell(text, doSpellCheck):

    if text in cache:
        global totHits
        totHits += 1
        return cache[text]

    if len(text.strip()) > 0:
        toSend  = ("TEXT " + text.replace("\n", " ").strip() + "\nENDQ\n").encode("latin-1", "ignore")
        commOK = 0
        tries = 0
        
        while tries < 5 and not commOK:
            reply = ""
            try:
                usock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                usock.settimeout(60 * 2) # if there is no reply in 2 minutes, give up and try again
                usock.connect(("skrutten.csc.kth.se", 6123))

                usock.send(toSend) # There is a length restriction on this service, but we should always be fine with our relatively short texts.

                first = 1
                haveAll = 0
                while not haveAll:
                    if first:
                        first = 0
                        reply = usock.recv(1024*1024)
                    else:
                        reply += usock.recv(1024*1024)

                    try:
                        tmp = reply.decode("latin-1")
                        if tmp.find("/Root>") >= 0:
                            haveAll = 1
                    except:
                        haveAll = 0
                usock.close()
                commOK = 1

            except Exception as e:
                log("Exception when using Granska: " + str(e))
                tries += 1
                time.sleep(15) # wait 15 seconds and see if the server is back again

        if commOK:
            
            try:
                t = reply.decode("latin-1")
                p = t.find("<Root>")
                t = t[p:]
                xml = XML.fromstring(t)
            except Exception as e:
                log ("WARNING: XML parsing failed:\n\n" + str(e) + "\n\n" + t + "\n\n" + text + "\n\n")
                writeCache()
                if t.lower().find("granska error"):
                    time.sleep(5*60) # sleep 5 minutes and wait for the Granska server to come back
                return []

            if doSpellCheck:
                return spellCheckAndTag(xml)
            else:
                return tagsFromXML(xml)
def spellCheckAndTag(xml):
    # Find all sentences
    sentences = []
    for elS in xml.iter("s"):
        if elS and elS.tag == "s" and elS.attrib:
            sentId = elS.attrib["ref"]
            sent = []
            for elW in elS.iter('w'):
                sent.append(elW.text)
            if len(sent) > 0:
                sentences.append([sentId, sent])

    # find all error reports, save the ones that are spelling errors with corrections
    spellingSuggs = []
    for elScrut in xml.iter('scrutinizer'):
        for elS in elScrut.iter('s'):
            sentId = elS.attrib["ref"]

            for elErr in elS.iter('gramerror'):
                isSpelling = 0
                for field in elErr:
                    if field.tag == "rule" and field.text == "stav1@stavning":
                        isSpelling = 1
                        break
                suggs = []
                if isSpelling:                        
                    for sugg in elErr.iter('sugg'):
                        suggs.append("".join(sugg.itertext()))
                markFrom = -1
                markTo = -1
                if len(suggs):
                    for mark in elErr.iter('mark'):
                        attribs = mark.attrib
                        if "begin" in attribs:
                            markFrom = int(attribs["begin"])
                        if "end" in attribs:
                            markTo = int(attribs["end"])
                if markTo >= 0 and markTo == markFrom:
                    spellingSuggs.append([sentId, markTo, suggs])

    # apply corrections
    atLeastOneChange = 0
    for sugg in spellingSuggs:
        sId = sugg[0]
        for s in range(len(sentences)):
            if sentences[s][0] == sId:
                markTo = sugg[1]
                replacement = sugg[2][0]
                sentences[s][1][markTo - 2] = replacement
                atLeastOneChange = 1
                break

    # if something changed, run Granska on the corrected text
    if atLeastOneChange:
        newText = ""
        for s in sentences:
            sent = " ".join(s[1])
            newText += sent
            newText += "\n"
        return posParseAndSpell(newText, False)
    else:
        return tagsFromXML(xml)

def tagsFromXML(xml):
    res = convertTags(xml)

    if res:
        cache[text] = res
        if useCache:
            global newReqsNotInFile
            newReqsNotInFile += 1
    
            if newReqsNotInFile > WHEN_TO_WRITE:
                writeCache()
    return res



def postag(text):
    if text in cache:
        global totHits
        totHits += 1
        return cache[text]
    
    if len(text.strip()) > 0:
        url = "https://skrutten.csc.kth.se/granskaapi/wtl.php"
        tries = 0
        while tries < 5:
            try:
                x = requests.post(url, data = {"coding":"json", "text":text})
                break
            except Exception as e:
                log("Exception when using Granska: " + str(e))
                tries += 1
                time.sleep(15) # wait 15 seconds and see if the server is back again
                
        if tries < 5 and x.ok:
            try:
                ls = json.loads(str(x.text))
                res = []
                s = []
                for w in ls:
                    s.append(w)
                    if w["t"] == "mad":
                        res.append(s)
                        s = []
                if len(s) > 0:
                    res.append(s)

                cache[text] = res
                if useCache:
                    global newReqsNotInFile
                    newReqsNotInFile += 1

                    if newReqsNotInFile > WHEN_TO_WRITE:
                        writeCache()
                return res
            except Exception as e:
                log ("WARNING: could not parse JSON:\n\n" + str(e) + "\n\n" + x.text + "\n\n" + text + "\n\n")
                writeCache()
                if x.text.lower().find("granska error"):
                    time.sleep(5*60) # sleep 5 minutes and wait for the Granska server to come back
        else:
            log ("WARNING: could not PoS-tag sentence.")
    return []

def writeCache():
    if not useCache:
        return
    
    global totNew
    global newReqsNotInFile
    f = open(cacheFile, "w")
    f.write(json.dumps(cache))
    f.close()
    totNew += newReqsNotInFile
    newReqsNotInFile = 0
    log("new cached items: " + str(totNew))
    
###########################################################################
# Does spelling error correction and part-of-speech tagging.            ###
# returns list of lists (one per sentence) of {w:word, t:tag, l:lemma}  ###
###########################################################################
def granska(text): # returns [{word, tag, lemma}, ...] after spelling correction
    if text in cache:
        global totHits
        totHits += 1
        return cache[text]
    
    if len(text.strip()) > 0:
        url = "https://skrutten.csc.kth.se/granskaapi/scrutinize.php"
        tries = 0
        while tries < 5:
            try:
                x = requests.post(url, data = {"text":text})
                break
            except Exception as e:
                log("Exception when using Granska: " + str(e))
                tries += 1
                time.sleep(15) # wait 15 seconds and see if the server is back again
                
        if tries < 5 and x.ok:
            t = html.unescape(x.text).replace("&", "&amp;").replace('"""', '"&quot;"').replace('>"<', '>&quot;<')

            try:
                xml = XML.fromstring(t)
            except Exception as e:
                log ("WARNING: XML parsing failed:\n\n" + str(e) + "\n\n" + t + "\n\n" + text + "\n\n")
                writeCache()
                if t.lower().find("granska error"):
                    time.sleep(5*60) # sleep 5 minutes and wait for the Granska server to come back
                return postag(text)
            
            # Find all sentences
            sentences = []
            for elS in xml.iter("s"):
                if elS and elS.tag == "s" and elS.attrib:
                    sentId = elS.attrib["ref"]
                    sent = []
                    for elW in elS.iter('w'):
                        sent.append(elW.text)
                    if len(sent) > 0:
                        sentences.append([sentId, sent])

            # find all error reports, save the ones that are spelling errors with corrections
            spellingSuggs = []
            for elScrut in xml.iter('scrutinizer'):
                for elS in elScrut.iter('s'):
                    sentId = elS.attrib["ref"]

                    for elErr in elS.iter('gramerror'):
                        isSpelling = 0
                        for field in elErr:
                            if field.tag == "rule" and field.text == "stav1@stavning":
                                isSpelling = 1
                                break
                        suggs = []
                        if isSpelling:                        
                            for sugg in elErr.iter('sugg'):
                                suggs.append("".join(sugg.itertext()))
                        markFrom = -1
                        markTo = -1
                        if len(suggs):
                            for mark in elErr.iter('mark'):
                                attribs = mark.attrib
                                if "begin" in attribs:
                                    markFrom = int(attribs["begin"])
                                if "end" in attribs:
                                    markTo = int(attribs["end"])
                        if markTo >= 0 and markTo == markFrom:
                            spellingSuggs.append([sentId, markTo, suggs])

            # apply corrections
            atLeastOneChange = 0
            for sugg in spellingSuggs:
                sId = sugg[0]
                for s in range(len(sentences)):
                    if sentences[s][0] == sId:
                        markTo = sugg[1]
                        replacement = sugg[2][0]
                        sentences[s][1][markTo - 2] = replacement
                        atLeastOneChange = 1
                        break

            # if something changed, run Granska on the corrected text
            if atLeastOneChange:
                newText = ""
                for s in sentences:
                    sent = " ".join(s[1])
                    newText += sent
                    newText += "\n"
                return postag(newText)
            else:
                # if nothing changed, return word-tag-lemma info
                res = convertTags(xml)

                cache[text] = res
                if useCache:
                    global newReqsNotInFile
                    newReqsNotInFile += 1

                    if newReqsNotInFile > WHEN_TO_WRITE:
                        writeCache()
                return res
        else:
            log ("WARNING: could not PoS-tag sentence.")
            return []
    return []
################################################################################################################
### When asking for spelling correction, tags come only as numbers. This list shows the tag for each number. ###
################################################################################################################
tagLex = ["nn.neu.sin.def.nom", "nn.utr", "hd.utr/neu.plu.ind", "jj.pos.sms", "dt.utr/neu.plu.def", "hs.def", "jj.kom.utr/neu.sin/plu.ind/def.nom", "jj.pos.utr/neu.plu.ind/def.nom", "dt.utr.sin.ind/def", "dt.utr/neu.sin.def", "nn.neu.plu.ind.gen", "nn", "nn.utr.plu.def.nom", "jj.pos.neu.sin.ind/def.nom", "nn.utr.sin.def.nom.dat", "vb.imp.akt.aux", "ps.utr.sin.def", "jj.pos.utr/neu.plu.ind.nom", "dt.utr/neu.plu.ind/def", "nn.utr.sin.ind.nom.dat", "hd.neu.sin.ind", "vb.prt.sfo.kop", "sen.que", "dt.utr/neu.plu.ind", "nn.neu", "pn.neu.sin.ind.sub/obj", "pn.utr/neu.plu.def.sub/obj", "hp", "ps.utr/neu.sin/plu.def", "pn.utr/neu.plu.def.obj", "vb.prt.akt.aux", "nn.utr.sin.ind.nom", "ro", "nn.utr.plu.def.gen", "nn.neu.plu.ind.nom", "nn.neu.sin.def.gen", "nn.sms", "jj.suv.mas.sin.def.nom", "jj.suv.utr/neu.sin/plu.def.nom", "vb.prs.sfo", "pm.nom", "sen.hea", "nn.utr.sin.def.nom.set", "sn", "ab.kom", "pad", "dt.utr/neu.sin.ind", "vb.imp", "pn.utr.sin.def.sub/obj", "pn.utr.sin.def.obj", "rg.utr/neu.plu.ind/def.nom", "jj.pos.utr/neu.sin.def.nom", "sen.exc", "rg.utr.sin.ind.nom", "vb.prs.akt", "pm.gen", "dt.utr.sin.ind", "dt.utr/neu.sin/plu.ind", "nn.utr.sms", "vb.inf.akt.aux", "pn.utr.sin.def.sub", "kn", "vb.prs.sfo.kop", "vb.prs.akt.mod", "vb.inf.akt.mod", "pc.gen", "ro.nom", "jj.pos.neu.sin.ind.nom", "nn.utr.plu.ind.nom", "pn.utr.sin.ind.sub", "jj.suv.utr/neu.plu.def.nom", "dt.neu.sin.def", "rg.sin", "ro.sin", "vb.imp.akt.kop", "hd.utr.sin.ind", "nn.neu.sin.def.nom.set", "vb.kon.prs.akt", "ab.suv", "vb.inf.akt", "jj.pos.utr.sin.ind.nom", "nn.neu.plu.def.gen", "vb.imp.akt.mod", "vb.prt.akt.mod", "dt.neu.sin.ind", "pn.utr/neu.plu.ind.sub/obj", "pn.neu.sin.def.sub/obj", "vb.inf.akt.kop", "rg.neu.sin.ind.nom", "pn.mas.sin.def.sub/obj", "ro.gen", "nn.neu.plu.def.nom", "dt.mas.sin.ind/def", "dt.neu.sin.ind/def", "vb.inf.sfo", "jj.suv.utr/neu.sin/plu.ind.nom", "rg.gen", "hp.neu.sin.ind", "vb.kon.prt", "sen.per", "ps.utr/neu.plu.def", "nn.utr.sin.ind.nom.set", "nn.utr.sin.def.nom", "pn.utr.plu.def.sub", "nn.neu.sin.ind.gen", "ps.neu.sin.def", "pn.utr.plu.def.obj", "jj.pos.utr.sin.ind/def.nom", "vb.prt.sfo", "mad", "ab", "pn.utr/neu.sin/plu.def.obj", "vb.sup.akt", "mid", "vb.sup.akt.kop", "jj.pos.mas.sin.def.nom", "hp.utr/neu.plu.ind", "vb.sup.akt.mod", "jj.kom.sms", "nn.utr.sin.def.gen", "rg.nom", "nn.neu.sin.ind.nom", "rg.yea", "pl", "in", "vb.prt.akt", "nn.neu.sms", "vb.sup.sfo", "nn.utr.plu.ind.gen", "pn.utr.sin.ind.sub/obj", "dt.utr.sin.def", "nn.neu.sin.ind.nom.set", "vb", "pp", "vb.prs.akt.kop", "nn.utr.sin.ind.gen", "jj.gen", "vb.prt.akt.kop", "ie", "ro.mas.sin.ind/def.nom", "jj.pos.utr/neu.sin/plu.ind/def.nom", "hp.utr.sin.ind", "pc.prs.utr/neu.sin/plu.ind/def.nom", "sen.non", "pn.utr/neu.plu.def.sub", "ha", "vb.prs.akt.aux", "ab.pos", "pm.sms"]

###########################################################################
### Convert granska numerical indexes of part-of-speech tags to strings ###
###########################################################################
def convertTags(granskaXML):
    sentences = []
    for elS in granskaXML.iter("s"):
        if elS and elS.tag == "s" and elS.attrib:
            sent = []
            for elW in elS.iter('w'):
                tmp = {}
                skip = 0
                tmp["w"] = elW.text
                if len(elW.text) < 1:
                    skip = 1
                    
                if elW.attrib:
                    if "tag" in elW.attrib:
                        tagtmp = elW.attrib["tag"]
                        if len(tagtmp) and tagtmp[0].isdigit():
                            tag = int(tagtmp)
                            if tag < len(tagLex):
                                tmp["t"] = tagLex[tag]
                            else:
                                skip = 1
                        else:
                            tmp["t"] = tagtmp
                    else:
                        skip = 1
                        
                    if "lemma" in elW.attrib:
                        tmp["l"] = elW.attrib["lemma"]
                    else:
                        skip = 1
                if not skip:
                    sent.append(tmp)
                
            if len(sent) > 0:
                sentences.append(sent)
    return sentences

############################
### read JSON from stdin ###
############################
data = {}

text = ""
for line in sys.stdin:
    text += line

try:
    data = json.loads(text)
except Exception as e:
    print("No input data or non-JSON data?")
    print(str(e))
    sys.exit(0)

#################################################################
### For each course, part-of-speech tag the ILO-list-sv field ###
#################################################################
cs = len(data["Course-list"])
for idx in range(cs):
#for c in data["Course-list"]:
    c = data["Course-list"][idx]
    ls = c["ILO-list-sv"]

    if tagAllTogether:
        text = ""
        for s in ls:
            text += "\n"
            text += s
        
        if doSpell:
            wtl = posParseAndSpell(text, True)
            # wtl = granska(text)        
        else:
            wtl = posParseAndSpell(text, False)
            # wtl = postag(s)
    else:
        res = []
        for s in ls:
            text = s
            if doSpell:
                wtl = posParseAndSpell(text, True)
            else:
                wtl = posParseAndSpell(text, False)
            res += wtl
        wtl = res
    c["ILO-list-sv-tagged"] = wtl

    if idx % 100 == 0:
        log("Courses: " + str(idx) + " of " + str(cs) + " done, " + str(totNew + newReqsNotInFile) + " non-cache items.")

##############################
### Print result to stdout ###
##############################
if useCache:
    if newReqsNotInFile > 0:
        writeCache()

log("Cache hits: " + str(totHits))
log("New entries in cache file: " + str(totNew))

print(json.dumps(data))
