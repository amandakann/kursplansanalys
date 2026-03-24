import sys
import re
import requests
import xml.etree.ElementTree as XML
import html
import datetime
import json

import time

delaySeconds = 15
delayMinutes = 15

###############
### Logging ###
###############
logging = False

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


# Swedish example URL
# https://www.du.se/sv/utbildning/kurser/kursplan/?code=KG2003

# English example URL
# https://www.du.se/en/study-at-du/kurser/syllabus/?code=KG2003

def getOneCourse(cc):

    plan = {
        "Failed":0
    }

    for data in courseCodes[cc]:
        plan["CourseCode"] = cc
    
    urlSv = "https://www.du.se/sv/utbildning/kurser/kursplan/?code=" + cc.upper()
    urlEn = "https://www.du.se/en/study-at-du/kurser/syllabus/?code=" + cc.upper()
    
    logFlush()

    # Get Swedish course info

    url = urlSv

    if cc in oldData and "html-sv" in oldData[cc] and oldData[cc]["html-sv"] != "":
        print ("Already downloaded Swedish HTML", cc)
        plan["html-sv"] = oldData[cc]["html-sv"]
    else:
        print ("Download Swedish HTML", cc)
        triesSoFar = 0
        GiveUpAfterXTries = 5
        failed = 1
        while triesSoFar < GiveUpAfterXTries:
            triesSoFar += 1
            try:
                time.sleep(delaySeconds)
                r = requests.get(url)
                failed = 0
                break
            except Exception as e:
                log("Failed getting " + url + "\n")
                log(str(e))
                if triesSoFar < GiveUpAfterXTries:
                    time.sleep(60 * delayMinutes) # wait 15 minutes and see if the server replies

        if failed:
            log("Failed to get course info " + url + ", giving up.\n")
            plan["Failed"] = 1

        # log("goal status: ")
        # log(str(r.status_code))

        if (str(r.status_code) == "200"): # everything went fine
            plan["html-sv"] = r.text
        else:
            log("WARNING: Could not fetch '" + url + "'")
            plan["Failed"] = 1

        r.close()


    # Get English course info

    url = urlEn

    if cc in oldData and "html-en" in oldData[cc] and oldData[cc]["html-en"] != "":
        print ("Already downloaded English HTML", cc)
        plan["html-en"] = oldData[cc]["html-en"]
    else:
        print ("Download English HTML", cc)

        triesSoFar = 0
        GiveUpAfterXTries = 5
        failed = 1
        while triesSoFar < GiveUpAfterXTries:
            triesSoFar += 1
            try:
                time.sleep(delaySeconds)
                r = requests.get(url)
                failed = 0
                break
            except Exception as e:
                log("Failed getting " + url + "\n")
                log(str(e))
                if triesSoFar < GiveUpAfterXTries:
                    time.sleep(60 * delayMinutes) # wait 15 minutes and see if the server replies

        if failed:
            log("Failed to get course info " + url + ", giving up.\n")
            plan["Failed"] = 1
            
        # log("goal status: ")
        # log(str(r.status_code))

        if (str(r.status_code) == "200"): # everything went fine
            plan["html-en"] = r.text
        else:
            log("WARNING: Could not fetch '" + url + "'")
            plan["Failed"] = 1

        r.close()

    return plan


#########################################
### Read list of Course IDs from file ###
#########################################
noofCC = 0
noofDups = 0
longestDup = 0
courseCodes = {}
try:
    open("data/DalarnasUniversitetKurskoder.utf.csv").read()
except Exception as e:
    print ("Could not find file with course codes (data/DalarnasUniversitetKurskoder.utf.csv)")
    print (e)

f = open("data/DalarnasUniversitetKurskoder.utf.csv")
started = False
for line in f.readlines():
    if line[0:7] == "Kurskod":
        started = True
        continue
    if started and line.strip() != ";;;;;;":
        ll = line.strip()
        tok = []
        cur = ""
        inStr = 0
        for i in range(len(ll)):
            if ll[i] == "\"":
                if inStr:
                    inStr = 0
                else:
                    inStr = 1
            elif ll[i] == ";":
                if not inStr:
                    tok.append(cur)
                    cur = ""
            else:
                cur += ll[i]
        if cur != "":
            tok.append(cur)

        # tok = line.strip().split(";")

        if len(tok) > 6:
            cc = tok[0]
            name = tok[1]
            hp = tok[2]
            utbOmr = tok[3]
            utbOmrCode = tok[4]
            percentage = tok[5]
            startDate = tok[6]

            data = [cc, name, hp, utbOmr, utbOmrCode, percentage, startDate, "", "", ""]
            
            if cc in courseCodes:
                # print("Duplicate line for Course Code " + cc + ":")
                # print(courseCodes[cc])
                # print(data)
                noofDups += 1
                courseCodes[cc].append(data)
                if len(courseCodes[cc]) > longestDup:
                    longestDup = len(courseCodes[cc])
            else:
                courseCodes[cc] = [data]
                noofCC += 1
f.close()
print ("Saw ", noofCC, " course codes, with ", noofDups, " duplicates. Most duplicates of one CC: ", longestDup)

################################################
### Read two more lists with URLs from files ###
################################################
noofCCk = 0
noofCCf = 0
noofDupsk = 0
noofDupsf = 0
overlap = 0
both = 0
courseCodesf = {}
courseCodesk = {}
try:
    open("data/HDa.kurser.utf.csv").read()
except Exception as e:
    print ("Could not find file with course codes (data/HDa.kurser.utf.csv)")
    print (e)
try:
    open("data/HDa.forskarkurser.utf.csv").read()
