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
for i in range(2, len(sys.argv)):
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
        # if (not timeSpanExp.fullmatch(timeSpan)):
        #     print ("WARNING:", timeSpan, "does not seem to be a correctly formatted year/semester.")
    elif (sys.argv[i] == "-cy" and i + 1 < len(sys.argv)):
        haveTime = 1
        haveFullYear = 1
        timeSpan = sys.argv[i+1]
        # if (not timeSpanExp.fullmatch(timeSpan)):
        #     print ("WARNING:", timeSpan, "does not seem to be a correctly formatted year/semester.")
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
#    print ("       -o <FILE_NAME>  Output file name (default is \"output.csv\").");
    print ("\nNote: One of -a OR -cc OR -ccs must be used.\n");
    sys.exit(0)


####################################
#### Read csv-file              ####
####################################
text = open(sys.argv[1]).read()
lines = []

c = 0
last = 0
line = []
token = ""
insideString = 0
while c < len(text):
    if text[c] == '"': # newline inside strings are allowed, so are semicolon
        if insideString:
            insideString = 0
        else:
            insideString = 1
    if text[c] == ";" and not insideString:
        token = text[last:c]
        line.append(token)
        last = c+1
    if text[c] == "\n" and not insideString:
        token = text[last:c]
        line.append(token)
        last = c+1
        lines.append(line)
        line = []
    c += 1

############################################
#### Figure out what time period to use ####
############################################
startYear = int(timeSpan[:4])
startTerm = int(timeSpan[-1:])
if haveFullYear:
    if startTerm == 1:
        endYear = startYear
        startMonth = 1
        endMonth = 12
    else:
        endYear = startYear + 1
        startMonth = 7
        endMonth = 6
else:
    if startTerm == 1:
        endYear = startYear
        startMonth = 1
        endMonth = 6
    else:
        endYear = startYear
        startMonth = 7
        endMonth = 12
startYm = startYear * 100 + startMonth
endYm = endYear * 100 + endMonth

################################################
#### Remove entries outside the time period ####
#### or that have been revoked etc.         ####
################################################
res = []
for lineno in range(1, len(lines)):
    fields = lines[lineno]

    # skip revoked courses
    if fields[1] == 1:
        continue

    cc = fields[4].replace('"', '') # new version has quotes, old does not

    # if we are to use only one CC, skip the other courses
    if haveCC and cc not in CCs:
        continue

    # if the course is not from the correct time span, skip
    start = fields[9].replace('"', '') # new version of data has quotes, old does not
    tmp = start.split("-")
    year = int(tmp[0])
    month = int(tmp[1])
    ym = year * 100 + month
    if month < 7:
        term = tmp[0] + ":1"
    else:
        term = tmp[0] + ":2"

    # for SU courses, the 'start' field is when the course plab was
    # first valid, then it continues to be valid for ever (until
    # revoked?) and there is no information available regarding if a
    # course was actually taught a specific year

    # if startYm <= ym and ym <= endYm: # this is not what we want
    if ym <= endYm: # if the course plan became valid before the query
                    # period ended, the course plan was valid during
                    # the queried time
        pass
    else:
        continue
        
    goals = fields[20]
    elig = fields[13]
    sc = fields[14].replace('"', '') # new version has quotes, old does not
    level = fields[16].replace('"', '') # new version has quotes, old does not
#    title = {'sv':fields[5], 'en':fields[6]}
    credit = fields[7].replace('"', '') # new version has quotes, old does not

#    descr = fields[19]
#    exam = fields[22]
    misc = fields[26].lower()

    ctype = ""
    title = fields[5].lower()
    if "uppdragsutbildning" in title or "commissioned education" in fields[6]:
        ctype = "uppdragsutbildning"
    elif "uppdragsutbildning" in misc:
        ctype = "uppdragsutbildning"
    elif "vidareutbildning" in title or "vidareutbildning" in misc:
        ctype = "vidareutbildning"
    else:
        ctype = "grundutbildning"
    
    r = {
        "startdate":start, # used to determine which duplicate to use, should not be printed
    
        "University":"SU", # one of (Miun, UmU, SU, KTH)
        
        "CourseCode":cc,
        "ECTS-credits":credit,
        "ValidFrom":term,
        "ILO-sv":goals,
        "ILO-en":"",
        "SCB-ID":sc,

        "CourseLevel-ID":level,
        # one of (G1N, G1F, G1E, G2F, G2E, A1N, A1F, A1E, A2E, GXX, AXX)
         
        "Prerequisites-sv":elig,
        "Prerequisites-en":"",
        
        "CourseType":ctype
        # one of: (vidareutbildning/uppdragsutbildning/förberedande utbildning/grundutbildning/forskarutbildning)
    }
    
    # check for duplicates
    dup = 0
    for i in range(len(res)):
        if res[i]["CourseCode"] == r["CourseCode"]:
            if res[i]["startdate"] >= r["startdate"]:
                dup = 1
                break
            else:
                res[i] = r
                dup = 1
                break
    if not dup:
        res.append(r)

####################################################################
### Remove the 'startdate' field now that it is no longer needed ###
####################################################################
for c in res:
    if "startdate" in c:
        del c["startdate"]

############################
### Print JSON to stdout ###
############################
output = {"Course-list": res}
print(json.dumps(output))

