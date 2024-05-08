import sys
import json
import re
import string
import sys

##############################
### check system arguments ###
##############################
doXX = 0
logging = 0
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-lev" or sys.argv[i] == "-l":
        doXX = 1
    elif sys.argv[i] == "-nl":
        doXX = 0
    elif sys.argv[i] == "-log":
        logging = 1
    else:
        print ("\nReads JSON from stdin, uses heuristics to extract goals from free text\nand to update GXX/AXX level tags based on prerequisites free text,\nprints result as JSON to stdout.")
        print ("\nusage options:")
        print ("     -l     update GXX/AXX tags where possible")
        print ("     -n     do not update GXX/AXX, only extract goals")
        print ("     -log   log debug information to " + sys.argv[0] + ".log\n")
        sys.exit(0)

############################
### read JSON from stdin ###
############################
data = {}

text = ""
for line in sys.stdin:
    text += line

try:
    data = json.loads(text)

    if isinstance(data, list):
        data = {"Course-list":data}

except Exception as e:
    print("No input data or non-JSON data?")
    print(str(e))
    sys.exit(0)

#####################################################################
#### Clean up things that sometimes are weird in the source data ####
#####################################################################
clexp1 = re.compile("^[0-9.•*·–…]*\s*")
clexp2 = re.compile("\s*[0-9.•*·–…]*\s*[.]*\s*$")
hpExp = re.compile("[A-ZÅÄÖ][a-zåäö, ]*, [0-9][0-9,.]*\s*hp[.]?")
def cleanStr(s):
    res = s.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ")
    res = re.sub("<\\s*br\\s*/*\\s*>", "\n", res, re.I)
    res = re.sub("[.][.][.]*", ".", res)
    res = re.sub("</?\\w*/?>", " ", res)
    res = re.sub("\s\s\s*", " ", res)
    res = re.sub("^–\s*", " ", res)
    res = res.strip()
    res = clexp1.sub(" ", res)
    res = clexp2.sub(" ", res)
    res = res.replace(" - ", " ")
    res = res.replace(" - ", " ")
    res = re.sub(" [ ]*", " ", res)
    if hpExp.match(res):
        res = ""
    if len(res) < SHORTEST_GOAL:
        res = ""
    res = res.strip()
    return res

def cleanUp(c):
    # Fix weirdness that some KTH texts have

    c["Prerequisites-sv"] = cleanStr(c["Prerequisites-sv"])
    c["ILO-sv"] = cleanStr(c["ILO-sv"])

###############
### Logging ###
###############
if logging:
    logf = open(sys.argv[0] + ".log", "w")
    
def logLs(s, ls):
    if not logging:
        return
    
    logf.write(s)
    logf.write("\n")

    for m in ls:
        logf.write("  ")
        logf.write(str(m))
        logf.write("\n")

def log(s, S):
    if not logging:
        return

    logf.write(s)
    logf.write(" ")
    logf.write(str(S))
    logf.write("\n")

#########################################################################
### See if 'Prerequisites' free text has information that can be used ###
### to update GXX or AXX to something more informative.               ###
#########################################################################
def updateLevelAttribute(c):
    if not "CourseLevel-ID" in c or not c["CourseLevel-ID"] or len(c["CourseLevel-ID"]) < 3 or c["CourseLevel-ID"][1] != "X":
        return
    
    if "Prerequisites-sv" in c:
        if c["CourseLevel-ID"] == "GXX" and not c["Prerequisites-sv"]:
            # if no prerequisites are listed at all, G1N?
            c["CourseLevel-ID"] = "G1N"
            return
        
    if "Prerequisites-sv" in c and c["Prerequisites-sv"]:
        
        pr = c["Prerequisites-sv"]
        
        if c["CourseLevel-ID"] == "GXX": # If "Grundläggande behörighet" then G1N
            if re.search("grundläggande.?(högskole)*behörighet", pr, re.I):
                c["CourseLevel-ID"] = "G1N"
                return
            
        courseCodes = re.findall("[A-Z][A-Z][0-9][0-9][0-9][0-9]", pr)
        haveAdvanced = 0
        for cc in courseCodes:
            if cc[2] == "2": # advanced course
                haveAdvanced = 1

        if not haveAdvanced and "avancerad nivå" in pr.lower() and not "/avancerad nivå" in pr.lower():
            haveAdvanced = 1
            
        if c["CourseLevel-ID"] == "AXX":
            if haveAdvanced: # if advanced prerequisite then A1F
                c["CourseLevel-ID"] = "A1F"
                return

        if c["CourseLevel-ID"] == "GXX":
            if len(courseCodes) > 0: # If we have at least some course requirements above basics, then G1F
                c["CourseLevel-ID"] = "G1F"
                return

