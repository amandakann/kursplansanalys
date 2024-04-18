import sys
import re
import requests
import xml.etree.ElementTree as XML
import html
import datetime
import json

import time

#######################################
#### Set default semester to "now" ####
#######################################
defaultSemester = ""
today = datetime.date.today()
defaultSemester = str(today.year)
if today.month < 7:
    defaultSemester += ":1"
else:
    defaultSemester += ":2"
timeSpan = defaultSemester

courseCode = "all"

def nextSemester(sem):
    y, t = sem.split(":")
    if (t == "1"):
        return y + ":" + "2"
    else:
        return str(int(y) + 1) + ":1"

timeSpanExp = re.compile("[0-9][0-9][0-9][0-9]:[0-9]")

#########################################################
#### Get list of courses offered a specific semester ####
#########################################################
def getRounds(sem):
    result = []
    r = requests.get("https://api.kth.se/api/kopps/v1/courseRounds/" + sem)

    if (str(r.status_code) == "200"): # everything went fine
        xml = XML.fromstring(r.text)
        for cr in xml:
            if (cr.tag == "courseRound"):
                atts = cr.attrib
                if(atts and ("courseCode" in atts) and ("roundId" in atts)):
                    if (haveCCall or courseCode == atts["courseCode"]):
                        result.append([atts["courseCode"], sem, atts["roundId"]])
                else:
                    log("WARNING: Courseround does not have all needed fields?")
                    log(str(cr))
    else:
        log("WARNING: Could not retrieve course rounds: " + "https://api.kth.se/api/kopps/v1/courseRounds/" + sem)

    return result

################################################################################
#### figure out what the "xml:lang" attribute looks like in this XML parser ####
################################################################################
langAttr = "xml:lang"
xml = XML.fromstring("<test xml:lang='se'>test</test>")
atts = xml.attrib
for a in atts:
    if a[-4:] == "lang":
        langAttr = a

