# Introduction

There are two classes in this package: *GetSyllabus* and *ResultsCreator*.

GetSyllabus downloads all syllabuses and creates "raw" data for each syllabus,
while ResultsCreator performs further classification according to the specifications.

**IMPORTANT!** To run any of the commands below, you need to be positioned in the base folder
(which also contains this README file and the folders `bin`, `data`, `lib` and `src`.)



# Compiling the programs

To compile the programs, the following command should be run (in this folder):

```javac -d bin -encoding UTF-8 -cp "lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar" src/KTHoriginal/*.java```

The binaries will appear in the `bin/KTHoriginal` folder.



# How to run GetSyllabus

To run GetSyllabus, the following base command should be used (in this folder):

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.GetSyllabus```

This is however not enough; you **must** use flags as well. All flags are found
by running the base command without any arguments or with the `-help` flag.

**EXAMPLE 1**: To create an output file called `raw_data.csv` containing
classification results for a specific course DA222X given in the spring of 2013 (2023:1) is:

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.GetSyllabus -cc DA222X -ct 2023:1 -o raw_data.csv```

Note that the `-o` flag is optional. If omitted, the default output file is `raw.csv`.

**EXAMPLE 2**: The following command classifies ALL (`-a`) syllabuses from courses given in the academec year 2022/2023 (2022:2 and 2023:1):

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.GetSyllabus -a -cy 2022:2 -o raw_data.csv```

Classifying all syllabuses will take some time (around 5-10 minutes) because all
syllabuses have to be downloaded from KTH and processed by WebbGranska.

**EXAMPLE 3**: The following command classifies ALL (`-a`) syllabuses from courses given in the fall semenster 2023 (2023:2):

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.GetSyllabus -a -ct 2023:2 -o raw_data.csv```

Olika debug-värden:

-d 25 matar ut särskild behörighet för EECS-kurser
-d 26 matar ut mål för exjobbskurser
-d 199 matar ut SBC-ämneskod
-d 10 > bad_ILOs.txt 
Sedan kan dåliga ILOs plockas bort med:
./filter_bad_ILOs bad_ILOs.txt

# How to run ResultsCreator

When you have an output CSV file from GetSyllabus, you can run ResultsCreator.

To run ResultsCreator, the following base command should be used (in this folder):

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.ResultsCreator```

You **must** also specify the input file name.

**EXAMPLE 1**: If the file created by GetSyllabus is called `raw_data.csv`
the command should be:

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.ResultsCreator raw_data.csv```

The results will be saved to the default output file (`results.csv`).

**EXAMPLE 2**: You can also specify the output file by adding a second argument. If the
input file is `raw_data.csv` and you want the output file to be `results_data.csv`
the command is:

```java -cp bin:lib/commons-lang3-3.5.jar:lib/jsoup-1.10.2.jar KTHoriginal.ResultsCreator raw_data.csv results_data.csv```


# Beskrivning av KTH:s kursplans-API

```https://api.kth.se/api/kopps/v1/```

I katalogen data ligger data-filer som läses av GetSyllabus.java

`course_subjects.csv`          Huvudområden för varje kurs 2019 (ingår tyvärr inte i KTH-API, inte uppdaterad)
`bloom_revised_all_words.txt`  Verb kategoriserade i nivåer enligt Blooms reviderade taxonomi
`bloom_tvetydiga.txt`	       Verb i bloom_revised_all_words.txt som ligger på flera nivåer
`swedish_trigrams.txt`         Vanligaste bokstavstrigrammen i svenska; används för språkidentifiering
`english_trigrams.txt`         Vanligaste bokstavstrigrammen i engelska; används för språkidentifiering
