import sys
import json
import re
import string
import requests

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

#############################################
### Read the Bloom verbs and their levels ###
#############################################
bloomLevel = 0
bloomLex = {}
ambiLex = {}
bloom = open(svFileName)
for line in bloom.readlines():
    if line[0] == "#":
        continue # skip comments

    if line[0:3] == "---": # new Bloom level
        m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
        if len(m) == 1:
            bloomLevel = int(m[0])
    
    if line[0] == "(": # ambiguous verb, not the default level of this verb
        p = line.find("#")
        if p > 0:
            exp = line[:p].strip()
        else:
            exp = line.strip()
        ambiLex[exp] = True
        
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
for v in bloomLex:
    ls = bloomLex[v]
    for i in range(len(ls) - 1):
        for j in range(i+1, len(ls)):
            if ls[i][1] == ls[j][1]:
                log ("WARNING: " + svFileName + " has verb '" + v + "' listed twice, for level " + str(ls[i][2]) + " and level " + str(ls[j][2]) + "\n")
            
bloomLevel = 0
bloomLexEn = {}
ambiLexEn = {}
bloom = open(enFileName)
for line in bloom.readlines():
    if line[0] == "#":
        continue # skip comments

    if line[0:3] == "---": # new Bloom level
        m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
        if len(m) == 1:
            bloomLevel = int(m[0])
    
    if line[0] == "(": # ambiguous verb, not the default level of this verb
        p = line.find("#")
        if p > 0:
            exp = line[:p].strip()
        else:
            exp = line.strip()
        ambiLexEn[exp] = True

        # Quick replace z with s to allow American spelling too. Maybe add better British -> American conversion?
        exp2 = exp.replace("z", "s")
        if exp2 != exp:
            ambiLexEn[exp] = True
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

        # Quick replace z with s to allow American spelling too. Maybe add better British -> American conversion?
        v2 = verb.replace("z", "s")
        exp2 = exp.replace("z", "s")
        if v2 != verb:
            if v2 in bloomLexEn:
                bloomLexEn[v2].append( [v2, exp2, bloomLevel] )
            else:
                bloomLexEn[v2] = [ [v2, exp2, bloomLevel] ]
            
bloom.close()
for v in bloomLexEn:
    ls = bloomLexEn[v]
    for i in range(len(ls) - 1):
        for j in range(i+1, len(ls)):
            if ls[i][1] == ls[j][1]:
                log ("WARNING: " + enFileName + " has verb '" + v + "' listed twice, for level " + str(ls[i][2]) + " and level " + str(ls[j][2]) + "\n")

