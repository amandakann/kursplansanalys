import sys
import string
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
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-log":
        logging = 1
    # elif sys.argv[i] == "-ns":
    #     doSpell = 0
    # elif sys.argv[i] == "-s":
    #     doSpell = 1
    else:
        print ("\nReads JSON from stdin, adds part-of-speech tagging, prints JSON to stdout.")
        print ("\nusage options:")
        # print ("     -s          do spelling error correction and part-of-speech tagging")
        # print ("     -ns         no spelling, just tagging")
        print ("     -log        log debug data to " + sys.argv[0] + ".log\n")
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

################################################################################################################
### When asking for spelling correction, tags come only as numbers. This list shows the tag for each number. ###
################################################################################################################
# tagLex = ["nn.neu.sin.def.nom", "nn.utr", "hd.utr/neu.plu.ind", "jj.pos.sms", "dt.utr/neu.plu.def", "hs.def", "jj.kom.utr/neu.sin/plu.ind/def.nom", "jj.pos.utr/neu.plu.ind/def.nom", "dt.utr.sin.ind/def", "dt.utr/neu.sin.def", "nn.neu.plu.ind.gen", "nn", "nn.utr.plu.def.nom", "jj.pos.neu.sin.ind/def.nom", "nn.utr.sin.def.nom.dat", "vb.imp.akt.aux", "ps.utr.sin.def", "jj.pos.utr/neu.plu.ind.nom", "dt.utr/neu.plu.ind/def", "nn.utr.sin.ind.nom.dat", "hd.neu.sin.ind", "vb.prt.sfo.kop", "sen.que", "dt.utr/neu.plu.ind", "nn.neu", "pn.neu.sin.ind.sub/obj", "pn.utr/neu.plu.def.sub/obj", "hp", "ps.utr/neu.sin/plu.def", "pn.utr/neu.plu.def.obj", "vb.prt.akt.aux", "nn.utr.sin.ind.nom", "ro", "nn.utr.plu.def.gen", "nn.neu.plu.ind.nom", "nn.neu.sin.def.gen", "nn.sms", "jj.suv.mas.sin.def.nom", "jj.suv.utr/neu.sin/plu.def.nom", "vb.prs.sfo", "pm.nom", "sen.hea", "nn.utr.sin.def.nom.set", "sn", "ab.kom", "pad", "dt.utr/neu.sin.ind", "vb.imp", "pn.utr.sin.def.sub/obj", "pn.utr.sin.def.obj", "rg.utr/neu.plu.ind/def.nom", "jj.pos.utr/neu.sin.def.nom", "sen.exc", "rg.utr.sin.ind.nom", "vb.prs.akt", "pm.gen", "dt.utr.sin.ind", "dt.utr/neu.sin/plu.ind", "nn.utr.sms", "vb.inf.akt.aux", "pn.utr.sin.def.sub", "kn", "vb.prs.sfo.kop", "vb.prs.akt.mod", "vb.inf.akt.mod", "pc.gen", "ro.nom", "jj.pos.neu.sin.ind.nom", "nn.utr.plu.ind.nom", "pn.utr.sin.ind.sub", "jj.suv.utr/neu.plu.def.nom", "dt.neu.sin.def", "rg.sin", "ro.sin", "vb.imp.akt.kop", "hd.utr.sin.ind", "nn.neu.sin.def.nom.set", "vb.kon.prs.akt", "ab.suv", "vb.inf.akt", "jj.pos.utr.sin.ind.nom", "nn.neu.plu.def.gen", "vb.imp.akt.mod", "vb.prt.akt.mod", "dt.neu.sin.ind", "pn.utr/neu.plu.ind.sub/obj", "pn.neu.sin.def.sub/obj", "vb.inf.akt.kop", "rg.neu.sin.ind.nom", "pn.mas.sin.def.sub/obj", "ro.gen", "nn.neu.plu.def.nom", "dt.mas.sin.ind/def", "dt.neu.sin.ind/def", "vb.inf.sfo", "jj.suv.utr/neu.sin/plu.ind.nom", "rg.gen", "hp.neu.sin.ind", "vb.kon.prt", "sen.per", "ps.utr/neu.plu.def", "nn.utr.sin.ind.nom.set", "nn.utr.sin.def.nom", "pn.utr.plu.def.sub", "nn.neu.sin.ind.gen", "ps.neu.sin.def", "pn.utr.plu.def.obj", "jj.pos.utr.sin.ind/def.nom", "vb.prt.sfo", "mad", "ab", "pn.utr/neu.sin/plu.def.obj", "vb.sup.akt", "mid", "vb.sup.akt.kop", "jj.pos.mas.sin.def.nom", "hp.utr/neu.plu.ind", "vb.sup.akt.mod", "jj.kom.sms", "nn.utr.sin.def.gen", "rg.nom", "nn.neu.sin.ind.nom", "rg.yea", "pl", "in", "vb.prt.akt", "nn.neu.sms", "vb.sup.sfo", "nn.utr.plu.ind.gen", "pn.utr.sin.ind.sub/obj", "dt.utr.sin.def", "nn.neu.sin.ind.nom.set", "vb", "pp", "vb.prs.akt.kop", "nn.utr.sin.ind.gen", "jj.gen", "vb.prt.akt.kop", "ie", "ro.mas.sin.ind/def.nom", "jj.pos.utr/neu.sin/plu.ind/def.nom", "hp.utr.sin.ind", "pc.prs.utr/neu.sin/plu.ind/def.nom", "sen.non", "pn.utr/neu.plu.def.sub", "ha", "vb.prs.akt.aux", "ab.pos", "pm.sms"]

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


