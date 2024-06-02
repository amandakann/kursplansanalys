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
                    log("Changed '" + lemma + "' to '" + lemma2 + "'")

                    lemma = lemma2
                    
                    if isSwedish:
                        s[i]["l"] = lemma
                    else:
                        s[i] = lemma

        if lemma in lex:
            exps = lex[lemma]

            for j in range(len(exps)): # for each Bloom verb expression starting with this word

                exp = exps[j][1]
                tokens = exp.split()

                toklen = len(tokens)

                ii = 0
                matchOK = 1
                hasVB = 0
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
                    else: # Not a wildcard token
                        if i + ii < len(s) and tokenMatch(tokens[k], s[i + ii], isSwedish):
                            if isSwedish and s[i + ii]["t"][:2] == "vb" and s[i + ii]["t"][-4:] != ".sfo":
                                hasVB = 1
                            ii += 1
                        else:
                            matchOK = 0
                            break

                if matchOK and (hasVB or not isSwedish):
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
                worseThan = {}
                
                for i in range(len(candidates) - 1):
                    for j in range(i+1, len(candidates)):
                        ifirst = candidates[i][0]
                        ilast = candidates[i][0] + candidates[i][1] - 1

                        jfirst = candidates[j][0]
                        jlast = candidates[j][0] + candidates[j][1] - 1

                        if ifirst > jlast or jfirst > ilast:
                            # no overlap
                            pass
                        else:
                            # i and j overlap
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
                                # log("Longer expr tie-break:\nuse " + str(jlen) + ":" + str(candidates[j]) + "\nskip " + str(ilen) + ":" + str(candidates[i]))
                            # else:
                                # log("Expr lengths same, i=" + str(i) + ", j=" + str(j) + " " + str(ilen) + "=" + str(jlen) + ", " + str(candidates[i]) + " and " + str(candidates[j]))
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
    return bloomMatches

def tokenMatch(tok, src, isSwedish):
    if tok.find("*") >= 0: # Single token that contains wildcard(s)
        r = tok.replace("*", ".*")
        if isSwedish:
            if re.fullmatch(r, src["w"], re.I) or re.fullmatch(r, src["l"], re.I):
                # log("Regex match: " + r + " matched " + str(src))
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
        else: # no WTL
            if tl == src.lower():
                return 1   
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
    
    # för att -> vänsterledet avgör nivån (utom för "använda * för att" och "applicera * för att" då det är högerledet som avgör nivån)
    check = 1
    while check:
        check = 0

        for i in range(1, len(s)):
            if s[i]["w"].lower() == "att" and s[i-1]["w"].lower() == "för":
                useLeft = 1
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
            if s[i]["w"].lower() == "att" and s[i-1]["w"].lower() == "genom":
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

    # som taggat som hp -> skippa hela bisatsen som inleds med “som”
    # (exempel: "Förutsäga vilka muskelrörelser som kontrollerar särskilda kroppsrörelser." - Här ska inte verbet kontrollerar bloomnivåbestämmas.)
    check = 1
    while check:
        check = 0

        for i in range(0, len(s)):
            if s[i]["w"].lower() == "som" and s[i]["t"] == "hp":
                new = []
                for j in range(i): # add everything on the left
                    new.append(s[j])

                sawMad = 0
                for j in range(i+1, len(s)): # add everything after sentence separator, if more than one sentence
                    if s[j]["t"] == "mad" or s[j]["t"] == "mid": # TODO: should use phrase analysis here instead
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

##################################################################################
### For each course in the course list, add Bloom verbs and their Bloom levels ###
##################################################################################
for c in data["Course-list"]:
    ls = c["ILO-list-sv-tagged"]

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
print (json.dumps(data))