###############################################################################
### Find Bloom verbs. If isSwedish is false, text is assumed to be English. ###
### Swedish text is assumed to be [{"w":word, "t":tag, "l":lemma}, ...] and ###
### English text is assumed to be ["word1", "word2", ...]                   ###
###############################################################################
def bloomVerbsInSentence(s, lex, aLex, isSwedish):
    if isSwedish:
        sOrg = s
        s = applyGeneralPrinciples(s)
    
    bloomMatches = []

    candidates = []
    
    for i in range(len(s)): # for each word, check if it is a verb
        if isSwedish:
            try:
                lemma = s[i]["l"]
            except:
                lemma = ""
                log("Could not get lemma for: " + str(s[i]))
        else:
            lemma = s[i].lower()

        # sometimes there are digits stuck to words, try to remove them
        if not lemma in lex and len(lemma) and lemma[0].isdigit():
            skip = 0
            while skip < len(lemma) and lemma[skip].isdigit():
                skip += 1
            if skip < len(lemma) - 1:
                lemma2 = lemma[skip:]
                if lemma2 in lex:
                    # log("Changed '" + lemma + "' to '" + lemma2 + "'")

                    lemma = lemma2
                    
                    if isSwedish:
                        s[i]["l"] = lemma
                    else:
                        s[i] = lemma

        if not lemma in lex and len(lemma) and lemma[0].lower() == "x" and lemma[1:] in lex:
            lemma = lemma[1:]
            if isSwedish and s[i]["w"][0].lower() == "x":
                s[i]["w"] = s[i]["w"][1:]
            if isSwedish:
                s[i]["l"] = lemma
            else:
                s[i] = lemma

        if not lemma in lex and len(lemma) and lemma[-1].lower() == "x" and lemma[:-1] in lex:
            lemma = lemma[1:]
            if isSwedish and s[i]["w"][-1].lower() == "x":
                s[i]["w"] = s[i]["w"][:-1]
            if isSwedish:
                s[i]["l"] = lemma
            else:
                s[i] = lemma

        # If the lemma form is not a known verb, try the inflected
        # form. This helps when PoS tagging is wrong, typically when a
        # verb occurs as the first word in a sentence with no subject
        # and is tagged as an adjective instead. This also over
        # generates, because it matches non-verbs when the PoS-tagging
        # is correct.
        if not lemma in lex and isSwedish and s[i]["w"].lower() in lex:
            if i == 0 or s[i]["w"][0].isupper():
                lemma = s[i]["w"].lower()
                s[i]["l"] = lemma
                s[i]["t"] = "vb.inf.akt"

            if i > 0 and (s[i-1]["w"] == "och" or s[i-1]["w"] == "samt"):
                lemma = s[i]["w"].lower()
                s[i]["l"] = lemma
                s[i]["t"] = "vb.inf.akt"
                
            if i > 0 and s[i-1]["t"] == "ab.pos" and s[i-1]["l"] != "mycket"  and s[i-1]["l"] != "vanligt" and  s[i-1]["l"] != "rutinmässigt" and  s[i-1]["l"] != "vardagligt":
                lemma = s[i]["w"].lower()
                s[i]["l"] = lemma
                s[i]["t"] = "vb.inf.akt"

        # Try suggestions from the spell check
        if isSwedish and spelling and not lemma in lex:
            found = 0
            if lemma.lower() in spellings:
                for v in spellings[lemma.lower()]:
                    if v in lex:
                        lemma = v
                        s[i]["l"] = lemma
                        s[i]["t"] = "vb.inf.akt"
                        found = 1
                        break
            if not found and s[i]["w"].lower() in spellings:
                for v in spellings[s[i]["w"].lower()]:
                    if v in lex:
                        lemma = v
                        s[i]["l"] = lemma
                        s[i]["t"] = "vb.inf.akt"
                        found = 1
                        break
        
        if lemma in lex:
            exps = lex[lemma]

            for j in range(len(exps)): # for each Bloom verb expression starting with this word

                exp = exps[j][1]
                tokens = exp.split()

                toklen = len(tokens)

                ii = 0
                matchOK = 1
                hasVB = 0
                hasUpper = 0
                for k in range(len(tokens)):
                    if tokens[k] == "*": # Whole token is a wildcard
                        tmp = 0
                        starOK = 0
                        while tmp + i + ii < len(s):
                            if tokenMatch(tokens[k + 1], s[i + ii + tmp], isSwedish):
                                ii += tmp
                                starOK = 1
                                break
                            tmp += 1
                        if not starOK:
                            matchOK = 0
                            break
                    elif tokens[k].find("<") >= 0:
                        # token refers to part-of-speech or phrase tag
                        if tokenMatchTags(tokens[k], s, i + ii, isSwedish, False):
                            hasUpper = 1
                            ii += 1
                        else:
                            matchOK = 0
                            break
                    else: # Not a wildcard token
                        if i + ii < len(s) and tokenMatch(tokens[k], s[i + ii], isSwedish):
                            if isSwedish and s[i + ii]["t"][:2] == "vb" and s[i + ii]["t"][-4:] != ".sfo":
                                hasVB = 1
                            if isSwedish and s[i + ii]["w"][0].isupper():
                                hasUpper = 1
                            ii += 1
                        else:
                            matchOK = 0
                            break
                
                if matchOK and (hasVB or not isSwedish or i == 0 or hasUpper):
                    log("Found match for " + str(exps[j]))
                    candidates.append([i, ii, exps[j]])

    while len(candidates):
        # check for overlapping matches and choose the best one, so a
        # sentence with "jämföra och värdera" only gives one match for
        # 'jämföra och värdera' and not extra matches for 'jämföra'
        # and 'värdera'.

        # Priority is given to long expressions ('jämföra * i relation till' is preferred over 'jämföra')
        
        # For length of expression, '*' tokens are slightly penalized
        # (counted as -0.1), so 'bevisa' is shorter than 'bevisa *
        # satser' which is in turn shorter than 'bevisa att'

        # Priority is given to short matches ('ge * kritik' is
        # preferred over 'ge * presentation' in the sentence 'ge
        # kritik av någons presentation')

        # Unambiguous expressions are preferred over ambiguous expressions

        # Overlaps are allowed for 'beskriva * begrepp' and 'jämföra'
        # in texts with 'och' (or ',') between the verbs, for example
        # 'beskriva och jämföra begrepp', unless the 'och' is a
        # non-wildcard token in the expression (so 'jämföra och
        # värdera' would remove 'jämföra' matches)

        if len(candidates) == 1:
            bloomMatches.append( candidates[0][2] ) # if only one match, add that matching expression
            candidates = []
        else:
            # check if any expression is free of overlap
            overlaps = {}
            noOverlap = {}
            for i in range(len(candidates) - 1):
                iOK = 1
                for j in range(i+1, len(candidates)):
                    ifirst = candidates[i][0]
                    ilast = candidates[i][0] + candidates[i][1] - 1

                    jfirst = candidates[j][0]
                    jlast = candidates[j][0] + candidates[j][1] - 1

                    if ifirst > jlast or jfirst > ilast:
                        # no overlap
                        pass
                    else:

                        #   check if the overlap is of the kind:
                        #          "verb1, verb2, och verb3 object"
                        #          with expressions "verb1 * object"
                        #          overlapping "verb2" or "verb3"
                        overlapIsOK = 0
                        if ifirst < jfirst:
                            overlapIsOK = checkOverlapsForOch(candidates[i], candidates[j], s, isSwedish)
                        elif jfirst < ifirst:
                            overlapIsOK = checkOverlapsForOch(candidates[j], candidates[i], s, isSwedish)
                        if not overlapIsOK:
                            # log(".......... Overlap " + str(i) + " and " + str(j) + ", " + str(candidates[i]) + " and " + str(candidates[j]))
                            overlaps[i] = 1
                            overlaps[j] = 1
                            iOK = 0
                if iOK and not i in overlaps:
                    noOverlap[i] = 1

            last = len(candidates) - 1
            if not last in overlaps:
                 noOverlap[last] = 1

            # log("noOverlap: " + str(noOverlap))
            # log("overlaps: " + str(overlaps))
            
            somethingChanged = 0
            for i in noOverlap:
                somethingChanged = 1
                bloomMatches.append( candidates[i][2] )
            
            if somethingChanged:
                newCandidates = []
                for i in range(len(candidates)):
                    if not i in noOverlap:
                        newCandidates.append(candidates[i])
                candidates = newCandidates
                    
            if len(candidates) > 1: # we have overlapping matches
                # log("More than one candidate: " + str(candidates))
                worseThan = {}
                
                for i in range(len(candidates) - 1):
                    for j in range(i+1, len(candidates)):
                        ifirst = candidates[i][0]
                        ilast = candidates[i][0] + candidates[i][1] - 1

                        jfirst = candidates[j][0]
                        jlast = candidates[j][0] + candidates[j][1] - 1

                        if ifirst > jlast or jfirst > ilast:
                            # no overlap
                            overlapIsOK = 1
                            pass
                        else:
                            # i and j overlap
                            if ifirst < jfirst:
                                overlapIsOK = checkOverlapsForOch(candidates[i], candidates[j], s, isSwedish)
                            elif jfirst < ifirst:
                                overlapIsOK = checkOverlapsForOch(candidates[j], candidates[i], s, isSwedish)
                            else:
                                overlapIsOK = 0
                                
                        if not overlapIsOK:
                            use = -1

                            # check longest expression
                            ilen = 0
                            for t in candidates[i][2][1].split():
                                if t == "*":
                                    ilen -= 0.1
                                else:
                                    ilen += 1
                            jlen = 0
                            for t in candidates[j][2][1].split():
                                if t == "*":
                                    jlen -= 0.1
                                else:
                                    jlen += 1

                            if ilen > jlen:
                                use = i
                                # log("Longer expr tie-break:\nuse " + str(ilen) + ":" + str(candidates[i]) + "\nskip " + str(jlen) + ":" + str(candidates[j]))
                            elif jlen > ilen:
                                use = j
                            #     log("Longer expr tie-break:\nuse " + str(jlen) + ":" + str(candidates[j]) + "\nskip " + str(ilen) + ":" + str(candidates[i]))
                            # else:
                            #      log("Expr lengths same, i=" + str(i) + ", j=" + str(j) + " " + str(ilen) + "=" + str(jlen) + ", " + str(candidates[i]) + " and " + str(candidates[j]))
                            if use < 0:
                                # check shortest match
                                ilen = candidates[i][1]
                                jlen = candidates[j][1]

                                if ilen < jlen:
                                    use = i
                                    # log("Tighter match tie-break:\nuse:" + str(candidates[i]) + "\nskip:" + str(candidates[j]) + "\ntext: " + str(s))
                                elif jlen < ilen:
                                    use = j
                                    # log("Tighter match tie-break:\nuse:" + str(candidates[j]) + "\nskip:" + str(candidates[i]) + "\ntext: " + str(s))

                            if use < 0:
                                iAmbi = 0
                                jAmbi = 0
                                if candidates[i][1] in aLex:
                                    iAmbi = 1
                                if candidates[j][1] in aLex:
                                    jAmbi = 1
                                if iAmbi and not jAmbi:
                                    use = j
                                elif jAmbi and not iAmbi:
                                    use = i

                            if use < 0: ### Default to first match?
                                use = i

                            # remove the not good match, go back to the start of the loop to check for more overlaps etc.
                            if use == i:
                                if j in worseThan:
                                    worseThan[j][i] = True
                                else:
                                    worseThan[j] = {}
                                    worseThan[j][i] = True
                                    
                                # candidates.pop(j) # We should check if what we overlap with will be removed by something else first
                            else:
                                if i in worseThan:
                                    worseThan[i][j] = True
                                else:
                                    worseThan[i] = {}
                                    worseThan[i][j] = True
                                
                                # candidates.pop(i) # We should check if what we overlap with will be removed by something else first
                
                # look in 'worseThan' to see which matches should be removed
                toRemove = []
                checkAgain = True
                while checkAgain:
                    checkAgain = False
                    for idx in worseThan:
                        if worseThan[idx]: # we need to see at least one winner
                            allRemain = True 
                            for winner in worseThan[idx]:
                                if winner in worseThan: # this candidate may be removed by something else
                                    allRemain = False
                                    break
                            if allRemain:
                                checkAgain = True
                                toRemove.append(idx)

                                # log("candidate " + str(idx) + " " + str(candidates[idx]) + " should definitely be removed: " + str(worseThan))
                            
                                for idx2 in worseThan:
                                    if idx in worseThan[idx2]:
                                        del worseThan[idx2][idx]
                                again = 1
                                while again:
                                    again = 0
                                    for idx2 in worseThan:
                                        if not worseThan[idx2]:
                                            del worseThan[idx2]
                                            again = 1
                                            break
                                
                                del worseThan[idx]
                                break
                        
                toRemove.sort(reverse=True)
                for idx in toRemove:
                    # log("Popping candidate " + str(idx) + " " + str(candidates[idx]))
                    candidates.pop(idx)
                # if len(toRemove):
                #     log("Remaining: " + str(candidates))
                #     log(str(s).replace("{", "\n{"))

    # if len(bloomMatches) > 0:
    #     log("-"*40)
    #     log("Final result: " + str(bloomMatches))
    #     log("in text: " + str(s))
    #     log("-"*40)

    if zero:
        if isSwedish and len(bloomMatches) == 0:
            vbLex = {}
            removedLex = {}
        
            tmp = ""

            hasVbAfterPrinciples = 0
            hasVbBeforePrinciples = 0
            for i in range(len(s)):
                if s[i]["t"][:2] == "vb":
                    hasVbAfterPrinciples = 1
                    vbLex[s[i]["l"]] = 1
            for i in range(len(sOrg)):
                if sOrg[i]["t"][:2] == "vb":
                    hasVbBeforePrinciples = 1
                    if not sOrg[i]["l"] in vbLex:
                        removedLex[sOrg[i]["l"]] = 1
                # tmp = tmp + sOrg[i]["w"]  + "(" + sOrg[i]["t"][:2] + ")" + " " 
                tmp = tmp + sOrg[i]["w"]  + " "
            for v in vbLex:
                if not v in zeroBloomGoalVerbs:
                    zeroBloomGoalVerbs[v] = 0
                zeroBloomGoalVerbs[v] += 1

            for v in removedLex:
                if not v in zeroBloomGoalVerbsPr:
                    zeroBloomGoalVerbsPr[v] = 0
                zeroBloomGoalVerbsPr[v] += 1
            zeroBloomGoalExamples.append([hasVbAfterPrinciples, tmp.strip()])
            if tmp.strip() == "":
                log("Empty sentence?: '" + str(s) + "'")
    return bloomMatches

