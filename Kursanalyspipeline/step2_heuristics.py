import sys
import json
import re
import string
import sys

##############################
### check system arguments ###
##############################
doXX = 0
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-lev" or sys.argv[i] == "-l":
        doXX = 1
    elif sys.argv[i] == "-nl":
        doXX = 0
    else:
        print ("\nReads JSON from stdin, uses heuristics to extract goals from free text\nand to update GXX/AXX level tags based on prerequisites free text,\nprints result as JSON to stdout.")
        print ("\nusage options:")
        print ("     -l  update GXX/AXX tags where possible")
        print ("     -n  do not update GXX/AXX, only extract goals\n")
        sys.exit(0)

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

#####################################################################
#### Clean up things that sometimes are weird in the source data ####
#####################################################################
def cleanStr(s):
    res = s.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", "")
    res = re.sub("<\\s*br\\s*/*\\s*>", "\n", res, re.I)
    res = re.sub("[.][.][.]*", ".", res)
    res = re.sub("</?\\w*/?>", " ", res)
    res = re.sub("\s\s\s*", " ", res)
    res = res.strip()
    return res

def cleanUp(c):
    # Fix weirdness that some KTH texts have

    c["Prerequisites"] = cleanStr(c["Prerequisites"])
    c["ILO-sv"] = cleanStr(c["ILO-sv"])

#########################################################################
### See if 'Prerequisites' free text has information that can be used ###
### to update GXX or AXX to something more informative.               ###
#########################################################################
def updateLevelAttribute(c):
    if not "CourseLevel-ID" in c or not c["CourseLevel-ID"] or len(c["CourseLevel-ID"]) < 3 or c["CourseLevel-ID"][1] != "X":
        return
    
    if "Prerequisites" in c:
        if c["CourseLevel-ID"] == "GXX" and not c["Prerequisites"]:
            # if no prerequisites are listed at all, G1N?
            c["CourseLevel-ID"] = "G1N"
            return
        
    if "Prerequisites" in c and c["Prerequisites"]:
        
        pr = c["Prerequisites"]
        
        if c["CourseLevel-ID"] == "GXX": # If "Grundläggande behörighet" then G1N
            if re.search("grundläggande.?(högskole)*behörighet", pr, re.I):
                c["CourseLevel-ID"] = "G1N"
                return
            
        courseCodes = re.findall("[A-Z][A-Z][0-9][0-9][0-9][0-9]", pr)
        haveAdvanced = 0
        for cc in courseCodes:
            if cc[2] == "2": # advanced course
                haveAdvanced = 1

        if not haveAdvanced and "avancerad nivå" in pr.lower() and not "/avancerad nivå" in pr.lower():
            haveAdvanced = 1
            
        if c["CourseLevel-ID"] == "AXX":
            if haveAdvanced: # if advanced prerequisite then A1F
                c["CourseLevel-ID"] = "A1F"
                return

        if c["CourseLevel-ID"] == "GXX":
            if len(courseCodes) > 0: # If we have at least some course requirements above basics, then G1F
                c["CourseLevel-ID"] = "G1F"
                return

#######################################
#### Language identification stuff ####
#######################################
MAXTRIGRAMS = 1000
sweTrigramLookup = {}
i = 0
for line in open("data/swedish_trigrams.txt").readlines():
    tri = line.strip()
    sweTrigramLookup[tri] = i
    i += 1
    if i >= MAXTRIGRAMS:
        break
i = 0
engTrigramLookup = {}
for line in open("data/english_trigrams.txt").readlines():
    tri = line.strip()
    engTrigramLookup[tri] = i
    i += 1
    if i >= MAXTRIGRAMS:
        break

def identifyLanguage(text):
    counts = {}
    words = text.lower().strip(string.punctuation).split()

    for word in words:
        for c in range(len(word) - 2):
            tri = word[c:c+3]

            if tri in counts:
                counts[tri] += 1
            else:
                counts[tri] = 1

    triList = []
    for tri in counts:
        triList.append([-counts[tri], tri])
    triList.sort()

    totSwe = 0
    totEng = 0
    
    for t in range(min(len(triList), MAXTRIGRAMS)):
        tri = triList[t][1]
        
        if tri in sweTrigramLookup:
            swe = sweTrigramLookup[tri]
        else:
            swe = -1

        if tri in engTrigramLookup:
            eng = engTrigramLookup[tri]
        else:
            eng = -1

        if swe < 0:
            distSwe = MAXTRIGRAMS
        else:
            distSwe = abs(swe - t)
        if eng < 0:
            distEng = MAXTRIGRAMS
        else:
            distEng = abs(eng - t)

        totSwe += distSwe
        totEng += distEng

    if totSwe <= totEng:
        return "sv"
    return "en"