#############################################
### Remove some common errors from step 2 ###
#############################################
gStoplist = open("data/goalStoplist.txt")
errorExamples = []
for line in gStoplist.readlines():
    errorExamples.append(line.strip())
gStoplist.close()
      
errors = []
for e in errorExamples:
    errors.append(e.split())

#######################################
### Remove common erroneous matches ###
#######################################
def removeCommonErrors(ls):
    newLs = []
    for s in ls:
        S = len(s)
        clearedAll = 1
        for e in errors:
            E = len(e)
            if len(e) == S or (E < S and e[-1][-1] == "*"):
                use = 0
                for i in range(E):
                    if e[i][0].isdigit():
                        if s[i]["w"] != e[i] and not s[i]["l"][-1].isdigit():
                            use = 1
                    elif e[i][-1] == "*":
                        if s[i]["w"][:len(e[i]) - 1] == e[i][:-1]:
                            pass
                        else:
                            use = 1
                    else:
                        if s[i]["w"] != e[i] and (not e[i][0].isdigit() or s[i]["l"] != "17"):
                            use = 1
                if not use:
                    clearedAll = 0
                    break
        if clearedAll:
            newLs.append(s)
            
    ls = newLs
    newLs = []
    for s in ls:
        skip = 0
        if s[0]["l"] == "för":
            mom = 0
            vb = 0
            godk = 0
            for i in range(len(s)):
                if s[i]["l"] == "moment" or s[i]["l"] == "del" or s[i]["l"] == "delkurs" or s[i]["l"] == "kursdel":
                    mom = 1
                if s[i]["l"] == "godkänd" or s[i]["l"] == "godkänt":
                    godk = 1
                if s[i]["t"][:2] == "vb" and s[i]["l"] != "ska":
                    vb = 1
            if not vb and (mom or godk):
                skip = 1
        if not skip:
            newLs.append(s)
            
    ls = newLs
    newLs = []
    for s in ls:
        skip = 0
        if s[0]["t"] == "pad" and s[-1]["t"] == "pad":
            skip = 1
            for i in range(1, len(s) - 1):
                if s[i]["t"][:2] == "vb":
                    skip = 0
                    break
        if not skip:
            newLs.append(s)

    ls = newLs
    newLs = []
    for s in ls:
        tag = s[0]["t"]
        while len(s) and (tag == "pad" or tag == "mid" or tag == "mad" or s[0]["w"] == "a" or s[0]["w"] == "a."):
            s = s[1:]
            if len(s):
                tag = s[0]["t"]
            else:
                tag = ""
        if len(s) > 0:
            newLs.append(s)

    ls = newLs
    newLs = []
    for s in ls:
        skip = 0
        if len(s) > 3 and s[0]["w"] == "Hon" and s[1]["w"] == "ska" and s[2]["w"] == "kunna":
            ss = s[3:]
        else:
            ss = s

        midmadpad = 0
        for i in range(len(ss)):
            if ss[i]["t"] == "mid" or ss[i]["t"] == "mad" or ss[i]["t"] == "pad":
                midmadpad += 1
            
        if len(ss) - midmadpad < 3:
            skip = 1
            for tt in range(len(ss)):
                t = ss[tt]["t"][:2]
                if t == "vb":
                    skip = 0

        if not skip:
            for i in range(len(ss)):
                if ss[i]["t"][:2] == "vb":
                    break
                if ss[i]["w"] == "hp":
                    left = len(ss) - i
                    if left < 3:
                        skip = 1
                        break
                    if left < 5 and (left > 2 and (ss[i + 1]["w"] == "ska" or ss[i+2]["w"] == "ska")):
                        skip = 1
                        break
                    if left < 7 and (ss[-1]["w"] == "FSR" or ss[-2]["w"] == "FSR" or ss[-3]["w"] == "FSR"):
                        skip = 1
                        break
        
        if not skip:
            newLs.append(s)
            
    ls = newLs
    newLs = []
    for s in ls:
        if len(ls) > 0:
            newLs.append(s)
            
    return newLs