#######################################
#### Language identification stuff ####
#######################################
MAXTRIGRAMS = 1000
sweTrigramLookup = {}
i = 0
for line in open("data/swedish_trigrams.txt").readlines():
    tri = line.strip()
    sweTrigramLookup[tri] = i
    i += 1
    if i >= MAXTRIGRAMS:
        break
i = 0
engTrigramLookup = {}
for line in open("data/english_trigrams.txt").readlines():
    tri = line.strip()
    engTrigramLookup[tri] = i
    i += 1
    if i >= MAXTRIGRAMS:
        break

MIN_LEN_LANGUAGE = 30
def identifyLanguage(text):
    counts = {}
    words = text.lower().strip(string.punctuation).split()

    for word in words:
        for c in range(len(word) - 2):
            tri = word[c:c+3]

            if tri in counts:
                counts[tri] += 1
            else:
                counts[tri] = 1

    triList = []
    for tri in counts:
        triList.append([-counts[tri], tri])
    triList.sort()

    totSwe = 0
    totEng = 0
    
    for t in range(min(len(triList), MAXTRIGRAMS)):
        tri = triList[t][1]
        
        if tri in sweTrigramLookup:
            swe = sweTrigramLookup[tri]
        else:
            swe = -1

        if tri in engTrigramLookup:
            eng = engTrigramLookup[tri]
        else:
            eng = -1

        if swe < 0:
            distSwe = MAXTRIGRAMS
        else:
            distSwe = abs(swe - t)
        if eng < 0:
            distEng = MAXTRIGRAMS
        else:
            distEng = abs(eng - t)

        totSwe += distSwe
        totEng += distEng

    if totSwe <= totEng:
        return "sv"
    return "en"

#######################################
### Check language of prerequisites ###
#######################################
def checkPre(c):
    if not "Prerequisites-sv" in c or not c["Prerequisites-sv"]:
        c["Prerequisites-sv"] = ""
    if not "Prerequisites-en" in c or not c["Prerequisites-en"]:
        c["Prerequisites-en"] = ""
    
    sv = c["Prerequisites-sv"]
    en = c["Prerequisites-en"]

    langSv = identifyLanguage(sv)
    langEn = identifyLanguage(en)

    if langSv != "sv":
        low = sv.lower()
        if "historia" in low or "pedagogik" in low or "ö" in low: # common error in language classification
            langSv = "sv"
    
    if langSv != "sv" and len(sv):
        log("Prerequisites-sv not Swedish?", sv)
            
    if (langEn == "sv" or len(en) <= 0) and langEn == "sv" and len(en):
        c["Prerequisites-sv"] = en
    elif langSv != "sv" and len(sv) > MIN_LEN_LANGUAGE:
        c["Prerequisites-sv"] = ""
        
    if langEn != "en" and len(en):
        log("Prerequisites-en not English?", en)
    
    if (langEn != "en" or len(en) <= 0) and langSv == "en" and len(sv):
        c["Prerequisites-en"] = sv
    elif langEn != "en" and len(en) > MIN_LEN_LANGUAGE:
        c["Prerequisites-en"] = ""

#######################################################################
### Regular expressions to capture different ways goals are written ###
#######################################################################

### KTH courses often use HTML <li>-lists for goals
###  "<p>Efter avslutad kurs skall studenten kunna:</p><ul><li>förklara grundläggande koncept av ... </li><li>..."
### (example course KTH SG2226)
htmlListExp = re.compile("<li>(.*?)(?:</?li>)", re.I)

### KTH courses can use HTML <p>-elements for goals
###   "<p>Efter genomförd kurs ska studenten kunna</p><p>• upprätta resurser för ... ,</p><p>\u2022 utföra spaning ..."
###   (example course KTH FEP3370)
pListExp = re.compile("<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*(?:</?p>)", re.I)