except Exception as e:
    print ("Could not find file with course codes (data/HDa.forskarkurser.utf.csv)")
    print (e)

htmlFileExp = re.compile("(https:.*?code=(.{6,7}));(https.*?code=(.{6,7}));[0-9]", re.I)

f = open("data/HDa.kurser.utf.csv")
for line in f.readlines():
    m = htmlFileExp.search(line)
    if m:
        noofCCk += 1
        cc = m[2]
        if m[4] != cc:
            print ("This line has two different course codes for the same course? '" + line.trim() + "'")

        data = [cc, "", "", "", "", "", "", m[1], m[3], "gk"]

        if cc in courseCodesk:
            noofDupsk += 1
            print ("Duplicated line for course " + cc)
        else:
            courseCodesk[cc] = data
        
        if cc in courseCodes:
            overlap += 1
        if cc in courseCodesf:
            both += 1
            print ("Course " + cc + " is in both 'forskarkurser' and 'kurser'")
f.close()

f = open("data/HDa.forskarkurser.utf.csv")
for line in f.readlines():
    m = htmlFileExp.search(line)
    if m:
        noofCCf += 1
        cc = m[2]
        if m[4] != cc:
            print ("This line has two different course codes for the same course? '" + line.trim() + "'")

        data = [cc, "", "", "", "", "", "", m[1], m[3], "fk"]

        if cc in courseCodesf:
            noofDupsf += 1
            print ("Duplicated line for course " + cc)
        else:
            courseCodesf[cc] = data

        if cc in courseCodes:
            overlap += 1
        if cc in courseCodesk:
            both += 1
            print ("Course " + cc + " is in both 'forskarkurser' and 'kurser'")
f.close()

print ("URLs in 'kurser':", noofCCk, noofDupsk)
print ("URLs in 'forskarkurser':", noofCCf, noofDupsf)
print ("URLs in both: ", both)
print ("Total:", noofCCk + noofCCf - both, "overlap with other file:", overlap, "total new:", noofCCk + noofCCf - both - overlap)

onlyOld = 0
for cc in courseCodes:
    if cc not in courseCodesk and cc not in courseCodesf:
        onlyOld += 1
print ("Number of URLs only in old file:", onlyOld)


for cc in courseCodesk:
    if cc in courseCodes:
        courseCodes[cc][0][-3] = courseCodesk[cc][-3]
        courseCodes[cc][0][-2] = courseCodesk[cc][-2]
        # courseCodes[cc][-1] = courseCodesk[cc][-1]
    else:
        courseCodes[cc] = [courseCodesk[cc]]
for cc in courseCodesf:
    if cc in courseCodes:
        courseCodes[cc][0][-3] = courseCodesf[cc][-3]
        courseCodes[cc][0][-2] = courseCodesf[cc][-2]
        courseCodes[cc][0][-1] = courseCodesf[cc][-1]
    else:
        courseCodes[cc] = [courseCodesf[cc]]


noofCC = 0
for cc in courseCodes:
    noofCC += 1

###############################################
#### Load all previously downloaded plans  ####
###############################################
try:
    f = open(sys.argv[0] + ".tempData")
    oldData = json.load(f)
    f.close()
    oldCount = 0
    for cc in oldData:
        oldCount += 1
    print("Found", oldCount, "cached courses on local disk.")
except Exception as e:
    print ("Could not find file with old data. (" + sys.argv[0] + ".tempData)")
    print (e)
    oldData = {}

############################################
#### Get each course  ####
############################################
fetched = 0
finished = 0
for cc in courseCodes:
    # print("Course", cc)
    
    if cc in oldData:
        if not "Failed" in oldData[cc] or oldData[cc]["Failed"] == 1 or ((not "html-sv" in oldData[cc] or oldData[cc]["html-sv"] == "") and (not "html-en" in oldData[cc] or oldData[cc]["html-en"] == "")):
            pass
        else:
            # print ("Already finished with ", cc)
            finished += 1
            continue
    
    res = getOneCourse(cc)
    oldData[cc] = res

    fetched += 1
    finished += 1

    if fetched % 10 == 0:
        print("Fetched ", fetched, "courses now, total of", finished, "courses in data so far (out of", noofCC, " courses)")

        try:
            f = open(sys.argv[0] + ".tempData", "w")
            f.write(json.dumps(oldData))
            f.close()
        except Exception as e:
            print("Failed to save temporary data.")
            print(e)

try:
    f = open(sys.argv[0] + ".tempData", "w")
    f.write(json.dumps(oldData))
    f.close()
except Exception as e:
    print("Failed to save downloaded data.")
    print(e)

##############################
### Print result to stdout ###
##############################
output = []
for cc in oldData:    
    res = {}
    tmp = oldData[cc]
    
    if "html-sv" in tmp:
        res["html-sv"] = tmp["html-sv"]
    if "html-en" in tmp:
        res["html-en"] = tmp["html-en"]
    if "CourseCode" in tmp:
        res["CourseCode"] = tmp["CourseCode"]

    if cc in courseCodes and courseCodes[cc][0][2] != "":
        res["ECTS-credits"] = courseCodes[cc][0][2]
    if cc in courseCodes and courseCodes[cc][0][6] != "":
        res["ValidFrom"] = courseCodes[cc][0][6]

    if cc in courseCodesf:
        res["CourseType"] = "forskarutbildning"
    
    output.append(res)
output = {"Course-list": output}

try:
    f = open(sys.argv[0] + ".output", "w")
    f.write(json.dumps(output))
    f.close()
    print("Saved downloaded data in file: " + sys.argv[0] + ".output")
except Exception as e:
    print("Failed to save downloaded data.")
    print(e)

