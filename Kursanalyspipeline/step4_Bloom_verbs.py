import sys
import json
import re
import string

##############################
### check system arguments ###
##############################
if len(sys.argv) < 2 or sys.argv[1][0] == "-" or sys.argv[1].lower() == "help":
    print ("\nReads JSON from stdin, extracts Bloom verbs and adds the Bloom levels, prints JSON to stdout.\n")
    print ("usage:")
    print ("    ", sys.argv[0], "<Bloom verbs filename>\n")
    sys.exit(0)

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
bloom = open(sys.argv[1])
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

##############################################
### In a tagged sentence, find Bloom verbs ###
##############################################
def bloomVerbsInSentence(s):
    bloomMatches = []
    for i in range(len(s)): # for each word, check if it is a verb
        try:
            tag = s[i]["t"]
        except:
            print ("could not get tag", s, i)
            
        if len(tag) >= 2 and tag[:2] == "vb":
            lemma = s[i]["l"]

            # sometimes there are digits stuck to words, try to remove them
            if not lemma in bloomLex and lemma[0].isdigit():
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
    c["Bloom-list"] = blooms

##############################
### Print result to stdout ###
##############################
print (json.dumps(data))
