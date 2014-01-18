from flask import Flask
from flask import url_for as local_url_for
from flask import redirect
from flask import render_template
from flask import g
from flask import __version__
from flask_s3 import FlaskS3
from flask_s3 import url_for
from os import listdir, walk, path
from os.path import isfile, join
from random import choice, shuffle
import urllib2
import csv
import re
from glob import glob
from time import strftime, gmtime
import datetime
from flask.ext.basicauth import BasicAuth


alltests_cache = dict()
GUESSNODIFF = "__guess_no_difference__"
NOSHOT = list()
    
def setup():
    app = Flask(__name__)
    app.jinja_env.globals.update(local_url_for=local_url_for)
    return app


app = setup()
app.config['S3_BUCKET_NAME'] = 'wikitoy'
app.config['BASIC_AUTH_USERNAME'] = 'infinite'
app.config['BASIC_AUTH_PASSWORD'] = 'jest'
app.config['BASIC_AUTH_FORCE'] = True
app.config['USE_S3_DEBUG'] = False

basic_auth = BasicAuth(app)
s3 = FlaskS3(app)

def real_value(value_slug, dirname):
    #given a short value, and the dirname (static/report/testname), look up the long description
    try:
        with open(join(dirname, 'val_lookup.csv'), 'r') as fin:
            reader = csv.reader(fin, delimiter=',')
            reader.next() #skip header
            lookup = dict(reader)
            return lookup[value_slug]
    except:
        return value_slug

def all_tests(batch):
    global alltests_cache
    if(batch not in alltests_cache):
        print 'alltests['+batch+"] is not cached. This should only happen once."
        if batch == 'chronological' or batch == 'reverse':  
            test_list = walk(join("static", "report")).next()[1]
            #walk gives (dirpath, dirnames, filenames). We only want dirnames, hence the [1]
            #metas = glob(join("static", "report", "*","meta.csv"))
            time_dict = dict()
            for testname in test_list:
                m = join("static", "report", testname, 'meta.csv')
                try:
                    with open(m, 'r') as fin:
                        reader = csv.DictReader(fin)
                        r = reader.next()
                        time = int(r['time'])
                        #avoid time collisions:
                        inserted_yet = False
                        while not inserted_yet:
                            if time in time_dict and time_dict[time] != testname:
                                time += 1
                            else:
                                #this is the money, right here. Insert the test into a dict where it's key is time of test, and value is testname
                                time_dict[time] = testname
                                inserted_yet = True        
                except:
                    pass

            sorted_timekey_list = sorted(time_dict)
            alltests_cache['chronological'] = list()
            for time in sorted_timekey_list:
                alltests_cache['chronological'].append(time_dict[time])
            #reverse sort
            sorted_timekey_list.sort(reverse=True)
            alltests_cache['reverse'] = list()
            for time in sorted_timekey_list:
                alltests_cache['reverse'].append(time_dict[time])
        
        elif batch == 'random':
            test_list = walk(join("static", "report")).next()[1]
            shuffle(test_list)
            alltests_cache[batch] = test_list
        
        elif batch == 'ascending' or batch == 'descending':
            metas = glob(join("static", "report", "*","meta.csv"))
            tests = dict()
            final_list = list()

            for m in metas:
                with open(m, 'r') as fin:
                    testname = m[14:-9]
                    #after static/report/ and before meta.csv"
                    reader = csv.DictReader(fin)
                    r = reader.next()
                    guess = float(r['bestguess'])
                    inserted_yet = False
                    while not inserted_yet:
                        if guess in tests and tests[guess] != testname:
                            guess += .001
                        else:
                            tests[guess] = testname
                            inserted_yet = True

            sorted_tests = sorted(tests)
            for guess in sorted_tests:
                final_list.append(tests[guess])

            ascending = final_list[:]
            final_list.reverse()
            descending = final_list[:]
            alltests_cache['descending'] = descending
            alltests_cache['ascending'] = ascending

        else:
            try:
                test_list = list()
                filename = join('static', 'order', batch+ '.txt')
                with open(filename, 'r') as fin:
                    for line in fin:
                        test_list.append(line.rstrip())

                alltests_cache[batch] = test_list
            except:
                print 'input order wrong'
                alltests_cache[batch] = list()

    return alltests_cache[batch]

    

def is_url(f_or_url):
    isurl = False
    if(f_or_url[0:4] == 'http'):
        isurl = True
    return isurl

