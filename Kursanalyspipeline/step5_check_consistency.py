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

bloomFile = ""
configFile = "step5.config"
unknown = 0

moreInputs = []

defaultSv = "data/bloom_revised_sv.txt"
defaultEn = "data/bloom_revised_en.txt"

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
    else:
        if sys.argv[i-1] != "-b" and sys.argv[i-1] != "-c" and sys.argv[i-1] != "-inp":
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

                bloomLexEn[exp] = bloomLevel
    except:
        bloomFileEn = ""
    for v in ambigEn:
        if v in bloomLexEn:
            ambigEn[v] = [bloomLexEn[v]] + ambigEn[v]
        else:
            print (bloomFileEn + " has verb '" + v + "' with ambiguous Bloom level but no default level.\n")

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

bloomStats = {"all":{}, "scb":{}, "level":{}, "type":{}, "uni":{}}
def addBloomList(ls, scb, level, ctype, uni):
    if not ctype in bloomStats["type"]:
        bloomStats["type"][ctype] = {"verbCounts":{}}
    if not level in bloomStats["level"]:
        bloomStats["level"][level] = {"verbCounts":{}}
    if not scb in bloomStats["scb"]:
        bloomStats["scb"][scb] = {"verbCounts":{}}
    if not uni in bloomStats["uni"]:
        bloomStats["uni"][uni] = {"verbCounts":{}}

    flat = []
    for goal in ls:
        for verb in goal:
            flat.append(verb[2])

            for lex in [bloomStats["scb"][scb], bloomStats["level"][level], bloomStats["type"][ctype], bloomStats["uni"][uni]]:
                if not verb[1] in lex["verbCounts"]:
                    lex["verbCounts"][verb[1]] = 1
                else:
                    lex["verbCounts"][verb[1]] += 1
    
    if len(flat) > 0:
        mn = 10
        mx = -1
        tot = 0
        mean = 0
        votes = {}
        for b in flat:
            tot += b
            if b > mx:
                mx = b
            if b < mn:
                mn = b
            if not b in votes:
                votes[b] = 1
            else:
                votes[b] += 1
        mean = tot / float(len(flat))
        n = len(flat)

        v = -1
        vm = 0
        for vv in votes:
            if votes[vv] > vm:
                vm = votes[vv]
                v = vv
        
        for lex in [bloomStats["scb"][scb], bloomStats["level"][level], bloomStats["type"][ctype], bloomStats["all"], bloomStats["uni"][uni]]:
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

            if not "common" in lex:
                lex["common"] = {}
            if not v in lex["common"]:
                lex["common"][v] = 1
            else:
                lex["common"][v] += 1

            if not "mean" in lex:
                lex["mean"] = []
            lex["mean"].append(mean)
            
            if not "val" in lex:
                lex["val"] = {}
            for b in flat:
                if not b in lex["val"]:
                    lex["val"][b] = 1
                else:
                    lex["val"][b] += 1

    else:
        for lex in [bloomStats["scb"][scb], bloomStats["level"][level], bloomStats["type"][ctype], bloomStats["all"], bloomStats["uni"][uni]]:

            if not "nVerbs" in lex:
                lex["nVerbs"] = {}
            if not 0 in lex["nVerbs"]:
                lex["nVerbs"][0] = 1
            else:
                lex["nVerbs"][0] += 1

