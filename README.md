In this version of wiki-know, you guess before seeing the answer.

##Setup:
####To run this project, first do:
	pip install -r requirements.txt
    source venv/bin/activate
####Then do: 
    python hello.py



##Adding your own tests:
### This app relies on data being in a standard format in directories. 
### Here are the assumptions:
1. Each test is found in it's on directory in static/reports/
2. In each test's directory, there must be at least the following files (formatted correctly):
    + meta.csv
    + screenshots.csv
3. In each tests directory, there should be the following files (formatted correctly):
    + val_lookup.csv
    + description.txt
    + reportA.html
    + reportB.html
    + pamplona.png
4. In each tests directory there can be as many png files as you want.


###A. How to format *meta.csv*:
Currently, meta.csv has an inflexible format that doesn't leave much room for changes. This will change.

####Things that have no room for error:
1. meta.csv must be a 2-line csv file.
2. each row must have at least 10 fields
3. row[4] and row[5] must point to the name of the winner and loser, respectively
    + those names must be the same as the names in val_lookup and screenshots.csv
4. row[6] must have the naive percentage winning amount
5. row[8] and row[9] must detail the outer and lower bound of confidence, respectively 
####The model *meta.csv* has values that look like this:

    "test_id","var","country","language","winner","loser","bestguess","p","lowerbound","upperbound","totalimpressions","totaldonations"
    "1366565886","Banner.design","YY","yy","Key.phrase.in.blue","All.text.in.black",2.69,0.018,0.46,4.92,95076500,31750

###B. How to format *screenshots.csv*:
####Things that have no room for error:
1. screenshots.csv's top line is assumed to be column names and is ignored
2. each row must have at least 4 fields
3. row[3] must be a direct URL to the relevant screenshot image
4. row[1] must be the name of the value to be tested. This should be identical to "winner" or "loser" in meta.csv and 'value' in val_lookup.csv
####Assumptions:
1. fields 5 and 6 are for alternate screenshots. (currently not used)
2. There will be only 2 different values. (Multiples with the same name are fine).

####The model *screenshots.csv* might look like this:
    "test_id","value","campaign","screenshot","extra.screenshot.1","extra.screenshot.2","testname"
    "1366565886","Key.phrase.in.blue","C13_wpnd_enWW_FR","http://i.imgur.com/32wJUQD.png",NA,NA,"1366565886Banner.design"
    "1366565886","All.text.in.black","C13_wpnd_enWW_FR","http://i.imgur.com/QW0FDGU.png",NA,NA,"1366565886Banner.design"
###C. How to format *val_lookup.csv*
1. First row is skipped
2. Column A is the canonical internal name of the thing being tested. Should be the same as in screenshots.csv and as "winner" or "loser" in meta.csv
3. Column B is the text you want to display to the user as the name of the banner being tested.
####The model *val_lookup.csv* looks like this:
        "value","description"
        "Key.phrase.in.blue","Key phrase in blue"
        "All.text.in.black","All text in black"
###D. How to format *description.txt*
Write in plain text (html works too) the description of what's going on in the test. Users will see it.
###E. How to format *reportA.html*
1. ReportA.html should contain a table, and only a table.
2. It should have these classes: "table table-hover table-bordered"
3. reportA should include interesting data about the test
###F. How to format *reportB.html*
*see report A*
###G. What is pamplona.png?
It is the main chart you use to show your confidence in the test over time. It gets pride-of-the-place treatment in the report.
