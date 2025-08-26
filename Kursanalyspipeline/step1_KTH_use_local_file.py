import sys
import re
import requests
import xml.etree.ElementTree as XML
import html
import datetime
import json

import time

defaultDir = "KTHfromKopps"
fileDir = defaultDir

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

CCs = {}

def nextSemester(sem):
    y, t = sem.split(":")
    if (t == "1"):
        return y + ":" + "2"
    else:
        return str(int(y) + 1) + ":1"

timeSpanExp = re.compile("[0-9][0-9][0-9][0-9]:[0-9]")

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
        delaySeconds = int(sys.argv[i + 1])
    elif (sys.argv[i] == "-retry") and i + 1 < len(sys.argv):
        delayMinutes = int(sys.argv[i + 1])
    elif sys.argv[i] == "-log":        
        logging = 1
    elif sys.argv[i] == "-dir" and i + 1 < len(sys.argv):
        fileDir = sys.argv[i+1]

if noCache:
    cacheFile = ""
else:
    if cacheFile == "":
        cacheFile = sys.argv[0] + ".cache"

if (not haveCC and not haveCCall) or (haveCC and haveCCall):
    print ("\nFetch course information from the KTH API, print result as JSON to stdout\n")
    print ("usage options: [-a] [-cc <CODE>] [-ct <SEMESTER>] [-cacheFile <FILE_NAME>] [-noCache] [-delay <SECONDS>] [-retry <MINUTES>] [-log]")
    print ("Flags: -a                              Classify all courses.")
    print ("       -cc <CODE>                      Course code (usually six alphanumeric characters).")
    print ("       -ccs \"<CODE1> <CODE2> ... \"     Course codes (six alphanumeric characters).");
    print ("       -ct <SEMESTER>                  Course semester in the format YYYY:T (e.g. 2016:1). Default is " + defaultSemester + ".")
    print ("       -cy <SEMESTER>                  Course year/semester in the format YYYY:T (e.g. 2016:2). Default is " + defaultSemester + ".")
#    print ("       -o <FILE_NAME>  Output file name (default is \"output.csv\").")
#    print ("       -d <level>      Set debug level, for example 10, 20, 100.")
    print ("       -dir <directory>                Directory with course data files, default is " + defaultDir + ".")    
    print ("       -log                            Log debug information to " + sys.argv[0] + ".log.")    
    print ("\nNote: One of -a OR -cc OR -ccs must be used.\n")
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



#########################
### Find a local file ###
#########################

files = []
if timeSpan[-1:] == "1":
    if haveFullYear:
        # need two files, since we have two semesters from different school years
        files.append(str(int(timeSpan[:4]) -1) + ".json")
        files.append(timeSpan[:4] + ".json")
    else:
        files.append(str(int(timeSpan[:4]) -1) + ".json")
else:
    files.append(timeSpan[:4] + ".json")

###################################################
### For each file, find the courses that match: ###
### * selected course codes (if given)          ###
### * selected time period                      ###
###################################################

if timeSpan[-1:] == "1":
    if haveFullYear:
        firstTerm = timeSpan
        lastTerm = timeSpan[:5] + "2"
    else:
        firstTerm = timeSpan
        lastTerm = timeSpan
else:
    if haveFullYear:
        firstTerm = timeSpan
        lastTerm = str(int(timeSpan[:4])+1) + ":1"
    else:
        firstTerm = timeSpan
        lastTerm = timeSpan
firstYear = int(firstTerm[:4])
lastYear = int(lastTerm[:4])
firstT = int(firstTerm[-1])
lastT = int(lastTerm[-1])

def dateCheck(c):
    if not "ValidFrom" in c:
        return False
    y = int(c["ValidFrom"][:4])
    t = int(c["ValidFrom"][-1])
    if (firstYear == y and t >= firstT and (y < lastYear or t <= lastT)) or (y == lastYear and t <= lastT and (y > firstYear or t >= firstT)):
        return True
    return False

if fileDir[-1] != "/":
    fileDir += "/"
    
listOfResults = []

for fileName in files:
    try:
        f = open(fileDir + fileName)
        localData = json.load(f)
        f.close()

        if "Course-list" in localData:
            cl = localData["Course-list"]
        else:
            cl = localData
            
        for c in cl:
            if not haveCC or c["CourseCode"] in CCs:
                # course code is OK

                if dateCheck(c):
                    # time period OK

                    # check for duplicates

                    dup = 0
                    for i in range(len(listOfResults)):
                        if listOfResults[i]["CourseCode"] == c["CourseCode"]:
                            diff = 0
                        for attr in c:
                            if listOfResults[i][attr] != c[attr]:
                                diff = 1
                                break
                        if not diff:
                            dup = 1
                            break
                    if not dup:
                        listOfResults.append(c)
    except:
        print ("Could not open file: '" + fileDir + fileName + "'")
        


##############################
### Print result to stdout ###
##############################
output = {"Course-list": listOfResults}
print(json.dumps(output))