def exists_and_is_url(file_or_url):
    #Given a url or file, try to fetch that item, and return if it exists or not
    is_a_url = is_url(file_or_url)
    def exists_url():
        #print "does" + file_or_url + "exist?"
        try:
            f = urllib2.urlopen(urllib2.Request(file_or_url))
            #print ('yes')
            return True
        except:
            #print('no')
            return False

    def exists_file():
        try:
            with open(file_or_url[1:]): #because of the weird way url_for works (it prefixes a forward slash to "static/...")
                return True
        except IOError:
                return False

    if(is_a_url):
        return exists_url(), True
    else:
        return exists_file(), False

def get_row(dirname):
    try:
        with open(join(dirname, 'meta.csv'), 'r') as fin:
            reader = csv.DictReader(fin, delimiter=',')
            row_dict = reader.next() #skip header
            return row_dict
    except:
        return None

def test_in_batch(thistest, batch):
    alltests = all_tests(batch)
    if thistest not in alltests:
        return False
    return True

def get_or_set_noshot_url():
        global NOSHOT
        if not NOSHOT:
            NOSHOT = url_for('static', filename='img/noshot.gif')
            exists, isurl = exists_and_is_url(NOSHOT)
            if(not exists):
                NOSHOT = local_url_for('static', filename='img/noshot.gif')
        return NOSHOT

def find_screenshots_and_names(lines, dirname):
    screenshots = {}
    longnames = {}
    #manytype: if there are multiple screenshots, is it multivariate or combo?
    manytype = "multivariate"
    #remember, 'line' = line in screenshots.csv
    for line in lines:
        varname = unicode(line[1])
        desc = real_value(varname, dirname)
        longnames[varname] = desc.decode('utf-8') #it would be best if we didn't need to do this, and trusted the R cruncher to deal with unicode on its own.
        thisshot = line[3]
        if line[1] in screenshots:
            if(thisshot != "NA"):
                if(thisshot not in screenshots[varname]):
                    screenshots[varname].append(thisshot)
                if(line[4] != "NA"):
                    manytype = "combo"
                    if(line[4] not in screenshots[varname]):
                        screenshots[varname].append(line[4])
                #screenshots[varname] = list(set(screenshots[varname]))
        else:
            if(thisshot != "NA"):
                screenshots[varname] = [thisshot]
                if(line[4] != "NA"):
                    manytype = "combo"
                    screenshots[varname].append(line[4])
            else:
                #screenshot missing
                screenshots[varname] = []
    
    NOSHOT = get_or_set_noshot_url()
    for val in screenshots:
        if screenshots[val] == []:
            screenshots[val].append(NOSHOT)

    return screenshots, longnames, manytype


def true_results(winrow, dirname):
        winner = winrow['winner']
        loser = winrow['loser']
        
        winner = real_value(winner, dirname).decode('utf-8') #delete the decoding after the next batch of decoding by R
        loser = real_value(loser, dirname).decode('utf-8') #delete the decoding after the next batch of decoding by R
        return winner, loser

### The real stuff

@app.route('/')
def welcome():
    #print 'welcome'
    return render_template('welcome.html')


@app.route('/dir/', defaults={'batch':"chronological"})
@app.route('/dir/<batch>')
def show_dir(batch):
    showthese = all_tests(batch)
    allshots = {}
    allnames = {}
    alldates = {}
    allresults = {}
    for test in showthese:
        dirname = join('static', 'report', test)
        with open( join(dirname, 'screenshots.csv'), 'r') as fin:
            reader = csv.reader(fin, delimiter=',')
            reader.next()
            lines = list(reader)
            screenshots, longnames, manytype = find_screenshots_and_names(lines, dirname)
            allshots[test] = screenshots
            allnames[test] = longnames
            winner_row = get_row(dirname)
            date = winner_row['time']
            date = gmtime(float(date))
            date = strftime("%a, %d %b %Y %H:%M:%S UTC", date)
            alldates[test] = date
            result = {}
            result['win_by'] = float(winner_row['bestguess'])
            result['lowerbound'] = float(winner_row['lowerbound'])
            result['upperbound'] = float(winner_row['upperbound'])
            result['dollar_pct'] = float(winner_row['dollarimprovementpct'])
            result['lower_dollar'] = float(winner_row['dollarlowerpct'])
            result['upper_dollar'] = float(winner_row['dollarupperpct'])
            result['winner'] = winner_row['winner']
            result['loser'] = winner_row['loser']
            allresults[test] = result

    return render_template('directory.html', batch=batch, list=showthese, allshots=allshots, allnames=allnames, alldates=alldates, allresults=allresults)