############################################
#### Get the information for one course ####
############################################
def getOneCourse(sem, cc, roundId):

    plan = {}
    url = "https://api.kth.se/api/kopps/v1/course/" + cc + "/plan/" + sem

    log("getOneCourse(" + sem + ", " + cc + ", " + roundId +")\n")
    log("url: " + url +")\n")
    logFlush()
    time.sleep(delaySeconds)

    triesSoFar = 0
    GiveUpAfterXTries = 5
    failed = 1
    while triesSoFar < GiveUpAfterXTries:
        triesSoFar += 1
        try:
            r = requests.get(url)
            failed = 0
        except Exception as e:
            log("Failed getting " + url + "\n")
            log(str(e))
            if triesSoFar < GiveUpAfterXTries:
                time.sleep(60 * delayMinutes) # wait 15 minutes and see if the server replies

    if failed:
        log("Failed to get round info " + url + ", giving up.\n")
        return {"Failed":1,
                "University":"KTH",
                "CourseCode":"",
                "ECTS-credits":"",
                "ValidFrom":"",
                "ILO-sv":"",
                "ILO-en":"",
                "SCB-ID":"",
                "CourseLevel-ID":"",
                "Prerequisites-sv":"",
                "Prerequisites-en":"",
                "CourseType":""}
    
    log("goal status: ")
    log(str(r.status_code))

    if (str(r.status_code) == "200"): # everything went fine

        xml = XML.fromstring(r.text + "\n")
        for el in xml.iter('goals'):
            if(el.attrib):
                atts = el.attrib
                if langAttr in atts:
                    if not "goals" in plan and el.text:
                        plan["goals"] = {}
                    try:
                        plan["goals"][atts[langAttr]] = html.unescape(el.text.replace("&nbsp;", " "))
                    except:
                        plan["goals"][atts[langAttr]] = el.text
        for el in xml.iter('eligibility'):
            if(el.attrib):
                atts = el.attrib
                if langAttr in atts and el.text:
                    if not "elig" in plan:
                        plan["elig"] = {}
                    try:
                        plan["elig"][atts[langAttr]] = html.unescape(el.text.replace("&nbsp;", " "))
                    except:
                        plan["elig"][atts[langAttr]] = el.text
    else:
        log("WARNING: Could not fetch '" + url + "'")
        r.close()
        return {"Failed":1,
                "University":"KTH",
                "CourseCode":"",
                "ECTS-credits":"",
                "ValidFrom":"",
                "ILO-sv":"",
                "ILO-en":"",
                "SCB-ID":"",
                "CourseLevel-ID":"",
                "Prerequisites-sv":"",
                "Prerequisites-en":"",
                "CourseType":""}

    r.close()
    time.sleep(delaySeconds)

    course = ""
    url = "https://api.kth.se/api/kopps/v1/course/" + cc

    failed = 1
    triesSoFar = 0
    while triesSoFar < GiveUpAfterXTries:
        triesSoFar += 1
        try:
            r = requests.get(url)
            failed = 0
        except Exception as e:
            log("Failed getting " + url + "\n")
            log(str(e))
            if triesSoFar < GiveUpAfterXTries:
                time.sleep(60*15) # wait 15 minutes and see if the server replies

    if failed:
        log("Failed to get course info: " + url + ", giving up.\n")
        return {"Failed":1,
                "University":"KTH",
                "CourseCode":"",
                "ECTS-credits":"",
                "ValidFrom":"",
                "ILO-sv":"",
                "ILO-en":"",
                "SCB-ID":"",
                "CourseLevel-ID":"",
                "Prerequisites-sv":"",
                "Prerequisites-en":"",
                "CourseType":""}
    
    log("subj.code status: ")
    log(str(r.status_code))

    hp = ""
    if (str(r.status_code) == "200"): # everything went fine
        course = {"title":{}, "subjectCode":""}
        xml = XML.fromstring(r.text)
        for el in xml.iter('subjectCode'):
            try:
                course["subjectCode"] = html.unescape(el.text.replace("&nbsp;", " "))
            except:
                course["subjectCode"] = el.text
        for el in xml.iter('credits'):
            if hp == "":
                hp = el.text
            else:
                if hp != el.text:
                    log("WARNING: two different values for ECTS-credits: " + hp + " and " + el.text)
    else:
        log ("WARNING: Could not fetch '" + url + "'")
        r.close()
        return {"Failed":1,
                "University":"KTH",
                "CourseCode":"",
                "ECTS-credits":"",
                "ValidFrom":"",
                "ILO-sv":"",
                "ILO-en":"",
                "SCB-ID":"",
                "CourseLevel-ID":"",
                "Prerequisites-sv":"",
                "Prerequisites-en":"",
                "CourseType":""}

    r.close()
    
    # Decide "level" based on the information in the course code
    level = ""
    if cc[5] == "X":
        if cc[2] == "1":
            level = "G2E"
        else:
            level = "A2E"
    else:
        if cc[2] == "1":
            level = "GXX"
        elif cc[2] == "2":
            level = "AXX"

    if level == "":
        pass # skip this course ??

    if "en" in plan["goals"] and plan["goals"]["en"]:
        iloen = plan["goals"]["en"]
    else:
        iloen = ""
    if "sv" in plan["goals"] and plan["goals"]["sv"]:
        ilosv = plan["goals"]["sv"]
    else:
        ilosv = ""

    if "elig" in plan and "sv" in plan["elig"] and plan["elig"]["sv"]:
        eligsv = plan["elig"]["sv"]
    else:
        eligsv = ""
    if "elig" in plan and "en" in plan["elig"] and plan["elig"]["en"]:
        eligen = plan["elig"]["en"]
    else:
        eligen = ""
        
    if "subjectCode" in course and course["subjectCode"]:
        scb = course["subjectCode"]
    else:
        scb = ""

    ctype = ""
    if cc[-1:] == "U":
        ctype = "uppdragsutbildning"
    elif cc[0] == "F":
        ctype = "forskarutbildning"
    elif cc[-1:] == "V":
        ctype = "vidareutbildning"
    elif cc[2] == "0":
        ctype = "förberedande utbildning"
        level = "" # Should not have a level such as GXX
    else:
        ctype = "grundutbildning"
    
    return {"University":"KTH", # (Miun, UmU, SU, KTH)
            "CourseCode":cc,

            "ECTS-credits":hp,
            
            "ValidFrom":sem,
            "ILO-sv":ilosv,
            "ILO-en":iloen,
            "SCB-ID":scb,

            "CourseLevel-ID":level,
            # (G1N, G1F, G1E, G2F, G2E, A1N, A1F, A1E, A2E, GXX, AXX) [SUHF]

            "Prerequisites-sv":eligsv,
            "Prerequisites-en":eligen,

            "CourseType":ctype
            # (vidareutbildning/uppdragsutbildning/förberedande utbildning/grundutbildning/forskarutbildning)
    }

####################################
#### Get command line arguments ####
####################################

haveCC = 0
haveCCall = 0
haveTime = 0
haveOut = 0
haveFullYear = 0
cacheFile = ""
noCache = 0
delaySeconds = 5
delayMinutes = 15
logging = 0

