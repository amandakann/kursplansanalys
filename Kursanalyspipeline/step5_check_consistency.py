import sys
import string
import json
import re

VERBS_BEFORE_MORE_THAN=15 # How many verbs to show before lumping the rest as "more than X"
VERBS_BEFORE_WARNING=50   # How many Bloom-classified verbs can a course have before warning for "very many verbs"?

##############################
### check system arguments ###
##############################

types = {"vidareutbildning":1, "uppdragsutbildning":1, "förberedande utbildning":1, "grundutbildning":1, "forskarutbildning":1}
checks = {"en":1, "level":1, "bloom":1, "scb":1, "cred":1, "ilo":1, "nonBloom":1, "type":1}
prints = {"courses":1, "errorList":1, "perSCB":0, "perType":0, "perLevel":0, "ambig":1, "nonBloom":1}
scbs = {"other":1}
levels = {"":1, "A1E":1, "A1F":1, "A1N":1, "A2E":1, "AXX":1, "G1F":1, "G1N":1, "G2E":1, "G2F":1, "GXX":1}

configFile = "step5.config"
unknown = 0

moreInputs = []

defaultSv = "data/bloom_revised_sv.txt"
defaultEn = "data/bloom_revised_en.txt"
stoplistFile = "data/stoplist.txt"

bloomFile = defaultSv
bloomFileEn = defaultEn
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-b" and i+1 < len(sys.argv):
        bloomFile = sys.argv[i+1]
    elif sys.argv[i] == "-be" and i+1 < len(sys.argv):
        bloomFileEn = sys.argv[i+1]
    elif sys.argv[i] == "-c" and i+1 < len(sys.argv):
        configFile = sys.argv[i+1]
    elif sys.argv[i] == "-inp" and i+1 < len(sys.argv):
        moreInputs.extend(sys.argv[i+1].split())
    elif sys.argv[i] == "-sl" and i + 1 < len(sys.argv):
        stoplistFile = sys.argv[i+1]
    else:
        if sys.argv[i-1] != "-b" and sys.argv[i-1] != "-c" and sys.argv[i-1] != "-inp" and sys.argv[i-1] != "-sl":
            unknown = 1

if unknown:
    print ("\nCheck courses for problems or ambiguities, collect stats. Reads JSON from stdin.")
    print ("usage options:")
    print ("     -b <filename>                 File with Bloom verb data for Swedish")
    print ("     -be <filename>                File with Bloom verb data for English")
    print ("     -c <filename>                 Config file")
    print ("     -inp \"<filename1> ... \"       More input files")
    print ()
    print ("Check the config file (\"" + configFile + "\") to see possible options.")
    print ("If no Bloom files are specified, \"" + defaultSv + "\" and \"" + defaultEn + "\" will be used.")
    print ()
    sys.exit(0)


######################################################
### Open the config file and read all the settings ###
######################################################
try:
    cf = open(configFile)
except:
    print ("Could not open config file (" + configFile + "), using default settings.")
    cf = 0

if cf:
    firstType = 1
    firstLevel = 1
    firstSCB = 1
    for rawline in cf.readlines():
        p = rawline.find("#")
        if p >= 0:
            line = rawline[:p].strip()
        else:
            line = rawline.strip()

        if len(line):
            val = -1
            if line[0] == "+":
                val = 1
            elif line[0] == "-":
                val = 0

            if val >= 0:
                tag = line[1:]

                if tag == "printEachCourse":
                    prints["courses"] = val
                elif tag == "printErrorTypeLists":
                    prints["errorList"] = val
                elif tag == "printPerSCB":
                    prints["perSCB"] = val
                elif tag == "printPerType":
                    prints["perType"] = val
                elif tag == "printPerLevel":
                    prints["perLevel"] = val
                elif tag == "printAmbiguousVerbs":
                    prints["ambig"] = val
                elif tag == "printNonBloom":
                    prints["nonBloom"] = val

                elif tag == "checkEn":
                    checks["en"] = val
                elif tag == "checkIlo":
                    checks["ilo"] = val
                elif tag == "checkBloom":
                    checks["bloom"] = val
                elif tag == "checkLevel":
                    checks["level"] = val
                elif tag == "checkSCB":
                    checks["scb"] = val
                elif tag == "checkVerbs":
                    checks["nonBloom"] = val
                elif tag == "checkCredits":
                    checks["cred"] = val
                    
                elif tag[:4] == "type":
                    if val == 1 and firstType:
                        firstType = 0
                        for t in types:
                            types[t] = 0
                        
                    if tag == "typeF":
                        types["forskarutbildning"] = val
                    elif tag == "typeV":
                        types["vidareutbildning"] = val
                    elif tag == "typeU":
                        types["uppdragsutbildning"] = val
                    elif tag == "typeFB":
                        types["förberedande utbildning"] = val
                    elif tag == "typeG":
                        types["grundutbildning"] = val
                    else:
                        print("Unknown type in config file: ", line)
                        
                elif tag[:5] == "level":
                    if val == 1 and firstLevel:
                        firstLevel = 0
                        for l in levels:
                            levels[l] = 0
                        
                    if tag == "levelNone":
                        levels[""] = val
                    elif tag == "levelA1E":
                        levels["A1E"] = val
                    elif tag == "levelA1F":
                        levels["A1F"] = val
                    elif tag == "levelA1N":
                        levels["A1N"] = val
                    elif tag == "levelA2E":
                        levels["A2E"] = val
                    elif tag == "levelAXX":
                        levels["AXX"] = val
                    elif tag == "levelG1F":
                        levels["G1F"] = val
                    elif tag == "levelG1N":
                        levels["G1N"] = val
                    elif tag == "levelG2E":
                        levels["G2E"] = val
                    elif tag == "levelG2F":
                        levels["G2F"] = val
                    elif tag == "levelGXX":
                        levels["GXX"] = val
                    elif tag == "levelA":
                        for l in levels:
                            if len(l) and l[0] == "A":
                                levels[l] = val
                    elif tag == "levelG":
                        for l in levels:
                            if len(l) and l[0] == "G":
                                levels[l] = val
                    elif tag == "levelE":
                        for l in levels:
                            if len(l) and l[-1] == "E":
                                levels[l] = val
                    elif tag == "levelXX":
                        levels["GXX"] = val
                        levels["AXX"] = val
                    else:
                        print("Unknown level tag in config file: ", line)
                elif tag[:3] == "scb":
                    scbID = tag[3:]
                    scbs[scbID] = val
                    if firstSCB:
                        firstSCB = 0
                        scbs["other"] = 1 - val
                else:
                    print ("Unknown option in config file: ", line)
            else:
                print ("Unknown option in config file: ", line)

if checks["bloom"]:
    if bloomFile == "":
        print("WARNING: No file with Bloom verb classifications, turning off Bloom verb checking.")
        checks["bloom"] = 0
    else:
        try:
            f = open(bloomFile)
            f.read()
            f.close()
        except:
            print("WARNING: Could not read Bloom verb data (" + bloomFile + "), turning off Bloom verb checking.")
            checks["bloom"] = 0
        try:
            f = open(bloomFileEn)
            f.read()
            f.close()
        except:
            print("WARNING: Could not read Bloom verb data (" + bloomFileEn + "), turning off Bloom verb checking.")

print ()

###########################################################################
### Check Bloom verbs, print info on courses with ambiguous Bloom verbs ###
###########################################################################
if checks["bloom"]:
    ambig = {}
    ambigEn = {}
    bloomLex = {}
    bloomLexEn = {}
    
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
                p = line.find("#")
                if p > 0:
                    exp = line[:p].strip()
                else:
                    exp = line.strip()
                    
                if v in ambig:
                    ambig[v].append(bloomLevel)
                else:
                    ambig[v] = [bloomLevel]
                    
            if line[0].islower() or line[0].isupper():
                p = line.find("#")
                if p > 0:
                    exp = line[:p].strip()
                else:
                    exp = line.strip()

                if exp in bloomLex:
                    print (bloomFile + " has verb '" + exp + "' listed with two default levels, level " + str(bloomLex[exp]) + " and level " + str(bloomLevel) + "\n")
                bloomLex[exp] = bloomLevel
    except:
        bloomFile = ""
    for v in ambig:
        if v in bloomLex:
            ambig[v] = [bloomLex[v]] + ambig[v]
        else:
            print (bloomFile + " has verb '" + v + "' with ambiguous Bloom level but no default level.\n")
    try:
        for line in open(bloomFileEn).readlines():
            if line[0] == "#":
                continue
            if line[0:3] == "---": # new Bloom level
                m = re.findall("---\s*\w*\s*([0-9][0-9]*)\s*---", line)
                if len(m) == 1:
                    bloomLevel = int(m[0])

            if line[0] == "(": # ambiguous verb, not the default level of this verb
                v = line.replace("(", "").replace(")", "").strip()
                if v in ambigEn:
                    ambigEn[v].append(bloomLevel)
                else:
                    ambigEn[v] = [bloomLevel]
                    
            if line[0].islower() or line[0].isupper():
                exp = line.strip()

                if exp in bloomLexEn:
                    print (bloomFileEn + " has verb '" + exp + "' listed with two default levels, level " + str(bloomLexEn[exp]) + " and level " + str(bloomLevel) + "\n")
                bloomLexEn[exp] = bloomLevel
    except:
        bloomFileEn = ""
    for v in ambigEn:
        if v in bloomLexEn:
            ambigEn[v] = [bloomLexEn[v]] + ambigEn[v]
        else:
            print (bloomFileEn + " has verb '" + v + "' with ambiguous Bloom level but no default level.\n")