### KTH courses can use HTML <BR> breaks to list goals
###   "Efter kursen ska du kunna:<br />• Beräkna hur att uppföra och driva olika processer inom hållbar vatten- och avloppsrening.<br />• Applicera kemiska och biologiska kunskaper ..."
###   (example course KTH AE2302)
brListExp = re.compile("<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*(.*?)\s*(?:<)", re.I)

### Courses can use various dots/hyphens/stars as markers for goals
###   "Efter genomförd kurs ska du kunna * identifiera grundläggande begrepp, ... inom reinforcement learning * utveckla och systematiskt testa ... inom reinforcement learning * experimentellt ..."
###   (example course KTH FDD3359)
dotListExp = re.compile("[•*·–…;]\s*[0-9]*[.]?\s*([^•*·–…;\n]*)\s*", re.I)

### Courses can list each goal on a separate line
###   "Efter att ha genomgått kursen förväntas studenten:
###    • Förstå principerna för nationalräkenskapernas uppläggning och för beräkningar av BNP
###    • Kunna tolka innebörden av makroekonomisk statistik
###    ... "
###   (example course SU EC1212)
newlineListExp = re.compile("\n\s*[-o•*·–.—]\s*[0-9]*[.]?\s*([^\n]*)", re.I)

### Some courses list goals on one long line with " - " as a marker for each goal
###   "ska studenten kunna 1. Kunskap och förståelse - Redogöra
###   för teorier om demokratisering och autokratisering på ett
###   samhällsvetenskapligt sätt, både muntligt och skriftligt
###   (kunskap) - Förstå och med egna ord förklara teorier ..."
###   (example course SU SV7098)
inlineHyphenListExp = re.compile(" - (.*?) - ", re.MULTILINE + re.DOTALL)

### Some courses enumerate goals with Roman numerals
###   "För godkänt resultat skall studenten kunna:
###     I.     kritiskt granska statistiska undersökningar utifrån ett vetenskapligt perspektiv,
###     II.    formulera statistiska modeller för elementära problem inom olika tillämpningsområden,
###     ... "
###   (example course SU ST111G)
romanListExp = re.compile("\n[IVX][IVX]*\s*[.]\s\s*([^\n]*)", re.I)

### Some courses enumerate goals with Arabic numerals
###    "För godkänt resultat på kursen ska studenten kunna:
###     <i>Kunskap och förståelse</i>
###     1. Redogöra för relevanta begrepp för att beskriva omfattningen av sjukdomar i den allmänna befolkningen
###     2. Beskriva våra vanligaste folkhälsoproblem och folksjukdomar och redogöra för förekomst och sjukdomsorsaker
###     ... "
###   (example course SU PH03G0)
arabicListExp = re.compile("\n[0-9][0-9]*\s*[).]\s*([^\n]*)", re.I)

arabicListExp2 = re.compile("[0-9][0-9]*\s*[).]\s*(....*?)\s*\\(?[0-9]*[0-9][.)]", re.I)

### Some courses enumerate goals with (a), (b), or (1), (2), etc. 
###    "Kursen syftar till (a) att öka deltagarnas förståelse ... ; (b) att ge de färdigheter som behövs för tillämpad dataanalys ... ; och (c) att ge träning i ... "
###   (example course SU PSMT15)
parListExp = re.compile("\n\s*\\([0-9a-zA-Z]\\)\s*([^\n]*)", re.I)
parListExp2 = re.compile("\s[0-9a-zA-Z]\\)\s*([^\\)][^\\)]*)", re.I)

### Some courses enumerate goals with X
###    "... Xvisa fördjupad kunskap om och förståelse för
###    skadeståndsrättens begrepp och principer , Xvisa fördjupad
###    kunskap om och förståelse för skadeståndsrättens struktur
###    och systematik samt Xvisa fördjupad kunskap ..."
###   (example course SU JU369A)
xListExp = re.compile("\sX\s*(..*)\sX*", re.I)

### Some courses specify goals with lines like "ska ... kunna ..."
###   "Den studerande skall efter genomgången kurs kunna
###   identifiera samt, såväl muntligt som skriftligt, redogöra
###   för hur förhållandet mellan människa och natur avspeglas och
###   gestaltas i de senaste hundra årens svenska barnlitteratur.
###   Detta inbegriper förtrogenhet med den barnlitterära
###   konventionen och en förmåga att relatera iakttagelserna till
###   en vidare samhällelig och kulturell kontext."
###  (example course SU LV1011)
skaKunnaExp = re.compile("[Kk]unna(..*?)[\n]", re.I)

