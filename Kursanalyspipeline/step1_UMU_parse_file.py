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

#####################################
#### Read extra file with credits ###
#####################################
creditLex = {}
creditsInLex = 0
creditsFound = 0
creditsMissed = 0
try:
    for line in open("data/UMU.credits.txt").readlines():
        tokens = line.strip().split()
        if len(tokens) > 2:
            cc = tokens[-1]
            creds = tokens[-2]

            creditLex[cc] = creds
            creditsInLex += 1
except:
    pass
            
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

scbTable = {
    "Administration och förvaltning":"AF1",
    "Allmän språkvetenskap/lingvistik":"AL1",
    "Antikens kultur":"AK1",
    "Arabiska":"AR1",
    "Arameiska/syriska":"AS1",
    "Arbetsvetenskap och ergonomi":"AE1",
    "Arkeologi":"AR2",
    "Arkitektur":"AR3",
    "Arkivvetenskap":"AV1",
    "Automatiseringsteknik":"AT1",
    "Barn- och ungdomsstudier":"BU2",
    "Berg- och mineralteknik":"BM1",
    "Biblioteks- och informationsvetenskap":"BV1",
    "Biologi":"BI1",
    "Biomedicinsk laboratorievetenskap":"BL1",
    "Bioteknik":"BT1",
    "Bosniska/kroatiska/serbiska":"BK1",
    "Bulgariska":"BU1",
    "Byggteknik":"BY1",
    "Cirkus":"CI1",
    "Dans":"DA2",
    "Dans- och teatervetenskap":"DT2",
    "Danska":"DA1",
    "Datateknik":"DT1",
    "Design":"DE1",
    "Djuromvårdnad":"DJ1",
    "Ekonomisk historia":"EH1",
    "Elektronik":"EL1",
    "Elektroteknik":"ET2",
    "Energiteknik":"EN2",
    "Engelska":"EN1",
    "Estetik":"ES2",
    "Estniska":"ES1",
    "Etnologi":"ET1",
    "Farkostteknik":"FT1",
    "Farmaci":"FC1",
    "Farmakologi":"FK1",
    "Film":"FM1",
    "Filmvetenskap":"FV1",
    "Filosofi":"FI2",
    "Finska":"FI1",
    "Fiske och vattenbruk":"FV2",
    "Flerspråkigt inriktade ämnen":"FL1",
    "Folkhälsovetenskap":"FH1",
    "Franska":"FR1",
    "Freds- och utvecklingsstudier":"FU1",
    "Fri konst":"FK2",
    "Friskvård":"FV3",
    "Fysik":"FY1",
    "Fysisk planering":"FP1",
    "Företagsekonomi":"FE1",
    "Författande":"FF1",
    "Genusstudier":"GS1",
    "Geografisk informationsteknik och lantmäteri":"GI1",
    "Geovetenskap och naturgeografi":"GN1",
    "Grekiska":"GR1",
    "Handikappvetenskap":"HV1",
    "Hebreiska":"HE1",
    "Hindi":"HI1",
    "Historia":"HI2",
    "Husdjursvetenskap":"HD1",
    "Hälso- och sjukvårdsutveckling":"HS1",
    "Idé- och lärdomshistoria/Idéhistoria":"IL1",
    "Idrott/idrottsvetenskap":"ID1",
    "Indologi och sanskrit":"IS1",
    "Indonesiska":"IN1",
    "Industriell ekonomi och organisation":"IE1",
    "Informatik/Data- och systemvetenskap":"IF1",
    "Italienska":"IT1",
    "Japanska":"JA1",
    "Journalistik":"JO1",
    "Juridik och rättsvetenskap":"JU1",
    "Kemi":"KE1",
    "Kemiteknik":"KT1",
    "Kinesiska":"KI1",
    "Konsthantverk":"KH1",
    "Konstvetenskap":"KV1",
    "Koreanska":"KO1",
    "Koreografi":"KO2",
    "Krigsvetenskap":"KV3",
    "Kriminologi":"KR1",
    "Kultur- och samhällsgeografi":"KS1",
    "Kulturvetenskap":"KV2",
    "Kulturvård":"KU2",
    "Kurdiska":"KU1",
    "Landskapsarkitektur":"LA2",
    "Lantbruksvetenskap":"LV2",
    "Latin":"LA1",
    "Ledarskap, organisation och styrning":"LO1",
    "Lettiska":"LE1",
    "Litauiska":"LI1",
    "Litteraturvetenskap":"LV1",
    "Livsmedelsvetenskap":"LM1",
    "Luftfart":"LF1",
    "Länderkunskap/länderstudier":"LL1",
    "Maskinteknik":"MT1",
    "Matematik":"MA1",
    "Matematisk statistik":"MS1",
    "Materialteknik":"MA2",
    "Medicin":"ME1",
    "Medicinsk biologi":"MB1",
    "Medicinska tekniker":"MT2",
    "Medie- o kommunikationsvetenskap":"MK1",
    "Medie- och kommunikationsvetenskap":"MK1",
    "Medieproduktion":"MP1",
    "Miljövetenskap":"MV1",
    "Miljövård och miljöskydd":"MM1",
    "Musik":"MU1",
    "Musikdramatisk scenframställning och gestaltning":"MC1",
    "Musikvetenskap":"MV2",
    "Måltids- och  hushållskunskap":"MH1",
    "Måltids- och hushållskunskap":"MH1",
    "Mänskliga rättigheter":"MR1",
    "Nationalekonomi":"NA1",
    "Nederländska":"NE1",
    "Nutrition":"NU1",
    "Nygrekiska":"NG1",
    "Odontologi":"OD1",
    "Omvårdnad/omvårdnadsvetenskap":"OM1",
    "Pedagogik":"PE1",
    "Persiska":"PR1",
    "Polska":"PO1",
    "Portugisiska":"PU1",
    "Psykologi":"PS1",
    "Psykoterapi":"PY1",
    "Regi":"RE1",
    "Religionsvetenskap":"RV1",
    "Retorik":"RO1",
    "Rumänska":"RU1",
    "Rymdteknik":"RY2",
    "Ryska":"RY1",
    "Samhällsbyggnadsteknik":"SB1",
    "Samhällskunskap":"SH1",
    "Samiska":"SA1",
    "Scen och medier":"SM1",
    "Sjöfart":"SJ1",
    "Skogsvetenskap":"SK1",
    "Socialantropologi":"SO2",
    "Socialt arbete och social omsorg":"SS2",
    "Sociologi":"SO1",
    "Spanska":"SP1",
    "Statistik":"ST1",
    "Statsvetenskap":"ST2",
    "Studie- och yrkesvägledning":"SY1",
    "Swahili":"SW1",
    "Svenska som andraspråk":"SS1",
    "Svenska/Nordiska Språk":"SV1",
    "Tamil":"TA1",
    "Tandteknik och oral hälsa":"TO1",
    "Teckenspråk":"TE1",
    "Teknik i samhällsperspektiv":"TS1",
    "Teknisk fysik":"TF1",
    "Teologi":"TL1",
    "Terapi, rehabilitering och kostbehandling":"TR1",
    "Textilteknologi":"TX1",
    "Thai":"TH1",
    "Tibetanska":"TI1",
    "Tjeckiska":"TJ1",
    "Trädgårdsvetenskap":"TV1",
    "Träfysik och träteknologi":"TT1",
    "Turism- och fritidsvetenskap":"TU1",
    "Tyska":"TY1",
    "Ungerska":"UN1",
    "Utbildningsvetenskap praktisk-estetiska ämnen":"UV3",
    "Utbildningsvetenskap teoretiska ämnen":"UV2",
    "Utbildningsvetenskap/didaktik allmänt":"UV1",
    "Veterinärmedicin":"VE1",
    "Väg- och vattenbyggnad":"VV1",
    "Översättning och tolkning":"TO2",
    "Övriga språk":"SP2",
    "Övriga tekniska ämnen":"TE9",
    "Övriga tvärvetenskapliga studier":"TV9",
    "Övrigt inom beteendevetenskap":"BE9",
    "Övrigt inom ekonomi och administration":"EK9",
    "Övrigt inom historisk-filosofiska ämnen":"HF9",
    "Övrigt inom konst":"KO9",
    "Övrigt inom medicin":"ME9",
    "Övrigt inom naturvetenskap":"NA9",
    "Övrigt inom omvårdnad":"OM9",
    "Övrigt inom samhällsvetenskap":"SA9",
    "Övrigt inom teater, film och dans":"TF9",
    "Övrigt inom transportsektorn":"TP9",
    "Övrigt journalistik, kommunikation, information":"JK9"
}

### Also add same string in lower case, because case is wrong sometimes
scbTable2 = {}
for k in scbTable:
    scbTable2[k] = scbTable[k]
    scbTable2[k.lower()] = scbTable[k]

    scbTable2[k[:37]] = scbTable[k]
    scbTable2[k[:37].lower()] = scbTable[k]

scbTable = scbTable2

logF = open(sys.argv[0] + ".log", "w")

def lookupSCB(s):
    if s in scbTable:
        return scbTable[s]
    elif s.lower() in scbTable:
        return scbTable[s.lower()]
    elif s[-3:] == "...":
        ss = s[:-3]
        if ss in scbTable:
            return scbTable[ss]
        elif ss.lower() in scbTable:
            return scbTable[ss.lower()]
    logF.write(s)
    logF.write("\n")
    return s

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
    
    sc = lookupSCB(fields[4].replace('"', '').strip())

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
    if cc in creditLex:
        credit = creditLex[cc]
        creditsFound += 1
    else:
        creditsMissed += 1
    
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
logF.write("Credits in file {:0}\nCredits score used {:1}\nCredits not found {:2}\n".format(creditsInLex, creditsFound, creditsMissed))