#####################
### read stoplist ###
#####################
stoplist = {}
try:
    for line in open(stoplistFile).readlines():
        v = line.strip()
        if len(v):
            stoplist[v] = 1
except:
    log("Error reading stoplist.")

############################
### read JSON from stdin ###
############################
data = {}

if not sys.stdin.isatty():
    text = ""
    for line in sys.stdin:
        text += line

    try:
            data = json.loads(text)
    except:
        data = {}
else:
    data = {"Course-list":[]}

#######################
### Read more data. ###
#######################
for i in range(len(moreInputs)):
    try:
        f = open(moreInputs[i])
        tmp = json.load(f)

        if tmp and "Course-list" in tmp:
            data["Course-list"].extend(tmp["Course-list"])
        f.close()
    except:
        print("Could not read data from:", moreInputs[i])

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

# bloomStats = {"course":{"all":{}, "scb":{}, "level":{}, "type":{}, "uni":{}}, "goal":"course":{"all":{}, "scb":{}, "level":{}, "type":{}, "uni":{}}}
bloomStatsCC = {"all":{}, "scb":{}, "level":{}, "type":{}, "uni":{}, "cred":{}, "levelG":{}, "scbG":{}}
bloomStatsGoal = {"all":{}, "scb":{}, "level":{}, "type":{}, "uni":{}, "cred":{}, "levelG":{}, "scbG":{}}

def median(ls):
    l = len(ls)
    if l == 0:
        return 0
    
    if l % 2: 
        return ls[int((l-1)/2)]
    else:
        return (ls[int(l / 2)] +ls[int(l/2) - 1]) / 2.0
    

def addBloomList(ls, scb, level, ctype, uni, scbGroup, levelGroup, creditsGroup):
    if not ctype in bloomStatsCC["type"]:
        bloomStatsCC["type"][ctype] = {"verbCounts":{}, "goalCounts":{}}
    if not level in bloomStatsCC["level"]:
        bloomStatsCC["level"][level] = {"verbCounts":{}, "goalCounts":{}}
    if not scb in bloomStatsCC["scb"]:
        bloomStatsCC["scb"][scb] = {"verbCounts":{}, "goalCounts":{}}
    if not uni in bloomStatsCC["uni"]:
        bloomStatsCC["uni"][uni] = {"verbCounts":{}, "goalCounts":{}}
    if not scbGroup in bloomStatsCC["scbG"]:
        bloomStatsCC["scbG"][scbGroup] = {"verbCounts":{}, "goalCounts":{}}
    if not levelGroup in bloomStatsCC["levelG"]:
        bloomStatsCC["levelG"][levelGroup] = {"verbCounts":{}, "goalCounts":{}}
    if not creditsGroup in bloomStatsCC["cred"]:
        bloomStatsCC["cred"][creditsGroup] = {"verbCounts":{}, "goalCounts":{}}

    if not ctype in bloomStatsGoal["type"]:
        bloomStatsGoal["type"][ctype] = {"verbCounts":{}}
    if not level in bloomStatsGoal["level"]:
        bloomStatsGoal["level"][level] = {"verbCounts":{}}
    if not scb in bloomStatsGoal["scb"]:
        bloomStatsGoal["scb"][scb] = {"verbCounts":{}}
    if not uni in bloomStatsGoal["uni"]:
        bloomStatsGoal["uni"][uni] = {"verbCounts":{}}
    if not scbGroup in bloomStatsGoal["scbG"]:
        bloomStatsGoal["scbG"][scbGroup] = {"verbCounts":{}}
    if not levelGroup in bloomStatsGoal["levelG"]:
        bloomStatsGoal["levelG"][levelGroup] = {"verbCounts":{}}
    if not creditsGroup in bloomStatsGoal["cred"]:
        bloomStatsGoal["cred"][creditsGroup] = {"verbCounts":{}}

    nGoals = len(ls)
    for lex in [bloomStatsCC["scb"][scb]["goalCounts"], bloomStatsCC["level"][level]["goalCounts"], bloomStatsCC["type"][ctype]["goalCounts"], bloomStatsCC["uni"][uni]["goalCounts"], bloomStatsCC["scbG"][scbGroup]["goalCounts"], bloomStatsCC["levelG"][levelGroup], bloomStatsCC["cred"][creditsGroup]]:
        if not nGoals in lex:
            lex[nGoals] = 0
        lex[nGoals] += 1

        if not "tot" in lex:
            lex["tot"] = 0
        lex["tot"] += nGoals

        if not "N" in lex:
            lex["N"] = 0
        lex["N"] += 1
        
    flat = []
    for goal in ls:
        nVerbs = len(goal)
        mn = 10
        mx = -1
        tot = 0
        mean = 0
        votes = {}
        s2 = 0
        ls = []
        
        for verb in goal:
            flat.append(verb[2])

            for lex in [bloomStatsCC["scb"][scb], bloomStatsCC["level"][level], bloomStatsCC["type"][ctype], bloomStatsCC["uni"][uni], bloomStatsCC["scbG"][scbGroup], bloomStatsCC["levelG"][levelGroup], bloomStatsCC["cred"][creditsGroup]]:
                if not verb[1] in lex["verbCounts"]:
                    lex["verbCounts"][verb[1]] = 1
                else:
                    lex["verbCounts"][verb[1]] += 1

            bLevel = verb[2]
            if bLevel > mx:
                mx = bLevel
            if bLevel < mn:
                mn = bLevel
            tot += 1
            s2 += bLevel*bLevel
            mean += bLevel
            ls.append(bLevel)
            
            if not bLevel in votes:
                votes[bLevel] = 1
            else:
                votes[bLevel] += 1
        ls.sort()
        med = median(ls)
        
        for lex in [bloomStatsGoal["all"], bloomStatsGoal["scb"][scb], bloomStatsGoal["level"][level], bloomStatsGoal["type"][ctype], bloomStatsGoal["uni"][uni], bloomStatsGoal["scbG"][scbGroup], bloomStatsGoal["levelG"][levelGroup], bloomStatsGoal["cred"][creditsGroup]]:
            if not "max" in lex:
                lex["max"] = {}
            if not mx in lex["max"]:
                lex["max"][mx] = 1
            else:
                lex["max"][mx] += 1

            if not "min" in lex:
                lex["min"] = {}
            if not mn in lex["min"]:
                lex["min"][mn] = 1
            else:
                lex["min"][mn] += 1

            if not "nVerbs" in lex:
                lex["nVerbs"] = {}

            if not tot in lex["nVerbs"]:
                lex["nVerbs"][tot] = 1
            else:
                lex["nVerbs"][tot] += 1

            if not "nVerbsG" in lex:
                lex["nVerbsG"] = {}
            totG = numberOfVerbsGroup(tot)
            if not totG in lex["nVerbsG"]:
                lex["nVerbsG"][totG] = 1
            else:
                lex["nVerbsG"][totG] += 1

            if not "mean" in lex:
                lex["mean"] = []
            if tot > 0:
                lex["mean"].append(mean / float(tot))

            if not "median" in lex:
                lex["median"] = []
            lex["median"].append(med)

            if not "variance" in lex:
                lex["variance"] = []
            if tot > 0:
                lex["variance"].append(abs((mean*mean / float(tot) - s2) / float(tot)))
                
            v = -1
            vm = 0
            for vv in votes:
                if votes[vv] > vm:
                    vm = votes[vv]
                    v = vv
            if not "common" in lex:
                lex["common"] = {}
            if not v in lex["common"]:
                lex["common"][v] = 1
            else:
                lex["common"][v] += 1

    flat.sort()
            
    if len(flat) > 0:
        mn = 10
        mx = -1
        tot = 0
        mean = 0
        votes = {}
        s2 = 0        
        for b in flat:
            tot += b
            s2 += b*b
            if b > mx:
                mx = b
            if b < mn:
                mn = b
            if not b in votes:
                votes[b] = 1
            else:
                votes[b] += 1
        n = len(flat)
        mean = tot / float(n)
        variance = abs((tot*tot/float(n) - s2) / float(n))

        v = -1
        vm = 0
        for vv in votes:
            if votes[vv] > vm:
                vm = votes[vv]
                v = vv
        
        for lex in [bloomStatsCC["scb"][scb], bloomStatsCC["level"][level], bloomStatsCC["type"][ctype], bloomStatsCC["all"], bloomStatsCC["uni"][uni], bloomStatsCC["scbG"][scbGroup], bloomStatsCC["levelG"][levelGroup], bloomStatsCC["cred"][creditsGroup]]:
            if not "max" in lex:
                lex["max"] = {}
            if not mx in lex["max"]:
                lex["max"][mx] = 1
            else:
                lex["max"][mx] += 1

            if not "min" in lex:
                lex["min"] = {}
            if not mn in lex["min"]:
                lex["min"][mn] = 1
            else:
                lex["min"][mn] += 1

            if not "nVerbs" in lex:
                lex["nVerbs"] = {}

            if n > VERBS_BEFORE_MORE_THAN:
                n = VERBS_BEFORE_MORE_THAN # treat anything with lots of verbs as "more than X"
            if not n in lex["nVerbs"]:
                lex["nVerbs"][n] = 1
            else:
                lex["nVerbs"][n] += 1

            if not "nVerbsG" in lex:
                lex["nVerbsG"] = {}
            nG = numberOfVerbsGroup(n)
            if not nG in lex["nVerbsG"]:
                lex["nVerbsG"][nG] = 1
            else:
                lex["nVerbsG"][nG] += 1

            if not "common" in lex:
                lex["common"] = {}
            if not v in lex["common"]:
                lex["common"][v] = 1
            else:
                lex["common"][v] += 1

            if not "mean" in lex:
                lex["mean"] = []
            lex["mean"].append(mean)

            if not "variance" in lex:
                lex["variance"] = []
            lex["variance"].append(variance)

            if not "median" in lex:
                lex["median"] = []
            lex["median"].append(median(flat))

            if not "val" in lex:
                lex["val"] = {}
            for b in flat:
                if not b in lex["val"]:
                    lex["val"][b] = 1
                else:
                    lex["val"][b] += 1

    else:
        for lex in [bloomStatsCC["scb"][scb], bloomStatsCC["level"][level], bloomStatsCC["type"][ctype], bloomStatsCC["all"], bloomStatsCC["uni"][uni], bloomStatsCC["scbG"][scbGroup], bloomStatsCC["levelG"][levelGroup], bloomStatsCC["cred"][creditsGroup]]:

            if not "nVerbs" in lex:
                lex["nVerbs"] = {}
            if not 0 in lex["nVerbs"]:
                lex["nVerbs"][0] = 1
            else:
                lex["nVerbs"][0] += 1

            if not "nVerbsG" in lex:
                lex["nVerbsG"] = {}
            n0 = numberOfVerbsGroup(0)
            if not n0 in lex["nVerbsG"]:
                lex["nVerbsG"][n0] = 1
            else:
                lex["nVerbsG"][n0] += 1
        
        nGoals = 0
        for lex in [bloomStatsCC["scb"][scb]["goalCounts"], bloomStatsCC["level"][level]["goalCounts"], bloomStatsCC["type"][ctype]["goalCounts"], bloomStatsCC["uni"][uni]["goalCounts"], bloomStatsCC["scbG"][scbGroup]["goalCounts"], bloomStatsCC["levelG"][levelGroup]["goalCounts"], bloomStatsCC["cred"][creditsGroup]["goalCounts"]]:
            if not nGoals in lex:
                lex[nGoals] = 0
            lex[nGoals] += 1

            if not "tot" in lex:
                lex["tot"] = 0
            lex["tot"] += nGoals

            if not "N" in lex:
                lex["N"] = 0
            lex["N"] += 1

