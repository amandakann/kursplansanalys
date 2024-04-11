import sys
import string
import json
import re

##############################
### check system arguments ###
##############################

types = {"vidareutbildning":1, "uppdragsutbildning":1, "förberedande utbildning":1, "grundutbildning":1, "forskarutbildning":1}
checkEN = 0
checkLev = 0
checkILO = 0
checkSCB = 0
checkBloom = 0
checkCreds = 0
checkNonBloomVerbs = 0
checkType = 0
bloomFile = ""
unknown = 0

printEachCourse = 0

ignoreF = 0
ignoreFB = 0
ignoreV = 0
ignoreU = 0
ignoreG = 0

for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-en":
        checkEN = 1
    elif sys.argv[i] == "-ilo":
        checkILO = 1
    elif sys.argv[i] == "-lev":
        checkLev = 1
    elif sys.argv[i] == "-scb":
        checkSCB = 1
    elif sys.argv[i] == "-b":
        checkBloom = 1
    elif sys.argv[i] == "-c":
        checkCreds = 1
    elif sys.argv[i] == "-v":
        checkNonBloomVerbs = 1
    elif sys.argv[i] == "-t":
        checkType = 1
    elif sys.argv[i] == "-a":
        checkEN = 1
        checkLev = 1
        checkILO = 1
        checkSCB = 1
        checkCreds = 1
        checkNonBloomVerbs = 1
        checkType = 1
        
    elif sys.argv[i] == "-pa":
        printEachCourse = 1
        
    elif sys.argv[i] == "-igF":
        ignoreF = 1
    elif sys.argv[i] == "-igFB":
        ignoreFB = 1
    elif sys.argv[i] == "-igV":
        ignoreV = 1
    elif sys.argv[i] == "-igU":
        ignoreU = 1
    elif sys.argv[i] == "-igG":
        ignoreG = 1
    else:
        if(sys.argv[i-1] != "-b"):
            unknown = 1
        else:
            bloomFile = sys.argv[i]

if unknown or (checkSCB + checkLev + checkEN + checkILO + checkBloom) < 1 or (checkBloom and bloomFile == ""):
    print ("\nCheck courses for problems or ambiguities. Reads JSON from stdin.")
    print ("usage options:")
    print ("     -ilo  Check if Swedish ILO contains Bloom verbs")
    print ("     -en   Check if English version available")
    print ("     -lev  Check if course level is properly specified")
    print ("     -SCB  Check if SCB-ID is present")
    print ("     -c    Check if ESCB-credits is present and seems OK")
    print ("     -v    Check for verbs that cannot be classified in the Bloom taxonomy")
    print ("     -b <filename>  Check Bloom verbs")
    print ("     -a    Check everything except Bloom verbs (-ilo -en -lev -SCB -c -v)")
    print ()
    print ("     -pc   Print each course and its problems")
    print ()
    print ("     -igF  Ignore all courses of type \"forskarutbildning\"")
    print ("     -igFB Ignore all courses of type \"förberedande utbildning\"")
    print ("     -igU  Ignore all courses of type \"uppdragsutbildning\"")
    print ("     -igV  Ignore all courses of type \"vidareutbildning\"")
    print ("     -igG  Ignore all courses of type \"grundutbildning\"")
    print ()
    sys.exit(0)

print ()

###########################################################################
### Check Bloom verbs, print info on courses with ambiguous Bloom verbs ###
###########################################################################
if checkBloom:
    ambig = {}
    bloomLex = {}
    
    try:
        for line in open(bloomFile).readlines():
            if line[0] == "#":
                continue
            if line[0:3] == "---": # new Bloom level
                m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
                if len(m) == 1:
                    bloomLevel = int(m[0])

            if line[0] == "(": # ambiguous verb, not the default level of this verb
                v = line.replace("(", "").replace(")", "").strip()
                if v in ambig:
                    ambig[v].append(bloomLevel)
                else:
                    ambig[v] = [bloomLevel]
                    
            if line[0].islower() or line[0].isupper():
                exp = line.strip()

                bloomLex[exp] = bloomLevel
    except:
        bloomFile = ""
    for v in ambig:
        ambig[v] = [bloomLex[v]] + ambig[v] 
        
############################
### read JSON from stdin ###
############################
data = {}

text = ""
for line in sys.stdin:
    text += line

data = json.loads(text)

#######################
### Statistics etc. ###
#######################
counts = {}
ccs = {}
def add(label, cc):
    if not label in counts:
        counts[label] = 0
    if not label in ccs:
        ccs[label] = []
    counts[label] += 1
    ccs[label].append(cc)

verbCounts = {}
bloomLevelCounts = {}
nonBloomVerbs = {}
nonBloomVerbsInfo = {}
ambiguousVerbs = {}

def addVerb(v, lev):
    if not v in verbCounts:
        verbCounts[v] = 0
    verbCounts[v] += 1
    
    if not lev in bloomLevelCounts:
        bloomLevelCounts[lev] = 0
    bloomLevelCounts[lev] += 1