### Some courses write goals as "Efter kursen kan ... " (less common than "ska kunna")
###   "Studenten kan tillämpa grundläggande arbetsmarknadsekonomiska begrepp ..."
###   (example course SU ATF012)
kanExp = re.compile("\skan\s(..*\s..*?)[.]", re.I)

### Goals can be written as "studenten ska vara förtrogen med" or
### "studenten ska ha förmåga att"
###   "Efter genomgången kurs ska studenten
###    1)      vara förtrogen med begreppen kultur, mångkulturalism och andra för kunskapsområdet centrala begrepp som exkluderings- och inkluderingprocesser präglar relationer mellan majoritets- och minoritetsbefolkningen samt aktuella teorier kring mångkulturalism och etnicitet
###    2)      ha förmåga att integrera relevanta teorier och metoder om mångkulturalism i en vägledningssituation samt kunna reflektera över hur kulturella normer, värderingar och tankemönster påverkar förhållningssätt till människor i andra etniska grupper
###   (example course SU UC119F)
fortrogenExp = re.compile("\sförtrogen\s*i\s(.*?)[.]", re.I)
formagaExp = re.compile("visa.*?\sförmåga.*?att\s*(.*?)[.]", re.I)

### Some courses list all goals on one line with arabic numerals enumerating, starting with "... kunna 1."
###   "... ska studenten kunna 1.Redovisa, diskutera och jämföra olika
###   historiskt kriminologiska studier. 2.Beskriva, ..."
###   (example course SU AKA132)
kunna1exp = re.compile("kunna.*1[. ].*2[. ]")

### Many courses have goals stated as "ska kunna:" and then one goal per line.
kunnaColonExp = re.compile("kunna:\s*?\n", re.I)

### Courses can have lists where each item starts with a Capital
### letter but not other wise noted:
###    "Efter avslutad kurs ska studenten kunna Visa goda kunskaper
###    ... konsekvenser. Analysera och tolka händelser ... "
###   (example course KTH MJ2416)
kunnaCapExp = re.compile("kunna:?\s*[A-ZÅÄÖ]", re.I)

kunnaHypExp = re.compile("kunna:?\s* -[a-zåäöA-ZÅÄÖ]", re.I)
kunnaHypExpM = re.compile(" -([a-zA-ZåäöÅÄÖ].*?)[.\n\"]", re.I)

### Some courses have goals stated as "ska kunna ... VERB <list of objects for VERB>
###   "Efter godkänd kurs ska studenten kunna självständigt och på ett strukturerat sätt skapa
###    - parametriserade detaljmodeller
###    - sammanställningsmodeller ..."
###   (example course KTH MG1028)
verbThenObjectsExp = re.compile("kunna[^a-zåäöA-ZÅÄÖ<]*(<[^>]*>)*([^\n•*·–…<:]*)\s*[\n•*·–…<:]", re.I)

### Some courses have goals stated as "Kursens mål är att ge studenterna ett tillfälle att ... VERB"
###   "Teknologerna får därigenom tillfälle att tillämpa sina kunskaper ..."
###   (example course KTH MF2025)
tillfalleExp = re.compile("tillfälle\s*att\s*([^•*·–….]*)\s*[•*·–….]", re.I)
traningExp = re.compile("träning\s*i\s*att\s*([^.]*)\s*[.]", re.I)

## maletExp = re.compile("målet.*är\s*att\s*([^.]*)\s*[.]", re.I) ### Skip this type of goal? Not well written.

parHeadingsExp = re.compile("\\([A-ZÅÄÖ]\w*:?\s*([0-9][0-9]*,?\s*(och)*(;\sEPA)*\s*)*\s*[0-9][0-9]*\s*\\)")

############################################################
### Expressions for removing motivation (not goals) text ###
############################################################
iSyfteExp = re.compile("<p>\s*i\s+syfte\s+att", re.I)
forAttExp = re.compile("<p>\s*för\s+att", re.I)
forAttGodkandExp = re.compile("<p>\s*för\s+att.*bli.*godkänd", re.I)

