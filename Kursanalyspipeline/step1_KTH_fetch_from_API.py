import sys
import re
import requests
import xml.etree.ElementTree as XML
import html
import datetime
import json

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
                    print ("WARNING: Courseround does not have all needed fields?", cr)
    else:
        print ("WARNING: Could not retrieve course rounds: " + "https://api.kth.se/api/kopps/v1/courseRounds/" + sem) 

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

    plan = {"goals":{}, "elig":{}}
    url = "https://api.kth.se/api/kopps/v1/course/" + cc + "/plan/" + sem # /{language (en|sv)}
    r = requests.get(url)
    if (str(r.status_code) == "200"): # everything went fine

        xml = XML.fromstring(r.text + "\n")
        for el in xml.iter('goals'):
            if(el.attrib):
                atts = el.attrib
                if langAttr in atts:
                    if not "goals" in plan:
                        plan["goals"] = {}
                    try:
                        plan["goals"][atts[langAttr]] = html.unescape(el.text.replace("&nbsp;", " "))
                    except:
                        plan["goals"][atts[langAttr]] = el.text
        for el in xml.iter('eligibility'):
            if(el.attrib):
                atts = el.attrib
                if langAttr in atts:
                    if not "elig" in plan:
                        plan["elig"] = {}
                    try:
                        plan["elig"][atts[langAttr]] = html.unescape(el.text.replace("&nbsp;", " "))
                    except:
                        plan["elig"][atts[langAttr]] = el.text
    else:
        print ("WARNING: Could not fetch '" + url + "'")
    r.close()

    course = ""
    url = "https://api.kth.se/api/kopps/v1/course/" + cc # + "/{language (en|sv)}
    r =  requests.get(url)
    if (str(r.status_code) == "200"): # everything went fine
        course = {"title":{}, "subjectCode":""}
        xml = XML.fromstring(r.text)
        for el in xml.iter('subjectCode'):
            try:
                course["subjectCode"] = html.unescape(el.text.replace("&nbsp;", " "))
            except:
                course["subjectCode"] = el.text
    else:
        print ("WARNING: Could not fetch '" + url + "'")
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

    if "en" in plan["goals"]:
        iloen = plan["goals"]["en"]
    else:
        iloen = ""
    if "sv" in plan["goals"]:
        ilosv = plan["goals"]["sv"]
    else:
        ilosv = ""
    if "sv" in plan["elig"]:
        eligsv = plan["elig"]["sv"]
    else:
        eligsv = ""
    if "subjectCode" in course:
        scb = course["subjectCode"]
    else:
        scb = ""
    return {"University":"KTH", # (Miun, UmU, SU, KTH)
            "CourseCode":cc,
            "ValidFrom":sem,
            "ILO-sv":ilosv,
            "ILO-en":iloen,
            "SCB-ID":scb, # SCB-ID   [SCBs lista]
            "CourseLevel-ID":level,         #  (G1N, G1F, G1E, G2F, G2E, A1N, A1F, A1E, A2E, GXX, AXX) [SUHF]
            "Prerequisites":eligsv
    }

####################################
#### Get command line arguments ####
####################################

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
        courseCode = sys.argv[i+1]
        # if (len(courseCode) != 6):
        #     print ("WARNING:", courseCode, "does not seem to be a correctly formatted course code.")
    elif (sys.argv[i] == "-ct" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 0
        timeSpan = sys.argv[i+1]
        if (not timeSpanExp.fullmatch(timeSpan)):
            print ("WARNING:", timeSpan, "does not seem to be a correctly formatted year/semester.")
            haveCC = 0 # force 'print help'
            haveCCall = 0
    elif (sys.argv[i] == "-cy" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 1
        timeSpan = sys.argv[i+1]
        if (not timeSpanExp.fullmatch(timeSpan)):
            print ("WARNING:", timeSpan, "does not seem to be a correctly formatted year/semester.")
            haveCC = 0 # force 'print help'
            haveCCall = 0

if (not haveCC and not haveCCall) or (haveCC and haveCCall):
    print ("\nFetch course information from the KTH API, print result as JSON to stdout\n")
    print ("usage options: [-a] [-cc <CODE>] [-ct <SEMESTER>] [-o <FILE_NAME>] [-r] [-d <level>]")
    print ("Flags: -a              Classify all courses.");
#    print ("       -s              Output the syllabus (code, name, ILOs, contents).");
    print ("       -cc <CODE>      Course code (usually six alphanumeric characters).");
    print ("       -ct <SEMESTER>  Course semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester);
    print ("       -cy <SEMESTER>  Course year/semester in the format YYYY:T (e.g. 2016:2). Default is " + defaultSemester);
#    print ("       -o <FILE_NAME>  Output file name (default is \"output.csv\").");
#    print ("       -d <level>      Set debug level, for example 10, 20, 100.");
    print ("\nNote: EITHER -a OR -cc must be used (not both).\n");
    sys.exit(0)

########################################
#### Build list of courses to fetch ####
########################################
listOfSemesters = [timeSpan]
if haveFullYear:
    listOfSemesters.append(nextSemester(timeSpan))

listOfCourses = []
for semester in listOfSemesters:
    listOfCourses.extend(getRounds(semester))

listOfResults = []
for i in range(len(listOfCourses)):
    tmp = getOneCourse(listOfCourses[i][1], listOfCourses[i][0], listOfCourses[i][2])

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

    # if len(listOfResults) > 150:
    #     break

##############################
### Print result to stdout ###
##############################
output = {"Course-list": listOfResults}
print(json.dumps(output))
