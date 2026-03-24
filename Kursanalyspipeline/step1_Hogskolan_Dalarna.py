import sys
import re
import datetime
import json

###################################
#### Default time set to "now" ####
###################################

defaultSemester = ""
today = datetime.date.today()
defaultSemester = str(today.year)
if today.month < 7:
    defaultSemester += ":1"
else:
    defaultSemester += ":2"
timeSpan = defaultSemester

outputFile = ""
timeSpanExp = re.compile("[0-9][0-9][0-9][0-9]:[0-9]")

####################################
#### Get command line arguments ####
####################################
CCs = {}
haveCC = 0
haveCCall = 0
haveTime = 0
haveOut = 0
haveFullYear = 0
for i in range(1, len(sys.argv)):
    if (sys.argv[i] == "-a"):
        haveCCall = 1
    elif (sys.argv[i] == "-cc" and i + 1 < len(sys.argv)):
        haveCC = 1
        CCs[sys.argv[i+1]] = 1
    elif (sys.argv[i] == "-ccs" and i + 1 < len(sys.argv)):
        haveCC = 1
        courseCodes = sys.argv[i+1].split()
        for c in courseCodes:
            CCs[c] = 1
    elif (sys.argv[i] == "-ct" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 0
        timeSpan = sys.argv[i+1]
    elif (sys.argv[i] == "-cy" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 1
        timeSpan = sys.argv[i+1]
    elif (sys.argv[i] == "-o" and i + 1 < len(sys.argv)):
        haveOut = 1
        outputFile = sys.argv[i+1]

if (not haveCC and not haveCCall) or (haveCC and haveCCall):
    print ("\nParse Excel (CSV) file and output course information as JSON\n")
    print ("usage options: <INPUT_FILE_NAME> [-cc <CODE>] [-ct <SEMESTER>]")
    print ("Flags: -a                              Classify all courses.");
    print ("       -cc <CODE>                      Course code (six alphanumeric characters).");
    print ("       -ccs \"<CODE1> <CODE2> ....\"   Course code (six alphanumeric characters).");
    print ("       -ct <SEMESTER>                  Course semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester);
    print ("       -cy <SEMESTER>                  Course year/semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester);
    print ("       -o <FILE_NAME>  Output file name (default is \"" + sys.argv[0] + ".output\").");
    print ("\nNote: One of -a OR -cc OR -ccs must be used.\n");
    sys.exit(0)


###############
### Logging ###
###############
logging = True

if logging:
    logF = open(sys.argv[0] + ".log", "w")

def log(s):
    if not logging:
        return
    logF.write(str(s))
    logF.write("\n")

def logFlush():
    if not logging:
        return
    logF.flush()




############################################
#### Get the information for one course ####
############################################
ccExpSv = re.compile("<dt>Kurskod</dt>\s*<dd>(.*?)</dd>", re.I + re.S)
hpExpSv = re.compile("<dt>Po&#228;ng</dt>\s*<dd>([0-9,.]+)[^<]*</dd>", re.I + re.S)

lvExpSv = re.compile("<dt>Niv&#229;</dt>\s*<dd[^>]*>(.*?)</dd>", re.I + re.S)
lvExpSv2 = re.compile("<dt>Niv&#229;</dt>\s*<dd.*?>(.*?((givande)|(reparand)|(C)).*?)</dd>", re.I + re.S)

scbExpSv = re.compile("<dt>&#196;mnestillh&#246;righet</dt>\s*<dd.*?>(.*?)<[^<]*?/dd>", re.I + re.S)

courselevelExpSv = re.compile("<dt>F&#246;rdjupningsbeteckning.*</dt>\s*<dd>.*([GA][0-9][EFNX]).*</dd>", re.I + re.S)
starDateExpSv = re.compile("<dt>Fastst&#228;lld</dt>\s*<dd>.*Kursplanen g.*ller fr.o.m. ([0-9]{4}-[0-9]{2}-[0-9]{2}).*</dd>", re.I + re.S)
starDateExpSv2 = re.compile("<dt>Reviderad</dt>\s*<dd>.*fr.o.m. ([0-9]{4}-[0-9]{2}-[0-9]{2}).*</dd>", re.I + re.S)

ccExpEn = re.compile("<dt>Code</dt>\s*<dd>(.*?)</dd>", re.I + re.S)
hpExpEn = re.compile("<dt>Points</dt>\s*<dd>([0-9,.]+)[^<]*</dd>", re.I + re.S)

lvExpEn = re.compile("<dt>Level</dt>\s*<dd.*>([^<>]*level[^<>]*?)<.*/dd>", re.I + re.S)
lvExpEn2 = re.compile("<dt>Level</dt>\s*<dd.*?>(.*?access.*?)</dd>", re.I + re.S)

scbExpEn = re.compile("<dt>Subject field</dt>\s*<dd.*?>(.*?)<[^<]*?/dd>", re.I + re.S)

courselevelExpEn = re.compile("<dt>Progression indicator.*</dt>\s*<dd>.*([GA][0-9][EFNX]).*</dd>", re.I + re.S)
starDateExpEn = re.compile("<dt>Approved</dt>\s*<dd>.*Approved.*from ([0-9]{2} [a-zA-Z]+ [0-9]{4}).*</dd>", re.I + re.S)
starDateExpEn2 = re.compile("<dt>Revised</dt>\s*<dd>.*from ([0-9]{2} [a-zA-Z]+ [0-9]{4}).*</dd>", re.I + re.S)

iloExpSv = re.compile("<h2>((M&#229;l)|(L&#228;randem&#229;l))</h2>\s*(.*?)((<h2>)|(</article>))", re.I + re.S)
iloExpSv2 = re.compile("<h2>((M&#229;l)|(L&#228;randem&#229;l))</h2>\s*(.*?)<h.>Delkurser</h.>(.*?)<h.>Examinationsform", re.I + re.S)
prereqExpSv = re.compile("<h2>F&#246;rkunskapskrav</h2>(.*?)((<h2>)|(</article>))", re.I + re.S)
prereqExpSv2 = re.compile("<h2>Beh&#246;righet</h2>(.*?)((<h2>)|(</article>))", re.I + re.S)

iloExpEn = re.compile("<h2>Learning Outcomes</h2>\s*(.*?)((<h2>)|(</article>))", re.I + re.S)
iloExpEn2 = re.compile("<h2>Summary in English</h2>\s*(.*?((able to)|(shall know)|(goals for this course are)).*?)((<h2>)|(</article>))", re.I + re.S)
prereqExpEn = re.compile("<h2>Prerequisites</h2>(.*?)((<h2>)|(</article>))", re.I + re.S)
prereqExpEn2 = re.compile("<h2>Entry Requirements</h2>(.*?)((<h2>)|(</article>))", re.I + re.S)


htmlChar = re.compile("&.{1,10};")
def fixSwedishHTMLChars(txt):
    res = txt.replace("&Aring;", "å").replace("&Auml;", "ä").replace("&Ouml;", "ö").replace("&aring;", "å").replace("&auml;", "ä").replace("&ouml;", "ö").replace("&nbsp;", " ").replace("&#160;", " ").replace("&#229;", "å").replace("&ndash;", "-").replace("&rsquo;", "'").replace("&lsquo;", "'").replace("&rdquo;", "\"").replace("&ldquo;", "\"").replace("&amp;", "&").replace("&bull;", "•").replace("&acute;", "'").replace("&middot;", "·").replace("&#x1E;", " ").replace("&agrave;", "à").replace("&eacute;", "é").replace("&egrave;", "è").replace("&quot;", "\"").replace("&#214;", "Ö").replace("&#197;", "Å").replace("&#196;", "Ä")

    m = htmlChar.search(res)
    if m:
        log("HTMLCHAR in goal: " + m[0])
    
    return res

def extractInfoFromWebpage(rawtxt):
    res = {}

    txt = cleanHTML(rawtxt)

    # log("Extract fields from: " + txt)
    
    m = ccExpSv.search(txt) 
    if m:
        # log("ccExpSv matches: " + m[1])
        res["CourseCode"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("ccExpSv NO MATCH")

    m = hpExpSv.search(txt) 
    if m:
        # log("hpExpSv matches: " + m[1])
        res["ECTS-credits"] = cleanHTML(m[1])
    else:
        pass
        # log("hpExpSv NO MATCH")
    
    m = courselevelExpSv.search(txt) 
    if m:
        # log("courselevelExpSv matches: " + m[1])
        res["CourseLevel-ID"] = cleanHTML(m[1])
    else:
        # log("courselevelExpSv NO MATCH")
        pass

    m = starDateExpSv.search(txt)
    if m:
        # log("starDateExpSv matches: " + m[1])
        res["ValidFrom"] = fixDateFormat(m[1])
    else:
        pass
        # log("starDateExpSv NO MATCH")

    m = starDateExpSv2.search(txt)
    if m:
        # log("starDateExpSv2 matches: " + m[1])
        res["ValidFrom"] = fixDateFormat(m[1])
    else:
        pass
        # log("starDateExpSv2 NO MATCH")

    m = iloExpSv.search(txt) 
    if m:
        log("iloExpSv matches: " + m[4])
        res["ILO-sv"] = cleanHTML(fixSwedishHTMLChars(m[4]))
    else:
        pass
        # log("iloExpSv NO MATCH")

    m = iloExpSv2.search(txt) 
    if m:
        log("iloExpSv2 matches: " + m[4] + "\n" + m[5])
        res["ILO-sv"] = cleanHTML(fixSwedishHTMLChars(m[4] + "\n" + m[5]))

    m = prereqExpSv.search(txt) 
    if m:
        # log("prereqExpSv matches: " + m[1])
        res["Prerequisites-sv"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("prereqExpSv NO MATCH")

    m = prereqExpSv2.search(txt) 
    if m:
        # log("prereqExpSv2 matches: " + m[1])
        res["Prerequisites-sv"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("prereqExpSv2 NO MATCH")

    m = scbExpSv.search(txt) 
    if m:
        # log("scbExpSv matches: " + m[1])
        res["SCB-ID"] = cleanHTML(m[1])
        res["SCB-ID"] = spaceExp.sub(" ", res["SCB-ID"])
        if res["SCB-ID"] in scbMappings:
            res["SCB-ID"] = scbMappings[res["SCB-ID"]]
        else:
            if "CourseCode" in res:
                cc = res["CourseCode"]
            else:
                cc = ""
            log("Unknown SCB-ID? " + res["SCB-ID"] + " course " + cc)
    else:
        pass
        # log("scbExpSv NO MATCH")

    m = ccExpEn.search(txt) 
    if m:
        # log("ccExpEn matches: " + m[1])
        res["CourseCode"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("ccExpEn NO MATCH")
        
    m = hpExpEn.search(txt) 
    if m:
        # log("hpExpEn matches: " + m[1])
        res["ECTS-credits"] = cleanHTML(m[1].replace(".", ","))
    else:
        pass
        # log("hpExpEn NO MATCH")
    
    m = courselevelExpEn.search(txt) 
    if m:
        # log("courselevelExpEn matches: " + m[1])
        res["CourseLevel-ID"] = cleanHTML(m[1])
    else:
        # log("courselevelExpEn NO MATCH")
        pass

    m = starDateExpEn.search(txt)
    if m:
        # log("starDateExpEn matches: " + m[1])
        res["ValidFrom"] = fixDateFormat(m[1])
    else:
        pass
        # log("starDateExpEn NO MATCH")

    m = starDateExpEn2.search(txt)
    if m:
        # log("starDateExpEn2 matches: " + m[1])
        res["ValidFrom"] = fixDateFormat(m[1])
    else:
        pass
        # log("starDateExpEn2 NO MATCH")

    m = iloExpEn.search(txt) 
    if m:
        # log("iloExpEn matches: " + m[1])
        res["ILO-en"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        m = iloExpEn2.search(txt) 
        if m:
            # log("iloExpEn2 matches: " + m[1])
            res["ILO-en"] = cleanHTML(fixSwedishHTMLChars(m[1]))
        else:
            pass
            # log("iloExpEn NO MATCH")

    m = prereqExpEn.search(txt) 
    if m:
        # log("prereqExpEn matches: " + m[1])
        res["Prerequisites-en"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("prereqExpEn NO MATCH")

    m = prereqExpEn2.search(txt) 
    if m:
        # log("prereqExpEn2 matches: " + m[1])
        res["Prerequisites-en"] = cleanHTML(fixSwedishHTMLChars(m[1]))
    else:
        pass
        # log("prereqExpEn2 NO MATCH")

    m = scbExpEn.search(txt) 
    if m:
        # log("scbExpEn matches: " + m[1])
        res["SCB-ID"] = cleanHTML(m[1])
    else:
        pass
        # log("scbExpEn NO MATCH")

    if not "CourseLevel-ID" in res or res["CourseLevel-ID"] == "":
        m = lvExpSv.search(txt) 
        if m:
            # log("lvExpSv matches: " + m[1])
            res["CourseLevel-ID"] = m[1]
        else:
            # log("lvExpSv NO MATCH")

            m = lvExpSv.search(txt) 
            if m:
                # log("lvExpSv2 matches: " + m[1])
                res["CourseLevel-ID"] = m[1]
            else:
                # log("lvExpSv2 NO MATCH")
                pass

        m = lvExpEn.search(txt) 
        if m:
            # log("lvExpEn matches: " + m[1])
            res["CourseLevel-ID"] = m[1]
        else:
            pass
            # log("lvExpEn NO MATCH")

            m = lvExpEn2.search(txt) 
            if m:
                # log("lvExpEn2 matches: " + m[1])
                res["CourseLevel-ID"] = m[1]
            else:
                pass
                # log("lvExpEn2 NO MATCH")

    if "CourseLevel-ID" in res and res["CourseLevel-ID"] != "" and res["CourseLevel-ID"] not in {"":1, "A1E":1, "A1F":1, "A1N":1, "A2E":1, "AXX":1, "G1F":1, "G1N":1, "G2E":1, "G2F":1, "GXX":1, "G1E":1, "G2E":1}:
        old = cleanHTML(res["CourseLevel-ID"])
        if old.find("Second Cycle") >= 0:
            res["CourseLevel-ID"] = "AXX"
        elif old.find("First Cycle") >= 0:
            res["CourseLevel-ID"] = "GXX"

        if old.find("Avancerad niv") >= 0:
            res["CourseLevel-ID"] = "AXX"
        elif old.find("Grundniv") >= 0:
            res["CourseLevel-ID"] = "GXX"
        
        if old.find("Preparatory Level") >= 0:
            res["CourseLevel-ID"] = ""
            res["CourseType"] = "förberedande utbildning"
        elif old.find("Preparandniv") >= 0:
            res["CourseLevel-ID"] = ""
            res["CourseType"] = "förberedande utbildning"
        elif old.find("Access") >= 0:
            res["CourseLevel-ID"] = ""
            res["CourseType"] = "förberedande utbildning"
        elif old.find("f&#246;rutbildning") >= 0:
            res["CourseLevel-ID"] = ""
            res["CourseType"] = "förberedande utbildning"
        elif old.find("C") >= 0 and old.find("Cycle") < 0:
            res["CourseLevel-ID"] = "AXX"

        if old.find("Forskarniv&#229;") >= 0:
            res["CourseLevel-ID"] = "AXX"
            
        if old != res["CourseLevel-ID"]:
            log(res["CourseCode"] + " changeing CourseLevel from " + old + " to " + res["CourseLevel-ID"] + "\n")

    if "SCB-ID" in res and res["SCB-ID"] == "()":
        res["SCB-ID"] = ""

    return res

spanExp = re.compile("</?\s*span[^<>]*>", re.I)
divExp = re.compile("</?\s*div[^<>]*>", re.I)
spaceExp = re.compile("\s+")
def cleanHTML(txt):
    res = spanExp.sub("", txt)
    res = divExp.sub("", res)
    res = res.strip()
    return res


scbMappings = {
    "Arabiska (ARA)":"AR1", # "Arabiska"
    "Arbetsvetenskap (ABA)":"AE1", # "Arbetsvetenskap och ergonomi"
    "Bild (BIL)":"KO9", # "Övrigt inom konst"
    "Bildproduktion (BPO)":"KO9", # "Övrigt inom konst"
    "Byggteknik (BYA)":"BY1",
    "Datateknik (DTA)":"DT1",
    "Energiteknik (M&#214;Y)":"EN2",
    "Engelska (ENA)":"EN1",
    "Filosofi (FIA)":"FI2",
    "Franska (FRA)":"FR1",
    "Fysioterapi (FYS)":"TR1", # "Terapi, rehabilitering och kostbehandling"
    "F&#246;retagsekonomi (F&#214;A)":"FE1",
    "Historia (HIA)":"HI2",
    "Idrotts- och h&#228;lsovetenskap (IDA)":"ID1", # "Idrott/idrottsvetenskap"
    "Informatik (IKA)":"IF1",
    "Japanska (JAA)":"JA1",
    "Kulturgeografi (KGA)":"KS1", # "Kultur- och samhällsgeografi"
    "Kinesiska (KIA)":"KI1",
    "Medicinsk vetenskap (MCA)":"ME1", # Medicino
    "Matematikdidaktik (MDI)":"UV1", # "Utbildningsvetenskap/didaktik allmänt"
    "Mikrodataanalys (XYZ)":"DT1", # Datateknik
    "Nationalekonomi (NAA)":"NA1",
    "Pedagogik (PEA)":"PE1",
    "Pedagogiskt arbete (PGA)":"PE1", # Pedagogik
    "Religionsvetenskap (RKA)":"RV1",
    "Ryska (RYA)":"RY1",
    "Afrikanska studier (UVX)":"LL1", # "Länderkunskap/länderstudier"
    "Socialt arbete (SAA)":"SS2",
    "Statsvetenskap (SKA)":"ST2",
    "Spanska (SPA)":"SP1",
    "Sexuell, reproduktiv och perinatal h&#228;lsa (SRP)":"OM1", # "Omvårdnad/omvårdnadsvetenskap"
    "Svenska som andraspr&#229;k (SSA)":"SS1",
    "Svenska (SVE)":"SV1",
    "Turismvetenskap (TRU)":"TU1",
    "Tyska (TYA)":"TY1",
    "V&#229;rdvetenskap (V&#197;E)":"OM1", # "Omvårdnad/omvårdnadsvetenskap"
    "Omv&#229;rdnad (OMV)":"OM1",
    "Fysik (FYA)":"FY1",
    "Kemi (KEA)":"KE1",
    "Elektroteknik (ETA)":"EL1",
    "Entrepren&#246;rskap och innovationsteknik (EUN)":"EK9", # "Övrigt inom ekonomi och administration"
    "Industriell ekonomi (IEA)":"IE1",
    "Italienska (ITA)":"IT1",
    "Ljud- och musikproduktion (LPU)":"MU1", # Musik
    "Matematik (MAA)":"MA1",
    "Medieproduktion (MPR)":"KO9", # "Övrigt inom konst"
    "Maskinteknik (MTA)":"MT1",
    "Naturvetenskap (NAV)":"NA9", # "Övrigt inom naturvetenskap"
    "Personal och arbetsliv (PEE)":"AF1", # "Administration och förvaltning"
    "Portugisiska (PRA)":"PU1",
    "R&#228;ttsvetenskap (RVA)":"JU1",
    "Sociologi (SOA)":"SO1",
    "Samh&#228;llsbyggnadsteknik (SQQ)":"SB1",
    "Statistik (STA)":"ST1",
    "Grafisk teknologi (GTO)":"TE9", # "Övriga tekniska ämnen"
    "Industriell ekonomi och arbetsvetenskap (IEV)":"IE1",
    "Psykologi (PSA)":"PS1",
    "V&#229;rdvetenskap med inriktning mot munh&#228;lsa (V&#197;U)":"TO1", # "Tandteknik och oral hälsa"
    "V&#229;rdvetenskap inr omv&#229;rdnad (V&#197;O)":"OM1",
    "Data Analytics (ANALYTIC)":"ST1", # Statistik
    "Energisystem i byggd milj&#246; (ENERGIBM)":"EN2", # Energiteknik
    "Mikrodataanalys (MIKRODAT)":"DT1", # Datateknik
    "Pedagogiskt arbete (PEDAGARB)":"PE1", # Pedagogik
    "Mikrodataanalys (MIKRODAT) Pedagogiskt arbete (PEDAGARB) V&#229;rdvetenskap (V&#197;RDVETS)":"TV9", # "Övriga tvärvetenskapliga studier"
    "V&#229;rdvetenskap (V&#197;RDVETS)":"OM1" # "Omvårdnad/omvårdnadsvetenskap"
}


def getOneCourse(cc, rawData):

    plan = {
        "University":"DU",
        "CourseCode":"",
        "ECTS-credits":"",
        "ValidFrom":"",
        "ILO-sv":"",
        "ILO-en":"",
        "SCB-ID":"",
        "CourseLevel-ID":"",
        "Prerequisites-sv":"",
        "Prerequisites-en":"",
        "CourseType":""
    }

    plan["CourseCode"] = fixSwedishHTMLChars(cc)
    if "ECTS-credits" in rawData[cc]:
        plan["ECTS-credits"] = rawData[cc]["ECTS-credits"]
    if "ValidFrom" in rawData[cc]:
        plan["ValidFrom"] = fixDateFormat(rawData[cc]["ValidFrom"])
    if "CourseType" in rawData[cc]:
        plan["CourseType"] = rawData[cc]["CourseType"]
        
    logFlush()

    # Get Swedish course info
    if rawData[cc]["html-sv"] and rawData[cc]["html-sv"] != "":
        if rawData[cc]["html-sv"].find("en kursplan med felaktig kurskod") > 0:
            log("WARNING: HTML says course code does not exist: " + cc)
            plan["Failed"]  = 1
            return plan
        else:
            svInfo = extractInfoFromWebpage(rawData[cc]["html-sv"])
    else:
        log("WARNING: no Swedish HTML for " + cc)
    
    if rawData[cc]["html-en"] and rawData[cc]["html-en"] != "":
        if rawData[cc]["html-en"].find("syllabus with incorrect course code") > 0:
            log("WARNING: English HTML says course code does not exist: " + cc)
            plan["Failed"]  = 1
            enInfo = {}
        else:
            enInfo = extractInfoFromWebpage(rawData[cc]["html-en"])
    else:
        log("WARNING: no English HTML for " + cc)
    
    for tag in plan:
        if tag in svInfo:
            if plan[tag] == "" and svInfo[tag] != "":
                plan[tag] = cleanHTML(svInfo[tag])
            if plan[tag] != "" and svInfo[tag] != "" and plan[tag] != cleanHTML(svInfo[tag]):
                log ("WARNING: Inconsistent Swe., course " + cc + " field " + tag + ": '" + plan[tag] + "' != '" + cleanHTML(svInfo[tag]) + "'")
        if tag in enInfo:
            if plan[tag] == "" and enInfo[tag] != "":
                plan[tag] = cleanHTML(enInfo[tag])
            if plan[tag] != "" and enInfo[tag] != "" and plan[tag] != cleanHTML(enInfo[tag]):
                if tag != "SCB-ID":
                    log ("WARNING: Inconsistent Eng., course " + cc + " field " + tag + ": '" + plan[tag] + "' != '" + cleanHTML(enInfo[tag]) + "'")
    
    if plan["CourseType"] == "":
        plan["CourseType"] = "grundutbildning"

    for tag in plan:
        if plan[tag] == "":
            if tag == "ILO-en":
                if "CourseCode" in enInfo and enInfo["CourseCode"] != "" and "ECTS-credits" in enInfo and enInfo["ECTS-credits"] != "":
                    log("WARNING: no English translation (no ILO-en found) " + cc + " field " + tag)
                else:
                    log("WARNING: Missing info, course " + cc + " field " + tag)
            else:
                log("WARNING: Missing info, course " + cc + " field " + tag)

    return plan

###############################################
#### Load all previously downloaded plans  ####
###############################################
try:
    f = open("data/hogskolanDalarna.raw.html.data.json")
    tmp = json.load(f)
    f.close()
    oldCount = 0
    rawData = {}
    for c in tmp["Course-list"]:
        oldCount += 1
        rawData[c["CourseCode"]] = c
    print("found ", oldCount, "HTML pages for courses on local disk")
except Exception as e:
    print ("ERROR: Did not find file with local data.")
    oldCount = 0
    print (e)
    rawData = {}
    sys.exit(1)

############################################
#### Write startdates in our format  ####
############################################
dateExp1 = re.compile("([VH]T)([0-9]{4})")
dateExp2 = re.compile("([0-9]{4})-([0-9]{2})-([0-9]{2})")
dateExp3 = re.compile("([0-9]{1,2})\s*([A-Z][a-z]*)\s*([0-9]{4})")
vtMonths = {"Jan":1, "January":1, "Feb":1, "February":1, "Mar":1, "March":1, "Apr":1, "April":1, "May":1, "Jun":1, "June":1}
htMonths = {"Jul":1, "July":1, "Aug":1, "August":1, "Sep":1, "September":1, "Oct":1, "October":1, "Nov":1, "November":1, "Dec":1, "December":1}
def fixDateFormat(txt):
    m = dateExp1.search(txt)
    if m:
        if m[1] == "VT":
            return m[2] + ":1"
        if m[1] == "HT":
            return m[2] + ":2"
        log("WARNING: could not parse date 1: " + txt + ", " + m)
    
    m = dateExp2.search(txt)
    if m:
        if int(m[2]) <= 6:
            return m[1] + ":1"
        if int(m[2]) >= 7:
            return m[1] + ":2"
        log("WARNING: could not parse date 2: " + txt + ", " + m)

    m = dateExp3.search(txt)
    if m:
        if m[2] in vtMonths:
            return m[3] + ":1"
        if m[2] in htMonths:
            return m[3] + ":2"
        log("WARNING: could not parse date 3: " + txt + ", " + m)

    log("WARNING: could not parse date: '" + txt + "'")
    return ""

############################################
#### Get each course  ####
############################################
warningFile = open(sys.argv[0] + ".warnings", "w")
noHTML = 0
uniqHTML = 0

output = []
handled = 0
for cc in rawData:
    if haveCCall:
        pass
    elif haveCC:
        if cc in CCs:
            pass
        else:
            continue # skip courses not specified
    
    res = getOneCourse(cc, rawData)

    if not "Failed" in res or res["Failed"] == 0:
        output.append(res)
    else:
        warningFile.write(cc + " no HTML found!!\n")
        noHTML += 1
            
    handled += 1

    if handled % 100 == 0:
        print ("Processed", handled, "course (out of", oldCount, "courses)")
    
##############################
### Print warnings to file ###
##############################
missing = {
    "no ILO-sv":0,
    "empty ILO-sv":0,
    "no ILO-en":0,
    "empty ILO-en":0,
    "no ECTS-credits":0,
    "no ValidFrom":0,
    "no SCB-ID":0,
    "no CourseLevel-ID":0,
    "no Prerequisites-sv":0,
    "no Prerequisites-en":0,
    "no CourseType":0,
    "unknown CourseLevel-ID":0
    }
uniques = {}
for tag in output[0]:
    uniques[tag] = {}

for plan in output:
    uniqHTML += 1
    
    if not "ILO-sv" in plan:
        warningFile.write(plan["CourseCode"] + " no ILO-sv\n")
        missing["no ILO-sv"] += 1
    elif plan["ILO-sv"] == "":
        warningFile.write(plan["CourseCode"] + " empty ILO-sv\n")
        missing["empty ILO-sv"] += 1

    if not "ILO-en" in plan:
        warningFile.write(plan["CourseCode"] + " no ILO-en\n")
        missing["no ILO-en"] += 1
    elif plan["ILO-en"] == "":
        warningFile.write(plan["CourseCode"] + " empty ILO-en\n")
        missing["empty ILO-en"] += 1

    if not "ECTS-credits" in plan or plan["ECTS-credits"] == "":
        warningFile.write(plan["CourseCode"] + " no ECTS-credits\n")
        missing["no ECTS-credits"] += 1
    else:
        uniques["ECTS-credits"][plan["ECTS-credits"]] = 1
        
    if not "ValidFrom" in plan or plan["ValidFrom"] == "":
        warningFile.write(plan["CourseCode"] + " no ValidFrom\n")
        missing["no ValidFrom"] += 1
    else:
        uniques["ValidFrom"][plan["ValidFrom"]] = 1

    if not "SCB-ID" in plan or plan["SCB-ID"] == "":        
        warningFile.write(plan["CourseCode"] + " no SCB-ID\n")
        missing["no SCB-ID"] += 1
    else:
        uniques["SCB-ID"][plan["SCB-ID"]] = 1

    if not "CourseLevel-ID" in plan or plan["CourseLevel-ID"] == "":
        warningFile.write(plan["CourseCode"] + " no CourseLevel-ID\n")
        missing["no CourseLevel-ID"] += 1
    else:
        if plan["CourseLevel-ID"] not in {"":1, "A1E":1, "A1F":1, "A1N":1, "A2E":1, "AXX":1, "G1F":1, "G1N":1, "G2E":1, "G2F":1, "GXX":1, "G1E":1, "G2E":1}:
            warningFile.write(plan["CourseCode"] + " unknown CourseLevel " + plan["CourseLevel-ID"] + "\n")
            missing["unknown CourseLevel-ID"] += 1

        uniques["CourseLevel-ID"][plan["CourseLevel-ID"]] = 1
    
    if not "Prerequisites-sv" in plan or plan["Prerequisites-sv"] == "":
        warningFile.write(plan["CourseCode"] + " no Prerequisites-sv\n")
        missing["no Prerequisites-sv"] += 1
    
    if not "Prerequisites-en" in plan or plan["Prerequisites-en"] == "":
        warningFile.write(plan["CourseCode"] + " no Prerequisites-en\n")
        missing["no Prerequisites-en"] += 1

    if not "CourseType" in plan or plan["CourseType"] == "":
        warningFile.write(plan["CourseCode"] + " no CourseType\n")
        missing["no CourseType"] += 1
    else:
        uniques["CourseType"][plan["CourseType"]] = 1


for tag in uniques:
    warningFile.write("-----" + tag + "------\n")
    for val in uniques[tag]:
        warningFile.write(str(val) + "\n")
warningFile.write("-----" + "-----" + "------\n")

for tag in missing:
    warningFile.write(str(missing[tag]) + " " + str(tag) + "\n")
warningFile.write("-------------------\n")
warningFile.write(str(noHTML) + " CourseCodes with no HTML page found\n")
warningFile.write(str(uniqHTML) + " unique CourseCodes with HTML (number of usable courses in data)\n")

warningFile.close()


##############################
### Print result to stdout ###
##############################
output = {"Course-list": output}
# print(json.dumps(output))

if haveOut:
    fout = open(outputFile, "w")
else:
    fout = open(sys.argv[0] + ".output", "w")
fout.write(json.dumps(output))
fout.close()