################################################################################
### Use heuristics to extract sentences with goals from the ILO-sv free text ###
################################################################################
def extractGoals(c):
    sv = c["ILO-sv"]
    en = c["ILO-en"]

    ######################################################################################
    ### Check language since there sometimes is English text in the Swedish field etc. ###
    ######################################################################################
    langSv = identifyLanguage(sv)
    langEn = identifyLanguage(en)

    if langSv != "sv" and len(sv):
        log("ILO-sv not Swedish? ", sv)
        
    if (langSv != "sv" or len(sv) <= 0) and langEn == "sv" and len(en):
        c["ILO-sv"] = en
    elif langSv != "sv" and len(sv) > MIN_LEN_LANGUAGE:
        c["ILO-sv"] = ""
        
    if langEn != "en":
        if len(en):
            log("ILO-en not English? ", en)
            
    if (langEn != "en" or len(en) <= 0) and langSv == "en" and len(sv):
        c["ILO-en"] = sv
    elif langEn != "en" and len(en) > MIN_LEN_LANGUAGE:
        c["ILO-en"] = ""
    
    sv = c["ILO-sv"]
    en = c["ILO-en"]

    #####################################################
    ### unify hyphens to simplify expression matching ###
    #####################################################
    sv = sv.replace("\n -", "\n–").replace("\n-", "\n–").replace("\n−", "\n–").replace(u"\uF095", "–")
    sv = sv.replace("\t", " ")


    sv = parHeadingsExp.sub(" ", sv) # remove things like "(Lärande mål 3 och 4)" or "(Modul 5, 6, och 7)"
    
    
    ##############################
    ### Fix some weird codings ###
    ##############################
    sv = sv.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ")
    sv = sv.replace("&eacute;", "é")
    sv = sv.strip()
    if len(sv) and sv[0] == '"':
        sv = sv[1:]
        if sv[-1] == '"':
            sv = sv[:-1]
    
    iloList = {}
   
    ###################################################################
    ### Remove motivation for having these goals from the goal text ###
    ###################################################################
    
    m = iSyfteExp.search(sv)
    if m:
        sv = iSyfteExp.split(sv)[0] # remove everything from "i syfte att" and forward
    else:
        m = forAttExp.search(sv)
        if m and m.start() > 0:
            m2 = forAttGodkandExp.search(sv)
            if not m2 or m2.start() < m.start():
                sv = forAttExp.split(sv)[0]  # remove everything from "för att" and forward

    
    
    found = 0

    m = htmlListExp.search(sv)
    if m:
        ls = htmlListExp.findall(sv)
        for l in ls: # remove duplicates
            ll = cleanStr(l)
            if len(ll):
                iloList[ll] = 1
                log("htmlListExp", ll)
                found = 1
    
    m = pListExp.search(sv)
    if m:
        ls = pListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("pListExp", l)
                found = 1

    m = brListExp.search(sv)
    if m:
        ls = brListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("brListExp", l)
                found = 1

    m = dotListExp.search(sv)
    if m:
        ls = dotListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("dotListExp", l)
                found = 1

    m = newlineListExp.search(sv)
    if m:
        ls = newlineListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("newlineListExp", l)
                found = 1

    m = xListExp.search(sv)
    if m:
        parts = sv.split(" X")
        ls = []
        for i in range(1, len(parts)):
            ls.append(cleanStr(parts[i]))

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("xListExp", l)
                found = 1

    m = inlineHyphenListExp.search(sv)
    if m:
        parts = sv.split(" - ")
        ls = []
        for i in range(1, len(parts)):
            ls.append(cleanStr(parts[i]))

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("inlineHyphenListExp", l)
                found = 1

    m = romanListExp.search(sv)
    if m:
        ls = romanListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("romanListExp", l)
                found = 1

    m = arabicListExp.search(sv)
    if m:
        ls = arabicListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            tmp = l
            if tmp[-2:] == "hp":
                pass # skip lines like "1. Tysk lingvistik, 6 hp" (sub-parts of a course)
            elif tmp.find("Moment ") >= 0 or tmp.find("Modul") >= 0:
                pass # skipe lines like "Moment 1. ..."
            elif len(l):
                iloList[tmp] = 1
                log("arabicListExp", tmp)
                found = 1

    m = parListExp.search(sv)
    if m:
        ls = parListExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])

        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("parListExp", l)
                found = 1

    m = parListExp2.search(sv)
    if m:
        ls = []
        while m:
            ls.append(m.group(1))
            m = parListExp2.search(sv, m.end() - 3)
        
        for l in range(len(ls)):
            ll = cleanStr(ls[l])
            if len(ll):
                iloList[ll] = 1
                log("parListExp2", ll)
                found = 1

    m = arabicListExp2.search(sv)
    if m:
        ls = []
        while m:
            ls.append(m.group(1))
            m = arabicListExp2.search(sv, m.end() - 3)
        
        for l in range(len(ls)):
            ll = cleanStr(ls[l])
            if len(ll):
                iloList[ll] = 1
                log("arabicListExp2", ll)
                found = 1

    if not found:
        m = skaKunnaExp.search(sv)
        if m:
            ls = skaKunnaExp.findall(sv)
            for l in range(len(ls)):
                ls[l] = cleanStr(ls[l])
            
            for l in ls: # remove duplicates
                if len(l):
                    iloList[l] = 1
                    log("skaKunnaExp", l)
                    found = 1
            
    m = fortrogenExp.search(sv)
    if m:
        ls = fortrogenExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("fortrogenExp", l)
                found = 1

    m = formagaExp.search(sv)
    if m:
        ls = formagaExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("formagaExp", l)
                found = 1
            
    m = kanExp.search(sv)
    if m:
        while m: # This pattern overgenerates a lot, so we should filter out obvious mistakes
            if sv[m.start() - 3:m.start()] != "som":
                l = cleanStr(m.group(1))
                if l[:6] != "därför":
                    p = l.find(" ")
                    if p < 0 or l[p-1] != "s": # passive form verbs are typically mistakes
                        iloList[l] = 1
                        log("kanExp", l)
                        found = 1
            m = kanExp.search(sv, m.end())

    m = verbThenObjectsExp.search(sv)
    if m:
        ls = verbThenObjectsExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l][1])
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("verbThenObjectsExp", l)
                found = 1
    
    m = tillfalleExp.search(sv)
    if m:
        ls = tillfalleExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("tillfalleExp", l)
                found = 1

    m = traningExp.search(sv)
    if m:
        ls = traningExp.findall(sv)
        for l in range(len(ls)):
            ls[l] = cleanStr(ls[l])
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l] = 1
                log("traningExp", l)
                found = 1

    # m = maletExp.search(sv)
    # if m:
    #     ls = maletExp.findall(sv)
    #     for l in range(len(ls)):
    #         ls[l] = cleanStr(ls[l])
            
    #     for l in ls: # remove duplicates
    #         if len(l):
    #             iloList[l] = 1
    #             log("maletExp", l)
    #             found = 1
    

    p = sv.find("unna:\n\n")
    ls = []
    if p > 0:
        p += 7
        p2 = sv.find("\n\n", p)
        if p2 > 0:
            tmp = sv[p:]
            tmpLs = tmp.split("\n\n")

            ls += tmpLs
    if len(ls):
        for l in ls: # remove duplicates
            if len(l):
                iloList[l.strip()] = 1
                log("unna:", l.strip())
                found = 1
    
    # if not found:
    #     m = kunna1exp.search(sv)
    # else:
    #     m = 0 # if some other type of list has been found, these things are likely to be subsection headings, not goals
    m = kunna1exp.search(sv) # These can also be section headings, but they will typically not have Bloom verbs so they will be removed later anyway
    if m:
        part = sv[m.start()-2:]
        parts = re.split("[0-9][0-9]*[. ]", part)
        
        ls = []
        for i in range(1, len(parts)):
            ls.append(cleanStr(parts[i]))
            
        for l in ls: # remove duplicates
            if len(l):
                iloList[l.strip()] = 1
                log("kunna1exp", l.strip())
                found = 1
                
    
    p = kunnaColonExp.search(sv)
    ls = []
    while p:
        p = p.span()[1]
        p2 = sv.find("\n\n", p)

        if p2 < 0:
            p2 = len(sv)
        tmp = sv[p:p2]
        tmpLs = tmp.split("\n")

        ls += tmpLs
            
        p = kunnaColonExp.search(sv, p)
    if len(ls):
        for l in ls: # remove duplicates
            if len(l):
                iloList[l.strip()] = 1
                log("kunnaColonExp", l.strip())
                found = 1

    m = kunnaCapExp.search(sv)
    if m:
        ls = []

        p = m.end() - 1
        p2 = p + 1

        while p2 < len(sv):
            if sv[p2].isupper():
                ls.append(cleanStr(sv[p:p2]))
                p = p2
            p2 += 1
        if p2 >= len(sv) and p2 - p > 3:
            ls.append(cleanStr(sv[p:p2]))
        
        for l in ls: # remove duplicates
            if len(l):
                if l[-2:] == "hp":
                    pass
                elif l.find("Moment ") >= 0 or l.find("Modul") >= 0:
                    pass # skipe lines like "Moment 1. ..."
                else:
                    iloList[l] = 1
                    log("kunnaCapExp", l)
                    found = 1
            
    m = kunnaHypExp.search(sv)
    if m:
        ls = []

        m2 = kunnaHypExpM.search(sv, m.end() - 2)

        while m2:
            ls.append(m2.group(1))
            m2 = kunnaHypExpM.search(sv, m2.end())
        if len(ls):
            for l in ls: # remove duplicates
                if len(l):
                    iloList[cleanStr(l)] = 1
                    log("kunnaHypExp", l)
                    found = 1

    p = sv.find(":</p>")
    if p > 0:
        p = sv.find("<p>",p)
    ls = []
    while p > 0:
        p += 3
        p2 = sv.find("</p>", p)

        if p2 < 0:
            p2 = len(sv)

        ls.append(sv[p:p2])
            
        p = sv.find("<p>",p2)
    if len(ls):
        for l in ls: # remove duplicates
            if len(l):
                iloList[l.strip()] = 1
                log(":<p>", l.strip())
                found = 1
        
    if not found:
        p = sv.find("kunna")
        if p > 0:
            tmp = sv[p:]
            tmp = cleanStr(tmp)
            iloList[tmp] = 1
            log("Add almost everything", tmp)
            found = 1
            
    if not found: # If not found, add the whole text ?
        if sv and len(sv) > 1:
            iloList[cleanStr(sv)] = 1
            log("Add everything", sv)

    ls = []
    content = re.compile("[a-zA-ZåäöÅÄÖ]")
    for l in iloList:
        ll = cleanStr(l)
        if content.search(ll):
            ls.append(ll)
    ls.sort()
    
    return ls