#######################################################################
### Go through the Granska reply, extract word-tag-lemma and clause ###
### information                                                     ###
#######################################################################
def extractTagsAndClauses(xml):
    phrases = []
    wtls = []

    for elB in xml.iter("bio"):
        sent = []
        for elR in elB.iter("row"):
            tmp = elR.text
            if tmp:
                wtpc = tmp.split("\t")
                sent.append({"w":wtpc[0], "t":wtpc[-3], "p":wtpc[-2], "c":wtpc[-1]})
        phrases.append(sent)
        
    for elS in xml.iter("s"):
        if elS.attrib:
            sentId = elS.attrib["ref"]

            sent = []
            for elW in elS.iter('w'):
                if elW.attrib:
                    w = elW.text
                    t = elW.attrib["tag"]
                    l = elW.attrib["lemma"]
                
                    sent.append({"w":w, "t":t, "l":l})
            
            wtls.append(sent)
    
    return [wtls, phrases]

#######################################################################
### Take the word-tag-lemma-clause data from all ILO texts from all ###
### courses and map it back to the ### respective courses.          ###
#######################################################################
def mapWTLbackToCoursesAndGaols(courseList, wtlList, phrList):

    ### Merge word-tag-lemma with phrase-clause
    merged = []

    nextWtl = 0
    nextPhr = 0

    while nextWtl < len(wtlList) and nextPhr < len(phrList):
        badMatch = False
        m = []

        wtl = wtlList[nextWtl]
        ph = phrList[nextPhr]

        if(len(wtl) != len(ph) + 4):
            log("WARNING, lengths are not as expected when merging: " + str(nextWtl) + " " + str(len(wtl)) + " " + str(len(ph)))
            log(str(wtl))
            log(str(ph))
        
        idxp = 0
        idxw = 0
        while idxw < len(wtl) and idxp < len(ph):
            while wtl[idxw]["t"][:4] == "sen.":
                idxw += 1
            if wtl[idxw]["w"].lower() == ph[idxp]["w"].lower():
                m.append({"w":wtl[idxw]["w"], "t":wtl[idxw]["t"], "l":wtl[idxw]["l"], "p":ph[idxp]["p"], "c":ph[idxp]["c"]})
                idxw += 1
                idxp += 1
            else:
                badMatch = True
                break
        
        if not badMatch:
            if len(m) < 1 or (len(m) == 1 and m[0]["w"] == "."):
                pass
            else:
                merged.append(m)
            nextWtl += 1
            nextPhr += 1
        else:
            if nextWtl+1 < len(wtlList) and wtlList[nextWtl+1][2]["w"] == phrList[nextPhr][0]["w"]:
                nextWtl += 1
            elif nextPhr+1 < len(phrList) and wtlList[nextWtl][2]["w"] == phrList[nextPhr+1][0]["w"]:
                nextPhr += 1
            else:
                nextWtl += 1
                nextPhr += 1

    ### Map merged info back to the corresponding courses

    mi = 0
    while mi < len(merged):
        m = merged[mi]
        
        if len(m) == 2 and m[0]["w"] in taggedCC:
            # start of course

            mj = mi + 1
            while mj < len(merged):
                m2 = merged[mj]
                if (len(m2) == 2 and m2[0]["w"] in taggedCC) or mj == len(merged) - 1:
                    # next course

                    taggedSents = []
                    for i in range(mi+1, mj):
                        taggedSents.append(merged[i])
                    if mj == len(merged) - 1:
                        taggedSents.append(merged[mj])
                        mi = mj + 1
                    else:
                        mi = mj

                    occurrences = taggedCC[m[0]["w"]]
                    if len(occurrences) > 0:
                        c = courseList[occurrences[0]] # use first (unused) occurence 
                        if len(occurrences) > 1:
                            taggedCC[m[0]["w"]] = occurrences[1:] # remove first occurence to add tags to the next occurence next time
                        
                        c["ILO-list-sv-tagged"] = removeCommonErrors(taggedSents)
                        
                    else:
                        log("WARNING: No record of course " + m[0]["w"] + " is left.")
                    
                    break
                else:
                    mj += 1
        else:
            log("WARNING: Found sentence but don't know where it belongs: " + str(mi) + ", " + str(merged[mi]))
            mi += 1

