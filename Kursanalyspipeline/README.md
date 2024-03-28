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

```python3 step1_KTH_fetch_from_API.py -cc ED2246 -cy 2023:2 | python3 step2_heuristics.py | python3 step3_PoS_and_spelling.py -ns | python3 step4_Bloom_verbs.py data/bloom_revised_all_words.txt | python3 step5_check_consistency.py -a -b data/bloom_revised_all_words.txt```

It is also possible to do one step at a time, saving the data to files.

```python3 step1_KTH_fetch_from_API.py -cc ED2246 -cy 2023:2 > kth.ED2246.json```

```python3 step2_heuristics.py < kth.ED2246.json > kth.ED2246.heuristics.json```

```python3 step3_PoS_and_spelling.py -ns < kth.ED2246.heuristics.json > kth.ED2246.pos.json```

```python3 step4_Bloom_verbs.py data/bloom_revised_all_words.txt < kth.ED2246.pos.json > kth.ED2246.bloom.json```

```python3 step5_check_consistency.py -a -b data/bloom_revised_all_words.txt < kth.ED2246.bloom.json```

# Options

The scripts can output a short description of available options:

```python3 step1_KTH_fetch_from_API.py -h```


**Step 1**: Step one is different depending on the source data but
  typically allows a choice between all courses (`-a`) or one specific
  course (`-cc <course code>`). You can also specify the time period
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

**Step 3**: Step three adds part-of-speech tags and can also correct
  spelling errors at the same time. The options `-s` (correct spelling
  errors) and `-ns` (ignore spelling errors) can be used. The default
  behavior is to ignore spelling errors.

**Step 4**: Step four needs a reference to a file with Bloom verbs and
  the levels for the Bloom verbs, but takes no other options.

**Step 5**: Step five currently checks the data for inconsistencies
  and ambiguities. The following flags can be used: `-ilo` (check that
  the ILO information is there and contains Bloom verbs), `-en` (check
  if goals are available in English), `-lev` (check for courses with
  GXX or AXX as course level), `-SCB` (check that the SCB information
  is present), `-b <Bloom verb file>` (check for ambiguous Bloom
  verbs).

Some steps take a LOT of time. Downloading a lot of course information
from the KTH API in *Step 1* can take a long time. *Step 3* can take a
lot of time since contacting the Granska API server takes time. The
other steps are typically fast.

# Data files

In the folder "data" you can find some data files used by the
scripts. These are the same files used by the KTH Java version for
analysing course information.

`bloom_revised_all_words.txt`  Verbs (in Swedish) and their Bloom levels

`swedish_trigrams.txt`         Character trigrams for Swedish; used for language identification

`english_trigrams.txt`         Character trigrams for English; used for language identification

If you want to have a different classification of goals you can use a
different file with verbs and give different levels to different
verbs. As long as the file keeps to the same format as the file above
and only verbs or expressions starting with a verb are used, it should
work with the scripts.