##########################################################################
### Check list for duplicates and substrings that are completely found ###
### in other strings, and remove them                                  ###
##########################################################################
SHORTEST_GOAL=4
def dupcheck(ls):
    res = []
    
    def lenf(s):
        return len(s)
    ls.sort(key=lenf)
    
    for s in ls:
        skip = 0
        if len(s) >= SHORTEST_GOAL:
            for i in range(len(res)):
                ss = res[i]
                if s.find(ss) >= 0 or ss.find(s) >= 0:
                    skip = 1
                    log("dupcheck, duplicates: ======>", s + "<======>" + ss + "<=====")

                    if len(s) > len(ss): # generally, we prefer the shorter match?
                        if s.find(" - " + ss) >= 0 or s.find("\n- " + ss) >= 0:
                            res[i] = s
                        else:
                            if ss.find(" ") < 0 and s.find(" ") > 0: # if short string is only one word, skip it
                                res[i] = s
                            else:
                                res[i] = ss
                    else:
                        if ss.find(" - " + s) >= 0 or ss.find("\n- " + s) >= 0:
                            res[i] = ss
                        else:
                            if s.find(" ") < 0 and ss.find(" ") > 0: # if short string is only one word, skip it
                                res[i] = ss
                            else:
                                res[i] = s
                    break
        if not skip and len(s) >= SHORTEST_GOAL:
            log("dupcheck, new goal: ", s)
            res.append(s)
    return res

######################################################################
### Check if a goal starts with upper or lower case. If lower case ###
### (i.e. probably not a complete sentence), add a dummy sentence  ###
### head.                                                          ###
######################################################################
def startcheck(ls):
    res = []
    for si in range(len(ls)):
        s = ls[si]
        for i in range(len(s)):
            if s[i].isupper():
                break
            if s[i].islower():
                s = "Hon ska kunna " + s
                break

        if not s[-1] in string.punctuation:
            s += " ."
        res.append(s)
    return res

######################################
### For each course, extract goals ###
######################################
for c in data["Course-list"]:
    iloList = extractGoals(c)
    iloList = dupcheck(iloList)
    iloList = startcheck(iloList)
    c["ILO-list-sv"] = iloList
    
    cleanUp(c)

    if doXX:
        updateLevelAttribute(c)

    checkPre(c)


##############################
### Print result to stdout ###
##############################
print(json.dumps(data))