##################################################################################
### Do part-of-speech tagging and phrase analysis using the online Granska API ###
##################################################################################

#################################################################
### Combine all ILO texts, send everything at once to Granska ###
#################################################################
fullText = ""
firstF = 1
cs = len(data["Course-list"])
chunks = []

#############################################################################
### Granska only accepts 100 000 bytes of data, so we need to divide data ###
### into smaller chunks                                                   ###
#############################################################################
GRANSKA_SIZE_LIMIT = 55000 #99000

taggedCC = {}

##########################
### Combine goal texts ###
##########################
for idx in range(cs):
    c = data["Course-list"][idx]

    first = True
    head = str(c["CourseCode"]) + " . . "
    goals = head
    
    if "ILO-list-sv" in c and c["ILO-list-sv"]:
        ls = c["ILO-list-sv"]

        for goal in ls:
            if len(goal.strip()):
                if first:
                    first = False
                else:
                    goals += " . . "

                goals = goals + goal

    if goals != head:
        if c["CourseCode"] in taggedCC:
            taggedCC[c["CourseCode"]].append(idx)
        else:
            taggedCC[c["CourseCode"]] = [idx]
        
        if len(fullText) + len(goals) > GRANSKA_SIZE_LIMIT:
            if len(fullText):
                chunks.append(fullText)
            fullText = ""
            firstF = True
        if firstF:
            firstF = False
        else:
            fullText += " . . "
        fullText += goals

if len(fullText):
    chunks.append(fullText)

##########################################################################
### For each chunk of ILO texts of a size that Granska API can handle, ###
### send it to Granska and read the reply                              ###
##########################################################################
chnk = 0
for chunk in chunks:
    tries = 0
    commOK = 0

    toSend  = ("TEXT " + chunk.replace("\n", " ").strip() + "\nENDQ\n").encode("latin-1", "ignore")

    chnk += 1

    while tries < 5 and not commOK:
        log("Try no " + str(tries) + ", size " + str(len(toSend)) + ", chunk " + str(chnk) + " of " + str(len(chunks)))
        try:
            # log("connecting to Granska")
            usock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            usock.settimeout(60 * 2) # if there is no reply in 2 minutes, give up and try again
            usock.connect(("skrutten.csc.kth.se", 6127))
            usock.settimeout(None)

            # log("Sending data")

            usock.settimeout(60) 
            usock.send(toSend) # There is a length restriction on this service, but we should always be fine with our relatively short texts.
            usock.settimeout(None)

            first = 1
            haveAll = 0
            reply = ""
            while not haveAll:
                # log("Receiving reply")
                
                usock.settimeout(60)
                tmp = usock.recv(1024*1024)
                usock.settimeout(None)
                
                if first:
                    first = 0
                    reply = tmp
                else:
                    reply += tmp

                # log("Received " + str(len(reply)) + " so far. " + str(reply[-10:]) + " this time " + str(len(tmp)))

                haveAll = 0
                try:
                    tmpR = reply.decode("latin-1")
                    if tmpR.find("/Root>") >= 0:
                        haveAll = 1
                        break
                except:
                    haveAll = 0
                    
                if len(tmp) == 0: # disconnected
                    break
                    
            if haveAll:
                log("Received everything.")
                usock.close()
                commOK = 1
            else:
                log("Did not receive a full reply.")
                tries += 1
                time.sleep(60) # wait 60 seconds and see if the server is back again

        except Exception as e:
            log("Exception when using Granska: " + str(e))
            tries += 1
            time.sleep(60) # wait 60 seconds and see if the server is back again
            log("Try again")
            continue

        if commOK:
            try:
                t = reply.decode("latin-1")
                p = t.find("<Root>")
                t = t[p:].replace(">&</w>", ">&amp;</w>")
                xml = XML.fromstring(t)
            except Exception as e:
                log ("WARNING: XML parsing failed:\n\n" + str(e) + "\n\n" + t + "\n\n" + text + "\n\n")
                xml = False

            if xml:
                tmp = extractTagsAndClauses(xml)

                wtlList = tmp[0]
                phrList = tmp[1]

                mapWTLbackToCoursesAndGaols(data["Course-list"], wtlList, phrList)

##############################
### Print result to stdout ###
##############################
print(json.dumps(data))