zeroBloomGoalVerbs = {}
zeroBloomGoalVerbsPr = {}
zeroBloomGoalExamples = []

def printZeroBloomInfo():
    f = open("zeroBloomVerbGoals.txt", "w")

    f.write("vvvv Verb in goals with 0 Bloom verbs\n")
    ls = []
    for v in zeroBloomGoalVerbs:
        ls.append([zeroBloomGoalVerbs[v], v])
    ls.sort(reverse=True)
    for p in ls:
        f.write("{0: >5} {1:}\n".format(p[0], p[1]))

    f.write("vvvv Verb removed by princples in goals with 0 Bloom verbs\n")
    ls = []
    for v in zeroBloomGoalVerbsPr:
        ls.append([zeroBloomGoalVerbsPr[v], v])
    ls.sort(reverse=True)
    for p in ls:
        f.write("{0: >5} {1:}\n".format(p[0], p[1]))

    f.write("vvvv Example goals with 0 Bloom verbs but with other verbs\n")
    zeroBloomGoalExamples.sort()
    for ex in zeroBloomGoalExamples:
        if ex[0]:
            f.write(ex[1])
            f.write("\n\n")
    f.write("vvvv Example goals with 0 Bloom verbs and no other verbs\n")
    for ex in zeroBloomGoalExamples:
        if not ex[0]:
            f.write(ex[1])
            f.write("\n\n")
    f.close()

