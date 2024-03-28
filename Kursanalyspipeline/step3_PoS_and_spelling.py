import sys
import string
import requests
import html
import xml.etree.ElementTree as XML
import json

##############################
### check system arguments ###
##############################
doSpell = 0
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-s":
        doSpell = 1
    elif sys.argv[i] == "-ns":
        doSpell = 0
    else:
        print ("\nReads JSON from stdin, adds part-of-speech tagging, prints JSON to stdout.")
        print ("\nusage options:")
        print ("     -s  do spelling error correction and part-of-speech tagging")
        print ("     -ns no spelling, just tagging\n")
        sys.exit(0)

########################################################
#### Granska stuff (part-of-speech, lemma, spelling ####
########################################################

###########################################################################
# Does part-of-speech tagging.                                          ###
# returns list of lists (one per sentence) of {w:word, t:tag, l:lemma}  ###
###########################################################################
def postag(text):
    if len(text.strip()) > 0:
        url = "https://skrutten.csc.kth.se/granskaapi/wtl.php"
        x = requests.post(url, data = {"coding":"json", "text":text})
        if x.ok:
            try:
                ls = json.loads(x.text)
                res = []
                s = []
                for w in ls:
                    s.append(w)
                    if w["t"] == "mad":
                        res.append(s)
                        s = []
                if len(s) > 0:
                    res.append(s)
                return res
            except:
                print ("WARNING: could not parse JSON:\n\n", x.text, "\n\n")
        else:
            print ("WARNING: could not PoS-tag sentence.")
    return []

###########################################################################
# Does spelling error correction and part-of-speech tagging.            ###
# returns list of lists (one per sentence) of {w:word, t:tag, l:lemma}  ###
###########################################################################
def granska(text): # returns [{word, tag, lemma}, ...] after spelling correction
    if len(text.strip()) > 0:
        url = "https://skrutten.csc.kth.se/granskaapi/scrutinize.php"
        x = requests.post(url, data = {"text":text})
        if x.ok:
            t = html.unescape(x.text).replace("&", "&amp;").replace('"""', '"&quot;"').replace('>"<', '>&quot;<')

            try:
                xml = XML.fromstring(t)
            except:
                print ("WARNING: XML parsing failed:\n\n", t, "\n\n")
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
                return convertTags(xml)
        else:
            print ("WARNING: could not PoS-tag sentence.")
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
                        tag = int(elW.attrib["tag"])
                        if tag < len(tagLex):
                            tmp["t"] = tagLex[tag]
                        else:
                            skip = 1
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
except:
    print("No input data?")
    sys.exit(0)

#################################################################
### For each course, part-of-speech tag the ILO-list-sv field ###
#################################################################
for c in data["Course-list"]:
    ls = c["ILO-list-sv"]

    text = ""
    for s in ls:
        text += "\n"
        text += s
    if doSpell:
        wtl = granska(text)        
    else:
        wtl = postag(text)
    c["ILO-list-sv-tagged"] = wtl

##############################
### Print result to stdout ###
##############################
print(json.dumps(data))