for i in range(1, len(sys.argv)):
    if (sys.argv[i] == "-a"):
        haveCCall = 1
    elif (sys.argv[i] == "-cc" and i + 1 < len(sys.argv)):
        haveCC = 1
        courseCode = sys.argv[i+1]
        # if (len(courseCode) != 6):
        #     print("WARNING:' " + courseCode + "' does not seem to be a correctly formatted course code.")
    elif (sys.argv[i] == "-ct" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 0
        timeSpan = sys.argv[i+1]
        if (not timeSpanExp.fullmatch(timeSpan)):
            print ("WARNING: '" + timeSpan + "' does not seem to be a correctly formatted year/semester.")
            haveCC = 0 # force 'print help'
            haveCCall = 0
    elif (sys.argv[i] == "-cy" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 1
        timeSpan = sys.argv[i+1]
        if (not timeSpanExp.fullmatch(timeSpan)):
            print ("WARNING: '" + timeSpan + "' does not seem to be a correctly formatted year/semester.")
            haveCC = 0 # force 'print help'
            haveCCall = 0
    elif (sys.argv[i] == "-cacheFile" or sys.argv[i] == "-cf") and i + 1 < len(sys.argv):
        cacheFile = sys.argv[i + 1]
    elif sys.argv[i] == "-noCache" or sys.argv[i] == "-nc":
        noCache = 1
    elif (sys.argv[i] == "-delay") and i + 1 < len(sys.argv):
        delaySeconds = sys.argv[i + 1]
    elif (sys.argv[i] == "-retry") and i + 1 < len(sys.argv):
        delayMinutes = sys.argv[i + 1]
    elif sys.argv[i] == "-log":
        logging = 1

if noCache:
    cacheFile = ""
else:
    if cacheFile == "":
        cacheFile = sys.argv[0] + ".cache"

if (not haveCC and not haveCCall) or (haveCC and haveCCall):
    print ("\nFetch course information from the KTH API, print result as JSON to stdout\n")
    print ("usage options: [-a] [-cc <CODE>] [-ct <SEMESTER>] [-cacheFile <FILE_NAME>] [-noCache] [-delay <SECONDS>] [-retry <MINUTES>] [-log]")
    print ("Flags: -a                      Classify all courses.")
    print ("       -cc <CODE>              Course code (usually six alphanumeric characters).")
    print ("       -ct <SEMESTER>          Course semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester + ".")
    print ("       -cy <SEMESTER>          Course year/semester in the format YYYY:T (e.g. 2016:2). Default is " + defaultSemester + ".")
#    print ("       -o <FILE_NAME>  Output file name (default is \"output.csv\").")
#    print ("       -d <level>      Set debug level, for example 10, 20, 100.")
    print ("       -cacheFile <FILENAME>   Use data in file <FILENAME>, only fetch data not alreadt in the file. Adds new data to the")
    print ("                                   same file. [-cf] can be used as short form. (If -cacheFile is not specified, ")
    print ("                                   " + sys.argv[0] + ".cache will be used.")
    print ("       -noCache                Do not save downloaded data for future use, only output result. [-nc] can be used as a short form.")
    print ("       -delay <SECONDS>        How many seconds to wait between each call to the server. If not specified, " + str(delaySeconds) + " seconds.")
    print ("       -retry <MINUTES>        How many minutes to wait before trying again when there are problems contacting the server. If not specified, " + str(delayMinutes) + " minutes.")
    print ("       -log                    Log debug information to " + sys.argv[0] + ".log.")    
    print ("\nNote: EITHER -a OR -cc must be used (not both).\n")
    sys.exit(0)


###############
### Logging ###
###############
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

###################################
#### Read data from cache file ####
###################################
cache = {}
if not noCache and cacheFile != "":
    try:
        f = open(cacheFile)
        cache = json.load(f)
        f.close()

        log("Loaded " + str(len(cache.keys())) + " cache items.")
    except:
        cache = {}

########################################
#### Build list of courses to fetch ####
########################################
listOfSemesters = [timeSpan]
if haveFullYear:
    listOfSemesters.append(nextSemester(timeSpan))

listOfCourses = []
for semester in listOfSemesters:
    listOfCourses.extend(getRounds(semester))

log(str(len(listOfCourses)) + " courses to fetch\n")
    
listOfResults = []
for i in range(len(listOfCourses)):
    tmp = 0
    if not noCache and cache and listOfCourses[i][0] in cache:
        ctmp = cache[listOfCourses[i][0]]
        for c in ctmp:
            if c[0] == listOfCourses[i][1] and c[1] == listOfCourses[i][2]:
                log("Cache hit for " + listOfCourses[i][0])
                tmp = c[2]
    if not tmp:
        tmp = getOneCourse(listOfCourses[i][1], listOfCourses[i][0], listOfCourses[i][2])

        if not noCache and cacheFile and not "Failed" in tmp:
            if not cache:
                cache = {}
            if not listOfCourses[i][0] in cache:
                cache[listOfCourses[i][0]] = [[listOfCourses[i][1], listOfCourses[i][2], tmp]]
            else:
                cache[listOfCourses[i][0]].append([listOfCourses[i][1], listOfCourses[i][2], tmp])
            f = open(cacheFile, "w")
            f.write(json.dumps(cache))
            f.close()

    if "Failed" in tmp:
        continue
    
    # check for duplicates
    dup = 0
    for i in range(len(listOfResults)):
        if listOfResults[i]["CourseCode"] == tmp["CourseCode"]:
            diff = 0
            for attr in tmp:
                if listOfResults[i][attr] != tmp[attr]:
                    diff = 1
                    break
            if not diff:
                dup = 1
                break
    if not dup:
        listOfResults.append(tmp)

##############################
### Print result to stdout ###
##############################
output = {"Course-list": listOfResults}
print(json.dumps(output))