################################################################################
### Use heuristics to extract sentences with goals from the ILO-sv free text ###
################################################################################
def extractGoals(c):
    sv = c["ILO-sv"]
    en = c["ILO-en"]

    ######################################################################################
    ### Check language since there sometimes is English text in the Swedish field etc. ###
    ######################################################################################
    langSv = identifyLanguage(sv)
    langEn = identifyLanguage(en)

    if langSv != "sv":
        c["ILO-sv"] = ""
        if langEn == "sv" and len(en):
            c["ILO-sv"] = en
            
    if langEn != "en":
        c["ILO-en"] = ""
        if langSv == "en" and len(sv):
            c["ILO-en"] = sv
    
    sv = c["ILO-sv"]
    en = c["ILO-en"]

    #####################################################
    ### unify hyphens to simplify expression matching ###
    #####################################################
    sv = sv.replace("\n -", "\n–").replace("\n-", "\n–").replace("\n−", "\n–").replace(u"\uF095", "–")

    iloList = {}
    
    iSyfteExp = re.compile("<p>\s*i\s+syfte\s+att", re.I)
    forAttExp = re.compile("<p>\s*för\s+att", re.I)
    
    htmlListExp = re.compile("<li>(.*?)(?:</?li>)", re.I)
    pListExp = re.compile("<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*(?:</?p>)", re.I)
    brListExp = re.compile("<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*(.*?)\s*(?:<)", re.I)

    dotListExp = re.compile("[•*·–…]\s*[0-9]*[.]?\s*([^•*·–…\n]*)\s*", re.I)
    newlineListExp = re.compile("\n\s*[-o•*·–.—]\s*[0-9]*[.]?\s*([^\n]*)", re.I)
    romanListExp = re.compile("\n[IVX][IVX]*\s*[.]\s\s*([^\n]*)", re.I)
    arabicListExp = re.compile("\n[0-9][0-9]*\s*[).]\s*([^\n]*)", re.I)
    parListExp = re.compile("\n\s*\\([0-9a-zA-Z]\\)\s*([^\n]*)", re.I)

    skaKunnaExp = re.compile("[Kk]unna(.*?)[.\n]", re.I)
    kanExp = re.compile("\skan\s(.*?)[.]", re.I)
    fortrogenExp = re.compile("\sförtrogen\s*i\s(.*?)[.]", re.I)
    formagaExp = re.compile("visa.*?\sförmåga.*?att\s*(.*?)[.]", re.I)
    kunnaColonExp = re.compile("kunna:\s*?\n", re.I)

    found = 0

    m = iSyfteExp.search(sv)
    if m:
        sv = iSyfteExp.split(sv)[0] # remove everything from "i syfte att" and forward
    else:
        m = forAtt.search(sv)
        if m:
            sv = forAttExp.split(sv)[0]  # remove everything from "för att" and forward
    
    m = htmlListExp.search(sv)
    if m:
        found = 1
        ls = htmlListExp.findall(sv)
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
    
    m = pListExp.search(sv)
    if m:
        found = 1
        ls = pListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = brListExp.search(sv)
    if m:
        found = 1
        ls = brListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = dotListExp.search(sv)
    if m:
        found = 1
        ls = dotListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = newlineListExp.search(sv)
    if m:
        found = 1
        ls = newlineListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = romanListExp.search(sv)
    if m:
        found = 1
        ls = romanListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = arabicListExp.search(sv)
    if m:
        found = 1
        ls = arabicListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = parListExp.search(sv)
    if m:
        found = 1
        ls = parListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = skaKunnaExp.search(sv)
    if m:
        found = 1
        ls = skaKunnaExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = fortrogenExp.search(sv)
    if m:
        found = 1
        ls = fortrogenExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1

    m = formagaExp.search(sv)
    if m:
        found = 1
        ls = formagaExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
            
    m = kanExp.search(sv)
    if m:
        found = 1
        ls = kanExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
            
    p = sv.find("unna:\n\n")
    ls = []
    if p > 0:
        p += 7
        p2 = sv.find("\n\n", p)
        if p2 > 0:
            tmp = sv[p:]
            tmpLs = tmp.split("\n\n")

            ls += tmpLs
            
    if len(ls):
        found = 1
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
            
    p = kunnaColonExp.search(sv)
    ls = []
    while p:
        p = p.span()[1]
        p2 = sv.find("\n\n", p)

        if p2 < 0:
            p2 = len(sv)
        tmp = sv[p:p2]
        tmpLs = tmp.split("\n")

        ls += tmpLs
            
        p = kunnaColonExp.search(sv, p)
    if len(ls):
        found = 1
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
        
    p = sv.find(":</p>")
    if p > 0:
        p = sv.find("<p>",p)
    ls = []
    while p > 0:
        p += 3
        p2 = sv.find("</p>", p)

        if p2 < 0:
            p2 = len(sv)

        ls.append(sv[p:p2])
            
        p = sv.find("<p>",p2)
    if len(ls):
        found = 1
            
        for l in ls: # remove duplicates
            iloList[l.strip()] = 1
        
    if not found: # If not found, add the whole text ?
        if sv and len(sv) > 1:
            iloList[sv] = 1

    ls = []
    content = re.compile("[a-zA-ZåäöÅÄÖ]")
    for l in iloList:
        ll = cleanStr(l)
        if content.search(ll):
            ls.append(ll)
    ls.sort()
    
    return ls

##########################################################################
### Check list for duplicates and substrings that are completely found ###
### in other strings, and remove them                                  ###
##########################################################################
def dupcheck(ls):
    res = []
    for s in ls:
        skip = 0
        for i in range(len(res)):
            ss = res[i]
            if s.find(ss) >= 0 or ss.find(s) >= 0:
                skip = 1
                if len(s) < len(ss):
                    res[i] = s

        if not skip and len(s) > 0:
            res.append(s)
    return res

######################################################################
### Check if a goal starts with upper or lower case. If lower case ###
### (i.e. probably not a complete sentence), add a dummy sentence  ###
### head.                                                          ###
######################################################################
def startcheck(ls):
    res = []
    for si in range(len(ls)):
        s = ls[si]
        for i in range(len(s)):
            if s[i].isupper():
                break
            if s[i].islower():
                s = "Hon ska kunna " + s
                break

        if not s[-1] in string.punctuation:
            s += " ."
        res.append(s)
    return res

######################################
### For each course, extract goals ###
######################################
for c in data["Course-list"]:
    iloList = extractGoals(c)
    iloList = dupcheck(iloList)
    iloList = startcheck(iloList)
    c["ILO-list-sv"] = iloList
    
    cleanUp(c)

    if doXX:
        updateLevelAttribute(c)

##############################
### Print result to stdout ###
##############################
print(json.dumps(data))
