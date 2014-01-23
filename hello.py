from flask import Flask
from flask import url_for as local_url_for
from flask import render_template
#from flask import redirect
#from flask import g
#from flask import __version__
from flask_s3 import FlaskS3
from flask.ext.basicauth import BasicAuth
import json
#NOTE!  We have a couple import statements lower down as well.

MODES = ["GUESS", "NOGUESS"]
MODE = MODES[1]

def setup():
    app = Flask(__name__)
    app.jinja_env.globals.update(local_url_for=local_url_for)
    return app

app = setup()

try:
    config = json.load(open('config.json'))
    app.config['S3_BUCKET_NAME'] = config['bucketname']
    app.config['BASIC_AUTH_USERNAME'] = config['basicauth_name']
    app.config['BASIC_AUTH_PASSWORD'] = config['basicauth_password']
    if 'mode' in config:
        MODE = config['mode']
    app.config['BASIC_AUTH_FORCE'] = True
    basic_auth = BasicAuth(app)
    app.config['USE_S3_DEBUG'] = False
    s3 = FlaskS3(app)
except:
    s3 = False

def is_s3():
    return s3

import app_functions as f
import app_helper as h

### The real stuff

@app.route('/')
def welcome():
    #print 'welcome'
    return render_template('welcome.html')


@app.route('/dir/', defaults={'batch':"chronological"})
@app.route('/dir/<batch>')
def go_dir(batch):
    if MODE in MODES:
        return f.show_dir(batch, MODE)
    else: 
        return render_template('error.html', why="Sorry, but mode " + MODE + " doesn't exist.", title="404'd!"), 404

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', why="There's nothing here. Sorry! Your URL was probably mistyped etc.", title="404'd!"), 404


@app.route('/show/', defaults={'batch':"chronological", 'testname': None})
@app.route('/show/<batch>/', defaults={'testname': None})
@app.route('/show/<batch>/<testname>')
def go_test(batch, testname):
              
    if testname == 'error':
        return render_template('error.html', batch=batch, why="Ordering scheme: "+batch + " not found", title="Err..."), 404

    if testname is None:
        testname=h.first_test(batch)

    if testname.lower() == 'random':
        testname=h.find_random_test(batch)

    if testname.lower() == 'fin':
        return render_template('finished.html', batch=batch)

    if not h.test_in_batch(testname, batch):
        return render_template('error.html', why="Sorry, but this test doesn't exist in the " + batch + " ordering scheme", title="404'd!"), 404

    if MODE == "GUESS":
        return f.ask_guess(testname, batch)
    elif MODE == "NOGUESS":
        return f.show_noguess(testname, batch)
    else: 
        return render_template('error.html', why="Sorry, but mode " + MODE + " doesn't exist.", title="404'd!"), 404


@app.route('/show/<batch>/<testname>/result/<guess>')
def go_result(batch, testname, guess):
    if not h.test_in_batch(testname, batch):
        return render_template('error.html', why="Sorry, but this test doesn't exist in the " + batch + " ordering scheme", title="404'd!"), 404

    if MODE == "GUESS":
        return f.result_guess(testname, batch, guess)
    elif MODE == "NOGUESS":
        return f.show_noguess(testname, batch)
    else: 
        return render_template('error.html', why="Sorry, but mode " + MODE + " doesn't exist.", title="404'd!"), 404
        
if __name__ == '__main__':
    app.run(debug=True)
    #app.run()



#We call these functions:
#result_guess(testname, batch, guess)
#ask_guess(testname, batch)
#show_noguess(testname, batch)
#show_dir(batch, MODE)