def printBloomStats():
    if not "all" in bloomStatsCC or not "max" in bloomStatsCC["all"]:
        return
    
    print ("-"*15, "Bloom classifications", "-"*15)

    print ("\n" + "-"*10, "Verbs per Bloom level", "-"*10)
    totCourses = 0
    for v in bloomStatsCC["all"]["max"]:
        totCourses += bloomStatsCC["all"]["max"][v]
    totBloom = 0
    for val in range(6):
        if val in bloomStatsCC["all"]["val"]:
            totBloom += bloomStatsCC["all"]["val"][val]

    for val in range(6):
        if val in bloomStatsCC["all"]["val"]:
            c = bloomStatsCC["all"]["val"][val]
            if totBloom > 0:
                proc = c / float(totBloom)
            else:
                proc = 0
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print ("\n" + str(totBloom), "classified verbs\n")

    ###############################
    ### Print stats per course ####
    ###############################
    
    print ("\n" + "-"*15, "Statistics per course", "-"*15)
    
    print ("-"*10, "Maximum Bloom level per course", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsCC["all"]["max"]:
            c = bloomStatsCC["all"]["max"][val]
            tmp += c
            if totCourses > 0:
                proc = c / float(totCourses)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "courses with Bloom data")
    
    print ("-"*10, "Minimum Bloom level per course", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsCC["all"]["min"]:
            c = bloomStatsCC["all"]["min"][val]
            tmp += c
            if totCourses > 0:
                proc = c / float(totCourses)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "courses with Bloom data")

    print ("-"*10, "Average Mean Bloom level per course", "-"*10)
    m = 0
    n = len(bloomStatsCC["all"]["mean"])
    for v in bloomStatsCC["all"]["mean"]:
        m += v
    if n > 0:
        m = m / n
    print ("{0: .2}".format(m))
        
    print ("-"*10, "Average Variance in Bloom level per course", "-"*10)
    m = 0
    n = len(bloomStatsCC["all"]["variance"])
    for v in bloomStatsCC["all"]["variance"]:
        m += v
    if n > 0:
        m = m / n
    print ("{0: .2}".format(m))

    print ("-"*10, "Median Bloom level per course", "-"*10)
    tmp = 0
    tmpTot = 0
    ls = []
    tmpLex = {}
    for val in bloomStatsCC["all"]["median"]:
        if not val in tmpLex:
            tmpLex[val] = 0
            ls.append(val)
        tmpLex[val] += 1
    ls.sort()
    
    for val in ls:
        if val in tmpLex:
            c = tmpLex[val]
            tmp += c
            tmpTot += c*val
            if totCourses > 0:
                proc = c / float(totCourses)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: <3}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: <3}: {1: >5} (0%)".format(val, 0))
    if tmp > 0:
        print("Average median value:", str(tmpTot / tmp))
    print (tmp, "courses with Bloom data")

    print ("-"*10, "Most common Bloom level per course", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsCC["all"]["common"]:
            c = bloomStatsCC["all"]["common"][val]
            tmp += c
            if totCourses > 0:
                proc = c / float(totCourses)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "courses with Bloom data")

    print ("-"*10, "Number of Bloom verbs per course", "-"*10)
    tmp = 0
    ls = []
    for val in bloomStatsCC["all"]["nVerbs"]:
        ls.append(val)
    ls.sort()
    for val in ls:
        c = bloomStatsCC["all"]["nVerbs"][val]
        tmp += c
        if totCourses > 0:
            proc = c / float(totCourses)
        else:
            proc = 0
        procs = "{:>5}".format("{:2.1%}".format(proc))
        if val == ls[-1]:
            print ("{0: >3}+: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >4}: {1: >5} ({2:})".format(val, c, procs))
    print (tmp, "courses in data")

    print ("-"*10, "Number of Bloom verbs per course (grouped)", "-"*10)
    tmp = 0
    ls = []
    for val in bloomStatsCC["all"]["nVerbsG"]:
        ls.append(val)
    ls.sort()
    for val in ls:
        c = bloomStatsCC["all"]["nVerbsG"][val]
        tmp += c
        if totCourses > 0:
            proc = c / float(totCourses)
        else:
            proc = 0
        procs = "{:>5}".format("{:2.1%}".format(proc))
        print ("{0: >9}: {1: >5} ({2:})".format(val, c, procs))
    
    #############################
    ### Print stats per goal ####
    #############################

    print ("\n" + "-"*15, "Statistics per goal", "-"*15)

    totGoals = 0
    for v in bloomStatsGoal["all"]["max"]:
        totGoals += bloomStatsGoal["all"]["max"][v]
    
    print ("-"*10, "Maximum Bloom level per goal", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsGoal["all"]["max"]:
            c = bloomStatsGoal["all"]["max"][val]
            tmp += c
            if totGoals > 0:
                proc = c / float(totGoals)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "goals with Bloom data")
    
    print ("-"*10, "Minimum Bloom level per goal", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsGoal["all"]["min"]:
            c = bloomStatsGoal["all"]["min"][val]
            tmp += c
            if totGoals > 0:
                proc = c / float(totGoals)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "goals with Bloom data")

    print ("-"*10, "Average Mean Bloom level per goal", "-"*10)
    m = 0
    n = len(bloomStatsGoal["all"]["mean"])
    for v in bloomStatsGoal["all"]["mean"]:
        m += v
    if n > 0:
        m = m / n
    print ("{0: .2}".format(m))
        
    print ("-"*10, "Average Variance in Bloom level per goal", "-"*10)
    m = 0
    n = len(bloomStatsGoal["all"]["variance"])
    for v in bloomStatsGoal["all"]["variance"]:
        m += v
    if n > 0:
        m = m / n
    print ("{0: .2}".format(m))
        
    print ("-"*10, "Median Bloom level per goal", "-"*10)
    tmp = 0
    tmpTot = 0
    ls = []
    tmpLex = {}
    for val in bloomStatsGoal["all"]["median"]:
        if not val in tmpLex:
            tmpLex[val] = 0
            ls.append(val)
        tmpLex[val] += 1
    ls.sort()
    
    for val in ls:
        if val in tmpLex:
            c = tmpLex[val]
            tmp += c
            tmpTot += c*val
            if totGoals > 0:
                proc = c / float(totGoals)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: <3}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: <3}: {1: >5} (0%)".format(val, 0))
    if tmp > 0:
        print("Average median value:", str(tmpTot / tmp))
    print (tmp, "goals with Bloom data")

    print ("-"*10, "Most common Bloom level per goal", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStatsGoal["all"]["common"]:
            c = bloomStatsGoal["all"]["common"][val]
            tmp += c
            if totGoals > 0:
                proc = c / float(totGoals)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "goals with Bloom data")

    print ("-"*10, "Number of Bloom verbs per goal", "-"*10)
    tmp = 0
    ls = []
    for val in bloomStatsGoal["all"]["nVerbs"]:
        ls.append(val)
    ls.sort()
    for val in ls:
        c = bloomStatsGoal["all"]["nVerbs"][val]
        tmp += c
        if totGoals > 0:
            proc = c / float(totGoals)
        else:
            proc = 0
        procs = "{:>5}".format("{:2.1%}".format(proc))
        if val == ls[-1]:
            print ("{0: >3}+: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >4}: {1: >5} ({2:})".format(val, c, procs))
    print (tmp, "goals in data")

    print ("-"*10, "Number of Bloom verbs per goal (grouped)", "-"*10)
    tmp = 0
    ls = []
    for val in bloomStatsGoal["all"]["nVerbsG"]:
        ls.append(val)
    ls.sort()
    for val in ls:
        c = bloomStatsGoal["all"]["nVerbsG"][val]
        tmp += c
        if totGoals > 0:
            proc = c / float(totGoals)
        else:
            proc = 0
        procs = "{:>5}".format("{:2.1%}".format(proc))
        print ("{0: >9}: {1: >5} ({2:})".format(val, c, procs))

    ###########################################
    ### Print data per uni etc., per course ###
    ###########################################

    for tmp in [["University", bloomStatsCC["uni"], bloomStatsGoal["uni"]], ["Credits", bloomStatsCC["cred"], bloomStatsGoal["cred"]], ["CourseLevel grouped", bloomStatsCC["levelG"], bloomStatsGoal["levelG"]], ["SCB grouped", bloomStatsCC["scbG"], bloomStatsGoal["scbG"]], ["SCB", bloomStatsCC["scb"], bloomStatsGoal["scb"]], ["CourseLevel", bloomStatsCC["level"], bloomStatsGoal["level"]], ["CourseType", bloomStatsCC["type"], bloomStatsGoal["type"]]]:
        label = tmp[0]
        if (label == "University") or (label == "Credits") or (label == "SCB grouped") or (label == "CourseLevel grouped") or (label == "SCB" and prints["perSCB"]) or (label == "CourseLevel" and prints["perLevel"]) or (label == "CourseType" and prints["perType"]):
            lex = tmp[1]

            if len(lex.keys()) > 1:
            
                print("\n" + "-"*10, "Statistics per", label, "-"*10)

                cats = []
                for cat in lex:
                    cats.append(cat)
                cats.sort()
                
                print("-"*10, "Most common verbs", "-"*10)
                for cat in cats:
                    ls = []
                    for v in lex[cat]["verbCounts"]:
                        ls.append([lex[cat]["verbCounts"][v], v])
                    ls.sort(reverse=True)
                    print ("--->", cat)
                    for vi in range(len(ls)):
                        print ("{0: >5}: {1:}".format(ls[vi][0], ls[vi][1]))
                        if vi >= 10:
                            break
                print()

                ls = []
                rowLabel = "Verbs per Bloom level"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                for v in range(6):
                    s += "{0: >6} ".format(v)
                s += "{0: >9}".format("Total")
                print ("-"*len(s))
                print (s)
                print ("-"*len(s))

                tots = 0
                for row in ls:
                    tot = 0
                    for v in range(6):
                        if "val" in lex[row] and v in lex[row]["val"]:
                            tot += lex[row]["val"][v]
                    tots += tot

                for row in ls:
                    tot = 0
                    for v in range(6):
                        if "val" in lex[row] and v in lex[row]["val"]:
                            tot += lex[row]["val"][v]

                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)
                    s2 = " "*len(s)

                    for v in range(6):
                        if "val" in lex[row] and v in lex[row]["val"]:
                            c = lex[row]["val"][v]
                            if tot > 0:
                                proc = c / float(tot)
                            else:
                                proc = 0

                            s += "{0: >6} ".format(c)
                            s2 += "{0: >6} ".format("{0: 2.1%}".format(proc))
                        else:
                            s += "{0: >6} ".format(0)
                            s2 += "{0: >6} ".format("{0: 2.1%}".format(0))
                    s += "{0: >9}".format(tot)
                    print (s)
                    if tots > 0:
                        s2 += "{: >9}".format("{0: 2.1%}".format(tot/float(tots)))
                    print (s2)
                    print ()
                print()

                printBloomHelper("max", "max Bloom/course", lex, 6)

                printBloomHelper("min", "min Bloom/course", lex, 6)

                ls = []
                rowLabel = "average mean Bloom per course"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "mean" in lex[row]:
                        m = 0
                        n = len(lex[row]["mean"])
                        for v in lex[row]["mean"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()

                ### Variance ###
                ls = []
                rowLabel = "average variance Bloom per course"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "variance" in lex[row]:
                        m = 0
                        n = len(lex[row]["variance"])
                        for v in lex[row]["variance"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()
                
                ### Median ###
                ls = []
                rowLabel = "average median Bloom per course"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "median" in lex[row]:
                        m = 0
                        n = len(lex[row]["median"])
                        for v in lex[row]["median"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()
                
                printBloomHelper("common", "most common Bloom level (per course)", lex, 6)

                printBloomHelper("nVerbs", "#verbs/course", lex, VERBS_BEFORE_MORE_THAN+1)
                printBloomHelper2("nVerbsG", "#verbs/course (grouped)", lex)
                
            #########################################
            ### Print data per uni etc., per goal ###
            #########################################
            lex = tmp[2]

            if len(lex.keys()) > 1:

                printBloomHelper("max", "max Bloom/goal", lex, 6)

                printBloomHelper("min", "min Bloom/goal", lex, 6)

                ls = []
                rowLabel = "average mean Bloom per goal"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "mean" in lex[row]:
                        m = 0
                        n = len(lex[row]["mean"])
                        for v in lex[row]["mean"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()

                ### Variance ###
                ls = []
                rowLabel = "average variance Bloom per goal"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "variance" in lex[row]:
                        m = 0
                        n = len(lex[row]["variance"])
                        for v in lex[row]["variance"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()

                ### Median ###
                ls = []
                rowLabel = "average median Bloom per goal"
                longest = len(rowLabel)
                for row in lex:
                    ls.append(row)
                    if len(row) > longest:
                        longest = len(row)
                ls.sort()

                s = "{0: >" + str(longest) + "}: "
                s = s.format(rowLabel)
                print (s)

                for row in ls:
                    s = "{0: >" + str(longest) + "}: "
                    s = s.format(row)

                    if "median" in lex[row]:
                        m = 0
                        n = len(lex[row]["median"])
                        for v in lex[row]["median"]:
                            m += v
                        if n > 0:
                            m = m / n
                        s += "{0: .2} ".format(m)
                    else:
                        s += "{0: >5} ".format(0)
                    print (s)
                print()
                
                printBloomHelper("common", "most common Bloom level (per goal)", lex, 6)

                printBloomHelper("nVerbs", "#verbs/goal", lex, VERBS_BEFORE_MORE_THAN+1)
                printBloomHelper2("nVerbsG", "#verbs/course (grouped)", lex)

    
def printBloomHelper(f, label, lex, n):
    ls = []
    rowLabel = label
    longest = len(rowLabel)
    for row in lex:
        ls.append(row)
        if len(row) > longest:
            longest = len(row)
    ls.sort()

    s = "{0: >" + str(longest) + "}: "
    s = s.format(rowLabel)
    for v in range(n):
        if v == n -1 and f == "nVerbs":
            s += "{0: >6}+".format(v)
        else:
            s += "{0: >6} ".format(v)
            
    s += "{0: >9}".format("Total")
    print ("-"*len(s))
    print (s)
    print ("-"*len(s))

    tots = 0
    for row in ls:
        tot = 0
        for v in range(n):
            if f in lex[row] and v in lex[row][f]:
                tot += lex[row][f][v]
        tots += tot

    for row in ls:
        s = "{0: >" + str(longest) + "}: "
        s = s.format(row)
        s2 = " "*len(s)

        tot = 0
        for v in range(n):
            if f in lex[row] and v in lex[row][f]:
                tot += lex[row][f][v]

        for v in range(n):
            if "max" in lex[row] and v in lex[row][f]:
                c = lex[row][f][v]
                if tot > 0:
                    proc = c / float(tot)
                else:
                    proc = 0
                s += "{0: >6} ".format(c)

                s2 += "{0: >6} ".format("{0: 2.1%}".format(proc))
            else:
                s += "{0: >6} ".format(0)
                s2 += "    0% "
        s += "{0: >9}".format(tot)
        print (s)

        if tots > 0:
            s2 += "{: >9}".format("{0: 2.1%}".format(tot/float(tots)))
        print (s2)
        print ()
    print()

def printBloomHelper2(f, label, lex):
    ls = []
    rowLabel = label
    longest = len(rowLabel)
    for row in lex:
        ls.append(row)
        if len(row) > longest:
            longest = len(row)
    ls.sort()

    cats = []
    tmp = {}
    for row in lex:
        for cat in lex[row][f]:
            tmp[cat] = 1
    for cat in tmp:
        cats.append(cat)
    cats.sort()

    s = "{0: >" + str(longest) + "}: "
    s = s.format(rowLabel)
    for v in cats:
        s += "{0: >9} ".format(v)
            
    s += "{0: >9}".format("Total")
    print ("-"*len(s))
    print (s)
    print ("-"*len(s))

    tots = 0
    for row in ls:
        tot = 0
        for v in cats:
            if f in lex[row] and v in lex[row][f]:
                tot += lex[row][f][v]
        tots += tot

    for row in ls:
        s = "{0: >" + str(longest) + "}: "
        s = s.format(row)
        s2 = " "*len(s)

        tot = 0
        for v in cats:
            if f in lex[row] and v in lex[row][f]:
                tot += lex[row][f][v]

        for v in cats:
            if "max" in lex[row] and v in lex[row][f]:
                c = lex[row][f][v]
                if tot > 0:
                    proc = c / float(tot)
                else:
                    proc = 0
                s += "{0: >9} ".format(c)

                s2 += "{0: >9} ".format("{0: 2.1%}".format(proc))
            else:
                s += "{0: >9} ".format(0)
                s2 += "       0% "
        s += "{0: >9}".format(tot)
        print (s)

        if tots > 0:
            s2 += "{: >9}".format("{0: 2.1%}".format(tot/float(tots)))
        print (s2)
        print ()
    print()

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

goalCounts = {"tot":0, "N":0, "max":0}
def addGoals(ls):
    n = len(ls)

    if not n in goalCounts:
        goalCounts[n] = 0
    goalCounts[n] += 1
    goalCounts["tot"] += n
    goalCounts["N"] += 1
    if n > goalCounts["max"]:
        goalCounts["max"] = n
    
typeCounts = {}
def addType(t):
    if not t in typeCounts:
        typeCounts[t] = 0
    typeCounts[t] += 1
    
def printStats():
    print ("\n","-"*15, "Problem Types", "-"*15)
    for label in counts:
        print ("{0: <35}: {1: >5}".format(label, counts[label]))

    if prints["errorList"]:
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
        tot = 0
        for t in typeCounts:
            tot += typeCounts[t]
        for t in typeCounts:
            c = typeCounts[t]
            if tot > 0:
                proc = c / float(tot)
            else:
                proc = 0
            procs = "{: >5}".format("{:2.1%}".format(proc))
            print("{0: >5} ({1:}) courses of type {2:}".format(c, procs, t))
    if goalCounts:
        print ("\n","-"*15, "Course Goals", "-"*15)
        if goalCounts["N"] > 0:
            print("{0: >5} goals in {1:} courses, averaging {2: 1.2} goals per course.".format(goalCounts["tot"], goalCounts["N"], goalCounts["tot"]/float(goalCounts["N"])))
        else:
            print("{0: >5} goals in {1:} courses.".format(goalCounts["tot"], goalCounts["N"]))

        print("\nThe number of courses with a specific number of goals")
        for n in range(goalCounts["max"] + 1):
            if n in goalCounts:
                print("{0: >2}: {1:}".format(n, goalCounts[n]))
    
def printBloom():
    tot = 0
    vs = 0
    ls = []
    for v in verbCounts:
        tot += verbCounts[v]
        vs += 1
        ls.append([verbCounts[v], v])
    ls.sort(reverse=True)
    
    print ("\n","-"*15, "VERBS", "-"*15)
    print (vs, "different verbs seen,", tot, "total occurences of these verbs.")
    print("Number of Bloom classifications of each level:")
    for c in range(6):
        if c in bloomLevelCounts:
            print ("{0: >2}: {1: >5}".format(c, bloomLevelCounts[c]))
        else:
            print ("{0: >2}: {1: >5}".format(c, 0))
    print ("\n","-"*15, "Most common verbs", "-"*15)
    for i in range(len(ls)):
        print ("{0: >5}: {1:}".format(ls[i][0], ls[i][1]))
        if i >= 10:
            break

    print ("-"*30)
    atot = 0
    avs = 0
    for v in ambiguousVerbs:
        atot += ambiguousVerbs[v]
        avs += 1
    print (avs, "different ambiguous verbs seen,", atot, "total occurences of these verbs.")
    ls = []
    for v in ambiguousVerbs:
        ls.append([ambiguousVerbs[v], v])
    ls.sort(reverse=True)
    for vv in ls:
        print ("{0: <35}: {1: >5}".format(vv[1],vv[0]))
    
def printNonBloom():
    if not checks["nonBloom"]:
        return

    if not prints["nonBloom"]:
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
    ls = []
    for v in nonBloomVerbsInfo:
        for ex in nonBloomVerbsInfo[v]:
            s = "** " + v + " ** in course " + ex[1] + ", goal text:\n" + ex[0] + "\n"
            ls.append(s)
            #print ("**", v, "** in course ", ex[1], "goal text:\n", ex[0], "\n")
    ls.sort()
    for s in ls:
        print(s)

def cPrint(s):
    if prints["courses"]:
        print(s)

scbCounts = {}
def addSCB(s):
    if not s in scbCounts:
        scbCounts[s] = 0
    scbCounts[s] += 1

def printSCB():
    print ("\n", "-"*15, "SCB IDs","-"*15)
    ls = []
    for s in scbCounts:
        ls.append(s)
    ls.sort()
    tot = 0
    for s in ls:
        tot += scbCounts[s]
    for s in ls:
        if len(s) > 3:
            continue
        if tot > 0:
            procs = "{:>5}".format("{:2.1%}".format(scbCounts[s]/float(tot)))
            print ("{0: >4}: {1: >5} ({2:})".format(s, scbCounts[s], procs))
        else:
            print ("{0: >4}: {1: >5}".format(s, scbCounts[s]))

    print ("\n", "."*15, "Grouped SCB","."*15)
    
    for s in ls:
        if len(s) <= 3:
            continue
        if tot > 0:
            procs = "{:>5}".format("{:2.1%}".format(scbCounts[s]/float(tot)))
            print ("{0: >30}: {1: >5} ({2:})".format(s, scbCounts[s], procs))
        else:
            print ("{0: >30}: {1: >5}".format(s, scbCounts[s]))

    if len(unknownSCB.keys()):
        print ("\n........SCB that were not grouped........\n")
        for k in unknownSCB:
            print ("'" + k + "'")
    
    print()
    
levCounts = {}
def addLevel(l):
    if not l in levCounts:
        levCounts[l] = 0
    levCounts[l] += 1

def printLevel():
    print ("\n", "-"*15, "Course Levels","-"*15)
    ls = []
    for l in levCounts:
        if len(l) <= 3:
            ls.append(l)
    ls.sort()
    tot = 0
    for l in ls:
        tot += levCounts[l]
    for l in ls:
        if tot > 0:
            procs = "{:>5}".format("{:2.1%}".format(levCounts[l]/float(tot)))
            print ("{0: >4}: {1: >5} ({2:})".format(l, levCounts[l], procs))
        else:
            print ("{0: >4}: {1: >5}".format(l, levCounts[l]))

    print ("\n", "."*15, "Grouped Course Levels","."*15)
    ls = []
    for l in levCounts:
        if len(l) > 3:
            ls.append(l)
    ls.sort()
    tot = 0
    for l in ls:
        tot += levCounts[l]
    for l in ls:
        if tot > 0:
            procs = "{:>5}".format("{:2.1%}".format(levCounts[l]/float(tot)))
            print ("{0: >22}: {1: >5} ({2:})".format(l, levCounts[l], procs))
        else:
            print ("{0: >22}: {1: >5}".format(l, levCounts[l]))
    

#######################
### Group SCB codes ###
#######################

# Humaniora och teologi, Juridig och samhällsvetenskap, Naturvetenskap, Teknik, Medicin och odontologi, Vård och omsorg, Konstnärligt område, Övrigt område

scbLookups = {
    "Humaniora och teologi":
    {
        "Historisk-filosofiska ämnen":
        {
	    "AK1":"Antikens kultur",
	    "AR2":"Arkeologi",
	    "AV1":"Arkivvetenskap",
	    "DT2":"Dans- och teatervetenskap",
	    "ES2":"Estetik",
	    "ET1":"Etnologi",
	    "FI2":"Filosofi",
	    "FV1":"Filmvetenskap",
	    "HI2":"Historia",
	    "IL1":"Idé- och lärdomshistoria/Idéhistoria",
	    "KU2":"Kulturvård",
	    "KV1":"Konstvetenskap",
	    "KV2":"Kulturvetenskap",
	    "LV1":"Litteraturvetenskap",
	    "MV2":"Musikvetenskap",
	    "RO1":"Retorik",
	    "HF9":"Övrigt inom historisk-filosofiska ämnen"
        },
	"Journalistik, kommunikation och information":
        {
	    "BV1":"Biblioteks- och informationsvetenskap",
	    "JO1":"Journalistik",
	    "MK1":"Medie- o kommunikationsvetenskap",
	    "MP1":"Medieproduktion",
	    "JK9":"Övrigt journalistik, kommunikation, information"
        },
	"Språkvetenskapliga ämnen":
        {
	    "AL1":"Allmän språkvetenskap/lingvistik",
	    "AR1":"Arabiska",
	    "AS1":"Arameiska/syriska",
	    "BK1":"Bosniska/kroatiska/serbiska",
	    "BU1":"Bulgariska",
	    "DA1":"Danska",
	    "EN1":"Engelska",
	    "ES1":"Estniska",
	    "FI1":"Finska",
	    "FL1":"Flerspråkigt inriktade ämnen",
	    "FR1":"Franska",
	    "GR1":"Grekiska",
	    "HE1":"Hebreiska",
	    "HI1":"Hindi",
	    "IN1":"Indonesiska",
	    "IS1":"Indologi och sanskrit",
	    "IT1":"Italienska",
	    "JA1":"Japanska",
	    "KI1":"Kinesiska",
	    "KO1":"Koreanska",
	    "KU1":"Kurdiska",
	    "LA1":"Latin",
	    "LE1":"Lettiska",
	    "LI1":"Litauiska",
	    "NE1":"Nederländska",
	    "NG1":"Nygrekiska",
	    "PO1":"Polska",
	    "PR1":"Persiska",
	    "PU1":"Portugisiska",
	    "RU1":"Rumänska",
	    "RY1":"Ryska",
	    "SA1":"Samiska",
	    "SP1":"Spanska",
	    "SS1":"Svenska som andraspråk",
	    "SV1":"Svenska/Nordiska Språk",
	    "SW1":"Swahili",
	    "TA1":"Tamil",
	    "TE1":"Teckenspråk",
	    "TH1":"Thai",
	    "TI1":"Tibetanska",
	    "TJ1":"Tjeckiska",
	    "TO2":"Översättning och tolkning",
	    "TY1":"Tyska",
	    "UN1":"Ungerska",
	    "SP2":"Övriga språk"
        },
	"Religionsvetenskap":
        {
	    "RV1":"Religionsvetenskap",
	    "TL1":"Teologi"
        }
    },
    "Juridik och samhällsvetenskap":
    {
        "Informatik/Data- och systemvetenskap":
        {
	    "IF1":"Informatik/Data- och systemvetenskap"
        },
	"Beteendevetenskap":
        {
	    "HV1":"Handikappvetenskap",
	    "KR1":"Kriminologi",
	    "PE1":"Pedagogik",
	    "PS1":"Psykologi",
	    "PY1":"Psykoterapi",
	    "SO1":"Sociologi",
	    "SO2":"Socialantropologi",
	    "SS2":"Socialt arbete och social omsorg",
	    "UV1":"Utbildningsvetenskap/didaktik allmänt",
	    "UV2":"Utbildningsvetenskap teoretiska ämnen",
	    "UV3":"Utbildningsvetenskap praktisk-estetiska ämnen",
	    "BE9":"Övrigt inom beteendevetenskap"
	},
        "Ekonomi/administration":
        {
	    "AF1":"Administration och förvaltning",
	    "EH1":"Ekonomisk historia",
	    "FE1":"Företagsekonomi",
	    "LO1":"Ledarskap, organisation och styrning",
	    "NA1":"Nationalekonomi",
	    "EK9":"Övrigt inom ekonomi och administration"
        },
	"Juridik":
        {		
	    "JU1":"Juridik och rättsvetenskap"
        },
	"Övriga samhällsvetenskapliga ämnen":
	{
	    "FU1":"Freds- och utvecklingsstudier",
	    "KS1":"Kultur- och samhällsgeografi",
	    "LL1":"Länderkunskap/länderstudier",
	    "MH1":"Måltids- och  hushållskunskap",
	    "MR1":"Mänskliga rättigheter",
	    "SH1":"Samhällskunskap",
	    "ST1":"Statistik",
	    "ST2":"Statsvetenskap",
	    "SY1":"Studie- och yrkesvägledning",
	    "TU1":"Turism- och fritidsvetenskap",
	    "SA9":"Övrigt inom samhällsvetenskap"
        }
    },
    "Naturvetenskap":
    {
        "Biologi":
        {
	    "BI1":"Biologi",
	    "BT1":"Bioteknik",
	    "MB1":"Medicinsk biologi",
	    "MV1":"Miljövetenskap",
	    "NU1":"Nutrition"
        },
	"Farmaci":
	{
	    "FC1":"Farmaci",
	    "FK1":"Farmakologi"
        },
	"Fysik":
        {
	    "FY1":"Fysik"
        },
			
	"Geovetenskap":
	{
	    "GN1":"Geovetenskap och naturgeografi"
            ,
        },
			
	"Kemi":
	{
	    "KE1":"Kemi"
        },
			
	"Lant- och skogsbruk":
	{
	    "FV2":"Fiske och vattenbruk",
	    "LV2":"Lantbruksvetenskap",
	    "SK1":"Skogsvetenskap",
	    "TV1":"Trädgårdsvetenskap"
        },
			
	"Matematik":
	{
	    "MA1":"Matematik",
	    "MS1":"Matematisk statistik"
        },
			
	"Övrigt":
	{
	    "HD1":"Husdjursvetenskap",
	    "LM1":"Livsmedelsvetenskap",
	    "NA9":"Övrigt inom naturvetenskap"
        }
    },
    "Teknik":
    {
	"Arkitektur":
	{
	    "AR3":"Arkitektur",
	    "LA2":"Landskapsarkitektur"
        },
			
	"Byggnadsteknik/Väg- och vatten":
	{
	    "BY1":"Byggteknik",
	    "VV1":"Väg- och vattenbyggnad"
        },
			
	"Datateknik":
	{
	    "DT1":"Datateknik"
        },
			
	"Elektroteknik":
	{
	    "EL1":"Elektronik",
	    "EN2":"Energiteknik",
	    "ET2":"Elektroteknik"
        },
			
	"Industriell ekonomi och organisation":
	{
	    "IE1":"Industriell ekonomi och organisation"
        },
			
	"Kemiteknik":
	{
	    "KT1":"Kemiteknik"
        },
			
	"Lantmäteri":
        {
	    "GI1":"Geografisk informationsteknik och lantmäteri"
            , "GVA":"Geovetenskap och biogeovetenskap" # From SU, not in the original list
        },
			
	"Maskinteknik":
	{
	    "FT1":"Farkostteknik",
	    "MT1":"Maskinteknik"
        },
			
	"Samhällsbyggnadsteknik":
	{
	    "FP1":"Fysisk planering",
	    "SB1":"Samhällsbyggnadsteknik"
        },
			
	"Teknisk fysik":
	{
	    "TF1":"Teknisk fysik"
        },
	"Övrig teknik":
	{
	    "AT1":"Automatiseringsteknik",
	    "BM1":"Berg- och mineralteknik",
	    "MA2":"Materialteknik",
	    "RY2":"Rymdteknik",
	    "TT1":"Träfysik och träteknologi",
	    "TX1":"Textilteknologi",
	    "TE9":"Övriga tekniska ämnen"
        }
    },
			
    "Medicin och odontologi":
    {
    
	"Medicin":
	{
	    "ME1":"Medicin"
        },
			
	"Odontologi":
        {		
	    "OD1":"Odontologi",
	    "TO1":"Tandteknik och oral hälsa"
        },
			
	"Veterinärmedicin":
	{
	    "DJ1":"Djuromvårdnad",
	    "VE1":"Veterinärmedicin"
        },
			
	"Övrigt":
	{
	    "BL1":"Biomedicinsk laboratorievetenskap",
	    "MT2":"Medicinska tekniker",
	    "ME9":"Övrigt inom medicin"
        }
    },
			
    "Vård och omsorg":
    {
	"Omvårdnad":
        {
	    "FH1":"Folkhälsovetenskap",
	    "HS1":"Hälso- och sjukvårdsutveckling",
	    "OM1":"Omvårdnad/omvårdnadsvetenskap",
	    "OM9":"Övrigt inom omvårdnad"
        },
			
	"Rehabilitering":
	{
	    "TR1":"Terapi, rehabilitering och kostbehandling"
        }
    },		
    "Konstnärligt område":
    {
	"Konst":
	{
	    "DE1":"Design",
	    "FF1":"Författande",
	    "FK2":"Fri konst",
	    "KH1":"Konsthantverk",
	    "KO9":"Övrigt inom konst"
        },
			
	"Musik":
	{
	    "MU1":"Musik"
        },
			
	"Teater, film och dans":
	{
	    "CI1":"Cirkus",
	    "DA2":"Dans",
	    "FM1":"Film",
	    "KO2":"Koreografi",
	    "MC1":"Musikdramatisk scenframställning och gestaltning",
	    "RE1":"Regi",
	    "SM1":"Scen och medier",
	    "TF9":"Övrigt inom teater, film och dans"
        }
    },
    "Övrigt område":
    {
	"Tvärvetenskap":
	{
	    "AE1":"Arbetsvetenskap och ergonomi",
	    "BU2":"Barn- och ungdomsstudier",
	    "GS1":"Genusstudier",
	    "MM1":"Miljövård och miljöskydd",
	    "TS1":"Teknik i samhällsperspektiv",
	    "TV9":"Övriga tvärvetenskapliga studier"
        },
			
	"Idrott och friskvård":
	{
	    "FV3":"Friskvård",
	    "ID1":"Idrott/idrottsvetenskap"
        },
			
	"Transport":
        {
	    "LF1":"Luftfart",
	    "SJ1":"Sjöfart",
	    "TP9":"Övrigt inom transportsektorn"
        },
			
	"Militär utbildning":
	{
	    "KV3":"Krigsvetenskap"
        }
    }
}

scbToSCBGroup = {}
scbToSCBGroupM = {}
unknownSCB = {}
for top in scbLookups:
    for mid in scbLookups[top]:
        for scb in scbLookups[top][mid]:
            scbToSCBGroup[scb] = top
            scbToSCBGroupM[scb] = mid

######################################
### Grouping based on CourseLevel. ###
######################################
def levelGroup(level):
    if level == "No level info":
        return "(No level info)"
    if level in ["GXX", "G1N", "G1F", "G2F"]:
        return "Grundnivå"
    elif level in ["G1E", "G2E"]:
        return "Grundnivåexjobb"
    elif level in ["AXX", "A1N", "A1F"]:
        return "Avancerad nivå"
    elif level in ["A1E", "A2E"]:
        return "Avancerad nivå exjobb"
    elif level == "":
        return "(No level info)"
    else:
        return "(Level: " + level + ")"
    
##################################
### Grouping based on credits. ###
##################################
def creditsGroup(creds):
    if not creds:
        return "4: (No Credits)"

    try:
        f = float(creds.replace(",", "."))

        if f >= 0 and f <= 5:
            return "0: 0-5"
        elif f > 5 and f <= 10:
            return "1: 5,5-10"
        elif f > 10 and f <= 15:
            return "2: 10,5-15"
        elif f > 15:
            return "3: 15+"
        else:
            return "5: (Unexpected credits: " + str(f) + ")"
    except:
        return "4: (No Credits)"
        
##########################################
### Grouping based on number of verbs. ###
##########################################
def numberOfVerbsGroup(n):
    if n == 0:
        return "0 (  0 )"
    elif n >= 1 and n <= 4:
        return "1 (1-4 )"
    elif n >= 5 and n <= 10:
        return "2 (5-10)"
    elif n >= 11:
        return "3 ( 11+)"
    else:
        return "4 (" + str(n) + ")"

###################################################
### For each course, check for ambiguities etc. ###
###################################################

for cl in data:
    unis = ""
    first = 0
    moreThanOneUni = 0
    for c in data[cl]:
        if "University" in c:
            if first:
                first = 0
                unis = c["University"]
            else:
                if unis != c["University"]:
                    moreThanOneUni = 1
                    break
        
    for c in data[cl]:
        printed = 0

        thisType = "No CourseType"
        if "CourseType" in c:
            thisType = c["CourseType"]
        thisType = thisType.lower()
            
        level = "No level info"
        if "CourseLevel-ID" in c:
            level = c["CourseLevel-ID"]
        if level == "\\N": # unify levels with no info as ""
            level = ""
        if level == "-":
            level = ""

        scb = "No SCB info"
        if "SCB-ID" in c:
            scb = c["SCB-ID"]

        ### Filter based on type of course
        if thisType in types and not types[thisType]:
            addType(thisType + " (skipped)")
            continue
        
        ### Filter based on course level
        if level in levels and not levels[level]:
            addLevel(level + " (skipped)")
            continue

        ### Filter based on SCB field
        if scb in scbs and not scbs[scb]:
            addSCB(scb + " (skipped)")
            continue
        elif not scb in scbs and not scbs["other"]:
            addSCB(scb + " (skipped)")
            continue

        addType(thisType)
        addLevel(level)
        addSCB(scb)

        if scb in scbToSCBGroup:
            scbGr = scbToSCBGroup[scb]
        elif scb == "":
            scbGr = "(No SCB)"
        else:
            unknownSCB[scb] = 1
            scbGr = "(Unrecognized SCB)"

        creds = ""
        if not "ECTS-credits" in c or c["ECTS-credits"] == "":
            pass
        else:
            creds = c["ECTS-credits"]
            
        levelGr = levelGroup(level)

        creditsGr = creditsGroup(creds)

        addSCB(scbGr)
        addLevel(levelGr)
        
        UNI = ""
        if moreThanOneUni and "University" in c:
            UNI = c["University"] + " "
        
        if "ILO-list-sv" in c:
            addGoals(c["ILO-list-sv"])
        else:
            addGoals([])
            
        if "Bloom-list-sv" in c:
            addBloomList(c["Bloom-list-sv"], scb, level, thisType, c["University"], scbGr, levelGr, creditsGr)
        else:
            addBloomList([], scb, level, thisType, c["University"], scbGr, levelGr, creditsGr)
            
        if checks["ilo"]:
            if not "ILO-sv" in c or c["ILO-sv"].strip() == "":
                if "ILO-en" in c and c["ILO-en"] and len(c["ILO-en"]):
                    cPrint(UNI + c["CourseCode"] + " has no ILO-sv but has English: " + c["ILO-en"])
                else:
                    cPrint(UNI + c["CourseCode"] + " has no ILO-sv")

                printed = 1
                add("No ILO-sv", c["CourseCode"])
                
            elif not "ILO-list-sv" in c or len(c["ILO-list-sv"]) < 1:
                cPrint(UNI + c["CourseCode"] + " has empty ILO-list-sv: " + c["ILO-sv"])
                printed = 1
                add("No ILO list", c["CourseCode"])
                
            elif not "Bloom-list-sv" in c or len(c["Bloom-list-sv"]) < 1:
                cPrint(UNI + c["CourseCode"] + " has empty Bloom-list: " + str(c["ILO-list-sv"]))
                printed = 1
                add("No Bloom-list", c["CourseCode"])

            else:
                # Check if there are ridiculously many verbs
                ls = c["Bloom-list-sv"]
                flat = []
                for goal in ls:
                    for verb in goal:
                        flat.append(verb[2])
                n = len(flat)
                if n > VERBS_BEFORE_WARNING:
                    tmp = ""
                    for lsb in c["Bloom-list-sv"]:
                        for b in lsb:
                            tmp += b[1] + "(" + str(b[2]) + ") "
                    cPrint(UNI + c["CourseCode"] + " has very long Bloom-list (" + str(n) + "):\n" + tmp + "\n from \n'" + c["ILO-sv"] + "'")
                    printed = 1
                    add("Very many Bloom verbs in list", c["CourseCode"])
                if n == 0:
                    cPrint(UNI + c["CourseCode"] + " has 0 Bloom verbs:\n" + str(c["ILO-list-sv"]) + "\n\n" + str(c["ILO-sv"]))
                    printed = 1
                    add("0 Bloom verbs", c["CourseCode"])
                    
        if checks["en"] and (not "Prerequisites-en" in c or not c["Prerequisites-en"] or c["Prerequisites-en"].strip() == ""):
            cPrint(UNI + c["CourseCode"] + " has no Prerequisites-en")
            printed = 1
            add("Missing English prerequisites", c["CourseCode"])
            
        if checks["en"] and (not "ILO-en" in c or c["ILO-en"].strip() == ""):
            cPrint(UNI + c["CourseCode"] + " has no ILO-en")
            printed = 1
            add("Missing English ILO", c["CourseCode"])

        if checks["en"] and ("ILO-en" in c and c["ILO-en"].strip() != "") and (not "Bloom-list-en" in c or len(c["Bloom-list-en"]) <= 0):
            cPrint(UNI + c["CourseCode"] + " has no Bloom-list-en")
            printed = 1
            add("No English Bloom-list", c["CourseCode"])

        if checks["en"] and ("ILO-en" in c and c["ILO-en"].strip() != "") and ("Bloom-list-en" in c and len(c["Bloom-list-en"]) > 0):
            ls = c["Bloom-list-en"]
            flat = []
            for goal in ls:
                for verb in goal:
                    flat.append(verb[2])
            n = len(flat)
            
            if n > VERBS_BEFORE_WARNING:
                tmp = ""
                for lsb in c["Bloom-list-en"]:
                    for b in lsb:
                        tmp += b[1] + "(" + str(b[2]) + ") "
                cPrint(UNI + c["CourseCode"] + " has very long English Bloom-list (" + str(n) + "):\n" + tmp + "\n from \n'" + c["ILO-sv"] + "'")
                printed = 1
                add("Very many English Bloom verbs in list", c["CourseCode"])
            if n == 0:
                cPrint(UNI + c["CourseCode"] + " has 0 English Bloom verbs:\n" + str(c["ILO-list-en"]) + "\n\n" + str(c["ILO-en"]))
                printed = 1
                add("0 English Bloom verbs", c["CourseCode"])
            
        if checks["level"]:
            if not "CourseLevel-ID" in c:
                if not "CourseType" in c or c["CourseType"].lower() != "förberedande utbildning":
                    cPrint(UNI + c["CourseCode"] + " has no CourseLevel-ID")
                    printed = 1
                    add("Missing course level", c["CourseCode"])
            elif "XX" in c["CourseLevel-ID"]:
                cPrint(UNI + c["CourseCode"] + " has uninformative Course Level: " + c["CourseLevel-ID"] + " " + c["Prerequisites-sv"])
                printed = 1
                add("Uninformative course level", c["CourseCode"])

            if not checks["type"] and "CourseLevel-ID" in c and "CourseType" in c and c["CourseType"].lower() == "förberedande utbildning" and c["CourseLevel-ID"] != "":
                cPrint(UNI + c["CourseCode"] + " has non-empty CourseLevel-ID when it should be empty: " + c["CourseType"] + " " + c["CourseLevel-ID"])
                printed = 1
                add("Course level not empty for 'förberedande kurs'", c["CourseCode"])

        if checks["scb"] and (not "SCB-ID" in c or c["SCB-ID"] == ""):
            cPrint(UNI + c["CourseCode"] + " has no SCB-ID")
            printed = 1
            add("Missing SCB", c["CourseCode"])
        elif checks["scb"] and scbGr == "(Unrecognized SCB)":
            cPrint(UNI + c["CourseCode"] + " has unrecognized SCB-ID: '" + c["SCB-ID"] + "'")
            printed = 1
            add("Unrecognized SCB", c["CourseCode"])
            
        if checks["cred"]:
            if not "ECTS-credits" in c:
                cPrint(UNI + c["CourseCode"] + " has no ECTS-credits field")
                printed = 1
                add("Missing credits", c["CourseCode"])
            elif c["ECTS-credits"] == "":
                cPrint(UNI + c["CourseCode"] + " has empty ECTS-credits field")
                printed = 1
                add("Missing credits", c["CourseCode"])
            else:
                try:
                    tmp = str(c["ECTS-credits"]).replace(",", ".")
                    tmp = str(tmp)
                except:
                    cPrint(UNI + c["CourseCode"] + ", ECTS-credits value invalid? " + c["ECTS-credits"])
                    printed = 1
                    add("Invalid credits", c["CourseCode"])
                
        if checks["nonBloom"]:
            if "ILO-list-sv-tagged" in c:
                ls = c["ILO-list-sv-tagged"]
                blooms = []
                if "Bloom-list-sv" in c:
                    blooms = c["Bloom-list-sv"]
                for si in range(len(ls)):
                    s = ls[si]

                    for i in range(len(s)):
                        wtl = s[i]

                        if wtl["t"][:2] == "vb" and wtl["t"][-4:] != ".sfo" and not (wtl["t"][-3:] == "aux" or wtl["t"][-3:] == "kop" or wtl["t"][-3:] == "mod"):
                            found = 0
                            w = wtl["l"]
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
                                for wwi in range(len(s)):
                                    ww = s[wwi]
                                    g += ww["w"]
                                    if wwi == i:
                                        g += " (" + wtl["t"].upper() + ")"
                                    g += " "
                                g.strip()
                                addNonBloom(w, g, c["CourseCode"])
        
        if checks["type"]:
            if not "CourseType" in c:
                cPrint(UNI + c["CourseCode"] + " has no CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] == "":
                cPrint(UNI + c["CourseCode"] + " has empty CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] not in types and c["CourseType"].lower() not in types:
                cPrint(UNI + c["CourseCode"] + " has an unknown CourseType: '" + c["CourseType"] + "'")
                printed = 1
                add("Unrecognized course type", c["CourseCode"])
            if "CourseType" in c and c["CourseType"].lower() == "förberedande utbildning":
                if "CourseLevel-ID" in c and c["CourseLevel-ID"] != "" and (c["CourseLevel-ID"][0] == "A" or c["CourseLevel-ID"][0] == "G"):
                    cPrint(UNI + c["CourseCode"] + " is 'förberedande utbildning' but has CourseLevel-ID: " + c["CourseLevel-ID"])
                    printed = 1
                    add("Course level not empty for 'förberedande kurs'", c["CourseCode"])
        if checks["bloom"]:
            if not checks["ilo"] and (not "Bloom-list-sv" in c or len(c["Bloom-list-sv"]) < 1):
                cPrint(UNI + c["CourseCode"] + " has empty Bloom-list " + str(c["ILO-list-sv"]))
                printed = 1
                add("Empty Bloom-list", c["CourseCode"])
            if "Bloom-list-sv" in c and len(c["Bloom-list-sv"]) >= 1:
                bl = c["Bloom-list-sv"]
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
                            if prints["ambig"]:
                                print(c["CourseCode"] + " ambiguous Bloom: '" + exp + "' " + str(ambig[exp]) + " in: " + thisGoal)
                            addAmbig(exp)

        
        if printed:
            cPrint("\n " + "-"*30 + "\n")

    print(len(data[cl]), "courses in data")
    printStats()

    if checks["bloom"]:
        printBloom()
    if checks["nonBloom"]:
        printNonBloom()

    printLevel()
    printSCB()
    printBloomStats()
    print ()