def tokenMatch(tok, src, isSwedish):
    if tok.find("*") >= 0: # Single token that contains wildcard(s)
        r = tok.replace("*", ".*")
        if isSwedish:
            if re.fullmatch(r, src["w"], re.I) or re.fullmatch(r, src["l"], re.I):
                # log("Regex match: " + r + " matched " + str(src))
                return 1
            if spelling:
                if src["w"] in spellings:
                    for v in spellings[src["w"]]:
                        if re.fullmatch(r, v, re.I):
                            return 1
                if src["l"] in spellings:
                    for v in spellings[src["l"]]:
                        if re.fullmatch(r, v, re.I):
                            return 1
        else: # no WTL
            if re.fullmatch(r, src, re.I):
                # log("Regex match: " + r + " matched " + str(src))
                return 1
    else: # token is a regular string
        tl = tok.lower()
        if isSwedish:
            if tl == src["w"].lower() or tl == src["l"].lower():
                return 1
            if spelling:
                if src["w"] in spellings:
                    for v in spellings[src["w"]]:
                        if tl == v:
                            return 1
                if src["l"] in spellings:
                    for v in spellings[src["l"]]:
                        if tl == v:
                            return 1
        else: # no WTL
            if tl == src.lower():
                return 1   
    return 0


def tokenMatchTags(tok, src, sIdx, isSwedish, everyWordCanMatch):
    if sIdx < len(src):
        allTokensOK = True
        
        if isSwedish:
            # remove < and >, split on ".", so <NP.sin.def>
            # becomes [NP, sin, def]
            elements = tok[1:-1].split(".") 

            for e in range(len(elements)):
                el = elements[e]

                noPhraseMatch = True
                
                phrases = src[sIdx]["p"].split("|")
                phrases.reverse() # order outer tag first in list, reverse of written order
                
                for pIdx in range(len(phrases)):
                    phraseTag = phrases[pIdx]
                    if phraseTag[:len(el)] == el:
                        # rest of match should be inside this phrase
                        noPhraseMatch = False

                        # collect other things that need to match inside this phrase
                        subElements = []
                        for e2 in range(e+1, len(elements)):
                            subElements.append(elements[e2])

                        if len(subElements):

                            # extract the phrase from the sentence
                            matchPhrase = [src[sIdx]]
                            for sIdx2 in range(sIdx + 1, len(src)):
                                phrases2 = src[sIdx2]["p"].split("|")
                                phrases2.reverse()
                                if pIdx < len(phrases2): # there is a phrase on the same depth we are looking
                                    if phrases2[pIdx][:len(el)] == phrases[pIdx][:len(el)] and not phrases2[pIdx][-1] == "B": # if we have the same type of phrase but not the beginning of a new phrase
                                        matchPhrase.append(src[sIdx2])
                                    else:
                                        break
                                else:
                                    break

                            # make a copy of the match, but strip out the outer phrases
                            copy = []
                            for wtl in matchPhrase:
                                newWtl = {"w":wtl["w"], "t":wtl["t"], "l":wtl["l"], "c":wtl["c"]}
                                newWtl["p"] = wtl["p"][pIdx:]
                                copy.append(newWtl)
                            newTok = "<" + ".".join(subElements) + ">"
                            
                            return tokenMatchTags(newTok, copy, 0, isSwedish, True)
                        else: # no subElements to match, we are done
                            return 1
                    else: # not a matching phrase tag on this level
                        pass # just trying next phrase level
                
                # if not a phrase tag match, check clauses and pos-tags instead

                # try caluses
                noClauseMatch = True
                
                clauses = src[sIdx]["c"].split("|")
                clauses.reverse() # order outer tag first in list, reverse of written order
                
                for cIdx in range(len(clauses)):
                    clTag = clauses[cIdx]
                    if clauses[:len(el)] == el:
                        # rest of match should be inside this clause
                        noClauseMatch = False

                        # collect other things that need to match inside this phrase
                        subElements = []
                        for e2 in range(e+1, len(elements)):
                            subElements.append(elements[e2])

                        if len(subElements):
                            # extract the clause from the sentence
                            matchClause = [src[sIdx]]
                            for sIdx2 in range(sIdx + 1, len(src)):
                                clauses2 = src[sIdx2]["c"].split("|")
                                clauses2.reverse()
                                if cIdx < len(clauses2) and clauses2[cIdx][:len(el)] == clauses[cIdx][:len(el)] and not clauses2[cIdx][-1] == "B": # if we have the clause continues
                                    matchPhrase.append(src[sIdx2])
                                else:
                                    break

                            # make a copy of the match, but strip out the outer phrases
                            copy = []
                            for wtl in matchPhrase:
                                newWtl = {"w":wtl["w"], "t":wtl["t"], "l":wtl["l"], "p":wtl["p"]}
                                newWtl["c"] = wtl["c"][cIdx:]
                                copy.append(newWtl)
                            newTok = "<" + ".".join(subElements) + ">"
                            
                            return tokenMatchTags(newTok, copy, 0, isSwedish, True)
                        else: # no subElements to match, we are done
                            return 1
                    else: # not a match on this clause level
                        pass # try next level
                
                # if not a phrase and not a clause, check pos-tags
                last = sIdx + 1
                if everyWordCanMatch:
                    last = len(src)

                thisIdxMatched = False
                for idx in range(sIdx, last):
                    pos = src[idx]["t"].split(".")
                    for pIdx in range(len(pos)):
                        if pos[pIdx] == el:
                            thisIdxMatched = True

                if thisIdxMatched:
                    pass # go on with next element in loop
                else:
                    return 0
            if allTokensOK:
                return 1 
        else: # not Swedish, so no WTL etc.
            return 0

    return 0

