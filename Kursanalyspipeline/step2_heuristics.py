import sys
import json
import re
import string
import sys

from timeit import default_timer as timer


SKIP_VG = 1 # Ignore goals that are for higher grades

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
    elif sys.argv[i] == "-VG":
        SKIP_VG = 0
    elif sys.argv[i] == "-noVG":
        SKIP_VG = 1
    else:
        print ("\nReads JSON from stdin, uses heuristics to extract goals from free text\nand to update GXX/AXX level tags based on prerequisites free text,\nprints result as JSON to stdout.")
        print ("\nusage options:")
        print ("     -l     update GXX/AXX tags where possible")
        print ("     -n     do not update GXX/AXX, only extract goals")
        print ("     -VG    keep goals for higher grades")
        print ("     -noVG  ignore goals for higher grades")
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
SHORTEST_GOAL=4
clexp1 = re.compile("^[0-9.•*·–…]*\s*")
clexp2 = re.compile("\s*[0-9.•*·–…]*\s*[.]*\s*$")
hpExp = re.compile("[A-ZÅÄÖ][a-zåäö, ]*, [0-9][0-9,.]*\s*hp[.]?")
def cleanStr(s):
    res = s.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ")
    res = re.sub("<\\s*br\\s*/*\\s*>", "\n", res, re.I)
    res = re.sub("[.][.][.]*", ".", res)
    res = re.sub("</?\\w*/?>", " ", res)
    res = re.sub("<br\s*/>", " ", res)
    res = re.sub("Kunskap och förståelse-?", "", res)
    res = re.sub("Färdighet(er)? och förmåga-?", "", res)
    res = re.sub("Värderingsförmåga och förhållningssätt-?", "", res)
    res = res.replace("Efter genomgången kurs förväntas studenterna kunna", "")
    res = res.replace("Efter avslutad kurs förväntas studenterna kunna", "")
    res = res.strip()
    if res[-7:] == ", kunna":
        res = res[:-7]
    res = re.sub("För godkänd kurs ska(([^ ]| [^ ]))*  ", "", res)
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
    res = res.strip()
    while len(res) and res[-1] == ",":
        res = res[:-1]
        res = res.strip()

    if len(res) < SHORTEST_GOAL:
        res = ""
    
    return res

def simpleCleanStr(s):
    res = s.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ")
    res = res.strip()
    
    return res

def cleanUp(c):
    # Fix weirdness that some KTH texts have

    c["Prerequisites-sv"] = simpleCleanStr(c["Prerequisites-sv"])
    c["ILO-sv"] = simpleCleanStr(c["ILO-sv"])

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
    logf.flush()

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

    text = re.sub("<[^>]+>", " ", text) # Remove HTML tags etc. that look like English
    
    # fix some common problems with mixed Swedish/English because English text quotes Swedish course names or similar things.
    low = text.lower()
    engWords = ["equivalent", "courses", "enrolled", "admitted", "programmes", "programming skill", "completed", "corresponding", "phd student"]
    sweWords = ["antagen till", "doktorand", "motsvarande", "matematik", "godkänd", "historia", "pedagogik", "ö"]
    if len(low) < MIN_LEN_LANGUAGE:
        for w in engWords:
            if low.find(w) >= 0:
                return "en"
        for w in sweWords:
            if low.find(w) >= 0:
                return "sv"
    
    
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
htmlListExpIndicator = re.compile("<[lL][Ii]>")

