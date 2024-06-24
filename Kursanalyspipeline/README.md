# Introduction

These are tools for analysing course descriptions, mainly extracting
Bloom verbs from the goals of the course description.

This is a collection of Python scripts named *step1_...*, *step2_...*,
etc. Step 1 is different depending on the source of the data (for
example, the SU data is expected to come in a CSV file while the KTH
data is expected to be available from an online API). The rest of the
steps are the same for all data sources.

# Running the scripts

The scripts are written for Python 3. Older versions of python may not work.

The scripts generally read data from the standard input and writes the
results to the standard output, so you can chain them together.

```python3 step1_KTH_fetch_from_API.py -cc DD2350 -cy 2023:2 | python3 step2_heuristics.py | python3 step3_PoS_and_spelling.py | python3 step4_Bloom_verbs.py | python3 step5_check_consistency.py```

It is also possible to do one step at a time, saving the data to files.

```python3 step1_KTH_fetch_from_API.py -cc DD2350 -cy 2023:2 > kth.DD2350.json```

```python3 step2_heuristics.py < kth.DD2350.json > kth.DD2350.heuristics.json```

```python3 step3_PoS_and_spelling.py -ns < kth.DD2350.heuristics.json > kth.DD2350.pos.json```

```python3 step4_Bloom_verbs.py < kth.DD2350.pos.json > kth.DD2350.bloom.json```

```python3 step5_check_consistency.py < kth.DD2350.bloom.json```

# Options

The scripts can output a short description of available options:

```python3 step1_KTH_fetch_from_API.py -h```


**Step 1**: Step one is different depending on the source data but
  typically allows a choice between all courses (`-a`), one specific
  course (`-cc <course code>`), or a few courses (`-ccs "<course
  code1> <course code2> ... "`). You can also specify the time period
  of interest with either `-ct <YEAR:TermNo>` (one semester) or `-cy
  <YEAR:TermNo>` (one year). The format is `YYYY:X`, where X is 1 for
  spring term and 2 for fall term, for example `2023:2` for the fall
  of 2023.

**Step 2**: Step two extracts the course objectives (learning goals)
  and can also try to update course level tags `GXX` and `AXX` to more
  detailed tags using the free text in the prerequisites field. The
  flags `-l` (update levels) and `-n` (do not update levels) can be
  used. If neither is specified, the default is to ignore the level
  information.

**Step 3**: Step three adds part-of-speech tags and phrase
  structure. This step uses an online API for part-of-speech tagging
  Swedish text, so it requires an Internet connection. The
  part-of-speech tagging can take quite a long time if there is a lot
  of text to tag, for example around 20 minutes for one year worth of
  courses.

**Step 4**: Step four needs a reference to a file with Bloom verbs and
  the levels for the Bloom verbs for Swedish, and another file for
  English. If no filenames are given, the files are assumed to be in a
  subfolder `data` with the names `data/bloom_revised_sv.txt` and
  `data/bloom_revised_en.txt`. This step can apply automatic spelling
  correction using an online API if the option `-s` is used. When
  using spelling correction, an Internet connection is required. The
  option `-z` can be used to write statistics and examples regarding
  verbs with no Bloom classification to a file.

**Step 5**: Step five collects statistics and checks for
  problems/inconsistencies in the data. It uses a config file
  `step5.config` (or use option `-c <filename>` to specify a different
  file) to specify what data to collect and what to print. For some
  options, the same data files with Bloom verb classifications used in
  Step 4 are used. The files to use for Bloom data can be specified
  with `-b <filename>` (Swedish) and `-be <filename>` (English). If
  not specified, `data/bloom_revised_sv.txt` and
  `data/bloom_revised_en.txt` will be used.

  The config file has one option per row and the options are commented
  with short explanations. For example `+printErrorTypeLists` means
  "do print (plus sign) a list of course codes for each error type"
  and `-printAmbiguousVerbs` means "do NOT (minus sign) print info on
  ambiguous verbs"

  Step 5 can read data from **more than one source**, for example if you
  want to compare data from multiple universities. You can specify
  input files with `-inp "<filename 1> <filename 2> ... "`. The script
  will also read data from stdin if there seem to be data there.

Some steps take a LOT of time. Downloading a lot of course information
from the KTH API in *Step 1* can take a long time. *Step 3* can take a
lot of time since contacting the Granska API server takes time and it
only accepts 100,000 bytes per request. Automatic spelling correction
in step 4 can take a few minutes but is much faster than
part-of-speech tagging.

# Data files

In the folder "data" you can find some data files used by the
scripts. These are the same files used by the KTH Java version for
analysing course information.

`bloom_revised_sv.txt`         Verbs (in Swedish) and their Bloom levels

`bloom_revised_en.txt`         Verbs (in English) and their Bloom levels

`swedish_trigrams.txt`         Character trigrams for Swedish; used for language identification

`english_trigrams.txt`         Character trigrams for English; used for language identification

`bloom_translations_sv_to_en.txt`         Rules for disambiguating Swedish verbs using English translations.

`UMU.credits.txt`              Course credit information for some courses missing this in the original data.

`stoplist.txt`         	       A list of verbs that should not be listed when listing verbs that did not receive a Bloom classification.

If you want to have a different classification of goals you can use
different files with verbs and give different levels to different
verbs. As long as the file keeps to the same format as the file above
and only verbs or expressions starting with a verb are used, it should
work with the scripts.