def checkOverlapsForOch(exp1, exp2, s, isSwedish):
    # log("Check overlap for 'och', " + str(exp1) + " and " + str(exp2) + " in " + str(s[exp1[0] : exp1[0]+exp1[1]]).replace("{", "\n{") + "\n(" + str(s[exp2[0] : exp2[0]+exp2[1]]).replace("{", "\n{") + ")")
    
    foundOch = 0
    for i in range(exp1[0], exp1[0] + exp1[1]):
        if isSwedish:
            if s[i]["w"] == "och" or s[i]["w"] == ",":
                # log("Check overlap for 'och', found 'och' at pos " + str(i))
                foundOch = 1
                break
        else:
            if s[i].lower() == "and" or s[i] == ",":
                # log("Check overlap for 'och', found 'och' at pos " + str(i))
                foundOch = 1
                break
    if foundOch:
        for t in exp1[2][1].split():
            if isSwedish:                                      
                if t == "och" or t == ",":
                    # log("Check overlap for 'och', " + str(exp1) + " has 'och' as token.")
                    return 0
            else:
                if t == "and" or t == ",":
                    # log("Check overlap for 'och', " + str(exp1) + " has 'och' as token.")
                    return 0
        return 1
    return 0


def applyGeneralPrinciples(s):
    # Generella principer
    
    # som taggat som hp -> skippa hela bisatsen som inleds med “som”
    # (exempel: "Förutsäga vilka muskelrörelser som kontrollerar särskilda kroppsrörelser." - Här ska inte verbet kontrollerar bloomnivåbestämmas.)
    check = 1
    while check:
        check = 0

        for i in range(0, len(s)):
            if s[i]["w"].lower() == "som" and (s[i]["t"] == "hp" or (i+3 < len(s) and (s[i+1]["w"] == "kan" or s[i+2]["w"] == "kan" or s[i+3]["w"] == "kan"))):
                new = []
                for j in range(i): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+1, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad" or (j > i+1 and s[j]["t"] == "mid") or (j > i+1 and s[j]["c"] == "CLB"): # new sentence or new clause
                        sawMad = 1
                    if sawMad:
                        new.append(s[j])
                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'som <hp>'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break
    
    # för att -> vänsterledet avgör nivån (utom för "använda * för att" och "applicera * för att" då det är högerledet som avgör nivån)
    check = 1
    while check:
        check = 0

        for i in range(1, len(s)):            
            if s[i]["w"].lower() == "att" and s[i-1]["w"].lower() == "för":
                useLeft = 1
                if not (i + 1 < len(s) and s[i+1]["w"].lower() == "få"):
                    # never 'use right' even if we find "använda" or "applicera" if we have "för att få", example:
                    # "Använda innovativ teknik för nya system och förbättring av gamla system för att få bättre funktion och uppfyller kraven i samhället ."
                    j = i - 2
                    while j >= 0:
                        if s[j]["l"] == "applicera" or s[j]["l"] == "använda" or s[j]["w"].lower() == "använda" or s[j]["w"].lower() == "applicera":
                            useLeft = 0
                            break
                        if s[j]["t"] == "mad":
                            break
                        j -= 1
                if useLeft:
                    new = []
                    for j in range(i-1): # add everything on the left
                        new.append(s[j])

                    sawMad = 0
                    for j in range(i+1, len(s)): # add everything after sentence separator, if more than one sentence
                        if s[j]["t"] == "mad":
                            sawMad = 1
                        if sawMad:
                            new.append(s[j])
                    if len(s) != len(new):

                        ss = ""
                        for t in s:
                            ss += " " + t["w"]
                            nn = ""
                        for t in new:
                            nn += " " + t["w"]
                        log("....... Principle 'för att'\n" + ss + "\nuse only:" + nn)
                        
                        s = new
                        check = 1
                        break
                else: # use right side
                    new = []
                    sawMad = 0
                    for j in range(i-1, -1, -1): # check for sentence delimiter on the left
                        if s[j]["t"] == "mad":
                            sawMad = j
                            break

                    if sawMad > 0:
                        for j in range(sawMad+1): # add anything on the left that is in another sentence
                            new.append(s[j])

                    for j in range(i+1, len(s)): # add everything on the right
                        new.append(s[j])

                    if len(s) != len(new):

                        ss = ""
                        for t in s:
                            ss += " " + t["w"]
                            nn = ""
                        for t in new:
                            nn += " " + t["w"]
                        log("....... Principle 'för att'\n" + ss + "\nuse only:" + nn)

                        s = new
                        check = 1
                        break
                    
    # i/med syfte att -> vänsterledet avgör nivån
    check = 1
    while check:
        check = 0

        for i in range(0, len(s) - 2):
            if (s[i]["w"].lower() == "i" or s[i]["w"].lower() == "med") and (s[i+1]["l"] == "syfte" or s[i+1]["w"].lower() == "syfte") and s[i+2]["w"].lower() == "att":
                new = []
                for j in range(i): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+1, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad":
                        sawMad = 1
                    if sawMad:
                        new.append(s[j])
                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'i syfte att'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break
    
    # genom att -> högerledet avgör nivån
    check = 1
    while check:
        check = 0

        for i in range(1, len(s)):
            if s[i]["w"].lower() == "att" and s[i-1]["w"].lower() == "genom" and (i < 2 or s[i-2]["w"] != "eller"):
                # use right side
                new = []
                sawMad = 0
                for j in range(i-1, -1, -1): # check for sentence delimiter on the left
                    if s[j]["t"] == "mad":
                        sawMad = j
                        break

                if sawMad > 0:
                    for j in range(sawMad+1): # add anything on the left that is in another sentence
                        new.append(s[j])

                for j in range(i+1, len(s)): # add everything on the right
                    new.append(s[j])

                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'genom att'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break

    # utveckla elever.*/studenter.* förmåga/egenskap.* att -> det som kommer efter borde avgöra nivån
    check = 1
    while check:
        check = 0

        utv = -1
        haveStu = 0
        for i in range(0, len(s) - 1):
            if s[i]["l"] == "utveckla" or s[i]["w"].lower() == "utveckla":
                utv = i
            elif utv >= 0 and (s[i]["l"] == "student" or s[i]["l"] == "elev"):
                haveStu = 1
            elif utv >= 0 and haveStu and (s[i]["l"] == "förmåga" or s[i]["l"] == "egenskap") and s[i+1]["l"] == "att":
                # use right side
                
                new = []
                sawMad = 0
                for j in range(utv-1, -1, -1): # check for sentence delimiter on the left
                    if s[j]["t"] == "mad":
                        sawMad = j
                        break

                if sawMad > 0:
                    for j in range(sawMad+1): # add anything on the left that is in another sentence
                        new.append(s[j])

                for j in range(i+2, len(s)): # add everything on the right
                    new.append(s[j])

                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'utveckla elevens förmåga att'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break

    # Skippa att bloomnivågranska verb som förekommer efter “med att”, “sätt att” och “hur”, se exempel nedan:
    # ex: "Reflektera över svårigheter med att modellera, simulera och optimera under de olika stegen i en utvecklingsprocess gällande produktion och logistik ."
    # ex: "Diskutera och problematisera olika sätt att planera, organisera och utvärdera undervisning inom ett eller flera av ämnena teknik, matematik, fysik och kemi ."
    # ex: "Förklara hur företag kan organisera och leda utveckling av nya värderbjudanden, både vad gäller varu- och tjänsteinnovationer"
    # ex: "Identifiera hur det är möjligt att välja och optimera parametrar FÖR ATT erhålla en hållbar metallurgisk processkedja ."
    check = 1
    while check:
        check = 0

        for i in range(0, len(s) - 1):
            if s[i]["w"].lower() == "hur" or ((s[i]["w"].lower() == "med" or s[i]["w"].lower() == "sätt") and s[i+1]["w"].lower() == "att"):
                new = []
                for j in range(i): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+1, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad":
                        sawMad = 1
                    if sawMad:
                        new.append(s[j])
                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'med att, sätt att, hur'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break

    # Ytterligare huvudvärksframkallande exempel:
    # "föreslå överförbara resultat FÖR ATT förbättra förvaltningen och effektiv användning av energi, GENOM ATT utveckla nya idéer ."

    
    # "syftet med ... är att ... <skip>",
    check = 1
    while check:
        check = 0

        haveSyfte = -1
        for i in range(0, len(s) - 2):
            if s[i]["l"].lower() == "syfte" and s[i+1]["w"].lower() == "med":
                haveSyfte = i
            elif s[i]["t"] == "mad":
                haveSyfte = -1
            elif haveSyfte >= 0 and s[i]["w"].lower() == "är"  and s[i+1]["w"].lower() == "att":
                
                new = []
                for j in range(haveSyfte): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+2, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad":
                        sawMad = 1
                    if sawMad:
                        new.append(s[j])
                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'syfte med ... är att'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break

    # "utan att ... "
    check = 1
    while check:
        check = 0

        for i in range(0, len(s) - 2):
            if s[i]["w"].lower() == "utan" and s[i+1]["w"].lower() == "att":
                new = []
                for j in range(i): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+2, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad":
                        sawMad = 1
                    if sawMad:
                        new.append(s[j])
                if len(s) != len(new):

                    ss = ""
                    for t in s:
                        ss += " " + t["w"]
                        nn = ""
                    for t in new:
                        nn += " " + t["w"]
                    log("....... Principle 'utan att'\n" + ss + "\nuse only:" + nn)

                    s = new
                    check = 1
                    break
    
    return s

    
