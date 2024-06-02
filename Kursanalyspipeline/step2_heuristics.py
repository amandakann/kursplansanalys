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
htmlListExpWrap = re.compile("(<[Pp]>)?[^<>]*kunna:?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)
htmlListExpWrap2 = re.compile("<.[Ll]>.*?</.[Ll]>", re.S)
htmlListExp = re.compile("<[lL][Ii]>(.*?)(?:</?[Ll][Ii]>)", re.S)

htmlListExpWrapEn = re.compile("(<[Pp]>)?[^<>]*((know\s*how)|(able))\s*to:?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)

htmlListExpWrap3 = re.compile("(<[Pp]>)?[^<>]*kunna\s*([^<>]{4,}):?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)
htmlListExpWrapEn3 = re.compile("(<[Pp]>)?[^<>]*((know\s*how)|(able))\s*to\s*([^<>]{4,}):?\s*(</?[Pp]>\s*)*<.[lL]>.*?</.[lL]>", re.S)


htmlListExpIndicator = re.compile("<[lL][Ii]>")

### KTH courses can use HTML <p>-elements for goals
###   "<p>Efter genomförd kurs ska studenten kunna</p><p>• upprätta resurser för ... ,</p><p>\u2022 utföra spaning ..."
###   (example course KTH FEP3370)
pListExp = re.compile("<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*(?:</?p>)", re.S)
pListExpWrap = re.compile("(<p>)?[A-ZÅÄÖ][^<>]*?kunna:?\s*(</\s*p>)?(<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*</?p>)+", re.S)
pListExpWrapEn = re.compile("(<p>)?[A-ZÅÄÖ][^<>]*?((know\s*how)|(able))\s*to:?\s*(</\s*p>)?(<p>\s*[-o•*·–]\s*[0-9]*\s*[.]?\s*(.*?)\s*</?p>)+", re.S)


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
dotListExp = re.compile("[•*·–…;]\s*[0-9]*[.]?\s*(([^•*·…;\n\s\\–]|( [^•*·…;\n\\–\s])){4,})", re.S)
dotListExpWrap = re.compile("[•*·–…;]\s*[0-9]*[.]?\s*([^•*·…;\n\s\\–]|( [^•*·…;\n\\–])){4,}(\s*.*?[•*·–…;]\s*[0-9]*[.]?\s*([^•*·…;\n\s\\–]|( [^•*·…;\n\\–\s])){4,})+", re.S)

### Studenten skall efter avslutad kurs behärska en grundläggande
### orientering i ämnesområdet teater i Sverige och kunna visa en
### förmåga att o diskutera olika aspekter av historiografi med
### avseende på teater i Sverige o analysera och diskutera olika
### aspekter av svensk kultur- och teaterpolitik.
dotListOExp = re.compile(" o ((([^ o])|( [^o])|( o[^ ])){4,}[^ o])", re.S)
dotListOExpWrap = re.compile("(Delkurs\s[0-9]+)?( o ((([^ o])|( [^o])|( o[^ ])){4,}))+", re.S)

### Courses can use X as markers for goals
###   "Efter genomgången kurs ska deltagarna kunna XReflektera kring och diskutera ämnet hållbar utveckling och koppla begreppen till det egna ämne
###    sområdet XPresentera hållbar utveckling som ett ämne som kräver kritisk reflektion och diskussion utifrån olika perspektiv och visa hur detta bör komma f
###    ram i utbildningen för studenter XDesigna kursmål ..."
###   (example course KTH LH215V)
XxListExp = re.compile("[^a-zåäöA-ZÅÄÖ][Xx]\s*(([^X\n\s]|( [^X\n\s])){4,}[^X\n\s])", re.S)
XxListExpWrap = re.compile("[^a-zåäöA-ZÅÄÖ][Xx]\s*([^X\n\s]|( [^X\n\s])){4,}(\s*.*?[^a-zåäöA-ZÅÄÖ][Xx]\s*([^X\n\s]|( [^X\n\s])){4,})+", re.S)

###    (example course UMU 2PS273)
oListExp = re.compile("[.\s][oO]\s(.*?)\\.")
oListExpWrap = re.compile("([.\s][oO]\s.*){3,}")

### Some courses list goals on one long line with " - " as a marker for each goal
###   "ska studenten kunna 1. Kunskap och förståelse - Redogöra
###   för teorier om demokratisering och autokratisering på ett
###   samhällsvetenskapligt sätt, både muntligt och skriftligt
###   (kunskap) - Förstå och med egna ord förklara teorier ..."
###   (example course SU SV7098)
inlineHyphenListExp = re.compile(" - +(([^ ]|( [^- ]))+)", re.S)
inlineHyphenListExpWrap = re.compile("( - +([^ ]|( [^- ])){4,})((\s{2,}[^-]*)?( - +([^ ]|( [^- ])){4,}))*", re.S)
inlineHyphenIndicator = re.compile(" - ")

### Some courses enumerate goals with Roman numerals
###   "För godkänt resultat skall studenten kunna:
###     I.     kritiskt granska statistiska undersökningar utifrån ett vetenskapligt perspektiv,
###     II.    formulera statistiska modeller för elementära problem inom olika tillämpningsområden,
###     ... "
###   (example course SU ST111G)
romanListExp = re.compile("[IVX]+\s*[.]\s+([^IVX]*)", re.S)
romanListExpWrap = re.compile("([A-ZÅÄÖ].*?kunna:?\s*)(\s*I\s*[.]\s+([^IVX ]|( [^IVX ]))+)(\s*[IVX]+\s*[.]\s+([^IVX ]|( [^IVX ]))+)*", re.S)

romanListIndicator = re.compile("kunna:?\s*I")
romanListIndicatorEn = re.compile("((know\s*how)|(able))\s*to:?\s*I")

### Some courses enumerate goals with Arabic numerals
###    "För godkänt resultat på kursen ska studenten kunna:
###     <i>Kunskap och förståelse</i>
###     1. Redogöra för relevanta begrepp för att beskriva omfattningen av sjukdomar i den allmänna befolkningen
###     2. Beskriva våra vanligaste folkhälsoproblem och folksjukdomar och redogöra för förekomst och sjukdomsorsaker
###     ... "
###   (example course SU PH03G0)
arabicListExp = re.compile("\\(?\s*[0-9]+\s*[).]\s*([^0-9 ](([^0-9 ]|([0-9][^).])|( [^0-9 ])){4,}))", re.S)
arabicListExpWrap = re.compile("\\(?\s*[0-9]+\s*[).]\s*([^0-9 ]|([0-9][^).])|( [^0-9 ])){4,}(\s*\\(?\s*[0-9]+\s*[).]\s*([^0-9 ]|([0-9][^).])|( [^0-9 ])){4,})*", re.S)
delkursExp = re.compile("Delkurs([^\\-•*·–…;]*?)hp")
delkursExp2 = re.compile("Delkurs\s[0-9]+[.]?,?(\s*[^A-ZÅÄÖ\\-,•*·–…;\n]*)")


### Some courses enumerate goals with (a), (b), or (1), (2), etc. 
###    "Kursen syftar till (a) att öka deltagarnas förståelse ... ; (b) att ge de färdigheter som behövs för tillämpad dataanalys ... ; och (c) att ge träning i ... "
###   (example course SU PSMT15)
parListExp = re.compile("\n\s*\\([0-9a-zA-Z]\\)\s*([^\n]*)") # not very common
parListExpWrap = parListExp

parListExp2 = re.compile("[\s\.][0-9a-hA-H]{1,2}\\)\s*((([^\s\\)<>])|(\s[^a-zA-Z0-9\s<>])|(\s[a-zA-Z0-9][^\\)])){4,}([^\\)\s</>\.0-9]){2})", re.S) # mainly this pattern is used
parListExpWrap2 = parListExp2

### Some courses specify goals with lines like "ska ... kunna ..."
###   "Den studerande skall efter genomgången kurs kunna
###   identifiera samt, såväl muntligt som skriftligt, redogöra
###   för hur förhållandet mellan människa och natur avspeglas och
###   gestaltas i de senaste hundra årens svenska barnlitteratur.
###   Detta inbegriper förtrogenhet med den barnlitterära
###   konventionen och en förmåga att relatera iakttagelserna till
###   en vidare samhällelig och kulturell kontext."
###  (example course SU LV1011)
skaKunnaExp = re.compile("[Kk]unna(\s*[^0-9\s]((([^\s])|([^\n][^\s])){4,}))")
skaKunnaExpEn = re.compile("[Aa]ble\s*to(.{4,}?)[\n]")

### Some courses write goals as "Efter kursen kan ... " (less common than "ska kunna")
###   "Studenten kan tillämpa grundläggande arbetsmarknadsekonomiska begrepp ..."
###   (example course SU ATF012)
kanExp = re.compile("\skan\s(([a-zåäö]*[^s]\s[^.]+)[\.]|(\s\s)|\n)", re.I)
kanExpEn = re.compile("\s(((know\s*how)|(able))\s*to\s(([^.]+\s[^.]+)[\.]|(\s\s)|\n))", re.I)

### Goals can be written as "studenten ska vara förtrogen med" or
### "studenten ska ha förmåga att"
###   "Efter genomgången kurs ska studenten
###    1)      vara förtrogen med begreppen kultur, mångkulturalism och andra för kunskapsområdet centrala begrepp som exkluderings- och inkluderingprocesser präglar relationer mellan majoritets- och minoritetsbefolkningen samt aktuella teorier kring mångkulturalism och etnicitet
###    2)      ha förmåga att integrera relevanta teorier och metoder om mångkulturalism i en vägledningssituation samt kunna reflektera över hur kulturella normer, värderingar och tankemönster påverkar förhållningssätt till människor i andra etniska grupper
###   (example course SU UC119F)
fortrogenExp = re.compile("\sförtrogen\s*med\s(([^.]{4,}?)(\.|\s\s))", re.I)
formagaExp = re.compile("\sförmåga.*?att\s*(([^.]{4,}?)(\.|\s\s))", re.I)

fortrogenExpEn = re.compile("\scomfortable\s*with\s(([^.]{4,}?)(\.|\s\s))", re.I)
formagaExpEn = re.compile("\sability.*?to\s*(([^.]{4,}?)(\.|\s\s))", re.I)

### Some courses list all goals on one line with arabic numerals enumerating, starting with "... kunna 1."
###   "... ska studenten kunna 1.Redovisa, diskutera och jämföra olika
###   historiskt kriminologiska studier. 2.Beskriva, ..."
###   (example course SU AKA132)
kunna1exp = re.compile("[0-9]+[. ]?\s*([^0-9]{4,})")
kunna1expWrap = re.compile("kunna.*(1.*?[^0-9]{4,}2.*?[^0-9]{4,}([0-9].*?[^0-9]{4,})*)")
kunna1expWrapEn = re.compile("((know\s*how)|(able))\s*to.*(1.*?[^0-9]{4,}2.*?[^0-9]{4,}([0-9].*?[^0-9]{4,})*)")

kunna1sub = re.compile("(,?\s*Efter avslutad kurs ska studenten)*\s*för betyget (.*?) kunna")

### Courses can have lists where each item starts with a Capital
### letter but not other wise noted:
###    "Efter avslutad kurs ska studenten kunna Visa goda kunskaper
###    ... konsekvenser. Analysera och tolka händelser ... "
###   (example course KTH MJ2416)
kunnaCapExp = re.compile("[\s>]([A-ZÅÄÖ](([^\s<\n])|([^<\n][^\s<\n])){4,})", re.S)
kunnaCapExpWrap = re.compile("kunna:?\s*[A-ZÅÄÖ][^\n]*", re.S)
kunnaCapExpWrapEn = re.compile("((know\s*how)|(able))\s*to:?\s*[A-ZÅÄÖ].*", re.S)

kunnaHypExp = re.compile(" -([a-zåäöA-ZÅÄÖ][^\-<]*[^\-<\s])", re.S)
kunnaHypExpWrap = re.compile("[A-ZÅÄÖ][^A-ZÅÄÖ]*?((\sska)|(kunna))[^-]*:?(\s+-[a-zåäöA-ZÅÄÖ][^\-<]*[^\-<\s])+", re.S)
kunnaHypExpWrapEn = re.compile("[A-Z][^A-Z]*?((know\s*how)|(able))\s*to:?\s*(\s+ -[a-zA-Z][^\-<]*[^\-<\s])+", re.S)

kunnaHypExpWrap2 = re.compile("([^a-zåäöA-ZÅÄÖ]-[a-zåäöA-ZÅÄÖ][^\-<]*[^\-<\s])+", re.S)

# Courses can have lists using HTML <p>-tags for list items but not be
# captured by the more precise pattern above. For example the course
# KTH IE1205 which has "<p>- "

pHypListExp = re.compile("<p>-\s(.*?)\s*(?:</?p>)", re.S)
pHypListExpWrap = re.compile("(<p>)?[^<>]*((ska)|(kunna))[^<>]*(</\s*p>)?(<p>-\s[^<>]*</?p>)([^<>]*<p>-\s[^<>]*</?p>)+", re.S)
pHypListExpWrapEn = re.compile("(<p>)?[^<>]*((can)|(know\s*how\s*to)|(able\s*to))[^<>]*(</\s*p>)?(<p>-\s[^<>]*</?p>)([^<>]*<p>-\s[^<>]*</?p>)+", re.S)

pHypListIndicator = re.compile("<p>-")
# Courses KTH CM2006 CM1004 has "<p>" but no dot or hyphen at all
pRawListExp = re.compile("<p>(.*?)(?:</?p>)", re.S)
pRawListExpWrap = re.compile("(<p>)?[^<>]*((ska)|(kunna))\s*:?\s*(</\s*p>)?(<p>[^<>]*</?p>)([^<>]*<p>[^<>]*</?p>)+", re.S)
pRawListExpWrapEn = re.compile("(<p>)?[^<>]*((can)|(know\s*how\s*to)|(able\s*to))\s*:?\s*(</\s*p>)?(<p>[^<>]*</?p>)([^<>]*<p>[^<>]*</?p>)+", re.S)

pRawListIndicator = re.compile("((ska)|(kunna))\s*:?\s*</\s*p>")
pRawListIndicatorEn = re.compile("((can)|(know\s*how\s*to)|(able\s*to))\s*:?\s*</\s*p>")

# # Courses KTH FAG3184 FAG3185 have a set of <p>...</p> that are one
# # goal each, and nothing else.
# onlyPListExp = re.compile("<p>(.*?)(?:</?p>)", re.S)

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


godkandExp = re.compile("[Ff]ör\s*(betyg(e[nt])?)?\s*((G)|([Gg]odkänd))")
vgExp = re.compile("(((Förväntat)|(Efter))[^A-ZÅÄÖ<>]+)?[Ff]ör\s*(betyg(e[tn])?)?\s*((VG)|([Vv]äl\s*[Gg]odkänd)|([Hh]ögre\s*[Bb]etyg))")
vgExp2 = re.compile("(((Förväntat)|(Efter)|(<p>))[^A-ZÅÄÖ<>]+)[Ff]ör\s*(betyg(e[tn])?)?\s*((VG)|([Vv]äl\s*[Gg]odkänd)|([Hh]ögre\s*[Bb]etyg))")


###############################################
### Expressions for common writing mistakes ###
###############################################
ochExp = re.compile("\soch([a-zåäö]+)")
attExp = re.compile("\satt([b-df-hj-npqs-zåäö]+)")

htmlTrash = re.compile("(<[^>]*[-][^>]*>)|(</?w[^>]*>)|(<![^>]*>)|(</?m[^>]*>)|(X-NONE)")
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
    sv = sv.replace(u"\u00A0", " ").replace(u"\u00AD", "")
    en = en.replace(u"\u00A0", " ").replace(u"\u00AD", "")

    sv = sv.replace("\n -", "\n–").replace("\n-", "\n–").replace("\n−", "\n–").replace(u"\uF095", "–")
    sv = re.sub("([0-9]{4})–([0-9]{4})", "\\1-\\2", sv)
    sv = sv.replace(" — ", " - ")
    sv = sv.replace("\t", " ")

    sv = parHeadingsExp.sub(" ", sv) # remove things like "(Lärandemål 3 och 4)" or "(Modul 5, 6, och 7)"
    sv = parHeadingsExp2.sub(" modul", sv)

    sv = delkursExp.sub("", sv)
    sv = delkursExp2.sub("", sv)


    sv = delparExp.sub("", sv)
    sv = ccparExp.sub("", sv)
    sv = betygparExp.sub("", sv)
    sv = momentExp.sub("", sv)
    
    
    en = gradeparExp.sub("", en)

    ##############################
    ### Fix some weird codings ###
    ##############################
    sv = sv.replace("å", "å").replace("ä", "ä").replace("ö", "ö").replace(":", " ").replace(u'\uf02d', "•")
    sv = sv.replace("&eacute;", "é")
    sv = sv.strip()
    while len(sv) and sv[0] == '"':
        sv = sv[1:]
    while len(sv) and sv[-1] == '"':
        sv = sv[:-1]
    
    iloList = []
    iloListEn = []

    
    #############################
    ### Remove some HTML tags ###
    #############################
    sv = htmlTrash.sub(" ", sv)
    en = htmlTrash.sub(" ", en)
    
    
    ########################################
    ### Fix some common writing mistakes ###
    ########################################

    sv = ochExp.sub(" och \\1", sv)
    sv = attExp.sub(" och \\1", sv)
    
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
    if SKIP_VG:
        skip = 0
        m = godkandExp.search(sv)
        if m:
            m2 = vgExp.search(sv)
            if m2 and m2.start() > m.start():
                skip = 1
                sv = sv[:m2.start()]
        else:
            m2 = vgExp2.search(sv)
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

    if brListIndicator.search(sv) or brListIndicator.search(en):
        sv, en = matchAndConsume(brListExpWrap, brListExp, sv, brListExpWrapEn, brListExp, en, "br-list", iloList, iloListEn)
        sv, en = matchAndConsume(brListExpWrap2, brListExp, sv, brListExpWrap2, brListExp, en, "br-list-2", iloList, iloListEn)

    sv, en = matchAndConsume(newlineListExpWrap, newlineListExp, sv, newlineListExpWrap, newlineListExp, en, "newline-list", iloList, iloListEn)
    
    sv, en = matchAndConsume(dotListExpWrap, dotListExp, sv, dotListExpWrap, dotListExp, en, "dot-list", iloList, iloListEn)
    sv, en = matchAndConsume(dotListOExpWrap, dotListOExp, sv, dotListOExpWrap, dotListOExp, en, "dot-list-O", iloList, iloListEn)

    sv, en = matchAndConsume(XxListExpWrap, XxListExp, sv, XxListExpWrap, XxListExp, en, "Xx-list", iloList, iloListEn)
    
    tmp = sv.replace(".o", ". o").replace("Färdighet och förmåga", " ").replace("Kunskap och förståelse", " ").replace("Värderingsförmåga och förhållningssätt", " ")
    sv, en = matchAndConsume(oListExpWrap, oListExp, tmp, oListExpWrap, oListExp, en, "o-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuHaLinesWrap, umuHaLines, sv, umuHaLinesWrapEn, umuHaLines, en, "umu-ha-lines", iloList, iloListEn)
    
    sv, tmp = matchAndConsumeSpecial(umuEfterHypWrapSpec2, umuEfterHyp, sv, umuEfterHyp, umuEfterHyp, "", "efter-hyphen-Spec-list", iloList, iloListEn)
    
    if umuEfterHypIndicator.search(sv) and not umuEfterHypNegativeIndicator.search(sv):
        sv, en = matchAndConsumeSpecial(umuEfterHypWrapSpec, umuEfterHyp, sv, umuEfterHyp, umuEfterHyp, en, "efter-hyphen-Spec-list", iloList, iloListEn)
        sv, en = matchAndConsume(umuEfterHypWrap, umuEfterHyp, sv, umuEfterHyp, umuEfterHyp, en, "efter-hyphen-list", iloList, iloListEn)

    sv, en = matchAndConsume(vetaHurExp, vetaHurExp, sv, vetaHurExp, vetaHurExp, en, "veta-hur-list", iloList, iloListEn)
    
    sv, tmp = matchAndConsume(formuleraExp, formuleraExp, sv, formuleraExp, formuleraExp, "", "formulera-list", iloList, iloListEn)
    
    if inlineHyphenIndicator.search(sv) or inlineHyphenIndicator.search(en):
        sv, en = matchAndConsume(inlineHyphenListExpWrap, inlineHyphenListExp, sv, inlineHyphenListExpWrap, inlineHyphenListExp, en, "inline-hyphen-list", iloList, iloListEn)
    
    if romanListIndicator.search(sv) or romanListIndicatorEn.search(en): # This expression is slow to match, so only try if a faster expression matches
        sv, en = matchAndConsume(romanListExpWrap, romanListExp, sv, romanListExpWrap, romanListExp, en, "roman-list", iloList, iloListEn)

    sv, en = matchAndConsume(arabicListExpWrap, arabicListExp, sv, arabicListExpWrap, arabicListExp, en, "arabic-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuSkaHaExpWrap2, umuSkaHaExp2, sv, umuSkaHaExp, umuSkaHaExp, en, "umu-ska-ha-list-2", iloList, iloListEn)
    sv, en = matchAndConsume(umuSkaHaExpWrap, umuSkaHaExp, sv, umuSkaHaExp, umuSkaHaExp, en, "umu-ska-ha-list", iloList, iloListEn)
                             
    sv, en = matchAndConsume(parListExpWrap, parListExp, sv, parListExpWrap, parListExp, en, "par-list", iloList, iloListEn)
    sv, en = matchAndConsume(parListExpWrap2, parListExp2, sv, parListExpWrap2, parListExp2, en, "par-list-2", iloList, iloListEn)
    
    sv, en = matchAndConsume(umuAvseendeExpWrap, umuAvseendeExp, sv, umuAvseendeExp, umuAvseendeExp, en, "avseende-list", iloList, iloListEn)

    sv, en = matchAndConsume(umuSamtligaMomentExpWrap, umuSamtligaMomentExp, sv, umuSamtligaMomentExp, umuSamtligaMomentExp, en, "Samtliga-moment-list", iloList, iloListEn)

    sv, tmp = matchAndConsume(forGodkandExpWrap, forGodkandExp, sv, forGodkandExpWrap, forGodkandExp, "", "for-godkand-list", iloList, iloListEn)
    sv, tmp = matchAndConsume(forGodkandExpWrap2, forGodkandExpWrap2, sv, forGodkandExpWrap, forGodkandExp, "", "for-godkand-list", iloList, iloListEn)

    sv, en = matchAndConsume(efterKunnaExpWrap, efterKunnaExp, sv, efterKunnaExpWrap, efterKunnaExp, en, "efter-kunna-list", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaNewlineExpWrap, kunnaNewlineExp, sv, kunnaNewlineExpWrapEn, kunnaNewlineExp, en, "kunna-newline-list", iloList, iloListEn)

    if kunnaNewlineExpWrap2Indicator.search(sv):
        sv, en = matchAndConsume(kunnaNewlineExpWrap2, kunnaNewlineExp, sv, kunnaNewlineExpWrapEn, kunnaNewlineExp, en, "kunna-newline-list-2", iloList, iloListEn)

    sv, en = matchAndConsume(kunnaCapExpWrap, kunnaCapExp, sv, kunnaCapExpWrapEn, kunnaCapExp, en, "kunna-Cap-exp", iloList, iloListEn)

    sv, tmp = matchAndConsume(umuNewlinesExpWrap4, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, "", "umu-newlines-4", iloList, iloListEn) 
    sv, tmp = matchAndConsume(umuNewlinesExpWrap5, umuNewlinesExp, sv, umuNewlinesExp, umuNewlinesExp, "", "umu-newlines-5", iloList, iloListEn) 
        
    sv, en = matchAndConsume(kunnaAexpWrap, kunnaAexp, sv, kunnaAexpWrapEn, kunnaAexp, en, "kunna-a-exp", iloList, iloListEn)
    
    sv, en = matchAndConsume(skaKunnaExp, skaKunnaExp, sv, skaKunnaExpEn, skaKunnaExpEn, en, "ska-kunna-list", iloList, iloListEn)

    sv, en = matchAndConsume(kunna1expWrap, kunna1exp, sv, kunna1expWrapEn, kunna1exp, en, "kunna-1-exp", iloList, iloListEn)

    for i in range(len(iloList)): # this captures too much in common UMU patterns, so we add a small correction here
        iloList[i] = kunna1sub.sub(" ", iloList[i])

    sv, en = matchAndConsume(kunnaHypExpWrap, kunnaHypExp, sv, kunnaHypExpWrapEn, kunnaHypExp, en, "kunna-hyp-exp", iloList, iloListEn)
    sv, en = matchAndConsume(kunnaHypExpWrap2, kunnaHypExp, sv, kunnaHypExpWrap2, kunnaHypExp, en, "kunna-hyp-exp-2", iloList, iloListEn)

    if pHypListIndicator.search(sv) or pHypListIndicator.search(en): # faster check before slow matching
        sv, en = matchAndConsume(pHypListExpWrap, pHypListExp, sv, pHypListExpWrapEn, pHypListExp, en, "p-hyp-list", iloList, iloListEn)

    if len(iloList) <= 0 and pRawListIndicator.search(sv):
        sv, tmp = matchAndConsume(pRawListExpWrap, pRawListExp, sv, pRawListExpWrapEn, pRawListExp, "", "p-raw-list", iloList, iloListEn)
    if len(iloListEn) <= 0 and pRawListIndicatorEn.search(en): # faster check before slow matching
        tmp, en = matchAndConsume(pRawListExpWrap, pRawListExp, "", pRawListExpWrapEn, pRawListExp, en, "p-raw-list", iloList, iloListEn)
        
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kunnaSentenceExp, kunnaSentenceExp, sv, kunnaSentenceExpEn, kunnaSentenceExpEn, en, "kunna-sentence-exp", iloList, iloListEn)
    
    sv, en = matchAndConsume(formagaExp, formagaExp, sv, formagaExpEn, formagaExpEn, en, "formaga-exp", iloList, iloListEn)
    
    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(fortrogenExp, fortrogenExp, sv, fortrogenExpEn, fortrogenExpEn, en, "fortrogen-exp", iloList, iloListEn)

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

    if len(iloList) <= 0: # This tends to overgenerate, so avoid if we have something else already
        sv, en = matchAndConsume(kanExp, kanExp, sv, kanExpEn, kanExpEn, en, "kan-exp", iloList, iloListEn) 

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
   
    return (iloList, iloListEn)

times = {}
def matchAndConsume(allExp, goalExp, sv, allExpEn, goalExpEn, en, name, lsS, lsE):
    iloListSv = []
    iloListEn = []
    iloList = []

    startime = timer()
    m = allExp.search(sv)
    
    while m:
        log("\nFOUND", name)
        log("\n" + str(m.start()) + " " + str(m.end()), "'" + sv[m.start():m.end()] + "'\n")
        found = 0
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
    return (sv, en)

def matchAndConsumeSpecial(allExp, goalExp, sv, allExpEn, goalExpEn, en, name, lsS, lsE):
    iloListSv = []
    iloListEn = []
    iloList = []
    
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
        if s[0] == "-":
            s = s[1:].strip()
        if s[0].isupper():
            pass
        elif s[0].islower():
            if s[:5] == "kunna":
                s = "Hon ska " + s
            elif s[:3] == "ha ":
                s = "Hon ska " + s
            else:
                s = "Hon ska kunna " + s
        if s[-3:] == "och":
            s = s[:-3].strip()

        p = s.find("För att bli godkänd")
        if p > 10:
            s = s[:p]
        if s[-5:] == "kunna":
            continue # most likely a faulty match, skip
        if s[-5:] == "skall":
            continue # most likely a faulty match, skip
        if not s[-1] in string.punctuation:
            s += " ."
        res.append(s)
    return res

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
