import sys
import string
import json
import re

##############################
### check system arguments ###
##############################

checkEN = 0
checkLev = 0
checkILO = 0
checkSCB = 0
checkBloom = 0
bloomFile = ""
unknown = 0
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
    elif sys.argv[i] == "-a":
        checkEN = 1
        checkLev = 1
        checkILO = 1
        checkSCB = 1
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
    print ("     -b <filename>  Check Bloom verbs")
    print ("     -a    Check everything except Bloom verbs (-ilo -en -lev -SCB)")
    sys.exit(0)

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

###################################################
### For each course, check for ambiguities etc. ###
###################################################
for cl in data:
    
    for c in data[cl]:
        printed = 0

        if checkILO:
            if not "ILO-sv" in c or c["ILO-sv"].strip() == "":
                print(c["CourseCode"], "has no ILO-sv")#, c)
                printed = 1
            elif not "ILO-list-sv" in c or len(c["ILO-list-sv"]) < 1:
                print(c["CourseCode"], "has empty ILO-list-sv", c["ILO-sv"])
                printed = 1
            elif not "Bloom-list" in c or len(c["Bloom-list"]) < 1:
                print(c["CourseCode"], "has empty Bloom-list", c["ILO-list-sv"])
                printed = 1

        if checkEN and (not "ILO-en" in c or c["ILO-en"].strip() == ""):
            print(c["CourseCode"], "has no ILO-en")#, c)
            printed = 1

        if checkLev:
            if not "CourseLevel-ID" in c:
                print(c["CourseCode"], "has no CourseLevel-ID")#, c)
                printed = 1
            elif "XX" in c["CourseLevel-ID"]:
                print(c["CourseCode"], "has uninformative Course Level: ", c["CourseLevel-ID"], c["Prerequisites"])
                printed = 1

        if checkSCB and not "SCB-ID" in c:
            print(c["CourseCode"], "has no SCB-ID")#, c)
            printed = 1

        if checkBloom:
            if not checkILO and not "Bloom-list" in c or len(c["Bloom-list"]) < 1:
                print(c["CourseCode"], "has empty Bloom-list", c["ILO-list-sv"])
                printed = 1
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
                        
                    for bloom in goal:
                        verb = bloom[0]
                        exp = bloom[1]
                        level = bloom[2]
                        if exp in ambig:
                            print(c["CourseCode"], "ambiguous Bloom: '" + exp + "' " + str(ambig[exp]) + " in:", thisGoal)
                            
        if printed:
            print ("-"*30, "\n\n")

    print(len(data[cl]), "courses in data")