def printBloomStats():
    if not "all" in bloomStats or not "max" in bloomStats["all"]:
        return
    
    print ("-"*15, "Bloom classifications", "-"*15)

    print ("-"*10, "Verbs per Bloom level", "-"*10)
    totCourses = 0
    for v in bloomStats["all"]["max"]:
        totCourses += bloomStats["all"]["max"][v]
    totBloom = 0
    for val in range(6):
        if val in bloomStats["all"]["val"]:
            totBloom += bloomStats["all"]["val"][val]

    for val in range(6):
        if val in bloomStats["all"]["val"]:
            c = bloomStats["all"]["val"][val]
            if totBloom > 0:
                proc = c / float(totBloom)
            else:
                proc = 0
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (totBloom, "classified verbs")
    
    print ("-"*10, "Maximum Bloom level per course", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStats["all"]["max"]:
            c = bloomStats["all"]["max"][val]
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
        if val in bloomStats["all"]["min"]:
            c = bloomStats["all"]["min"][val]
            tmp += c
            if totCourses > 0:
                proc = c / float(totCourses)
            procs = "{:>5}".format("{:2.1%}".format(proc))
            print ("{0: >2}: {1: >5} ({2:})".format(val, c, procs))
        else:
            print ("{0: >2}: {1: >5} (0%)".format(val, 0))
    print (tmp, "courses with Bloom data")

    print ("-"*10, "Mean Bloom level per course", "-"*10)
    m = 0
    n = len(bloomStats["all"]["mean"])
    for v in bloomStats["all"]["mean"]:
        m += v
    if n > 0:
        m = m / n
    print ("{0: .2}".format(m))
        
    print ("-"*10, "Most common Bloom level per course", "-"*10)
    tmp = 0
    for val in range(6):
        if val in bloomStats["all"]["common"]:
            c = bloomStats["all"]["common"][val]
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
    for val in bloomStats["all"]["nVerbs"]:
        ls.append(val)
    ls.sort()
    for val in ls:
        c = bloomStats["all"]["nVerbs"][val]
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

    for tmp in [["University", bloomStats["uni"]], ["SCB", bloomStats["scb"]], ["CourseLevel", bloomStats["level"]], ["CourseType", bloomStats["type"]]]:
        label = tmp[0]
        if (label == "University") or (label == "SCB" and prints["perSCB"]) or (label == "CourseLevel" and prints["perLevel"]) or (label == "CourseType" and prints["perType"]):
            lex = tmp[1]

            if len(lex.keys()) > 1:
            
                print("-"*10, label, "-"*10)

                printBloomHelper("max", "max Bloom", lex, 6)

                printBloomHelper("min", "min Bloom", lex, 6)

                ls = []
                rowLabel = "mean Bloom"
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

                print("-"*10, "Most common verbs", "-"*10)
                for uni in lex:
                    ls = []
                    for v in lex[uni]["verbCounts"]:
                        ls.append([lex[uni]["verbCounts"][v], v])
                    ls.sort(reverse=True)
                    print ("--->", uni)
                    for vi in range(len(ls)):
                        print ("{0: >5}: {1:}".format(ls[vi][0], ls[vi][1]))
                        if vi >= 10:
                            break
                print()


                printBloomHelper("common", "most common Bloom level", lex, 6)

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

                printBloomHelper("nVerbs", "#verbs", lex, VERBS_BEFORE_MORE_THAN+1)

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
        if tot > 0:
            procs = "{:>5}".format("{:2.1%}".format(scbCounts[s]/float(tot)))
            print ("{0: >4}: {1: >5} ({2:})".format(s, scbCounts[s], procs))
        else:
            print ("{0: >4}: {1: >5}".format(s, scbCounts[s]))
    
levCounts = {}
def addLevel(l):
    if not l in levCounts:
        levCounts[l] = 0
    levCounts[l] += 1

def printLevel():
    print ("\n", "-"*15, "Course Levels","-"*15)
    ls = []
    for l in levCounts:
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

###################################################
### For each course, check for ambiguities etc. ###
###################################################

for cl in data:
    
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

        if "Bloom-list-sv" in c:
            addBloomList(c["Bloom-list-sv"], scb, level, thisType, c["University"])
        
        if checks["ilo"]:
            if not "ILO-sv" in c or c["ILO-sv"].strip() == "":
                if "ILO-en" in c and c["ILO-en"] and len(c["ILO-en"]):
                    cPrint(c["CourseCode"] + " has no ILO-sv but has English: " + c["ILO-en"])
                else:
                    cPrint(c["CourseCode"] + " has no ILO-sv")

                printed = 1
                add("No ILO-sv", c["CourseCode"])
                
            elif not "ILO-list-sv" in c or len(c["ILO-list-sv"]) < 1:
                cPrint(c["CourseCode"] + " has empty ILO-list-sv: " + c["ILO-sv"])
                printed = 1
                add("No ILO list", c["CourseCode"])
                
            elif not "Bloom-list-sv" in c or len(c["Bloom-list-sv"]) < 1:
                cPrint(c["CourseCode"] + " has empty Bloom-list: " + str(c["ILO-list-sv"]))
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
                    cPrint(c["CourseCode"] + " has very long Bloom-list (" + str(n) + "):\n" + tmp + "\n from \n'" + c["ILO-sv"] + "'")
                    printed = 1
                    add("Very many Bloom verbs in list", c["CourseCode"])
                if n == 0:
                    cPrint(c["CourseCode"] + " has 0 Bloom verbs:\n" + str(c["ILO-list-sv"]) + "\n\n" + str(c["ILO-sv"]))
                    printed = 1
                    add("0 Bloom verbs", c["CourseCode"])
                    
        if checks["en"] and (not "Prerequisites-en" in c or not c["Prerequisites-en"] or c["Prerequisites-en"].strip() == ""):
            cPrint(c["CourseCode"] + " has no Prerequisites-en")
            printed = 1
            add("Missing English prerequisites", c["CourseCode"])
            
        if checks["en"] and (not "ILO-en" in c or c["ILO-en"].strip() == ""):
            cPrint(c["CourseCode"] + " has no ILO-en")
            printed = 1
            add("Missing English ILO", c["CourseCode"])

        if checks["en"] and ("ILO-en" in c and c["ILO-en"].strip() != "") and (not "Bloom-list-en" in c or len(c["Bloom-list-en"]) <= 0):
            cPrint(c["CourseCode"] + " has no Bloom-list-en")
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
                cPrint(c["CourseCode"] + " has very long English Bloom-list (" + str(n) + "):\n" + tmp + "\n from \n'" + c["ILO-sv"] + "'")
                printed = 1
                add("Very many English Bloom verbs in list", c["CourseCode"])
            if n == 0:
                cPrint(c["CourseCode"] + " has 0 English Bloom verbs:\n" + str(c["ILO-list-en"]) + "\n\n" + str(c["ILO-en"]))
                printed = 1
                add("0 English Bloom verbs", c["CourseCode"])
            
        if checks["level"]:
            if not "CourseLevel-ID" in c:
                if not "CourseType" in c or c["CourseType"].lower() != "förberedande utbildning":
                    cPrint(c["CourseCode"] + " has no CourseLevel-ID")
                    printed = 1
                    add("Missing course level", c["CourseCode"])
            elif "XX" in c["CourseLevel-ID"]:
                cPrint(c["CourseCode"] + " has uninformative Course Level: " + c["CourseLevel-ID"] + " " + c["Prerequisites-sv"])
                printed = 1
                add("Uninformative course level", c["CourseCode"])

            if not checks["type"] and "CourseLevel-ID" in c and "CourseType" in c and c["CourseType"].lower() == "förberedande utbildning" and c["CourseLevel-ID"] != "":
                cPrint(c["CourseCode"] + " has non-empty CourseLevel-ID when it should be empty: " + c["CourseType"] + " " + c["CourseLevel-ID"])
                printed = 1
                add("Course level not empty for 'förberedande kurs'", c["CourseCode"])

        if checks["scb"] and not "SCB-ID" in c:
            cPrint(c["CourseCode"] + " has no SCB-ID")
            printed = 1
            add("Missing SCB", c["CourseCode"])

        if checks["cred"]:
            if not "ECTS-credits" in c:
                cPrint(c["CourseCode"] + " has no ECTS-credits field")
                printed = 1
                add("Missing credits", c["CourseCode"])
            elif c["ECTS-credits"] == "":
                cPrint(c["CourseCode"] + " has empty ECTS-credits field")
                printed = 1
                add("Missing credits", c["CourseCode"])
            else:
                try:
                    tmp = str(c["ECTS-credits"]).replace(",", ".")
                    tmp = str(tmp)
                except:
                    cPrint(c["CourseCode"] + ", ECTS-credits value invalid? " + c["ECTS-credits"])
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
                cPrint(c["CourseCode"] + " has no CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] == "":
                cPrint(c["CourseCode"] + " has empty CourseType field")
                printed = 1
                add("Missing course type", c["CourseCode"])
            elif c["CourseType"] not in types and c["CourseType"].lower() not in types:
                cPrint(c["CourseCode"] + " has an unknown CourseType: '" + c["CourseType"] + "'")
                printed = 1
                add("Unrecognized course type", c["CourseCode"])
            if "CourseType" in c and c["CourseType"].lower() == "förberedande utbildning":
                if "CourseLevel-ID" in c and c["CourseLevel-ID"] != "" and (c["CourseLevel-ID"][0] == "A" or c["CourseLevel-ID"][0] == "G"):
                    cPrint(c["CourseCode"] + " is 'förberedande utbildning' but has CourseLevel-ID: " + c["CourseLevel-ID"])
                    printed = 1
                    add("Course level not empty for 'förberedande kurs'", c["CourseCode"])
        if checks["bloom"]:
            if not checks["ilo"] and (not "Bloom-list-sv" in c or len(c["Bloom-list-sv"]) < 1):
                cPrint(c["CourseCode"] + " has empty Bloom-list " + str(c["ILO-list-sv"]))
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