##########################################################################################
### Find all unique word forms, send them to Stava (spell check) and store suggestions ###
##########################################################################################
uniq = {}
spellings = {}
if spelling:
    for c in data["Course-list"]:
        if "ILO-list-sv-tagged" in c:
            for s in c["ILO-list-sv-tagged"]:
                for wtl in s:
                    uniq[wtl["w"].lower()] = 1
                    uniq[wtl["l"].lower()] = 1
    text = ""
    for w in uniq:
        if w != ",":
            text += w
            text += "\n"
    
    url = "https://skrutten.csc.kth.se/granskaapi/spell.php"
    try:
        x = requests.post(url, data = {"coding":"text", "words":text})
        if x.ok and x.text.find("<div") < 0:
            lines = x.text.split("\n")
            for l in lines:
                p = l.find(":")
        
                if p > 0:
                    word = l[:p].strip()
                    suggs = l[p+1:].strip().split(",")
                else:
                    word = l.strip()
                    suggs = []

                variants = []
                for ss in suggs:
                    s = ss.strip()
                    if len(s) and s != word:
                        variants.append(s)
                        if s.find(" ") > 0: # Sometimes words are corrected to multi-words, and we accept matches on either one of them (we should perhaps redo the PoS-tagging of the sentence instead)
                            ls = s.split(" ")
                            for sub in ls:
                                if len(sub.strip()) and sub.strip() != word:
                                    variants.append(sub.strip())
                if len(variants):
                    spellings[word] = variants
    except Exception as e:
        log("Error when using Stava: " + str(e))

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
        m = bloomVerbsInSentence(s, bloomLex, ambiLex, True)
        blooms.append(m)
    c["Bloom-list-sv"] = blooms

    ls = c["ILO-list-en"]

    blooms = []
    for s in ls:
        tmp = re.findall("\w+", s)
        m = bloomVerbsInSentence(tmp, bloomLexEn, ambiLexEn, False)
        blooms.append(m)
    c["Bloom-list-en"] = blooms
    
##############################
### Print result to stdout ###
##############################
if zero:
    printZeroBloomInfo()

print (json.dumps(data))