@app.route('/show/', defaults={'batch':"chronological", 'testname': None})
@app.route('/show/<batch>/', defaults={'testname': None})
@app.route('/show/<batch>/<testname>')
def go_test(batch, testname):
    def first_test():
        #Thanks to: http://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
        test_list = all_tests(batch)
        #assume all_tests() already sorts
        if not test_list:
            return 'error'
        else:
            result = test_list[0]
            return result
    
    def find_random_test():
        possibilities = all_tests(batch)
        randtest = choice(possibilities)
        return randtest
              
    if testname == 'error':
        return render_template('error.html', batch=batch, why="Ordering scheme: "+batch + " not found", title="Err..."), 404

    if testname is None:
        testname=first_test()

    if testname.lower() == 'random':
        testname=find_random_test()

    if testname.lower() == 'fin':
        return render_template('finished.html', batch=batch)

    if not test_in_batch(testname, batch):
        return render_template('error.html', why="Sorry, but this test doesn't exist in the " + batch + " ordering scheme", title="404'd!"), 404

    return show_winner(testname, batch)

def show_winner(testname, batch):
    def next_test(thistest, batch):
        #assume all_tests is already sorted, so we just need to find the next one.
        if not test_in_batch(thistest, batch):
            return "wrong batch"
        alltests = all_tests(batch)
        thisindex = alltests.index(thistest)
        nextindex = thisindex +1
        if(nextindex < len(alltests) ):
            next = alltests[nextindex]
        else:
            return None
        return next

    def prev_test(thistest, batch):
        #assume all_tests is already sorted, so we just need to find the next one.
        if not test_in_batch(thistest, batch):
            return "wrong batch"
        alltests = all_tests(batch)
        thisindex = alltests.index(thistest)
        previndex = thisindex -1
        if(previndex > 0):
            prev = alltests[previndex]
        else:
            return None
        return prev

    def is_confident(winrow):
        lowbound = winrow['lowerbound']
        if float(lowbound) < 0: #if there is no clear winner
            return False
        return True

    def get_tables(filename):
        try:
            tables = list()
            f = open(join(filename, 'reportA.html'), 'r')
            tables.append(f.read())
            f.close()
            f = open(join(filename,'reportB.html'), 'r')
            tables.append(f.read())
            f.close()
        except:
            try:
                f = open(filename + 'report.html', 'r')
                tables = f.read()
                f.close()
            except:
                tables = "notable"
        return tables

    def max_diagnostic_num(testname, diag_type):
        #returns the maximum X on the files called "diagnostic[X].jpeg"
        #assuming that there is no gap
        #return 0 if none exist
        STARTCHECK = 10
        MAXNUM = 30
        #start at i = STARTCHECK. See if there's a plot of the name diagnostic<i>.jpeg existing. 
        #   If not, decrement i until it does. (Stop below 1)
        #   If so, increment i until it doesn't (Stop at MAXNUM)
        #return i
        i = STARTCHECK
        direction = 'start'
        use_local = False
        while i > 0 & i < MAXNUM:
            if diag_type != "":
                filename = "_".join(['diagnostic', diag_type, str(i)])
            else:
                filename = "_".join(['diagnostic', str(i)])
            file_or_url_name = join('report', testname, filename+'.jpeg' )
            exists, isurl = exists_and_is_url(url_for('static', filename=file_or_url_name))
            #if it's not on the server, fallback to trying local file
            if(isurl and not exists):
                #print ('isurl and not exists')
                #print ('isurl = '+ str(isurl))
                #print ('exists = '+ str(exists))
                exists, isurl = exists_and_is_url(join('/static', file_or_url_name)) 
                if(exists):
                    use_local = True
                #the slash is needed to mimic the bad behavior of url_for

            if exists:
                print(file_or_url_name)
                if direction == 'decrement':
                    #print "returning " + str(i) + ","+str(use_local)
                    return i, use_local
                else:
                    i = i +1
                    direction = 'increment'
            else:
                if direction == 'increment':
                    #print "returning " + str(i) + ","+str(use_local)
                    return i, use_local
                else:
                    i = i - 1
                    direction = 'decrement'
        #print "returning " + str(i) + ","+str(use_local)
        return i, False

    def get_diagnostic_charts(directory):
        names = glob(directory + '/diagnostic_data*.html')
        toreturn = list()
        for name in names:
            f = open(name, 'r')
            toreturn.append(f.read())
            f.close()
        return toreturn

    def graph_local(testname, graphname):
        use_local = False
        file_or_url_name = join('report',testname, graphname)
        exists, isurl = exists_and_is_url(url_for('static', filename=file_or_url_name))
        #if it's not on the server, fallback to trying local file
        if(not exists & isurl):
            exists, isurl = exists_and_is_url(join('/static', file_or_url_name)) 
            use_local = True
        return use_local

    def get_info(dirname):
        infofile = "info.txt"
        try:
            with open(join(dirname, infofile), 'r') as fin:
                infotext = fin.read()
        except:
            #probably no such file
            infotext = ""
        return infotext


    if testname.lower() == 'milestone':
        nexttest = next_test(testname, batch)
        if nexttest is None:
            nexttest = "fin"
        return render_template('milestone.html', next=nexttest,batch=batch)

    dirname = join('static', 'report',testname)
    winner_row = get_row(dirname)

    if winner_row is None:
        return render_template('error.html', batch=batch,why="Incorrect Test Name", secret=winner_row)

    win_by = winner_row['bestguess']
    lowerbound = winner_row['lowerbound']
    upperbound = winner_row['upperbound']
    dollar_pct = float(winner_row['dollarimprovementpct'])
    lower_dollar = float(winner_row['dollarlowerpct'])
    upper_dollar = float(winner_row['dollarupperpct'])

    isconfidence = is_confident(winner_row)

    #If isconfidence is False, then there's no clear winner. If True, then there is.
    winner, loser = true_results(winner_row, dirname)
    
    tables = get_tables(dirname)
    
    def diagnostic_types(testname):
        return(["", "amount"])

    diag_types = diagnostic_types(testname)
    diag = {}
    for diag_type in diag_types:
        diagnostic_num, use_local_diag = max_diagnostic_num(testname, diag_type)
        diag[diag_type] = {'num':diagnostic_num, 'local':use_local_diag}
    diagnostic_charts = get_diagnostic_charts(dirname)

    graphname = 'pamplona.jpeg'
    force_local_graph = graph_local(testname, graphname)
    
    if not test_in_batch(testname, batch):
         return render_template('error.html', batch=batch, why="Ordering scheme: "+batch + " not found", title="Err..."), 404   
    
    nexttest = next_test(testname, batch)
    if nexttest is None:
        nexttest = "fin"
    prevtest = prev_test(testname, batch)
    
    #SCREENSHOTS
    try:
        with open(join(dirname, 'screenshots.csv'), 'r') as fin:
            reader = csv.reader(fin, delimiter=',')
            reader.next()
            lines = list(reader)
    except:
        return render_template('error.html', batch=batch, why="No such test: "+testname, title="404'd!"), 404
    #so "lines" = lines in screenshots.csv
    if(len(set(zip(*lines)[1])) != 2):
        #if there are not 2 variations
        return render_template('error.html', batch=batch, why="Wrong number of screenshots: "+testname, title="My bad."), 404

    screenshots, longnames, manytype = find_screenshots_and_names(lines, dirname)

    info = get_info(dirname)
    #print "rendering"
    #print('result.html graphname='+graphname+", guessedcorrectly="+str(guessedcorrectly)+", isconfidence=" + str(isconfidence)+", win_by=" + win_by+", atleast=" +lowerbound+", atmost=" +upperbound+", winner="+winner+", loser="+loser+", testname="+testname+", nexttest="+nexttest)
    #print "diagnostic_num="+str(diagnostic_num)+ ", force_local_diagnostic="+str(use_local_diag)+", force_local_graph="+str(force_local_graph)
    

    return render_template('result.html', batch=batch, graphname=graphname, isconfidence=isconfidence, win_by=win_by, atleast=lowerbound, 
        atmost=upperbound, winner=winner, loser=loser, testname=testname, nexttest=nexttest, prevtest=prevtest, tables=tables, 
        diagnostic_graphs=diag, diagnostic_charts=diagnostic_charts, 
        force_local_graph=force_local_graph, manytype=manytype, imgs=screenshots, longnames=longnames, 
        description=info, dollar_pct=dollar_pct, lower_dollar=lower_dollar, upper_dollar=upper_dollar)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', why="There's nothing here. Sorry! Your URL was probably mistyped etc.", title="404'd!"), 404
        
if __name__ == '__main__':
    app.run(debug=True)
    #app.run()