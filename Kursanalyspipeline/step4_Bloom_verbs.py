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
for i in range(len(sys.argv)):
    if sys.argv[i] == "-log":
        logging = 1
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
    if sys.argv[i] != "-log" and sys.argv[i][0] == "-":
        hlp = 1
    if sys.argv[i] == "help":
        hlp = 1

if hlp:
    print ("\nReads JSON from stdin, extracts Bloom verbs and adds the Bloom levels, prints JSON to stdout.\n")
    print ("usage:")
    print ("    ", sys.argv[0], "<Bloom verbs filename (Swedish)> <Bloom verbs filename (English)>\n")
    print ("    ", "(If no files are specified, " + defaultSv + " and " + defaultEn + " will be used.)\n")
    sys.exit(0)

first = True
svFileName = defaultSv
enFileName = defaultEn
for i in range(1, len(sys.argv)):
    if sys.argv[i] != "-log":
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

#############################################
### Read the Bloom verbs and their levels ###
#############################################
bloomLevel = 0
bloomLex = {}
bloom = open(svFileName)
for line in bloom.readlines():
    if line[0] == "#":
        continue # skip comments

    if line[0:3] == "---": # new Bloom level
        m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
        if len(m) == 1:
            bloomLevel = int(m[0])
    
    if line[0] == "(": # ambiguous verb, not the default level of this verb
        continue

    if line[0].islower() or line[0].isupper():
        exp = line.strip()
        if " " in exp:
            verb = exp.split()[0]
        else:
            verb = exp

        if verb in bloomLex:
            bloomLex[verb].append( [verb, exp, bloomLevel] )
        else:
            bloomLex[verb] = [ [verb, exp, bloomLevel] ]
bloom.close()
            
bloomLevel = 0
bloomLexEn = {}
bloom = open(enFileName)
for line in bloom.readlines():
    if line[0] == "#":
        continue # skip comments

    if line[0:3] == "---": # new Bloom level
        m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
        if len(m) == 1:
            bloomLevel = int(m[0])
    
    if line[0] == "(": # ambiguous verb, not the default level of this verb
        continue

    if line[0].islower() or line[0].isupper():
        exp = line.strip()
        if " " in exp:
            verb = exp.split()[0]
        else:
            verb = exp

        if verb in bloomLexEn:
            bloomLexEn[verb].append( [verb, exp, bloomLevel] )
        else:
            bloomLexEn[verb] = [ [verb, exp, bloomLevel] ]
bloom.close()

##############################################
### In a tagged sentence, find Bloom verbs ###
##############################################
def bloomVerbsInSentenceEn(s):
    bloomMatches = []
    for i in range(len(s)): # for each word, check if it is a verb
        lemma = s[i].lower()

        if lemma in bloomLexEn:
            exps = bloomLexEn[lemma]
            longestMatch = -1
            longestIdx = -1
                
            for j in range(len(exps)): # for each Bloom verb expression starting with this verb
                    
                exp = exps[j][1]
                tokens = exp.split()

                # log("match exp '" + str(exp) + "' in: " + str(s))
                
                toklen = len(tokens)

                ii = 0
                kk = 0
                matchOK = 1
                for k in range(len(tokens)):
                    if tokens[k] == "*":
                        tmp = 0
                        starOK = 0
                        while tmp + i + ii < len(s):
                            if tokens[k + 1].lower() == s[i + ii + tmp].lower():
                                ii += tmp
                                starOK = 1
                                break
                            tmp += 1
                        if not starOK:
                            matchOK = 0
                            break
                    elif i + ii < len(s) and tokens[k].lower() == s[i + ii].lower():
                        # log("OK for tokens[" + str(k)  + "] and s[" + str(i+ ii) + "], " + tokens[k])
                        ii += 1
                    else:
                        # log("NOT OK for tokens[" + str(k)  + "] and s[" + str(i+ ii) + "], " + tokens[k])
                        matchOK = 0
                        break
                if matchOK:
                    log("exp was a match " + str(exp))
                    if toklen > longestMatch:
                        longestMatch = toklen
                        longestIdx = j
            if longestIdx >= 0:
                bloomMatches.append( exps[longestIdx] )

    return bloomMatches


def bloomVerbsInSentence(s):
    bloomMatches = []
    for i in range(len(s)): # for each word, check if it is a verb
        try:
            tag = s[i]["t"]
        except:
            print ("could not get tag", s, i)
            continue
            
        if len(tag) >= 2 and tag[:2] == "vb":            
            lemma = s[i]["l"]

            # sometimes there are digits stuck to words, try to remove them
            if not lemma in bloomLex and lemma[0].isdigit():
                log("not in lex: " + lemma)
                skip = 0
                while lemma[skip].isdigit() and skip < len(lemma):
                    skip += 1
                if skip < len(lemma):
                    lemma = lemma[skip:]
                log("Changed '" + s[i]["l"] + "' to '" + lemma + "'")

                s[i]["l"] = lemma
                
            if lemma in bloomLex:
                exps = bloomLex[lemma]
                longestMatch = -1
                # highestLevel = -1
                longestIdx = -1
                
                for j in range(len(exps)): # for each Bloom verb expression starting with this verb
                    
                    exp = exps[j][1]
                    tokens = exp.split()

                    # log("try exp: " + str(exp) + " in " + str(s))
                    
                    toklen = len(tokens)
                    # level = exps[j][2]

                    ii = 0
                    kk = 0
                    matchOK = 1
                    for k in range(len(tokens)):
                        if tokens[k] == "*":
                            tmp = 0
                            starOK = 0
                            while tmp + i + ii < len(s):
                                if tokens[k + 1] == s[i + ii + tmp]["w"] or tokens[k + 1] == s[i + ii + tmp]["l"]:
                                    ii += tmp
                                    starOK = 1
                                    break
                                tmp += 1
                            if not starOK:
                                matchOK = 0
                                break
                        elif i + ii < len(s) and (tokens[k] == s[i + ii]["w"] or tokens[k] == s[i + ii]["l"]):
                            ii += 1
                        else:
                            matchOK = 0
                            break
                    if matchOK:
                        if toklen > longestMatch:
                            longestMatch = toklen
                            longestIdx = j
                        # if level > highestLevel:
                        #     highestLevel = level
                if longestIdx >= 0:
                    if tag[-4:] == ".sfo":
                        tmp = ""
                        for wtl in s:
                            tmp += wtl["w"]
                            if wtl["t"][:2] == "vb" and wtl["t"][-4:] == ".sfo":
                                tmp += " (" +  wtl["t"].upper() + ")"
                            tmp += " "
                        log("matched '" + str(exps[longestIdx]) + "' in '" + tmp + "'\n")
                    else:
                        bloomMatches.append( exps[longestIdx] )

    return bloomMatches


##################################################################################
### For each course in the course list, add Bloom verbs and their Bloom levels ###
##################################################################################
for c in data["Course-list"]:
    ls = c["ILO-list-sv-tagged"]

    blooms = []
    for s in ls:
        m = bloomVerbsInSentence(s)
        blooms.append(m)
    c["Bloom-list-sv"] = blooms

    ls = c["ILO-list-en"]

    blooms = []
    for s in ls:
        tmp = re.findall("\w+", s)
        m = bloomVerbsInSentenceEn(tmp)
        blooms.append(m)
    c["Bloom-list-en"] = blooms
    
##############################
### Print result to stdout ###
##############################
print (json.dumps(data))
