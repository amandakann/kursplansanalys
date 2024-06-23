import sys
import json
import re
import string

defaultSv = "data/bloom_revised_sv.txt"
defaultEn = "data/bloom_revised_en.txt"

###############
### Logging ###
###############
logging = 0
zero = False
spelling = False
for i in range(len(sys.argv)):
    if sys.argv[i] == "-log":
        logging = 1
    elif sys.argv[i] == "-z":
        zero = True
    elif sys.argv[i] == "-s":
        spelling = True
        
if logging:
    logf = open(sys.argv[0] + ".log", "w")
def log(s):
    if not logging:
        return

    logf.write(s)
    logf.write("\n")
    logf.flush()

##############################
### check system arguments ###
##############################
hlp = 0
for i in range(1, len(sys.argv)):
    if sys.argv[i] != "-log" and sys.argv[i] != "-z" and sys.argv[i] != "-s" and sys.argv[i][0] == "-":
        hlp = 1
    if sys.argv[i] == "help":
        hlp = 1
if hlp:
    print ("\nReads JSON from stdin, extracts Bloom verbs and adds the Bloom levels, prints JSON to stdout.\n")
    print ("usage:")
    print ("    ", sys.argv[0], "<Bloom verbs filename (Swedish)> <Bloom verbs filename (English)> [-z] [-s]")
    print ("     ", "                    -z   Collect data on goals with 0 Bloom classified verbs.\n")
    print ("     ", "                    -s   Try automatic spelling correction.\n")
    print ("    ", "(If no files are specified, " + defaultSv + " and " + defaultEn + " will be used.)\n")
    sys.exit(0)

first = True
svFileName = defaultSv
enFileName = defaultEn
for i in range(1, len(sys.argv)):
    if sys.argv[i] != "-log" and sys.argv[i] != "-z" and sys.argv[i] != "-s":
        if first:
            svFileName = sys.argv[i]
            first = False
        else:
            enFileName = sys.argv[i]
log("Using files " + svFileName + " and " + enFileName)

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

#######################################
### read Bloom classifications etc. ###
#######################################

import bloom_functions
    
bloomLex, ambiLex, bloomLexEn, ambiLexEn = bloom_functions.readBloomFiles(svFileName, enFileName, spelling, logging, zero)
translationsSuggs = bloom_functions.bloomTranslations("data/bloom_translations_sv_to_en.txt")
bloom_functions.initBloomSpellings(data)

##################################################################################
### For each course in the course list, add Bloom verbs and their Bloom levels ###
##################################################################################
for c in data["Course-list"]:
    if "ILO-list-sv-tagged" in c:
        ls = c["ILO-list-sv-tagged"]
    else:
        log("No 'ILO-list-sv-tagged' in " + c["CourseCode"])
        ls = []
    if ls == None:
        ls = []
    
    blooms = []
    for s in ls:
        m = bloom_functions.bloomVerbsInSentence(s, bloomLex, ambiLex, True)
        blooms.append(m)
    c["Bloom-list-sv"] = blooms

    ls = c["ILO-list-en"]

    blooms = []
    for s in ls:
        tmp = re.findall("\w+", s)
        m = bloom_functions.bloomVerbsInSentence(tmp, bloomLexEn, ambiLexEn, False)
        blooms.append(m)
    c["Bloom-list-en"] = blooms


    if len(c["ILO-en"]): # if we have English text
        hasAmbiguous = 0
        for bb in c["Bloom-list-sv"]:
            for b in bb:
                if b[1] in translationsSuggs:
                    hasAmbiguous = 1
                
        if hasAmbiguous:
            log(c["CourseCode"])
            bloom_functions.checkEnglishWhenSwedishIsAmbiguous(c["Bloom-list-sv"], c["Bloom-list-en"], c["ILO-list-en"], c["ILO-en"])


##############################
### Print result to stdout ###
##############################
if zero:
    bloom_functions.printZeroBloomInfo()

print (json.dumps(data))

