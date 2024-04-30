import sys
import re
import datetime
import json
import codecs

CCs = {}
outputFile = ""
timeSpanExp = re.compile("[0-9][0-9][0-9][0-9]:[0-9]")

####################################
#### Get command line arguments ####
####################################
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
    elif (sys.argv[i] == "-o" and i + 1 < len(sys.argv)):
        haveOut = 1
        outputFile = sys.argv[i+1]

if (not haveCC and not haveCCall) or (haveCC and haveCCall):
    print ("\nParse TAB separated file (Excel->Save as->Unicode Text) and output course information as JSON\n")
    print ("usage options: <INPUT_FILE_NAME> [-cc <CODE>] [-a]")
    print ("Flags: -a                              Classify all courses.");
    print ("       -cc <CODE>                      Course code (six alphanumeric characters).");
    print ("       -ccs \"<CODE1> <CODE2> ....\"   Course code (six alphanumeric characters).");
#    print ("       -o <FILE_NAME>  Output file name (default is \"output.csv\").");
    print ("\nNote: One of -a OR -cc OR -ccs must be used.\n");
    sys.exit(0)


################################
#### Read file              ####
################################
f = open(sys.argv[1])
text = f.read()

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
    elif text[c] == ";" and not insideString:
        token = text[last:c]
        line.append(token.replace("\t", "\n"))
        last = c+1
    elif text[c] == "\n" and not insideString:
        token = text[last:c]
        line.append(token.replace("\t", "\n"))
        last = c+1
        lines.append(line)
        line = []
    c += 1

try:
    from html.parser import HTMLParser  # Python 3
except ModuleNotFoundError:
    from HTMLParser import HTMLParser  # Python 2
parser = HTMLParser()

capExp = re.compile("(\w\w[a-zåäö])([A-ZÅÄÖ][a-zåäö])")
hpExp =  re.compile("(\shp)([A-ZÅÄÖ])")
res = []
for lineno in range(1, len(lines)):
    fields = lines[lineno]

    cc = fields[0].strip()

    # if we are to use only one CC, skip the other courses
    if haveCC and not cc in CCs:
        continue

    titleSv = fields[1]
    # titleEn = fields[2]

    goals = fields[3].strip()
    try:
        tmp = parser.unescape(goals)
        goals = tmp
    except:
        pass
    m = capExp.search(goals) 
    goals = capExp.sub("\\1 \\2", goals).replace("ava Script", "avaScript")
    goals = hpExp.sub("\\1 \\2", goals)
    
    sc = fields[4].replace('"', '').strip()

    level = fields[5].strip()
    if level.lower() == "grund":
        level = "GXX"
    if level.lower() == "avancerad":
        level = "AXX"
        
    # undervForm = fields[6] # in person, remote, 
    term = fields[7].replace('"', '').strip()

    ctype = ""
    if "baskurs" in titleSv or level == "":
        ctype = "förberedande utbildning"
    else:
        ctype = "grundutbildning"
        
    elig = ""
    credit = ""
    
    r = {
        "University":"UMU", # one of (Miun, UmU, SU, KTH)
        
        "CourseCode":cc,
        "ECTS-credits":credit,
        "ValidFrom":term,
        "ILO-sv":goals,
        "ILO-en":"",
        "SCB-ID":sc,

        "CourseLevel-ID":level,

        "Prerequisites-sv":elig,
        "Prerequisites-en":"",
        
        "CourseType":ctype
        # one of: (vidareutbildning/uppdragsutbildning/förberedande utbildning/grundutbildning/forskarutbildning)
    }

    if term != "2024:1" and term != "2023:2":
        print ("WARNING: ", fields)
        for f in range(len(fields)):
            print (f, fields[f])
    
    # check for duplicates
    dup = 0
    for i in range(len(res)):
        if res[i]["CourseCode"] == r["CourseCode"]:
            dup = 1
            break
    if not dup:
        res.append(r)

############################
### Print JSON to stdout ###
############################
output = {"Course-list": res}
print(json.dumps(output))