def addAmbig(v):
    if not v in ambiguousVerbs:
        ambiguousVerbs[v] = 0
    ambiguousVerbs[v] += 1

def addNonBloom(v, goal, cc):
    if not v in nonBloomVerbs:
        nonBloomVerbs[v] = 0
        nonBloomVerbs[v] += 1

    if not v in nonBloomVerbsInfo:
        nonBloomVerbsInfo[v] = []
        nonBloomVerbsInfo[v].append([goal, cc])

typeCounts = {}
def addType(t):
    if not t in typeCounts:
        typeCounts[t] = 0
    typeCounts[t] += 1
    
def printStats():
    print ("\n","-"*15, "Problem Types", "-"*15)
    for label in counts:
        print ("{0: <35}: {1: >5}".format(label, counts[label]))

    print ("\n","-"*15, "Problems and Courses", "-"*15)
    for label in ccs:
        print ("-"*5, label, "-"*5)
        ccstr = ""
        for cc in ccs[label]:
            ccstr += cc
            ccstr += " "
        print ("  ", ccstr)

    if typeCounts:
        print ("\n","-"*15, "Course types", "-"*15)
        for t in typeCounts:
            print("{0: >5} course of type {1:}".format(typeCounts[t], t))
    
def printBloom():
    tot = 0
    vs = 0
    for v in verbCounts:
        tot += verbCounts[v]
        vs += 1

    print ("\n","-"*15, "VERBS", "-"*15)
    print (vs, "different verbs seen,", tot, "total occurences of these verbs.")
    print("Number of Bloom classifications of each level:")
    for c in range(6):
        if c in bloomLevelCounts:
            print ("{0: >2}: {1: >5}".format(c, bloomLevelCounts[c]))
        else:
            print ("{0: >2}: {1: >5}".format(c, 0))
    print ("-"*30)
    atot = 0
    avs = 0
    for v in ambiguousVerbs:
        atot += ambiguousVerbs[v]
        avs += 1
    print (avs, "different ambiguous verbs seen,", atot, "total occurences of these verbs.")
    for v in ambiguousVerbs:
        print ("{0: <35}: {1: >5}".format(v, ambiguousVerbs[v]))
    
def printNonBloom():
    if not checkNonBloomVerbs:
        return

    tot = 0
    vs = 0
    for v in nonBloomVerbs:
        tot += nonBloomVerbs[v]
        vs += 1
    print ("\n", "-"*15, "Non-Bloom","-"*15)
    print (vs, "verbs found that did not get a Bloom classification.")
    print (tot, "total occurences of these verbs.")
    print ("-"*10)
    for v in nonBloomVerbsInfo:
        for ex in nonBloomVerbsInfo[v]:
            print ("**", v, "** in course ", ex[1], "goal text: ", ex[0])


def cPrint(s):
    if printEachCourse:
        print(s)

###################################################
### For each course, check for ambiguities etc. ###
###################################################