htmlListExpWrap = re.compile("(<[Pp]>)?[^<>]*kunna:?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)
htmlListExpWrap2 = re.compile("<.[Ll]>.*?</.[Ll]>", re.S)
htmlListExpWrap3 = re.compile("(<[Pp]>)?[^<>]*kunna\s*([^<>]{4,}):?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)

htmlListExp = re.compile("<[lL][Ii]>(.*?)(?=</?[Ll][Ii]>)", re.S)

htmlListExpWrapEn = re.compile("(<[Pp]>)?[^<>]*((know\s*how)|(able))\s*to:?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)
htmlListExpWrapEn3 = re.compile("(<[Pp]>)?[^<>]*((know\s*how)|(able))\s*to\s*([^<>]{4,}):?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)

### KTH courses can use HTML <p>-elements for goals
###   "<p>Efter genomförd kurs ska studenten kunna</p><p>• upprätta resurser för ... ,</p><p>\u2022 utföra spaning ..."
###   (example course KTH FEP3370)
pListExp = re.compile("<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*(?=</?p>)", re.S)
pListExpWrap = re.compile("(<p>)?[A-ZÅÄÖ][^<>]*?kunna:?\s*(</\s*p>)?\s*(<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*</?p>\s*)+", re.S)
pListExpWrapEn = re.compile("(<p>)?[A-ZÅÄÖ][^<>]*?((know\s*how)|(able))\s*to:?\s*(</\s*p>)?(<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*</?p>)+", re.S)

### KTH courses with LM1, LM2 ... etc
###    (example course KTH MF2088)
lm1Exp = re.compile("LM[0-9]+:?\s*(.*?)</p>", re.S)
lm1ExpWrap = re.compile("(LM[0-9]+(.*?)</p>)(.*?LM[0-9]+(.*?)</p>)+", re.S)

### KTH courses can use HTML <BR> breaks to list goals
###   "Efter kursen ska du kunna:<br />• Beräkna hur att uppföra och driva olika processer inom hållbar vatten- och avloppsrening.<br />• Applicera kemiska och biologiska kunskaper ..."
###   (example course KTH AE2302)
brListExp = re.compile("<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*([^<]*)\s*", re.S)
brListExpWrap = re.compile("[A-ZÅÄÖ][^<>]*?[kK]unna:?\s*(<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*([^<]*)\s*)+", re.S)
brListExpWrap2 = re.compile("(<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*([^<]*)\s*)+", re.S)
brListExpWrapEn = re.compile("[A-Z][^<>]*?((know\s*how)|(able))\s*to:?\s*(<?br\s*/?>\s*[-o•*·–]\s*[0-9]*[.]?\s*([^<]*)\s*)+", re.S)
brListIndicator = re.compile("br\s*/?>")

### Courses can list each goal on a separate line
###   "Efter avslutad kurs ska den studerande ha  
###    - förvärvat grundläggande kunskaper om Sara Lidmans författarskap.
###    - studerat och analyserat ett representativt urval texter ur Sara Lidmans författarskap.
###    - fått en första orientering om samt teoretiska och litteraturhistoriska redskap för att förstå den samtida norrländska litteraturen."
###   (example course UMU 1LV033)
newlineListExp = re.compile("\n\s*[-o•*·–.—]\s*[0-9]*[.]?\s*([^\n]*)", re.I)
newlineListExpWrap = re.compile("(\n\s*[-o•*·–.—]\s*[0-9]*[.]?\s*([^\n]*)){2,}", re.I)

### Courses can use various dots/hyphens/stars as markers for goals
###   "Efter genomförd kurs ska du kunna * identifiera grundläggande begrepp, ... inom reinforcement learning * utveckla och systematiskt testa ... inom reinforcement learning * experimentellt ..."
###   (example course KTH FDD3359)
# dotListExp = re.compile("[•*·–…;]\s*[0-9]*[.]?\s*(([^•*·…;\n\s\\–]|( [^•*·…;\n\\–\s])){4,})", re.S)
dotListExp = re.compile("[-–•*·…]\s*[0-9]*[.]?\s*(([^-–•*·…\n\s]|( [^-–•*·…\n\s])){4,})(?=$|[.]|<|[-–•*·…\n\s]|([(]Del))", re.S)
# dotListExpWrap = re.compile("[•*·–…;]\s*[0-9]*[.]?\s*([^•*·…;\n\s\\–]|( [^•*·…;\n\\–])){4,}(\s*.*?[•*·–…;]\s*[0-9]*[.]?\s*([^•*·…;\n\s\\–]|( [^•*·…;\n\\–\s])){4,})+", re.S)
dotListExpWrap = re.compile(r'[-–•*·…]\s*[0-9]*[.]?\s*([^-–•*·…\n\s]|( [^-–•*·…\n])){4,}(\s*.*?[-–•*·…]\s*[0-9]*[.]?\s*([^-–•*·…\n\s]|( [^-–•*·…\n\s])){4,})+', re.S)


dotListBeforeExp = re.compile("((\s\s[a-zåäöA-ZÅÄÖ][a-zåäö\s]{4,})?[–•*·…]\s*[0-9]*[.]?\s*([^–•*·…\n\s]|( [^–•*·…\n\s])){4,})(?=$|[.]|<|[–•*·…\n\s]|([(]Del))", re.S)
dotListBeforeExpWrap = re.compile("\s\s([a-zåäöA-ZÅÄÖ][a-zåäö\s]{4,})[–•*·…]\s*[0-9]*[.]?\s*([^–•*·…\n\s]|( [^–•*·…\n])){4,}(\s*.*?\s\s([a-zåäöA-ZÅÄÖ\s]{4,})[–•*·…]\s*[0-9]*[.]?\s*([^–•*·…\n\s]|( [^–•*·…\n\s])){4,})+", re.S)

### Studenten skall efter avslutad kurs behärska en grundläggande
### orientering i ämnesområdet teater i Sverige och kunna visa en
### förmåga att o diskutera olika aspekter av historiografi med
### avseende på teater i Sverige o analysera och diskutera olika
### aspekter av svensk kultur- och teaterpolitik.
dotListOExp = re.compile(" o ((([^ \n])|(\n[^\n])|( [^o])|( o[^ ])){4,}[^ ])", re.S)
dotListOExpWrap = re.compile("(Delkurs\s[0-9]+)?( o ((([^ ])|( [^o])|( o[^ ])){4,}))+", re.S)

threedotListExp = re.compile("\.\.\.\s*([^.]{4,}.*?)(?=$|(\s*\.\.\.)|(\n\n))", re.S)
threedotListExpWrap = re.compile("\.\.\.(.*?)(\.\.\..*){3,}", re.S)


###    (example course UMU 2PS273)
oListExp = re.compile("[oO]\s((([^\n])|(\n[^\n])){4,}?)\\.")
oListExpWrap = re.compile("([.\s][oO]\s(([^\n])|(\n[^\n]))*){3,}")

### Some courses list goals on one long line with " - " as a marker for each goal
###   "ska studenten kunna 1. Kunskap och förståelse - Redogöra
###   för teorier om demokratisering och autokratisering på ett
###   samhällsvetenskapligt sätt, både muntligt och skriftligt
###   (kunskap) - Förstå och med egna ord förklara teorier ..."
###   (example course SU SV7098)
inlineHyphenListExp = re.compile(" - +(([^ ]|( [^- ]))+)", re.S)
inlineHyphenListExpWrap = re.compile("( - +([^ ]|( [^- ])){4,})(.*( - +(([^\n ])|( [^- ])|(\n[^\n])){4,}))+", re.S)
inlineHyphenIndicator = re.compile("^(.(?!innehålla))* - ", re.S)

### Some courses enumerate goals with Roman numerals
###   "För godkänt resultat skall studenten kunna:
###     I.     kritiskt granska statistiska undersökningar utifrån ett vetenskapligt perspektiv,
###     II.    formulera statistiska modeller för elementära problem inom olika tillämpningsområden,
###     ... "
###   (example course SU ST111G)
# romanListExp = re.compile("[IVX]+\s*[.]\s+([^IVX]*)", re.S)
romanListExp = re.compile("[IVX]+\s*[.]\s+((([^IVX\n])|(\n[^\n]))*)", re.S)
romanListExpWrap = re.compile("([A-ZÅÄÖ].*?kunna:?\s*)(\s*I\s*[.]\s+([^IVX ]|( [^IVX ]))+)(\s*[IVX]+\s*[.]\s+([^IVX ]|( [^IVX ]))+)*", re.S)

romanListIndicator = re.compile("kunna:?\s*I", re.S)
romanListIndicatorEn = re.compile("((know\s*how)|(able))\s*to:?\s*I", re.S)

### Some courses enumerate goals with Arabic numerals
###    "För godkänt resultat på kursen ska studenten kunna:
###     <i>Kunskap och förståelse</i>
###     1. Redogöra för relevanta begrepp för att beskriva omfattningen av sjukdomar i den allmänna befolkningen
###     2. Beskriva våra vanligaste folkhälsoproblem och folksjukdomar och redogöra för förekomst och sjukdomsorsaker
###     ... "
###   (example course SU PH03G0)
arabicPListExp = re.compile(r'>\s*\(?\s*[0-9]+\s*[).]?\s*([^<]{8,})', re.S)
arabicPListExpWrap = re.compile(r'(p>\(?\s*[0-9]+\s*[).]?\s*([^<]){8,}(.*>\s*\(?\s*[0-9]+\s*[).]?\s*([^<]){8,}){2,})', re.S)
arabicPListIndicator = re.compile("(>.*[0-9]+\s*[).]?[^<]{8,}.*<){3,3}", re.S)

arabicListExpWrap123 = re.compile(r'(1\s*[).]\s*)([^\n\s3].*2\s*[).]\s*)([^\n\s4].*3\s*[).]\s*)([^\s\n].*?)(?=((\n\n)|$))', re.S + re.I)
arabicListExpWrap12345 = re.compile(r'1\s*[).]\s*(.*)2\s*[).]\s*(.*)3\s*[).]\s*(.*)4\s*[).]\s*(.*)5\s*[).]\s*(.*).*?(?=(\n\n)|$)', re.S + re.I)
arabicListExp12345 = re.compile(r'\(?\s*[0-9]+\s*[).]\s*([^0-9 ]((([^0-9 \n][^0-9\n])|(\n[^\n])|( [^0-9 ])|( [0-9]+[^0-9().])|([^0-9 ][0-9])|( ?[0-9A-F]+\s*((till)|[-–])\s*[0-9]+)){8,}))', re.S)

arabicListExp = re.compile(r'\(?\s*[0-9]+\s*[).]\s*([^0-9 ](([^0-9 \n]|([0-9][^).])|( [^0-9 ])|(\n[^\n])){8,}))', re.S)
arabicListExpWrap = re.compile(r'\(?\s*[0-9]+\s*[).]\s*([^0-9 ]|([0-9][^).])|( [^0-9 ])){8,}(\s*\(?\s*[0-9]+\s*[).]\s*([^0-9 \n]|([0-9][^).])|( [^0-9 ])|(\n[^\n])){8,})+', re.S)

arabicListExpB = re.compile(r'\(?\s*[0-9]+\s*[).]?\s+([^0-9 ]([^h]|(h[^p])){8,}?)(?=$|\n|(\s\s)|(\(?[0-9]))', re.S)
arabicListExpBWrap = re.compile(r'\(?\s*1\s*[).]?\s*([^h]|(h[^p])){8,}\(?\s*2\s*[).]?\s*([^h]|(h[^p])){8,}\(?\s*3\s*[).]?\s*([^h]|(h[^p])){8,}\(?\s*4\s*[).]?\s*([^h]|(h[^p])){8,}\(?\s*[0-9]+\s*[).]?\s*([^h]|(h[^p])){8,}(?=$|\n|(\s\s))', re.S)

### Some courses enumerate goals with (a), (b), or (1), (2), etc. 
###    "Kursen syftar till (a) att öka deltagarnas förståelse ... ; (b) att ge de färdigheter som behövs för tillämpad dataanalys ... ; och (c) att ge träning i ... "
###   (example course SU PSMT15)
parListExp = re.compile("\s*\\([0-9a-zA-Z]\\)\s*([^\n]*)", re.S) # not very common
parListExpWrap = re.compile("\n\s*\\([0-9a-zA-Z]\\)\s*([^\n]*).*\n\s*\\([0-9a-zA-Z]\\)\s*([^\n]*)", re.S)

parListExp2 = re.compile("[\s.(][0-9a-hA-H.]{1,3}\)\s*((([^()<>\s.])|(ex.)|(\s[^a-zA-Z0-9<>().\s])|(\s[a-zA-Z0-9][^()]))*([^()\s<>/0-9.]){2}[.]?)", re.S) # mainly this pattern is used
parListExpWrap2 = re.compile("([\s.(][0-9a-hA-H.]{1,3}\)\s*((([^()<>\s])|(\s[^a-zA-Z0-9<>])|(\s[a-zA-Z0-9][^()]))*([^()\s<>/0-9]){2})){2,}", re.S)

### Some courses specify goals with lines like "ska ... kunna ..."
###   "Den studerande skall efter genomgången kurs kunna
###   identifiera samt, såväl muntligt som skriftligt, redogöra
###   för hur förhållandet mellan människa och natur avspeglas och
###   gestaltas i de senaste hundra årens svenska barnlitteratur.
###   Detta inbegriper förtrogenhet med den barnlitterära
###   konventionen och en förmåga att relatera iakttagelserna till
###   en vidare samhällelig och kulturell kontext."
###  (example course SU LV1011)
skaKunnaExp = re.compile(r'[Kk]unna:?\s*([^0-9\s]((([^\s])|([^\n][^\s])|(\n[^\nA-ZÅÄÖ])){8,}))', re.S)
skaKunnaExpWrap = re.compile(r'[Kk]unna:?(=!\s*Moment\s*)(\s*[^n0-9\s]((([^\s])|([^\n][^\s])|(\n[^\n])){8,}))', re.S)
skaKunnaExpEn = re.compile(r'be able:?(\s*[^0-9\s]((([^\s])|([^\n][^\s])|(\n[^\nA-Z])){8,}))', re.S)

### Some courses write goals as "Efter kursen kan ... " (less common than "ska kunna")
###   "Studenten kan tillämpa grundläggande arbetsmarknadsekonomiska begrepp ..."
###   (example course SU ATF012)
kanExp = re.compile("\skan\s([a-zåäö]*[^s]\s[^.]+)(?=$|\n|\s\s|[.])", re.I);
kanExpWrap = kanExp
kanExpEn = re.compile("\s(((know\s*how)|(able))\s*to\s(([^.]+\s[^.]+)[\.]|(\s\s)|\n))", re.I)

### Goals can be written as "studenten ska vara förtrogen med" or
### "studenten ska ha förmåga att"
###   "Efter genomgången kurs ska studenten
###    1)      vara förtrogen med begreppen kultur, mångkulturalism och andra för kunskapsområdet centrala begrepp som exkluderings- och inkluderingprocesser präglar relationer mellan majoritets- och minoritetsbefolkningen samt aktuella teorier kring mångkulturalism och etnicitet
###    2)      ha förmåga att integrera relevanta teorier och metoder om mångkulturalism i en vägledningssituation samt kunna reflektera över hur kulturella normer, värderingar och tankemönster påverkar förhållningssätt till människor i andra etniska grupper
###   (example course SU UC119F)
fortrogenExp = re.compile("\s(förtrogen\s*med\s([^.]{8,}?))(?=$|\n|\s\s|[.])", re.I)
fortrogenExpEn = re.compile("\s(scomfortable\s*with\s([^.]{8,}?))(?=$|\n|\s\s|[.])", re.I)

formagaExp = re.compile("\sförmåga.*?att\s*([^.]{8,}?)(?=$|\n|\s\s|[.])", re.I)
formagaExpEn = re.compile("\sability.*?to\s*([^.]{8,}?)(?=$|\n|\s\s|[.])", re.I)

### Some courses list all goals on one line with arabic numerals enumerating, starting with "... kunna 1."
###   "... ska studenten kunna 1.Redovisa, diskutera och jämföra olika
###   historiskt kriminologiska studier. 2.Beskriva, ..."
###   (example course SU AKA132)
kunna1exp = re.compile("[0-9. ()]*[0-9]+[0-9. ()]*\s*([^0-9]{8,})(?=$|\n\n|\s\s|[.0-9]|(\([0-9])|(Färdighet)|(Moment)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])|(Del ))", re.S)
kunna1expWrap = re.compile("kunna[^\n]*(1[- ()0-9]*.*\w{8,}.*(=!Moment\s*)2.*\w{8,}.*([0-9].*\w{8,}.*)+)(?=$|(\n\n))", re.S)

kunna1expWrapEn = re.compile("((know\s*how)|(able))\s*to[^\n]*(1[- ()0-9]*[^0-9]{8,}2[- ()0-9]+?[^0-9]{8,}([- ()0-9]+[^0-9]{8,})*)(?=$|(\n\n)|(\s\s)|[.])", re.S)

kunna1sub = re.compile("(,?\s*Efter avslutad kurs ska studenten)*\s*för betyget (.*?) kunna")

kunna1indicator = re.compile("kunna.*1.*2.*[0-9]+.*", re.S)

### Courses can have lists where each item starts with a Capital
### letter but not other wise noted:
###    "Efter avslutad kurs ska studenten kunna Visa goda kunskaper
###    ... konsekvenser. Analysera och tolka händelser ... "
###   (example course KTH MJ2416)
kunnaCapExp = re.compile("[\s>]([A-ZÅÄÖ](([^<\n\s])|(\s[^\s])|(\s\s[^\sA-ZÅÄÖ])|(\n[^\nA-ZÅÄÖ])){4,})", re.S)
kunnaCapExpWrap = re.compile("kunna:?\s*([A-ZÅÄÖ]([^\n]|(\n[^\n]))*){2,}?(?=$|\n\n)", re.S)
kunnaCapExpWrapEn = re.compile("((know\s*how)|(able))\s*to:?\s*[A-ZÅÄÖ].*", re.S)

kunnaSemiColonExp = re.compile("([a-zåäö][^;]{4,})(?=[.]|;|$|\")", re.S);
kunnaSemiColonExpWrap = re.compile("kunna[\s:]*(([a-zåäö].{4,})(;\s*[a-zåäö][^;]{4,}){2,})", re.S);

kunnaHypIndicator = re.compile("^(.(?!innehålla))*-", re.S)
kunnaHypExp = re.compile("\s*-\s*([a-zåäöA-ZÅÄÖ]([^\-<]|([a-zA-ZåäöÅÄÖ0-9]-[a-zA-ZåäöÅÄÖ0-9]))*[^\-<\s])", re.S)
kunnaHypExpWrap = re.compile("[A-ZÅÄÖ][^A-ZÅÄÖ]*?((\sska)|(kunna))[^-–]*:?(\s*[-–]\s?[a-zåäöA-ZÅÄÖ]([^\-–<\n]|(\n[^\n]))*)(.*?\s*[-–]\s?[a-zåäöA-ZÅÄÖ]([^\-–<\n]|(\n[^\n]))*)+", re.S)
kunnaHypExpWrap2 = re.compile("([^a-zåäöA-ZÅÄÖ][-–][a-zåäöA-ZÅÄÖ][^\-–<]{4,}[^\-–<\s])(.*?([^a-zåäöA-ZÅÄÖ][-–][a-zåäöA-ZÅÄÖ][^\-–<]{4,}[^\-–<\s]))+", re.S)

kunnaHypExpWrapEn = re.compile("[A-Z][^A-Z]*?((know\s*how)|(able))\s*to:?\s*(\s+ -[a-zA-Z][^\-<]*[^\-<\s])+", re.S)

# Courses can have lists using HTML <p>-tags for list items but not be
# captured by the more precise pattern above. For example the course
# KTH IE1205 which has "<p>- "

pHypListExp = re.compile("<p>-\s?(.*?)\s*(?=</?p>)", re.S)
pHypListExpWrap = re.compile("(<p>)?[^<>]*((ska)|(kunna))[^<>]*(</\s*p>)?(<p>-\s?[^<>]*</?p>)([^<>]*<p>-\s?[^<>]*</?p>)+", re.S)
pHypListExpWrapEn = re.compile("(<p>)?[^<>]*((can)|(know\s*how\s*to)|(able\s*to))[^<>]*(</\s*p>)?(<p>-\s[^<>]*</?p>)([^<>]*<p>-\s[^<>]*</?p>)+", re.S)
pHypListIndicator = re.compile("<p>-")

# Courses KTH CM2006 CM1004 has "<p>" but no dot or hyphen at all
pRawListExp = re.compile("<p>(.*?)(?=</?p>)", re.S)
pRawListExpWrap = re.compile("(<p>)?[^<>]*((ska)|(kunna))\s*:?\s*((</\s*p>)?(\s*<p>[^<>]*</?p>)([^<>]*<p>[^<>]*</?p>)+?)\s*(?=((\n\n)|$|(<p>för att)))", re.S)
pRawListExpWrapEn = re.compile("(<p>)?[^<>]*((can)|(know\s*how\s*to)|(able\s*to))\s*:?\s*(</\s*p>)?(<p>[^<>]*</?p>)([^<>]*<p>[^<>]*</?p>)+", re.S)

pRawListIndicator = re.compile("((ska)|(kunna))\s*:?\s*</\s*p>")
pRawListIndicatorEn = re.compile("((can)|(know\s*how\s*to)|(able\s*to))\s*:?\s*</\s*p>")

# UMU courses with "ska ... - ha ... - ha ..."
umuHypHaAndStarExp = re.compile("\n?[*–\-]\s(.{4,}?)(?=(\n|([;*–\-]\s)|(Det innebär)|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuHypHaAndStarExpWrap = re.compile("((godkän)|(efter)).*([–\-]\s?((ha)|(i)|(ge)|(kunna)|(vara)|(besitta)|(beskriva)|(förstå)|(känna)|(med\shjälp\sav)|(redogöra)|(genom)|(genomföra)|(arbeta)|(jämföra)|(planera)|(exemplifiera)|(förklara)|(modellera)|(göra)|(formulera)|(identifiera)|(utifrån)|(dokumentera)|(tillämpa)|(upprätta)|(värdera)|(använda))([^*]*[*]){2,}.*){2,}", re.S + re.I)

umuHypHaExp = re.compile("\n?[–\-]\s?(([^\s]*\s*)?(([a-zåäö][^\s]*a)|([A-ZÅÄÖ][^\s]*)|([Hh]a)|([Ii]\s*)|([Gg]e)|([Kk]unna)|([Vv]ara)|([Vv]isa)|([Bb]esitta)|(([Bb]e)?[Ss]kriva)|([Kk]änna)|([Ff]örstå)|([Mm]ed\shjälp\sav)|([Rr]edogöra)|([Gg]enom)|([Gg]enomföra)|([Aa]rbeta)|([Jj]ämföra)|([Pp]lanera)|([Ee]xemplifiera)|([Ff]örklara)|([Mm]odellera)|([Gg]öra)|([Ff]ormulera)|([Ii]dentifiera)|([Uu]tifrån)|([Dd]okumentera)|([Tt]illämpa)|([Uu]pprätta)|([Vv]ärdera)|([Aa]nvända)|([Vv]älja)|(([Åå]ter)?[Ss]kapa)|([Ss]tödja)|([Kk]ommunicera)|([Dd]iskutera)|([Ss]ammanställa)|([Tt]olka)|([Ss]öka)|([Gg]ranska)|([Tt]änka)|([Mm]untlig[^\s]*)|([Ss]jälv(ständigt))|([Aa]tt)|([Bb]ehärska)|([Uu]rskilja)|([Dd]elta(ga)?)|([Uu]tföra)|([Aa]nalysera)|([Vv]isualisera)|([Uu]tveckla)|([Ii]ntervjua)|([Ss]amla)|([Vv]isa)|([Ff]örbereda)|([Pp]å)|([Pp]resentera)|([Rr]eflektera)|([Mm]ed)|([Ss]krift[^\s]*)|([Aa]ktiv[^\s]*)|([Ff]öreslå)|([Ii]nom)|([Uu]tforma)|([Ss]kydda)|([Vv]ad)|([Tt]eoretiskt)|([Pp]rocessen)|([Kk]ritiskt)|([Bb]åde)),?\s.{4,}?)(?=(\n|([–\-]\s)|(\(?Moment)|$|(\(?Färdighet)|(\(?Kunskap)|(\(?Värdering)|(\(?Modul)|(För god)|(Område [0-9])|(Del)))", re.S)
umuHypHaExpWrap = re.compile("(([Gg]odkän)|([Ee]fter))([^.–\-]*)([–\-]\s{0,2}(([a-zåäö][^\s]*a)|([A-ZÅÄÖ][^\s]*)|([Hh]a)|([Ii]\s)|([Gg]e)|([Kk]unna)|([Vv]ara)|([Bb]esitta)|(([Bb]e)?[Ss]kriva)|([Ff]örstå)|([Kk]änna)|([Mm]ed\s[Hh]jälp\s[Aa]v)|([Rr]edogöra)|([Gg]enom)|([Gg]enomföra)|([Aa]rbeta)|([Jj]ämföra)|([Pp]lanera)|([Ee]xemplifiera)|([Ff]örklara)|([Mm]odellera)|([Gg]öra)|([Ff]ormulera)|([Ii]dentifiera)|([Uu]tifrån)|([Dd]okumentera)|([Tt]illämpa)|([Uu]pprätta)|([Vv]ärdera)|([Aa]nvända)|([Vv]älja)|(([Åå]ter)?[Ss]kapa)|([Ss]tödja)|([Kk]ommunicera)|([Dd]iskutera)|([Ss]ammanställa)|([Tt]olka)|([Ss]öka)|([Gg]ranska)|([Tt]änka)|([Mm]untlig[^\s]*)|([Bb]ehärska)|([Uu]rskilja)|([Dd]elta(ga)?)|([Uu]tföra)|([Aa]nalysera)|([Vv]isualisera)|([Uu]tveckla)|([Ii]ntervjua)|([Ss]amla)|([Vv]isa)|([Ff]örbereda)|([Pp]å)|([Pp]resentera)|([Rr]eflektera)|([Mm]ed)|([Ss]krift[^\s]*)|([Aa]ktiv[^\s]*)|([Ff]öreslå)|([Ii]nom)|([Uu]tforma)|([Ss]kydda)|([Vv]ad)|([Tt]eoretiskt)|([Pp]rocessen)|([Aa]tt)|([Kk]ritiskt)|([Bb]åde)),?\s(([^\s]|(\s[^–\-])|(\s[–\-][^\s])){4,}\s?)){2,}", re.S)

###    (example course UMU 5BI261)
###    'delFSR1 tillämpa ett analytiskt förhållningsätt till ekologin i terrestra arktiska och subarktiska ekosystem från process till ett landskapsperspektiv och över olika tidsskalorFSR2 tillämpa ett analytiskt förhållningssätt till pågående och möjliga framtida effekter av klimatförändringar på arktiska som inkluderar subarktiska ekosystem och hur terrestra processer återkopplar till dessa.FSR3 formulera genomförbara hypoteser som relaterar till effekterna av en eller två potentiella interagerande ekologiska faktorer i arktiska ekosystem processer.Modul 2, ProjektarbeteFSR4tillämpa ett vetenskapligt förhållningssätt för att planera och genomföra en fördjupad vetenskaplig studie inom arktisk terrester ekologiFSR5 inhämta, bearbeta, analysera och tolka information om ekologiska processer,FSR6 analysera och jämför resultaten i relation till publicerad litteratur inom ämnet,FSR7 presentera resultaten i skrift i form av en individuellt skriven vetenskaplig rapport och muntligt i form av seminarium. Efter avklarad kurs skall studenten för betyget Väl Godkänd kunna FSR8 kritiskt granska vetenskaplig litteratur för att tolka vetenskapliga resultat.FSR9kritiskt granska vetenskaplig litteratur för att formulera följder eller konsekvenser av egna och/eller publicerade resultat i ett vidare perspektivFSR10 tillämpa kursens innehåll för att formulera nya frågeställningar och hypoteser.'

umuFSRexp = re.compile('FSR\s*[0-9]+[.]?\s*(.{4,}?)(?=((FSR)|(Modul)|(\n\n)|$|(Förvänt)|(Efter)))', re.S)
umuFSRexpWrap = re.compile('(FSR\s*[0-9]+[.]?\s*.{4,})(.*(FSR\s*[0-9]+[.]?\s*.{4,}))+', re.S)

efterSkallExp = re.compile("((För.*?)?(([Ee]fter\s)|([Ss]tudent)|([Vv]idar)|([Gg]odkän))[ A-Za-zåäöÅÄÖ]*((förväntas)|(ska))[ A-Za-zåäöÅÄÖ]*\s((kunna)|(ha)|(också))\s*(.*?))(?=$|(\s\s)|\n|[–•*·….])")
efterSkallExpWrap = re.compile("(För.*?)?(([Ee]fter\s)|([Ss]tudent)|([Vv]idar)|([Gg]odkän))[ A-Za-zåäöÅÄÖ]*\s((förväntas)|(ska))[ A-Za-zåäöÅÄÖ]*\s((kunna)|(ha)|(också))\s *[a-zåäöA-ZÅÄÖ][a-zåäöA-ZÅÄÖ, \-]{4,}?(?=$|(\n$)|(  )|(\n[^a-zåäöA-ZÅÄÖ])|[–•*·….])")

efterSkallExp2 = re.compile("((För.*?)?((förväntas)|(ska))[ A-Za-zåäöÅÄÖ]*(([Ee]fter\s)|([Ss]tudent)|([Vv]idar)|([Gg]odkän))[ A-Za-zåäöÅÄÖ]*\s((kunna)|(ha)|(också)|(få))\s*(.*?))(?=$|(\s\s)|\n|[–•*·….])")
efterSkallExp2Wrap = re.compile("(För.*?)?((förväntas)|([^a-zåäö]ska))[ A-Za-zåäöÅÄÖ]*(([Ee]fter\s)|([Ss]tudent)|([Vv]idar)|([Gg]odkän))[ A-Za-zåäöÅÄÖ]*\s((kunna)|(ha)|(också)|(få))\s *[a-zåäöA-ZÅÄÖ][a-zåäöA-ZÅÄÖ, \-]{4,}?(?=$|(\n$)|(  )|(\n[^a-zåäöA-ZÅÄÖ])|[–•*·….])")

attStudentenKanExp = re.compile("\s*\n\s*([a-zåäö][^\n]{4,}?)(?=$|\n|(För godk)|([Mm]odul)|([Mm]oment))", re.S)
attStudentenKanExpWrap = re.compile("att student[^\s]* kan\s*(\n\s*[a-zåäö][^\n]{4,})((\n[a-zåäö][^\n]{4,}){2,})(\s*\n\s*För godk[^\n]*((kan)|(kunna))[^\n]*(\n[a-zåäö][^\n]{4,}){1,}){0,}", re.S)

efterSkaKunnaExp = re.compile("\s*\n\s*([a-zåäö][^\n]{4,}?)(?=$|\n|(Efter)|(För godk)|([Mm]odul)|([Mm]oment))", re.S)
efterSkaKunnaExpWrap = re.compile("(Efter[^\n]*ska[^\n]*((studenten)|(kunna))[^\n]*)\n\s*(([a-zåäö][^\n]{4,}\n)\s*){3,}?([a-zåäö][^\n]{4,}?(?=$|(\n$)|(\n\n)|(Efter )|(För )|(Modul )|(Moment )))", re.S)

efterSkaKunnaExp2Wrap = re.compile("(För[^\n]*godkän[^\n]*ska[^\n]*((stude)|(kunna))[^\n]*)\n\s*(([a-zåäö][^\n]{4,}\n)\s*){3,}?([a-zåäö][^\n]{4,}?(?=$|(\n$)|(\n\n)|(Efter )|(För )|(Modul )|(Moment )))", re.S)

umuMomentExp = re.compile("\n\s*([a-zåäö][^\n]{4,}?)(?=$|\n|(Moment)|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område))", re.S)
umuMomentExpWrap = re.compile("Moment 1.*\n[a-zåäö].*Moment 2.*\n[a-zåäö].*(Moment.*\n[a-zåäö].*)", re.S)

kunnaNLExp = re.compile("\n([a-zåäö][^\n]{4,})(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
kunnaNLExpWrap = re.compile("[Kk]unna([^\n]*att)?:?\s*((\n([a-zåäö][^\n]{4,})){3,})", re.S)

kunnaNLExp2 = re.compile("\n\s*([A-ZÅÄÖ][^\n]{4,})(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
kunnaNLExp2Wrap = re.compile("[Kk]unna([^\n]*((att)|(följande)|(<[^>]*>)))?:?\s*((\n\s*([A-ZÅÄÖ][^\n]{4,})){3,})", re.S)

kunnaNLExp3 = re.compile("\n\s*([a-zåäöA-ZÅÄÖ][^\n]{4,})(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
kunnaNLExp3Wrap = re.compile("[Kk]unna([^\n]*((att)|(följande)))?:?\s*((\n\s*([a-zåäöA-ZÅÄÖ][^\n]{4,})){3,})", re.S)

kunnaNLExp4 = re.compile("([a-zåäö][^\n]{4,})(?=(\n|(,\n)|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
kunnaNLExp4Wrap = re.compile("[Kk]unna(([^\nM]|(M[^\no])|(Mo[^\nm]))*att)?:?\s*(([a-zåäö][^\n]{4,}\n)?([a-zåäö][^\n]{4,},\s*\n\s*){3,}([a-zåäö][^\n]{4,}?(?=$|\n|(Efter )))?)", re.S)

kunnaNLExp5 = re.compile("\n\s*([a-zåäö][^\n]{4,})(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
kunnaNLExp5Wrap = re.compile("[Kk]unna([^\n]*att)?:?\s*((\n\s*(visa[^\n]{4,}))(\n\s*([a-zåäö][^\n]{4,})){1,})", re.S)

dessutomSkaExp = re.compile("((([Dd]essutom)|([Dd]u)) ska(ll)? ((du)|(dessutom)|(också)) .{10,}?)(?=[.]|$|(\n\n))", re.S)
dessutomSkaExpWrap = re.compile("((([Dd]u)|([Dd]essutom)) ska(ll)? ((du)|(dessutom)|(också)) (.{10,}?))(?=[.]|$|(\n\n))", re.S)

skaEfterAvslutadExp = re.compile("efter avslutad (.{10,}?)(?=[.]|$|(\n\n))", re.S)
skaEfterAvslutadExpWrap = re.compile("([Ss]ka(ll)? efter avslutad (.{15,}?))(?=[.]|$|(\n\n))", re.S)

skaEfterAvslutadRevExp = re.compile("[Ee]fter avslutad .* ska[^\s]* (.{10,}?)(?=[.]|$|(\n\n))", re.S)
skaEfterAvslutadRevExpWrap = re.compile("([Ee]fter avslutad .* ska[^\s]* (.{15,}?))(?=[.]|$|(\n\n))", re.S)


umuNLHaExp = re.compile("\n\s*((.*?)(([Hh]a)|([Ii]\s)|([Gg]e)|([Kk]unna)|([Vv]ara)|([Vv]isa)|([Bb]esitta)|([Bb]eskriva)|([Kk]änna)|([Ff]örstå)|([Mm]ed\shjälp\sav)|([Rr]edogöra)|([Gg]enom)|([Gg]enomföra)|([Aa]rbeta)|([Jj]ämföra)|([Pp]lanera)|([Ee]xemplifiera)|([Ff]örklara)|([Mm]odellera)|([Gg]öra)|([Ff]ormulera)|([Ii]dentifiera)|([Uu]tifrån)|([Dd]okumentera)|([Tt]illämpa)|([Uu]pprätta)|([Vv]ärdera)|([Aa]nvända)|([Vv]ad)|([Ss]jälv(ständigt))|([Aa]tt)),?\s.{4,}?)(?=((;?\n)|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuNLHaExpWrap = re.compile("((godkän)|(efter))[^\n]*(\n((ha)|(kunna)|(vara)|(besitta)|(beskriva)|(förstå)|(känna)|(med\shjälp\sav)|(redogöra)|(genom)|(genomföra)|(arbeta)|(jämföra)|(planera)|(exemplifiera)|(förklara)|(modellera)|(göra)|(formulera)|(identifiera)|(utifrån)|(dokumentera)|(tillämpa)|(upprätta)|(värdera)|(använda)|(vad)|(själv(ständigt))|([Aa]tt)),?\s([^\n]*?)){2,}(?=((\n\n)|$|(\s\sFör\s)|\n|(Efter )))", re.S + re.I)


umuAstExp = re.compile("((\\n?[*]\\s?(.{4,}?))|(kunna:?\\s.{10,}?))(?=(\\n|[*]|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuAstExpWrap = re.compile(r'((godkän)|(efter)).*([*]\s?.{4,}){2,}', re.S + re.I)

umuHaExp = re.compile("((( - )|(ha\s)).{4,}?)(?=(\n|(ha\s)|( - )|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuHaExpWrap = re.compile("((godkän)|(efter)).*kunskap och förståelse.*(ha\s(förmåga att)?[^\n]{4,}){2,}", re.S + re.I)

umuNLExp = re.compile("(\n\s*[A-ZÅÄÖ].{4,}?)(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuNLExpWrap = re.compile("(([Gg]odkän)|([Ee]fter)).*[Kk]unskap och [Ff]örståelse.*(\n\s?[A-ZÅÄÖ].*){2,}", re.S)

umuNLExp2 = re.compile("(\n\s*[a-zåäö].{4,}?)(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuNLExp2Wrap = re.compile("(([Gg]odkän)|([Ee]fter)).*[Kk]unskap och [Ff]örståelse.*(\n\s?[a-zåäö].*){3,}", re.S)

# umuWSExp = re.compile("  (.{4,}?)(?=(\n|(\s\s)|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)))", re.S)
# umuWSExpWrap = re.compile("(([Gg]odkän)|([Ee]fter)).*[Kk]unskap och [Ff]örståelse.*(([^0-9\n]|([^ \n][0-9]))  [^\s0-9*][^*\n]{4}.*){3,}", re.S)
# umuWSindicator = re.compile("((godkän)|(efter)).*kunskap och förståelse.*(  [^\s]{4,}.*){3,}", re.S + re.I)

umuWSExp = re.compile(r'  (.{4,}?)(?=(\n|(\s\s)|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))', re.S)
umuWSExpWrap = re.compile(r'(([Gg]odkän)|([Ee]fter)).*[Kk]unskap och [Ff]örståelse.*(([^0-9\n]|([^ \n][0-9]))  [^\s0-9*][^*\n]{4}.*){3,}')
umuWSindicator = re.compile(r'((godkän)|(efter)).*kunskap och förståelse.*(  [^\s]{4,}.*){3,}', re.S + re.I)

miunWSexp = re.compile("\n\s{3,}([^\n]{4,})")
miunWSexpWrap = re.compile("(\n\s{3,}[^\n]{4,}){3,}")


umuCatchallExp = re.compile("(.{4,}?)(?=(\n|(Moment)|$|(Färdighet)|(Kunskap)|(Värdering)|(Modul)|(För god)|(Område [0-9])))", re.S)
umuCatchallExpWrap = re.compile("((godkän)|(efter)).*?kunskap och förståelse(.*färdighet och förmåga.*)", re.S)

oneparExp = re.compile("(kunna.{4,}?)<\/p>", re.S + re.I)
oneparExpWrap = re.compile("<p>([^<>]*ska[^<>]*(<\/p><p>)?[^<>]*kunna[^<>]{4,})<\/p>", re.S + re.I)
oneparExpWrap2 = re.compile("<p>(kunna [^<>]{8,})<\/p>", re.S + re.I)

onelineExp = re.compile("(.{4,})")
onelineExpWrap = re.compile("^[^\n]*((godkän)|(efter)|(avslutad)|(avklarad))[^\n]*((förväntas)|(ska)|(kunna))([^\n]{4,})(?=\n*$)", re.S + re.I)

efterModulExp = re.compile("\n((.){4,}?)(?=([Mm]odul )|([Ee]fter)|$|\n)", re.S + re.I)
efterModulExpWrap = re.compile("(efter.*?modul.*?((ska)|(kunna)).*){3,}?(?=(\n\n)|$)", re.S + re.I)

del1del2Exp = re.compile("Del\s*[0-9]+\s*((.*?[0-9]\s*[Hh][Pp])?(.{4,}?))(?=(Del\s)|(\n\n)|$)", re.S)
del1del2ExpWrap = re.compile("(Del\s*1.*?Del\s*2.*(Del\s*[0-9].*)*)(?=(\n\n)|$)", re.S)

abcExp = re.compile("\s[a-z]\s*[).]\s*(.*?)(?=(\n\n)|$|(\s[a-z]\s*[).]))", re.S)
abcExpWrap = re.compile("\s*a\s*[).]\s*(.*)\sb\s*[).]\s*(.*)\sc\s*[).]\s*.*?(?=(\n\n)|$)", re.S)

iIIiiiExp = re.compile("\\(i+\\)\s*(.*?)(?=(\n\n)|$|(\\(i+\\)))", re.S + re.I)
iIIiiiExpWrap = re.compile("\\(i\\)\s*(.*)\\(ii\\)\s*(.*)\\(iii\\).*?(?=(\n\n)|$)", re.S + re.I)

avenKunnaExp = re.compile("[A-ZÅÄÖ].*?även kunna(.*?)(?=$|(\n\n)|[.])", re.I + re.S)
avenKunnaExpWrap = re.compile("[A-ZÅÄÖ].*?även kunna.*?(?=$|(\n\n)|[.])", re.I + re.S)




### Courses can use X as markers for goals
###   "Efter genomgången kurs ska deltagarna kunna XReflektera kring och diskutera ämnet hållbar utveckling och koppla begreppen till det egna ämne
###    sområdet XPresentera hållbar utveckling som ett ämne som kräver kritisk reflektion och diskussion utifrån olika perspektiv och visa hur detta bör komma f
###    ram i utbildningen för studenter XDesigna kursmål ..."
###   (example course KTH LH215V)
XxListExp = re.compile("[^a-zåäöA-ZÅÄÖ][Xx]\s*(([^XM\n\s]|( [^X\n\s])){4,}[^X\n\s])", re.S)
XxListExpWrap = re.compile("[^a-zåäöA-ZÅÄÖ][Xx]\s*([^XM\n\s]|( [^X\n\s])){4,}(\s*.*?[^a-zåäöA-ZÅÄÖ][Xx]\s*([^X\n\s]|( [^X\n\s])){4,})+", re.S)


delkursExp = re.compile("Delkurs([^\\-•*·–…;]*?)hp")
delkursExp2 = re.compile("Delkurs\s[0-9]+[.]?,?(\s*[^A-ZÅÄÖ\\-,•*·–…;\n]*)")

# # Courses KTH FAG3184 FAG3185 have a set of <p>...</p> that are one
# # goal each, and nothing else.
# onlyPListExp = re.compile("<p>(.*?)(?=</?p>)", re.S)


umuHypHaExpMaybe = re.compile("- ([A-ZÅÄÖ](([^-])|(-[^ ])){4,})", re.S)
umuHypHaExpWrapMaybe = re.compile("- [A-ZÅÄÖ](([^-])|(-[^ ])){4,}(- [A-ZÅÄÖ](([^-])|(-[^ ])){4,})+", re.S)



### Some courses only have one sentence with "studenter ska kunna ..."
### This pattern tends to over generate, so it should be used after
### other (more precise) patterns have failed to find anything.
kunnaSentenceExp = re.compile("[Kk]unna[^.]{4,}\.")
kunnaSentenceExpEn = re.compile("((([Kk]now\s*how)|([Bb]e\s*able)|([Aa]bility))\s*to[^.]{4,}\.)")

### Some courses have goals stated as "Kursens mål är att ge studenterna ett tillfälle att ... VERB"
###   "Teknologerna får därigenom tillfälle att tillämpa sina kunskaper ..."
###   (example course KTH MF2025)
tillfalleExp = re.compile("[Tt]illfälle\s*att\s*([^•*·–….]*)\s*[•*·–….]", re.S)
traningExp = re.compile("[Tt]räning\s*i\s*att\s*([^.]*)\s*[.]", re.S)

tillfalleExpEn = re.compile("[oO]pportunity([^•*·–….]*)\s*[•*·–….]", re.S)
traningExpEn = re.compile("[Tt]raining\s*([^.]*)\s*[.]", re.S)

### Some course descriptions lists each goal on a separate line, like:
###    "För godkänd kurs ska studenten kunna 
###     uppvisa förståelse för människans språk betraktat som en del av hennes kognitiva utrustning 
###     uppvisa kännedom om ..."
###    (example course UMU 1LI034)
kunnaNewlineExp = re.compile("\n[^<>\n]{4,}", re.S)
kunnaNewlineExpWrap = re.compile("(kunna\s*:?\s*([Kk]unskap\s*och\s*[Ff]örståelse)?(<ol>)?(uppvisa förmåga att)?(följande)?([Ff]ärdighet och förmåga)?(\\([A-ZÅÄÖa-zåäö]+\\))?\s*(\n[^<>\n]{4,})+)", re.S)
kunnaNewlineExpWrapEn = re.compile("((know\s*how)|(able))\s*to\s*:?\n.*", re.S)

kunnaNewlineExpWrap2Indicator = re.compile("((betyget Godkänd)|(godkänd kurs))")
kunnaNewlineExpWrap2 = re.compile("(För ((betyget Godkänd)|(godkänd kurs))\s*ska den studerande(\s*((avseende)|(kunna:?)|([^\n]*(K|k)unskap och förståelse-?)|(\\([A-ZÅÄÖa-zåäö]+\\))|(Summativ bedömning i teori och praktik)))*\s*\n.*)", re.S)


kunnaHyphenB = re.compile("- ([^-]{4,})", re.S)
kunnaHyphenBWrap = re.compile("(((unskap och förståelse)|(kunna))- ([^-]{4,})(- [^-]{4,}){2,})", re.S)
kunnaHyphenBWrapEn = re.compile("(((know\s*how\s*to)|(able\s*to))- ([^-]{4,})(- [^-]{4,}){2,})", re.S)


###    (example course UMU 1LV057)
umuSkaHaExp = re.compile("\s{2,}(([^\s])|(\s[^\s])){4,}[^\s]", re.S)
umuSkaHaExpWrap = re.compile("Efter avslutad kurs ska den studerande ha\s*(\s{2,}(([^\s])|(\s[^\s])){4,})+", re.S)
umuSkaHaExp2 = re.compile("\s+((([^\s.])|(\s[^\s])){4,})\\.", re.S)
umuSkaHaExpWrap2 = re.compile("Efter avslutad kurs ska den studerande ha\s*(\s*[a-zåäö](([^\s])|(\s[^\s])){4,}\\.)+", re.S)

### Courses from UMU often have one goal per line, with no sentence
### structure. Some patterns to capture such goals.
###    (example course UMU 6PE264)
umuNewlinesExp = re.compile("\n[^\n]{4,}")
umuNewlinesExpWrap = re.compile("ska den studerande (avseende)*\s*kunskap och förståelse\s*\n(.*)", re.S)
umuNewlinesExpWrap2 = re.compile("^Kunskap och förståelse\s*\n(.*)", re.S)
umuNewlinesExpWrap3 = re.compile("För .*? ska .*? stud.*? Kunskap och förståelse\s*\n(.*)", re.S)

umuNewlinesExpWrap4 = re.compile("Efter avklarad kurs ska studenterna kunna, med avseende på\s*\n(.*)", re.S)
umuNewlinesExpWrap5 = re.compile("För godkänd kurs ska den studerande[^\n]*Practice\s*\n.*", re.S)

###    (example course UMU 5MO120)
umuHypExp = re.compile("- ([^-]{4,})")
umuHypExpWrap = re.compile("Efter ((avslutad)|(genomgången)) kurs ska studenten- ([^-]{4,})(- [^-]{4,})+")

###    (example course UMU 2SO030)
umuEfterHyp = re.compile("-((([^\\-E0-9])|([0-9]+\\-?)|(,[^\\-E0-9])|(-,)){4,})", re.S)
umuEfterHypWrap = re.compile("(Efter[^-]+((( -)|(- ))(([^\\-E0-9])|([0-9]+\\-?)|(EU)){4,}){2,})", re.S)
umuEfterHypWrapSpec = re.compile("Efter[^-]+(kunna [^\s\\-]+[^-]*)((( -)|(- ))(([^\\-E0-9,])|(,[^\\-E0-9])|(-,)|([0-9]+\\-?)|(EU)){4,}){2,}", re.S)
umuEfterHypWrapSpec2 = re.compile("De studerande skall efter avslutad kurs (förstå)\s*((( -)|(- ))(([^\\-E0-9,])|(,[^\\-E0-9])|(-,)|([0-9]+\\-?)|(EU)){4,}){2,}", re.S)
umuEfterHypIndicator = re.compile("Efter[^-]*-[^-]*-")
umuEfterHypNegativeIndicator = re.compile("[a-zåäö]- och")

hypNoSpaceExp = re.compile("[^A-ZÅÄÖ]-[A-ZÅÄÖ][a-zåäö]")
hypCommaExp = re.compile(",-")

###    (example course UMU 2SV060)
umuSamtligaMomentExp = re.compile("\n((([^\s\n])|([^\n][^\s\n])){4,})", re.S)
umuSamtligaMomentExpWrap = re.compile("Samtliga\s*moment\s*\n(.*)", re.S)

###    (example course UMU )
umuAvseendeExp = re.compile("\n((([^\s\n])|([^\n][^\s\n])){4,})", re.S)
umuAvseendeExpWrap = re.compile("[Aa]vseende\s+(\S+)\s+och\s+(\S+)\s*\n(([^A])|(A[^v])|(Av[^s])|(Avs[^e])){4,}", re.S)

###    (example course UMU 1AR000)
umuHaLines = re.compile("\n[a-zåäö][^\n]{4,}")
umuHaLinesWrap = re.compile("(((kunna)|(Kunskap och förståelse)|(Kunskap, undervisning och lärande,?\s?[0-9]*h?p?))\s*\n[a-zåäö](.*)(\n[a-zåäö].*){2,}(\n[a-zåäö][^\n]*))") # at least 4 lines starting with lower case
umuHaLinesWrapEn = re.compile("((able\s*to).*\n[a-zåäö](.*)(\n[a-zåäö].*){2,}(\n[a-zåäö][^\n]*))")


###    (example course UMU )
efterKunnaExp = re.compile("\n[^\n]{4,}")
efterKunnaExpWrap = re.compile("((Efter avklarad kurs ska (den )?stude((rande)|(nten)|(nterna)) kunna)|(Efter avslutad kurs ska (den )?stude((rande)|(nten)|(nterna)) kunna)|(Efter genomgången kurs förväntas (den )?stude((rande)|(nten)|(nterna)))|(Efter genomgången kurs skall (den )?stude((rande)|(nten)|(nterna)) kunna))(\s*Kunskap och förståele)?(\s*,?\s*med avseende på)?([^\n]*)\n([a-zåäö].*\n){3,}.*", re.S)

forGodkandExp = re.compile("\n[a-zåäö][^\n]{4,}")
forGodkandExpWrap = re.compile("För betyget godkänd ska den studerande[^\n]*\n([a-zåäö][^\n]{4,}\n){3,}.*", re.S)

forGodkandExpWrap2 = re.compile("Efter godkänd kurs ska du kunna ([a-zåäöA-ZÅÄÖ ]){4,}\\.")

###    (example course MIUN KEA002F KEA005F)
whitespacesExp = re.compile("\s{2,}((([^\s])|(\s[^\s])){4,}[^\s])")
whitespacesExpWrap = re.compile("Efter ((avslutad)|(genomgången)) kurs.*?\s{2,}.*?\s{2,}.*", re.S)
whitespacesExpWrapEn = re.compile("Efter ((avslutad)|(genomgången)) kurs.*?\s{2,}.*?\s{2,}.*", re.S)
whitespacesExp2 = re.compile("((([^\s])|(\s[^\s])){4,}[^\s])")
whitespacesExpWrap2 = re.compile(".*\s{2,}.*\s{2,}.*", re.S)

###    (example course UMU 5EL272)
vetaHurExp = re.compile("[Vv]eta\s*(hur\s*.*?)\\.", re.S)

###    (example course MIUN ELA017F)
formuleraExp = re.compile("Efter avslutad kurs ska[ a-zåäöA-ZÅÄÖ,]*formulera[^\\.\n]{4,}")

kunnaAexp = re.compile(" [a-hA-h][.\\)] ((([^. ])|( [^. ])){4,})")
kunnaAexpWrap = re.compile("kunna:?\s*\\(?[aA][.\\)].* [bB][.\\)] .*( [c-hC-H][.\\)] .*)+")
kunnaAexpWrapEn = re.compile("able to:? \\(?[aA][.\\)].* [bB][.\\)] .*( [c-hC-H][.\\)] .*)+")


### Many courses have goals stated as "ska kunna:" and then one goal per line.
kunnaColonExp = re.compile("kunna:\s*?\n", re.I)

# "praktiska färdigheter att", KTH EP2120 FAE3007

# "kunna [^.]*[.]"

# KTH ML0022, <p>-list?

# KTH AD236V, "ska studenten ha"
# KTH HS202X, skall </p><p>Visa sig ha kunskap och kompetens för att utveckla och genomföra ett självständigt examensarbete inom området, ’Architectural Lighting Design and Health’.</p><p>Visa sig ha kapacitet att strukturera en frågeställning, problematisera och definiera en användbar relevant metod för arbetsp

# KTH EF1113, praktisk erfarenhet av att


#########################################################################
### Things to remove because they interfere with the other expressions ###
#########################################################################
parHeadingsExp = re.compile("\\([A-ZÅÄÖ]\w{3,}:?\s*([0-9][0-9]*,?\s*(och)*(;\sEPA)*\s*)*\s*[0-9]+\s*\\)") # (<name of things>)
parHeadingsExp2 = re.compile("\s+modul\s+[0-9]+\s+(\\([\w\\-,]+\s+([\w\\-,]+\s+)*[0-9]+\\))", re.I) # module 1 (<name of module>)
delparExp = re.compile("\\(del\s*[0-9i]+[a-z]?(\s*(och)?,?\s*(del)?\s*[0-9i]+[a-z]?)*\\)", re.I)    # (del 1)
ccparExp = re.compile("\\([A-Z0-9]{6,7}\\)")                                                        # (<course code>)
betygparExp = re.compile("\\(((Betyg)|((Del)?Mål)|(Moment)|(Modul))\s*[A-F0-9]+(,?\s*(och)?(eller)?\s*[A-F0-9]+)*\\)", re.I) # (betyg D)
momentExp = re.compile("(((Modul)|(Moment))\s*[0-9IVXA-F]+\\.?(\s*och\s*[0-9IVXA-F]+\\.?)?)")
gradeparExp = re.compile("\\(((Grade)|(than)|((Sub)?Goal))\s*[A-F0-9]+(,?\s*(and)?(or)?\s*[A-F0-9]+)*\\)", re.I)             # (grade D)

############################################################
### Expressions for removing motivation (not goals) text ###
############################################################
iSyfteExp = re.compile("<p>\s*i\s+syfte\s+att", re.I)
forAttExp = re.compile("<p>\s*för\s+att", re.I)
forAttGodkandExp = re.compile("<p>\s*för\s+att.*bli.*godkänd", re.I)
forAttExpEn = re.compile("<p>\s*in\s+order\s+to", re.I)

malExp = re.compile("(<p>(([Kk]urs)|(([Dd]et\s)?[Öö]vergripande))[^<]*?\smål[^<]*\sär\satt[^<]*?)(?=(<\/p>)|(Efter))", re.S)

godkandExp = re.compile("[Ff]ör\s*(betyg(e[nt])?)?\s*((G)|([Gg]odkänd))")
vgExp = re.compile("(((Förväntat)|(Efter))[^A-ZÅÄÖ<>]+)?[Ff]ör\s*(betyg(e[tn])?)?\s*((VG)|([Vv]äl\s*[Gg]odkänd)|([Hh]ögre\s*[Bb]etyg))")
vgExp2 = re.compile("(((Förväntat)|(Efter)|(<p>))[^A-ZÅÄÖ<>]+)[Ff]ör\s*(betyg(e[tn])?)?\s*((VG)|([Vv]äl\s*[Gg]odkänd)|([Hh]ögre\s*[Bb]etyg))")
vgExp3 = re.compile("erhålla högre betyg.*ska", re.I)

###############################################
### Expressions for common writing mistakes ###
###############################################
ochExp = re.compile("\soch([a-zåäö]+)")
attExp = re.compile("\satt([b-df-hj-npqs-zåäö]+)")

htmlTrash = re.compile("(<[^>]*[-][^>]*>)|(</?w[^>]*>)|(<![^>]*>)|(</?m[^>]*>)|(X-NONE)")

##################################################################
### Remove hyphens that are part of the text so they don't get ###
### mistaken for list heading markup hyphens.                  ###
##################################################################
def stripHyphens(inp):
    txt = inp
    txt = re.sub("IT-([^ ])", "IT\\1", txt)
    txt = re.sub("([A-ZÅÄÖa-zåäö])- och ", "\\1 och ", txt)
    txt = re.sub("eller -([^ ])", "eller \\1", txt)
    txt = re.sub("([23]D)-", "\\1", txt)
    txt = re.sub("(GUI)-", "\\1", txt)
    # txtEn = re.sub("Karush-Kuhn-Tucker", "Karush Kuhn Tucker", txtEn)
    txt = re.sub("Karush-Kuhn-Tucker", "Karush Kuhn Tucker", txt)
    txt = re.sub("Stream-", "Stream", txt)

    return txt

def cleanCommonWritingProblems(text):
    res = text
    tmp = res
    
    res = res.replace(u"\u00A0", " ").replace(u"\u00AD", "")
    res = res.replace(u"\u0095", "*").replace("<U+0095>", "*")

    res = res.replace("\n -", "\n –").replace("\n-", "\n–").replace("\n−", "\n–").replace(" — ", " - ").replace("\uF095", "–")
    res = re.sub("([0-9]{4})–([0-9]{4})", "\\1-\\2", res)
    res = re.sub("F-3-", "FHYPHENTREHYPHEN", res)    
    res = re.sub("([F0-9]+)\s*[-–]\s*([0-9]+)", "\\1till\\2", res); # Hyphens are used as list item markers, but also for other things, try to avoid confusion
    res = re.sub("([F0-9]+)\s*[-–]\s*([0-9]+)", "\\1till\\2", res)
    res = re.sub("([a-zåäöA-ZÅÄÖ]{3,})-(\s*((och)|(eller)))", "\\1HYPHEN\\2", res)
    res = re.sub("([a-zåäöA-ZÅÄÖ]{3,})–(\s*((och)|(eller)))", "\\1HyPHEN\\2", res)
    res = re.sub("([A-ZÅÄÖ]{2,})-([a-zåäöA-ZÅÄÖ])", "\\1HYPHEN\\2", res)
    res = re.sub("([A-ZÅÄÖ]{2,})–([a-zåäöA-ZÅÄÖ])", "\\1HyPHEN\\2", res)
    res = re.sub("([a-zåäöA-ZÅÄÖ]{2,})-([,/])", "\\1HYPHEN\\2", res)
    res = re.sub("(non)-", "\\1HYPHEN", res)
    res = re.sub("-(historisk)", "HYPHEN\\1", res)
    res = re.sub("-in-", "HYPHENinHYPHEN", res)
    res = re.sub("-on-", "HYPHENonHYPHEN", res)
    res = re.sub("([A-ZÅÄÖa-zåäö])-([a-zåäö]{2,}[.])", "\\1HYPHEN\\2", res)
    res = re.sub("([A-ZÅÄÖa-zåäö])–([a-zåäö]{2,}[.])", "\\1HyPHEN\\2", res)
    res = re.sub("Hamilton-Jacobi-", "HamiltonHYPHENJacobiHYPHEN", res)    
    res = re.sub("on-line", "onHYPHENline", res)    
    res = re.sub("in- och ut", "inHYPHEN och ut", res)    
    res = re.sub("state-of-the-art", "stateHYPHENofHYPHENtheHYPHENart", res)    
    res = re.sub("meta-data", "metaHYPHENdata", res)    
    res = re.sub("(\s)R-([A-ZÅÄÖa-zåäö])", "\\1RHYPHEN\\2", res)    
    res = re.sub("X((Pointer)|(Path)|(Link))", "\\1", res)
    res = re.sub("meta-([a-zåäö])", "metaHYPHEN\\1", res)    
    
    res = res.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace("&eacute;", "é") # replace some weird codings
    res = re.sub(u"\uF02D", "•", res)

    res = htmlTrash.sub(" ", res)
    res = re.sub("(<[^>]*[-][^>]*>)|(<\/?w[^>]*>)|(<![^>]*>)|(<\/?m[^>]*>)|(X-NONE)", " ", res); # remove some HTML markup we do not use
    
    return res


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

    if c["ILO-sv"] == "NULL" or c["ILO-sv"] == "#NAMN?":
        c["ILO-sv"] = ""
    if c["ILO-en"] == "NULL":
        c["ILO-en"] = ""
        
    sv = c["ILO-sv"]
    en = c["ILO-en"]

    #####################################################
    ### unify hyphens to simplify expression matching ###
    #####################################################
    # sv = sv.replace(u"\u00A0", " ").replace(u"\u00AD", "")
    # en = en.replace(u"\u00A0", " ").replace(u"\u00AD", "")

    # sv = sv.replace(u"\u0095", "*").replace("<U+0095>", "*")
    # en = en.replace(u"\u0095", "*").replace("<U+0095>", "*")
    
    # sv = sv.replace("\n -", "\n–").replace("\n-", "\n–").replace("\n−", "\n–").replace(u"\uF095", "–")
    # sv = re.sub("([0-9]{4})–([0-9]{4})", "\\1-\\2", sv)
    # sv = sv.replace(" — ", " - ")
    # sv = sv.replace("\t", " ")

    # sv = parHeadingsExp.sub(" ", sv) # remove things like "(Lärandemål 3 och 4)" or "(Modul 5, 6, och 7)"
    # sv = parHeadingsExp2.sub(" modul", sv)

    # sv = delkursExp.sub("", sv)
    # sv = delkursExp2.sub("", sv)


    # sv = delparExp.sub("", sv)
    # sv = ccparExp.sub("", sv)
    # sv = betygparExp.sub("", sv)
    # sv = momentExp.sub("", sv)

    # # sv = re.sub("([F0-9]+)\s*[-–]\s*([0-9]+)", "\\1 till \\2", sv)
    # sv = re.sub("([F0-9]+)\s*[-–]\s*([0-9]+)", "\\1till\\2", sv)
    # sv = re.sub("([a-zåäöA-ZÅÄÖ]{3,})-(\s*((och)|(eller)))", "\\1HYPHEN\\2", sv)
    # sv = re.sub("([a-zåäöA-ZÅÄÖ]{3,})–(\s*((och)|(eller)))", "\\1HyPHEN\\2", sv)
    # sv = re.sub("([A-ZÅÄÖ]{2,})-([a-zåäöA-ZÅÄÖ])", "\\1HYPHEN\\2", sv)
    # sv = re.sub("([A-ZÅÄÖ]{2,})–([a-zåäöA-ZÅÄÖ])", "\\1HyPHEN\\2", sv)
    # sv = re.sub("([a-zåäöA-ZÅÄÖ]{2,})-([,/])", "\\1HYPHEN\\2", sv)
    # sv = re.sub("(non)-", "\\1HYPHEN", sv)
    # sv = re.sub("-(historisk)", "HYPHEN\\1", sv)
    # sv = re.sub("-in-", "HYPHENinHYPHEN", sv)
    # sv = re.sub("-on-", "HYPHENonHYPHEN", sv)
    # sv = re.sub("([A-ZÅÄÖa-zåäö])-([a-zåäö]{2,}[.])", "\\1HYPHEN\\2", sv)
    # sv = re.sub("([A-ZÅÄÖa-zåäö])–([a-zåäö]{2,}[.])", "\\1HyPHEN\\2", sv)
    # sv = re.sub("Hamilton-Jacobi-", "HamiltonHYPHENJacobiHYPHEN", sv)    
    # sv = re.sub("X((Pointer)|(Path)|(Link))", "\\1", sv)
    
    # en = gradeparExp.sub("", en)

    # ##############################
    # ### Fix some weird codings ###
    # ##############################
    # sv = sv.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ").replace(u'\uf02d', "•")
    # sv = sv.replace("&eacute;", "é")

    sv = cleanCommonWritingProblems(sv)
    en = cleanCommonWritingProblems(en)

    sv = sv.strip()
    while len(sv) and sv[0] == '"':
        sv = sv[1:]
    while len(sv) and sv[-1] == '"':
        sv = sv[:-1]
    
    iloList = []
    iloListEn = []
    
    # #############################
    # ### Remove some HTML tags ###
    # #############################
    # sv = htmlTrash.sub(" ", sv)
    # en = htmlTrash.sub(" ", en)
    
    
    ########################################
    ### Fix some common writing mistakes ###
    ########################################

    sv = ochExp.sub(" och \\1", sv)
    sv = attExp.sub(" att \\1", sv)
    
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

    # log("After iSyfte sv=", sv)
    
    m = malExp.search(sv)
    if m:
        sv = malExp.sub("", sv)

    # log("After malExp sv=", sv)
        
    if SKIP_VG:
        skip = 0
        m = godkandExp.search(sv)
        if m:
            m2 = vgExp.search(sv)
            if m2 and m2.start() > m.start():
                skip = 1
                sv = sv[:m2.start()]
        else:
            m2 = vgExp.search(sv)
            if m2:
                skip = 1
                sv = sv[:m2.start()]
        
        if m:
            m2 = vgExp2.search(sv)
            if m2 and m2.start() > m.start():
                skip = 1
                sv = sv[:m2.start()]
        else:
            m2 = vgExp2.search(sv)
            if m2:
                skip = 1
                sv = sv[:m2.start()]

        if m:
            m2 = vgExp3.search(sv)
            if m2 and m2.start() > m.start():
                skip = 1
                sv = sv[:m2.start()]
        else:
            m2 = vgExp3.search(sv)
            if m2:
                skip = 1
                sv = sv[:m2.start()]
    if en:
        m = forAttExpEn.search(en)
        if m and m.start() > 0:
            en = forAttExpEn.split(en)[0]  # remove everything from "in order to" and forward
    
    found = 0

    if htmlListExpIndicator.search(sv) or htmlListExpIndicator.search(en): # This expression is slow to match, so only try if a faster expression matches
        sv, en = matchAndConsume(htmlListExpWrap, htmlListExp, sv, htmlListExpWrapEn, htmlListExp, en, "html-list", iloList, iloListEn)
        sv, en = matchAndConsumeSpecial(htmlListExpWrap3, htmlListExp, sv, htmlListExpWrapEn3, htmlListExp, en, "html-list-3", iloList, iloListEn) # should run before #2
        sv, en = matchAndConsume(htmlListExpWrap2, htmlListExp, sv, htmlListExpWrap2, htmlListExp, en, "html-list-2", iloList, iloListEn)

    if sv.find("<p>") >= 0 or en.find("<p>") >= 0:
        sv, en = matchAndConsume(pListExpWrap, pListExp, sv, pListExpWrapEn, pListExp, en, "p-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuFSRexpWrap, umuFSRexp, sv, umuFSRexp, umuFSRexp, en, "FSR-list", iloList, iloListEn)
    
    sv, en = matchAndConsume(efterModulExpWrap, efterModulExp, sv, efterModulExpWrap, efterModulExp, en, "efter-modul-list", iloList, iloListEn)

    sv, en = matchAndConsume(threedotListExpWrap, threedotListExp, sv, threedotListExpWrap, threedotListExp, en, "three-dot-list", iloList, iloListEn)
    sv, en = matchAndConsume(abcExpWrap, abcExp, sv, abcExpWrap, abcExp, en, "abc-list", iloList, iloListEn)
    sv, en = matchAndConsume(iIIiiiExpWrap, iIIiiiExp, sv, iIIiiiExpWrap, iIIiiiExp, en, "i-ii-iii-list", iloList, iloListEn)

    sv, en = matchAndConsume(attStudentenKanExpWrap, attStudentenKanExp, sv, attStudentenKanExpWrap, attStudentenKanExp, en, "att-studentenkan-list", iloList, iloListEn)
    
    sv, en = matchAndConsume(efterSkaKunnaExpWrap, efterSkaKunnaExp, sv, efterSkaKunnaExpWrap, efterSkaKunnaExp, en, "efter-ska-kunna-exp", iloList, iloListEn)
    sv, en = matchAndConsume(efterSkaKunnaExp2Wrap, efterSkaKunnaExp, sv, efterSkaKunnaExp2Wrap, efterSkaKunnaExp, en, "efter-ska-kunna-exp2", iloList, iloListEn)

    sv, en = matchAndConsume(umuNLHaExpWrap, umuNLHaExp, sv, umuNLHaExpWrap, umuNLHaExp, en, "umu-NL-ha-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuHypHaAndStarExpWrap, umuHypHaAndStarExp, sv, umuHypHaAndStarExpWrap, umuHypHaAndStarExp, en, "umu-Hyp-Ha-and-Star-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuHypHaExpWrap, umuHypHaExp, sv, umuHypHaExpWrap, umuHypHaExp, en, "umu-Hyp-Ha-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuHaExpWrap, umuHaExp, sv, umuHaExpWrap, umuHaExp, en, "umu-Ha-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuNLExp2Wrap, umuNLExp2, sv, umuNLExp2Wrap, umuNLExp2, en, "umu-NL-list-2", iloList, iloListEn)

    sv, en = matchAndConsume(umuNLExpWrap, umuNLExp, sv, umuNLExpWrap, umuNLExp, en, "umu-NL-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuAstExpWrap, umuAstExp, sv, umuAstExpWrap, umuAstExp, en, "umu-Asterisk-list", iloList, iloListEn)

    if sv.find("LM1") >= 0 or en.find("LM1") >= 0:
        sv, en = matchAndConsume(lm1ExpWrap, lm1Exp, sv, lm1ExpWrap, lm1Exp, en, "LM-1-list", iloList, iloListEn)

    if brListIndicator.search(sv) or brListIndicator.search(en):
        sv, en = matchAndConsume(brListExpWrap, brListExp, sv, brListExpWrapEn, brListExp, en, "br-list", iloList, iloListEn)
        sv, en = matchAndConsume(brListExpWrap2, brListExp, sv, brListExpWrap2, brListExp, en, "br-list-2", iloList, iloListEn)

    sv, en = matchAndConsume(newlineListExpWrap, newlineListExp, sv, newlineListExpWrap, newlineListExp, en, "newline-list", iloList, iloListEn)
    
    sv, en = matchAndConsume(dotListBeforeExpWrap, dotListBeforeExp, sv, dotListBeforeExpWrap, dotListBeforeExp, en, "dot-before-list", iloList, iloListEn)
    sv, en = matchAndConsume(dotListExpWrap, dotListExp, sv, dotListExpWrap, dotListExp, en, "dot-list", iloList, iloListEn)
    sv, en = matchAndConsume(dotListOExpWrap, dotListOExp, sv, dotListOExpWrap, dotListOExp, en, "dot-list-O", iloList, iloListEn)

    # tmp = sv.replace(".o", ". o").replace("Färdighet och förmåga", " ").replace("Kunskap och förståelse", " ").replace("Värderingsförmåga och förhållningssätt", " ")
    # sv, en = matchAndConsume(oListExpWrap, oListExp, tmp, oListExpWrap, oListExp, en, "o-list", iloList, iloListEn)
    sv, en = matchAndConsume(oListExpWrap, oListExp, sv, oListExpWrap, oListExp, en, "o-list", iloList, iloListEn)

    if inlineHyphenIndicator.search(sv) or inlineHyphenIndicator.search(en):
        sv, en = matchAndConsume(inlineHyphenListExpWrap, inlineHyphenListExp, sv, inlineHyphenListExpWrap, inlineHyphenListExp, en, "inline-hyphen-list", iloList, iloListEn)
    
    if romanListIndicator.search(sv) or romanListIndicatorEn.search(en): # This expression is slow to match, so only try if a faster expression matches
        sv, en = matchAndConsume(romanListExpWrap, romanListExp, sv, romanListExpWrap, romanListExp, en, "roman-list", iloList, iloListEn)

    if arabicPListIndicator.search(sv):
        sv, en = matchAndConsume(arabicPListExpWrap, arabicPListExp, sv, arabicPListExpWrap, arabicPListExp, en, "arabic-P-list", iloList, iloListEn)

    sv, en = matchAndConsume(parListExpWrap, parListExp, sv, parListExpWrap, parListExp, en, "par-list", iloList, iloListEn)
    sv, en = matchAndConsume(parListExpWrap2, parListExp2, sv, parListExpWrap2, parListExp2, en, "par-list-2", iloList, iloListEn)
    
    sv, en = matchAndConsume(arabicListExpWrap123, arabicListExp, sv, arabicListExpWrap123, arabicListExp, en, "arabic-list-123", iloList, iloListEn)
    sv, en = matchAndConsume(arabicListExpWrap12345, arabicListExp12345, sv, arabicListExpWrap12345, arabicListExp12345, en, "arabic-list-12345", iloList, iloListEn)
        
    if umuWSindicator.search(sv):
        sv, en = matchAndConsume(umuWSExpWrap, umuWSExp, sv, umuWSExpWrap, umuWSExp, en, "umu-WS-list", iloList, iloListEn)
    else:
        log("umu-ws, indicator failed, TEXT:", sv)

    sv, en = matchAndConsume(miunWSexpWrap, miunWSexp, sv, miunWSexpWrap, miunWSexp, en, "miun-ws", iloList, iloListEn)

    sv, en = matchAndConsume(kunnaSemiColonExpWrap, kunnaSemiColonExp, sv, kunnaSemiColonExpWrap, kunnaSemiColonExp, en, "semi-colon-list", iloList, iloListEn)
        
    if kunna1indicator.search(sv):
        sv, en = matchAndConsume(kunna1expWrap, kunna1exp, sv, kunna1expWrapEn, kunna1exp, en, "kunna-1-exp", iloList, iloListEn)
    else:
        log("kunna-1 indicator failed, TEXT:", sv)
        
    for i in range(len(iloList)): # this captures too much in common UMU patterns, so we add a small correction here
        iloList[i] = kunna1sub.sub(" ", iloList[i])

    sv, en = matchAndConsume(kunnaCapExpWrap, kunnaCapExp, sv, kunnaCapExpWrapEn, kunnaCapExp, en, "kunna-Cap-exp", iloList, iloListEn)

    if kunnaHypIndicator.search(sv):
        sv, en = matchAndConsume(kunnaHypExpWrap, kunnaHypExp, sv, kunnaHypExpWrapEn, kunnaHypExp, en, "kunna-hyp-exp", iloList, iloListEn)
        sv, en = matchAndConsume(kunnaHypExpWrap2, kunnaHypExp, sv, kunnaHypExpWrap2, kunnaHypExp, en, "kunna-hyp-exp-2", iloList, iloListEn)

    sv, en = matchAndConsume(efterSkallExpWrap, efterSkallExp, sv, efterSkallExpWrap, efterSkallExp, en, "efter-ska-exp", iloList, iloListEn)
    sv, en = matchAndConsume(efterSkallExp2Wrap, efterSkallExp2, sv, efterSkallExp2Wrap, efterSkallExp2, en, "efter-ska-exp2", iloList, iloListEn)

    sv, en = matchAndConsume(avenKunnaExpWrap, avenKunnaExp, sv, avenKunnaExpWrap, avenKunnaExp, en, "aven-kunna-exp", iloList, iloListEn)
    
    sv, en = matchAndConsume(umuMomentExpWrap, umuMomentExp, sv, umuMomentExpWrap, umuMomentExp, en, "moment-exp", iloList, iloListEn)

    sv, en = matchAndConsume(skaEfterAvslutadExpWrap, skaEfterAvslutadExp, sv, skaEfterAvslutadExpWrap, skaEfterAvslutadExp, en, "ska-efter-avslutad-exp", iloList, iloListEn)

    sv, en = matchAndConsume(skaEfterAvslutadRevExpWrap, skaEfterAvslutadRevExp, sv, skaEfterAvslutadRevExpWrap, skaEfterAvslutadRevExp, en, "ska-efter-avslutad-rev-exp", iloList, iloListEn)

    sv, en = matchAndConsume(dessutomSkaExpWrap, dessutomSkaExp, sv, dessutomSkaExpWrap, dessutomSkaExp, en, "dessutom-ska-exp", iloList, iloListEn)
    
    if len(iloList) <= 0:
        sv, en = matchAndConsume(umuCatchallExpWrap, umuCatchallExp, sv, umuCatchallExpWrap, umuCatchallExp, en, "umu-Catch-All-list", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(arabicListExpWrap, arabicListExp, sv, arabicListExpWrap, arabicListExp, en, "arabic-list", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(arabicListExpBWrap, arabicListExpB, sv, arabicListExpWrap, arabicListExp, en, "arabic-list-B", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNLExpWrap, kunnaNLExp, sv, kunnaNLExpWrap, kunnaNLExp, en, "kunna-NL-list", iloList, iloListEn)
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNLExp2Wrap, kunnaNLExp2, sv, kunnaNLExp2Wrap, kunnaNLExp2, en, "kunna-NL-list-2", iloList, iloListEn)
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNLExp3Wrap, kunnaNLExp3, sv, kunnaNLExp3Wrap, kunnaNLExp3, en, "kunna-NL-list-3", iloList, iloListEn)

    sv, en = matchAndConsume(kunnaNLExp4Wrap, kunnaNLExp4, sv, kunnaNLExp4Wrap, kunnaNLExp4, en, "kunna-NL-list-4", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNLExp5Wrap, kunnaNLExp5, sv, kunnaNLExp5Wrap, kunnaNLExp5, en, "kunna-NL-list-5", iloList, iloListEn)
        
    #if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
    sv, en = matchAndConsume(skaKunnaExp, skaKunnaExp, sv, skaKunnaExpEn, skaKunnaExpEn, en, "ska-kunna-list", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kanExp, kanExp, sv, kanExpEn, kanExpEn, en, "kan-exp", iloList, iloListEn) 

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(fortrogenExp, fortrogenExp, sv, fortrogenExpEn, fortrogenExpEn, en, "fortrogen-exp", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(formagaExp, formagaExp, sv, formagaExpEn, formagaExpEn, en, "formaga-exp", iloList, iloListEn)
    
    if len(iloList) <= 0 and (pHypListIndicator.search(sv) or pHypListIndicator.search(en)): # faster check before slow matching
        sv, en = matchAndConsume(pHypListExpWrap, pHypListExp, sv, pHypListExpWrapEn, pHypListExp, en, "p-hyp-list", iloList, iloListEn)

    if len(iloList) <= 0 and pRawListIndicator.search(sv):
        sv, tmp = matchAndConsume(pRawListExpWrap, pRawListExp, sv, pRawListExpWrapEn, pRawListExp, "", "p-raw-list", iloList, iloListEn)
    if len(iloListEn) <= 0 and pRawListIndicatorEn.search(en): # faster check before slow matching
        tmp, en = matchAndConsume(pRawListExpWrap, pRawListExp, "", pRawListExpWrapEn, pRawListExp, en, "p-raw-list", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(oneparExpWrap, oneparExp, sv, oneparExpWrap, oneparExp, en, "one-par", iloList, iloListEn)
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(oneparExpWrap2, oneparExp, sv, oneparExpWrap2, oneparExp, en, "one-par2", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(onelineExpWrap, onelineExp, sv, onelineExpWrap, onelineExp, en, "one-line", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(del1del2ExpWrap, del1del2Exp, sv, del1del2ExpWrap, del1del2Exp, en, "del1-del2", iloList, iloListEn)
        

        
                        

    

    sv, en = matchAndConsume(XxListExpWrap, XxListExp, sv, XxListExpWrap, XxListExp, en, "Xx-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuHaLinesWrap, umuHaLines, sv, umuHaLinesWrapEn, umuHaLines, en, "umu-ha-lines", iloList, iloListEn)

    # svTmp = stripHyphens(sv)
    # sv, tmp = matchAndConsumeSpecial(umuEfterHypWrapSpec2, umuEfterHyp, svTmp, umuEfterHyp, umuEfterHyp, "", "efter-hyphen-Spec-list", iloList, iloListEn)
    
    if umuEfterHypIndicator.search(sv) and not umuEfterHypNegativeIndicator.search(sv):
        sv, en = matchAndConsumeSpecial(umuEfterHypWrapSpec, umuEfterHyp, sv, umuEfterHyp, umuEfterHyp, en, "efter-hyphen-Spec-list", iloList, iloListEn)
        sv, en = matchAndConsume(umuEfterHypWrap, umuEfterHyp, sv, umuEfterHyp, umuEfterHyp, en, "efter-hyphen-list", iloList, iloListEn)

    sv, en = matchAndConsume(vetaHurExp, vetaHurExp, sv, vetaHurExp, vetaHurExp, en, "veta-hur-list", iloList, iloListEn)
    
    sv, tmp = matchAndConsume(formuleraExp, formuleraExp, sv, formuleraExp, formuleraExp, "", "formulera-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuSkaHaExpWrap2, umuSkaHaExp2, sv, umuSkaHaExp, umuSkaHaExp, en, "umu-ska-ha-list-2", iloList, iloListEn)
    sv, en = matchAndConsume(umuSkaHaExpWrap, umuSkaHaExp, sv, umuSkaHaExp, umuSkaHaExp, en, "umu-ska-ha-list", iloList, iloListEn)
                             
    sv, en = matchAndConsume(umuAvseendeExpWrap, umuAvseendeExp, sv, umuAvseendeExp, umuAvseendeExp, en, "avseende-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuSamtligaMomentExpWrap, umuSamtligaMomentExp, sv, umuSamtligaMomentExp, umuSamtligaMomentExp, en, "Samtliga-moment-list", iloList, iloListEn)

    sv, tmp = matchAndConsume(forGodkandExpWrap, forGodkandExp, sv, forGodkandExpWrap, forGodkandExp, "", "for-godkand-list", iloList, iloListEn)
    sv, tmp = matchAndConsume(forGodkandExpWrap2, forGodkandExpWrap2, sv, forGodkandExpWrap, forGodkandExp, "", "for-godkand-list", iloList, iloListEn)

    sv, en = matchAndConsume(efterKunnaExpWrap, efterKunnaExp, sv, efterKunnaExpWrap, efterKunnaExp, en, "efter-kunna-list", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNewlineExpWrap, kunnaNewlineExp, sv, kunnaNewlineExpWrapEn, kunnaNewlineExp, en, "kunna-newline-list", iloList, iloListEn)

    if kunnaNewlineExpWrap2Indicator.search(sv):
        sv, en = matchAndConsume(kunnaNewlineExpWrap2, kunnaNewlineExp, sv, kunnaNewlineExpWrapEn, kunnaNewlineExp, en, "kunna-newline-list-2", iloList, iloListEn)

    sv, tmp = matchAndConsume(umuNewlinesExpWrap4, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, "", "umu-newlines-4", iloList, iloListEn) 
    sv, tmp = matchAndConsume(umuNewlinesExpWrap5, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, "", "umu-newlines-5", iloList, iloListEn) 
        
    sv, en = matchAndConsume(kunnaAexpWrap, kunnaAexp, sv, kunnaAexpWrapEn, kunnaAexp, en, "kunna-a-exp", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaSentenceExp, kunnaSentenceExp, sv, kunnaSentenceExpEn, kunnaSentenceExpEn, en, "kunna-sentence-exp", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(tillfalleExp, tillfalleExp, sv, tillfalleExpEn, tillfalleExpEn, en, "tillfalle-exp", iloList, iloListEn)
        sv, en = matchAndConsume(traningExp, traningExp, sv, traningExpEn, traningExpEn, en, "traning-exp", iloList, iloListEn)
                    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaHyphenBWrap, kunnaHyphenB, sv, kunnaHyphenBWrapEn, kunnaHyphenB, en, "kunna-hyp-B-list", iloList, iloListEn)
    
    if len(iloList) <= 0:
        sv, tmp = matchAndConsume(pRawListExp, pRawListExp, sv, pRawListExpWrapEn, pRawListExp, "", "p-raw-list", iloList, iloListEn)
    if len(iloListEn) <= 0:
        tmp, en = matchAndConsume(pRawListExp, pRawListExp, "", pRawListExp, pRawListExp, en, "p-raw-list", iloList, iloListEn)
    # if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
    #     sv, en = matchAndConsume(onlyPListExp, onlyPListExp, sv, onlyPListExp, onlyPListExp, en, "p-only-list", iloList, iloListEn)

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(umuHypExpWrap, umuHypExp, sv, umuHypExpWrap, umuHypExp, en, "umu-hypens", iloList, iloListEn) 
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(umuNewlinesExpWrap, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, en, "umu-newlines", iloList, iloListEn) 
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(umuNewlinesExpWrap2, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, en, "umu-newlines-2", iloList, iloListEn) 
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(umuNewlinesExpWrap3, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, en, "umu-newlines-3", iloList, iloListEn) 

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(whitespacesExpWrap, whitespacesExp, sv, whitespacesExpWrapEn, whitespacesExp, en, "whitespace", iloList, iloListEn) 
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(whitespacesExpWrap2, whitespacesExp2, sv, whitespacesExpWrap2, whitespacesExp2, en, "whitespace", iloList, iloListEn)


    ### If nothing is found, try to add the whole text ###
    if len(iloList) <= 0:
        sv = cleanStr(c["ILO-sv"])
        if len(sv):
            iloList.append(sv)

    if len(iloListEn) <= 0:
        en = cleanStr(c["ILO-en"])
        if len(en):
            iloListEn.append(en)

    ### Fix for some faulty matchings

    iloList = iloListFixes(iloList)
    iloListEn = iloListFixes(iloListEn)

    tmp = []
    for ilo in iloList:
        iloFix = ilo
        iloFix = re.sub("FHYPHENTREHYPHEN", "F-3-", iloFix)
        iloFix = re.sub("([F0-9]+)till([0-9]+)", "\\1 - \\2", iloFix)
        iloFix = re.sub("([a-zåäöA-ZÅÄÖ]{3,})HYPHEN(\s*((och)|(eller)))", "\\1-\\2", iloFix)
        iloFix = re.sub("([a-zåäöA-ZÅÄÖ]{3,})HyPHEN(\s*((och)|(eller)))", "\\1–\\2", iloFix)
        iloFix = re.sub("([A-ZÅÄÖ]{2,})HYPHEN([a-zåäöA-ZÅÄÖ])", "\\1-\\2", iloFix)
        iloFix = re.sub("([A-ZÅÄÖ]{2,})HyPHEN([a-zåäöA-ZÅÄÖ])", "\\1–\\2", iloFix)
        iloFix = re.sub("([a-zåäöA-ZÅÄÖ]{2,})HYPHEN([,/])", "\\1-\\2", iloFix)
        iloFix = re.sub("(non)HYPHEN", "\\1-", iloFix)
        iloFix = re.sub("HYPHEN(historisk)", "-\\1", iloFix)
        iloFix = re.sub("HYPHENinHYPHEN", "-in-", iloFix)
        iloFix = re.sub("HYPHENonHYPHEN", "-on-", iloFix)
        iloFix = re.sub("([A-ZÅÄÖa-zåäö])HyPHEN([a-zåäö]{2,}([.]|$))", "\\1–\\2", iloFix)
        iloFix = re.sub("([A-ZÅÄÖa-zåäö])HYPHEN([a-zåäö]{2,}([.]|$))", "\\1-\\2", iloFix)
        iloFix = re.sub("HamiltonHYPHENJacobiHYPHEN", "Hamilton-Jacobi-", iloFix)
        iloFix = re.sub("onHYPHENline", "on-line", iloFix)
        iloFix = re.sub("inHYPHEN och ut", "in- och ut", iloFix)
        iloFix = re.sub("stateHYPHENofHYPHENtheHYPHENart", "state-of-the-art", iloFix)
        iloFix = re.sub("metaHYPHENdata", "meta-data", iloFix)
        iloFix = re.sub("(\s)RHYPHEN([A-ZÅÄÖa-zåäö])", "\\1R-\\2", iloFix)
        iloFix = re.sub("metaHYPHEN([a-zåäö])", "meta-\\1", iloFix)
        tmp.append(iloFix)
    iloList = tmp
    
    return (iloList, iloListEn)

##########################################################################
### Match parts of the ILO text, and removed the matched text so other ###
### heuristics do not match the same text again.                       ###
##########################################################################

times = {}
def matchAndConsume(allExp, goalExp, sv, allExpEn, goalExpEn, en, name, lsS, lsE):
    iloListSv = []
    iloListEn = []
    iloList = []

    startime = timer()
    # log("matchAndConsume starting!", name)

    #if(name == "dot-list" or name == "efter-ska-kunna-exp" and name == "arabic-list-12345" and name == "arabic-list-123"):
    # if name == "ska-kunna-list":
    #     log("TEXT:", sv)
    #     log("MATCH:", allExp.search(sv))
    
    m = allExp.search(sv)
    # log("matchAndConsume initial search finished!", name)

    while m:
        log("\nFOUND", name)
        log("\n" + str(m.start()) + " " + str(m.end()), "'" + sv[m.start():m.end()] + "'\n")
        found = 0

        ### Text of the wrapper expression, for example the
        ### <ol>...</ol>, used to extract each individual expression,
        ### for example each <li>...</li>
        txt = sv[m.start():m.end()]
        
        ls = goalExp.findall(txt)
        
        for l in ls:
            if isinstance(l, tuple): # regular expression with nested paranthesis return tuples, with the whole match at index 0
                l = l[0]
            ll = cleanStr(l)
            if len(ll):
                iloListSv.append(ll)
                log(name, ll)
                found = 1
        if found:
            sv = sv[:m.start()] + " " + sv[m.end():]
            # log("We found something, NEW TEXT:", sv)
            m = allExp.search(sv)
        else:
            m = allExp.search(sv, m.end() + 1)

    if en:
        m = allExpEn.search(en)

        while m:
            log("\nFOUND", name + "En")
            log(str(m.start()) + " " + str(m.end()), en[m.start():m.end()] + "\n")
            
            found = 0
            txt = en[m.start():m.end()]
            
            ls = goalExpEn.findall(txt)
            for l in ls:
                if isinstance(l, tuple): # regular expression with nested paranthesis return tuples, with the whole match at index 0
                    l = l[0]
                if l.find("able to:") < 5 and l.find("know how to:") < 0:
                    ll = cleanStr(l)
                    if len(ll):
                        iloListEn.append(ll)
                        log(name+"En", ll)
                        found = 1
            if found:
                en = en[:m.start()] + " " + en[m.end():]
                m = allExpEn.search(en)
            else:
                m = allExpEn.search(en, m.end() + 1)

    if en:
        S = len(iloListSv)
        E = len(iloListEn)
        if S != E:
            log("matchAndConsume", "WARNING: Number of matches in Swe and Eng are different! " + name)
            log("Matches: ", str(S) + " " + str(E))

        lsS.extend(iloListSv)
        lsE.extend(iloListEn)
    else:
        lsS.extend(iloListSv)
    endtime = timer()
    if not name in times:
        times[name] = 0
    times[name] += endtime - startime

    # log("\nReturning this text:", sv + "\n")
    
    return (sv, en)

##########################################################################
### Match parts of the ILO text, and removed the matched text so other ###
### heuristics do not match the same text again. This version is used  ###
### when a part of the wrapping expression should be added to each     ###
### goal, such as "students shall be able to                           ###
### understand<ul><li>match</li><li>physics</li></ul>" which happens   ###
### with one verb and a list of objects for the verb.                  ###
##########################################################################
def matchAndConsumeSpecial(allExp, goalExp, sv, allExpEn, goalExpEn, en, name, lsS, lsE):
    iloListSv = []
    iloListEn = []
    iloList = []

    # log("matchAndConsumeSpecial starting!", name)
    
    startime = timer()
    m = allExp.search(sv)

    while m:
        log("\nFOUND", name)
        log(str(m.start()) + " " + str(m.end()), "'" + sv[m.start():m.end()] + "'\n")
        found = 0
        
        head = ""
        for gg in range(1, len(m.groups())):
            g = m.group(gg)
            if len(g) and g[0] != "<":
                head = g.strip()
                break
        
        txt = sv[m.start():m.end()]
        ls = goalExp.findall(txt)

        for l in ls: 
            if isinstance(l, tuple): # regular expression with nested paranthesis return tuples, with the whole match at index 0
                l = l[0]
            ll = cleanStr(head + " " + l)
            if len(ll):
                iloListSv.append(ll)
                log(name, ll)
                found = 1
        if found:
            sv = sv[:m.start()] + " " + sv[m.end():]
            m = allExp.search(sv)
        else:
            m = allExp.search(sv, m.end() + 1)

    if en:
        m = allExpEn.search(en)
        while m:
            log("\nFOUND", name + "EN")
            log(str(m.start()) + " " + str(m.end()), en[m.start():m.end()] + "\n")
            
            found = 0
            txt = en[m.start():m.end()]
            head = ""
            for g in m.groups():
                if g and len(g) and g[0] != "<" and g != "able" and g[:4] != "know":
                    head = g.strip()
                    break
            
            ls = goalExpEn.findall(txt)
            for l in ls:
                if isinstance(l, tuple): # regular expression with nested paranthesis return tuples, with the whole match at index 0
                    l = l[0]
                if l.find("able to:") < 0 and l.find("know how to:") < 0:
                    ll = cleanStr(head + " " + l)
                    if len(ll):
                        iloListEn.append(ll)
                        log(name+"En", ll)
                        found = 1
            if found:
                en = en[:m.start()] + " " + en[m.end():]
                m = allExpEn.search(en)
            else:
                m = allExpEn.search(en, m.end() + 1)

    if en:
        S = len(iloListSv)
        E = len(iloListEn)
        if S != E:
            log("matchAndConsume", "WARNING: Number of matches in Swe and Eng are different! " + name)
            log("Matches: ", str(S) + " " + str(E))

        lsS.extend(iloListSv)
        lsE.extend(iloListEn)
    else:
        lsS.extend(iloListSv)
    endtime = timer()
    if not name in times:
        times[name] = 0
    times[name] += endtime - startime
    return (sv, en)

########################################################################
### Clean up matched strings, handle things such as common errors or ###
### non-standard list markers                                        ###
########################################################################
def iloListFixes(iloList):
    newLs = []
    for goal in iloList:
        ls = goal.split(",-")
        if len(ls) > 1:
            for g in ls:
                gg = g.strip()
                if len(gg):
                    newLs.append(gg)
        else:
            newLs.append(goal)
    if len(newLs) > len(iloList):
        iloList = newLs

    newLs = []
    for goal in iloList:
        ls = goal.split(".-")
        if len(ls) > 1:
            for g in ls:
                gg = g.strip()
                if len(gg):
                    newLs.append(gg)
        else:
            newLs.append(goal)
    if len(newLs) > len(iloList):
        iloList = newLs

    newLs = []
    for goal in iloList:
        ls = goal.split(" X ")
        if len(ls) <= 2:
            ls = goal.split("•")
        if len(ls) > 2:
            for g in ls:
                gg = g.strip()
                if len(gg):
                    newLs.append(gg)
        else:
            newLs.append(goal)
    if len(newLs) > len(iloList):
        iloList = newLs

    newLs = []
    for goal in iloList:
        ls = re.split("FSR [0-9]+", goal)
        if len(ls) > 2:
            for g in ls:
                gg = g.strip()
                if len(gg):
                    newLs.append(gg)
        else:
            newLs.append(goal)
    if len(newLs) > len(iloList):
        iloList = newLs
        
    newLs = []
    changes = 0
    for goal in iloList:
        ngoal = goal.replace("-kunna", " kunna").replace("-uppvisa", " uppvisa")
        if goal != ngoal:
            newLs.append(ngoal)
            chages = 1
        else:
            newLs.append(goal)
    if changes:
        iloList = newLs

    newLs = []
    for goal in iloList:
        tail = goal
        m = hypNoSpaceExp.search(tail)
        ls = []
        while m:
            tmp = tail
            head = tail[:m.start()+1].strip()
            tail = tail[m.end() - 2:].strip()
            if len(head) > 20 and len(tail) > 20:
                ls.append(head)
                m = hypNoSpaceExp.search(tail)
            else:
                m = 0
                tail = goal
                ls = []
        ls.append(tail)
        if len(ls) > 2:
            newLs.extend(ls)
        elif len(ls) > 1 and ls[0].strip()[0] == "-":
            newLs.extend(ls)
        else:
            newLs.append(goal)
    if len(newLs) != len(iloList):
        iloList = newLs
    
    return iloList

######################################################################
### Check if a goal starts with upper or lower case. If lower case ###
### (i.e. probably not a complete sentence), add a dummy sentence  ###
### head.                                                          ###
######################################################################
def startcheck(ls):
    res = []
    for si in range(len(ls)):
        s = ls[si].strip()
        while len(s) and (s[0] == "-" or s[0] == "/" or s[0] == ")"):
            s = s[1:].strip()
        if len(s) and s[0].isupper():
            pass
        elif len(s) and s[0].islower():
            if s[:5] == "kunna":
                s = "Du ska " + s
            elif s[:3] == "ha ":
                s = "Du ska " + s
            else:
                s = "Du ska kunna " + s
        if s[-3:] == "och":
            s = s[:-3].strip()

        p = s.find("För att bli godkänd")
        if p > 10:
            s = s[:p]
        if s[-5:] == "kunna":
            continue # most likely a faulty match, skip
        if s[-5:] == "skall":
            continue # most likely a faulty match, skip
        if len(s) and not s[-1] in string.punctuation:
            s += " ."
        res.append(s)
    if len(res) == 0 and len(ls) == 1:
        res = ls
    return res

#######################################################################
### Check if the goal looks like a sentence or just a fragment that ###
### could use a sentence head                                       ###
#######################################################################
def startcheckEn(ls):
    res = []
    for si in range(len(ls)):
        s = ls[si]
        if s[0].isupper():
            pass
        elif s[0].islower():
            if s[:2] == "to":
                s = "You should be able " + s
            elif s[:7] == "able to":
                s = "You should be " + s
            elif s[:10] == "be able to":
                s = "You should " + s
            else:
                s = "You should be able to " + s

        if not s[-1] in string.punctuation:
            s += " ."
        res.append(s)
    if len(res) == 0 and len(ls) == 1:
        res = ls
    return res

######################################
### For each course, extract goals ###
######################################
for c in data["Course-list"]:
    log("New course ---------------------------------------------", c["CourseCode"])
    iloList, iloListEn = extractGoals(c)

    iloList = startcheck(iloList)
    c["ILO-list-sv"] = iloList
    
    iloListEn = startcheckEn(iloListEn)
    c["ILO-list-en"] = iloListEn
    
    cleanUp(c)

    if doXX:
        updateLevelAttribute(c)

    checkPre(c)

ls = []
for name in times:
    ls.append([times[name], name])
ls.sort()

for p in ls:
    log(p[1], "runtime {:1.2f}".format(p[0]))
    
##############################
### Print result to stdout ###
##############################
print(json.dumps(data))
