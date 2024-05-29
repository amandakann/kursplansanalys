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
        p = line.find("#")
        if p > 0:
            exp = line[:p].strip()
        else:
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
        p = line.find("#")
        if p > 0:
            exp = line[:p].strip()
        else:
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

################################################
### In a tagged sentence, find Bloom verbs   ###
### This version is not using part-of-speech ###
### but should be updated to do so.          ###
################################################
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
                
                toklen = len(tokens) # length of rule expression
                matchLen = 0         # length of matched text 

                ii = 0
                matchOK = 1
                for k in range(len(tokens)):
                    if tokens[k] == "*": # Whole token is a wildcard
                        tmp = 0
                        starOK = 0
                        while tmp + i + ii < len(s):
                            if tokenMatch(tokens[k + 1], s[i + ii + tmp], False):
                                ii += tmp
                                starOK = 1
                                break
                            tmp += 1
                        if not starOK:
                            matchOK = 0
                            break
                    else: # Not a wildcard token
                        if i + ii < len(s) and tokenMatch(tokens[k], s[i + ii], False):
                            ii += 1
                        else:
                            matchOK = 0
                            break
                if matchOK:
                    matchLen = ii
                    log("exp was a match " + str(exp))
                    if toklen > longestMatch:
                        # when more than one expression with this verb matches,
                        # use the one that has more tokens
                        # (so "göra * analys" has priority over "göra")
                        longestMatch = toklen
                        longestMatchML = matchLen
                        longestIdx = j
                    elif toklen == longestMatch:
                        # when more than one expression matches, use
                        # the one that has the tightest match so:
                        #   "formulera * frågeställningar" matching
                        #   "formulera frågeställningar [där molekylära
                        #    analyser är lämpade]"
                        # has priority over
                        #   "formulera * analyser" matching "formulera
                        #    frågeställningar där molekylära analyser [är
                        #    lämpade]"
                        if matchLen < longestMatchML:
                            longestMatchML = matchLen
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

                    toklen = len(tokens)

                    ii = 0
                    matchOK = 1
                    for k in range(len(tokens)):
                        if tokens[k] == "*": # Whole token is a wildcard
                            tmp = 0
                            starOK = 0
                            while tmp + i + ii < len(s):
                                if tokenMatch(tokens[k + 1], s[i + ii + tmp], True):
                                    ii += tmp
                                    starOK = 1
                                    break
                                tmp += 1
                            if not starOK:
                                matchOK = 0
                                break
                        else: # Not a wildcard token
                            if i + ii < len(s) and tokenMatch(tokens[k], s[i + ii], True):
                                ii += 1
                            else:
                                matchOK = 0
                                break
                            
                    if matchOK:
                        matchLen = ii
                        if toklen > longestMatch:
                            # when more than one expression with this verb matches,
                            # use the one that has more tokens
                            # (so "göra * analys" has priority over "göra")
                            longestMatch = toklen
                            longestMatchML = matchLen
                            longestIdx = j
                        elif toklen == longestMatch:
                            # when more than one expression matches, use
                            # the one that has the tightest match so:
                            #   "formulera * frågeställningar" matching
                            #   "formulera frågeställningar [där molekylära
                            #    analyser är lämpade]"
                            # has priority over
                            #   "formulera * analyser" matching "formulera
                            #    frågeställningar där molekylära analyser [är
                            #    lämpade]"
                            if matchLen < longestMatchML:
                                log("Tighter match tie-break:\nnew:" + str(exps[j]) + "\nold:" + str(exps[longestIdx]) + "\ntext: " + str(s))
                                longestMatchML = matchLen
                                longestIdx = j
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

def tokenMatch(tok, src, haveWTL):
    if tok.find("*") >= 0: # Single token that contains wildcard(s)
        r = tok.replace("*", ".*")
        log("Regex token '" + tok + "' use regex '" + r + "'")
        if haveWTL:
            if re.fullmatch(r, src["w"], re.I) or re.fullmatch(r, src["l"], re.I):
                log("Regex match: " + r + " matched " + str(src))
                return 1
        else: # no WTL
            if re.fullmatch(r, src, re.I):
                log("Regex match: " + r + " matched " + str(src))
                return 1
    else: # token is a regular string
        tl = tok.lower()
        if haveWTL:
            if tl == src["w"].lower() or tl == src["l"].lower():
                return 1
        else: # no WTL
            if tl == src.lower():
                return 1   
    return 0

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