for cl in data:
    
    for c in data[cl]:
        printed = 0

        thisType = "No CourseType"
        if "CourseType" in c:
            thisType = c["CourseType"]

        if (ignoreF and thisType == "forskarutbildning") or (ignoreV and thisType == "vidareutbildning") or (ignoreU and thisType == "uppdragsutbildning") or (ignoreFB and thisType == "förberedande utbildning") or (ignoreG and thisType == "grundutbildning"):

            addType(thisType + " (skipped)")
            continue
        else:
            addType(thisType)

        if checkILO:
            if not "ILO-sv" in c or c["ILO-sv"].strip() == "":
                if "ILO-en" in c:
                    cPrint(c["CourseCode"] + " has no ILO-sv but has English: " + c["ILO-en"])
                else:
                    cPrint(c["CourseCode"] + " has no ILO-sv")
                printed = 1
                add("No ILO-sv", c["CourseCode"])
            elif not "ILO-list-sv" in c or len(c["ILO-list-sv"]) < 1:
                cPrint(c["CourseCode"] + " has empty ILO-list-sv: " + c["ILO-sv"])
                printed = 1
                add("No ILO list", c["CourseCode"])
            elif not "Bloom-list" in c or len(c["Bloom-list"]) < 1:
                cPrint(c["CourseCode"] + " has empty Bloom-list: " + c["ILO-list-sv"])
                printed = 1
                add("No Bloom-list", c["CourseCode"])
            
        if checkEN and (not "Prerequisites-en" in c or not c["Prerequisites-en"] or c["Prerequisites-en"].strip() == ""):
            cPrint(c["CourseCode"] + " has no Prerequisites-en")
            printed = 1
            add("Missing English prerequisites", c["CourseCode"])
        if checkEN and (not "ILO-en" in c or c["ILO-en"].strip() == ""):
            cPrint(c["CourseCode"] + " has no ILO-en")
            printed = 1
            add("Missing English ILO", c["CourseCode"])

        if checkLev:
            if not "CourseLevel-ID" in c:
                if not "CourseType" in c or c["CourseType"] != "förberedande utbildning":
                    cPrint(c["CourseCode"] + " has no CourseLevel-ID")
                    printed = 1
                    add("Missing course level", c["CourseCode"])
            elif "XX" in c["CourseLevel-ID"]:
                cPrint(c["CourseCode"] + " has uninformative Course Level: " + c["CourseLevel-ID"] + " " + c["Prerequisites-sv"])
                printed = 1
                add("Uninformative course level", c["CourseCode"])

            if not checkType and "CourseLevel-ID" in c and "CourseType" in c and c["CourseType"] == "förberedande utbildning" and c["CourseLevel-ID"] != "":
                cPrint(c["CourseCode"] + " has non-empty CourseLevel-ID when it should be empty: " + c["CourseType"] + " " + c["CourseLevel-ID"])
                printed = 1
                add("Course level not empty for 'förberedande kurs'", c["CourseCode"])

        if checkSCB and not "SCB-ID" in c:
            cPrint(c["CourseCode"] + " has no SCB-ID")
            printed = 1
            add("Missng SCB", c["CourseCode"])

        if checkCreds:
            if not "ECTS-credits" in c:
                cPrint(c["CourseCode"] + " has no ECTS-credits field")
                printed = 1
                add("Missng credits", c["CourseCode"])
            elif c["ECTS-credits"] == "":
                cPrint(c["CourseCode"] + " has empty ECTS-credits field")
                printed = 1
                add("Missng credits", c["CourseCode"])
            else:
                try:
                    tmp = c["ECTS-credits"].replace(",", ".")
                    tmp = str(tmp)
                except:
                    cPrint(c["CourseCode"] + ", ECTS-credits value invalid? " + c["ECTS-credits"])
                    printed = 1
                    add("Invalid credits", c["CourseCode"])
                
        if checkNonBloomVerbs:
            if "ILO-list-sv-tagged" in c:
                ls = c["ILO-list-sv-tagged"]
                blooms = []
                if "Bloom-list" in c:
                    blooms = c["Bloom-list"]
                for si in range(len(ls)):
                    s = ls[si]

                    for i in range(len(s)):
                        wtl = s[i]

                        if wtl["t"][:2] == "vb" and not (wtl["t"][-3:] == "aux" or wtl["t"][-3:] == "kop" or wtl["t"][-3:] == "mod"):
                            found = 0
                            w = wtl["l"]
                            stoplist = {"ska":1, "kunna":1, "ske":1}
                            if w in stoplist:
                                continue

                            for bl in blooms:
                                for b in bl:
                                    if b[0] == w:
                                        found = 1
                                        break
                                if found:
                                    break
                                
                            if not found:
                                g = "(" + wtl["t"] + ") "
                                for ww in s:
                                    g += ww["w"]
                                    g += " "
                                g.strip()
                                addNonBloom(w, g, c["CourseCode"])
        
        if checkType:
            if not "CourseType" in c:
                cPrint(c["CourseCode"] + " has no CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] == "":
                cPrint(c["CourseCode"] + " has empty CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] not in types:
                cPrint(c["CourseCode"] + " has an unknown CourseType: " + c["CourseType"])
                printed = 1
                add("Unrecognized course type", c["CourseCode"])
            if "CourseType" in c and c["CourseType"] == "förberedande utbildning":
                if "CourseLevel-ID" in c and c["CourseLevel-ID"] != "":
                    cPrint(c["CourseCode"] + " is 'förberedande utbildning' but has CourseLevel-ID: " + c["CourseLevel-ID"])
                    printed = 1
                    add("Course level not empty for 'förberedande kurs'", c["CourseCode"])
        if checkBloom:
            if not checkILO and not "Bloom-list" in c or len(c["Bloom-list"]) < 1:
                cPrint(c["CourseCode"] + " has empty Bloom-list " + c["ILO-list-sv"])
                printed = 1
                add("Empty Bloom-list", c["CourseCode"])
            if "Bloom-list" in c and len(c["Bloom-list"]) >= 1:
                bl = c["Bloom-list"]
                for goal in bl:
                    thisGoal = ""
                    mx = -1
                    mn = 6
                    for bloom in goal:
                        verb = bloom[0]
                        exp = bloom[1]
                        level = bloom[2]
                        if level > mx:
                            mx = level
                        if level < mn:
                            mn = level
                        if len(thisGoal):
                            thisGoal += ", "
                        thisGoal += exp + " (" + str(level) + ")"

                        addVerb(exp, level)
                        
                    for bloom in goal:
                        verb = bloom[0]
                        exp = bloom[1]
                        level = bloom[2]
                        if exp in ambig:
                            cPrint(c["CourseCode"] + " ambiguous Bloom: '" + exp + "' " + str(ambig[exp]) + " in: " + thisGoal)
                            printed = 1
                            addAmbig(exp)

        
        if printed:
            cPrint("\n " + "-"*30 + "\n")

    print(len(data[cl]), "courses in data")
    printStats()

    if checkBloom:
        printBloom()
    if checkNonBloomVerbs:
        printNonBloom()

    print ()
