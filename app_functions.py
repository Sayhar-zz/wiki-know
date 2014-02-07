#!/usr/bin/env python
#app_functions

#This defines the following functions called by hello.py:

#result_guess(testname, batch, guess)
#show_noguess(testname, batch)
#ask_guess(testname, batch)
#show_dir(batch, MODE)
#It relies on functions in app_helper.py

from flask import render_template
from os.path import join
import csv


class app_functions:
	def __init__(self, theapp, helper):
		self.app = theapp
		self.h = helper
		

	def result_guess(self, testname, batch, guess):
		#Show the result of the guess. Only in guess mode.
		#Used to be called show_winner
		winner_row, dirname = self.h.win_dir(testname)

		if winner_row is None:
			return render_template('error.html', batch=batch,why="Incorrect Test Name", secret=winner_row), 404

		if not self.h.test_in_batch(testname, batch):
			return render_template('error.html', batch=batch, why="Ordering scheme: "+batch + " not found", title="Err..."), 404

		stats = self.h.row_stats(winner_row)
		guessstats = self.h.guess_stats(winner_row, dirname, guess)
		tables = self.h.get_tables(dirname)
		#diagnostic_num, use_local_diag = max_diagnostic_num(testname)
		diagnostic_charts = self.h.get_diagnostic_charts(dirname)

		graphname = 'pamplona.jpeg'
		force_local_graph = self.h.graph_local(testname, graphname)
		nexttest = self.h.next_test(testname, batch)
		prevtest = self.h.prev_test(testname, batch)

		diag = self.h.get_diag_graphs(testname)
		
		return render_template('result_guess.html', batch=batch, graphname=graphname, 
			leancorrectly=guessstats['leancorrectly'], guessedcorrectly=guessstats['guessedcorrectly'], 
			isconfidence=guessstats['isconfidence'], win_by=stats['win_by'], atleast=stats['lowerbound'], 
			atmost=stats['upperbound'], winner=guessstats['winner'], loser=guessstats['loser'], testname=testname, 
			nexttest=nexttest, prevtest=prevtest, tables=tables, diagnostic_graphs=diag,
			diagnostic_charts=diagnostic_charts,  
			force_local_graph=force_local_graph, dollar_pct=stats['dollar_pct'], lower_dollar=stats['lower_dollar'], upper_dollar=stats['upper_dollar'])


	def ask_guess(self, testname, batch):
		#Ask the user to guess a winner
		#Only in guess mode
		winner_row, dirname = self.h.win_dir(testname)
		screenshotlines = self.h.screenshot_lines(dirname)
		if screenshotlines['error']:
			return render_template('error.html', batch=batch, why=screenshotlines['why'], title="404'd!"), 404
		else:
			screenshotlines = screenshotlines['lines']

		screenshots, longnames, manytype = self.h.find_screenshots_and_names(dirname, screenshotlines)
		stats = self.h.row_stats(winner_row)
		guessnone = self.h.get_guessnone()

		return render_template('guess.html', manytype=manytype, batch=batch, 
			testname=testname, imgs=screenshots, 
			longnames=longnames, guessnone=guessnone, date=stats['date'])


	def show_noguess(self, testname, batch):
		#Show the stats, screenshots, etc all in the same page
		winner_row, dirname = self.h.win_dir(testname)
		if winner_row is None:
			return render_template('error.html', batch=batch,why="Incorrect Test Name", secret=winner_row)

		if not self.h.test_in_batch(testname, batch):
			return render_template('error.html', batch=batch, why="Ordering scheme: "+batch + " not found", title="Err..."), 404   

		screenshotlines = self.h.screenshot_lines(dirname)
		if screenshotlines['error']:
			return render_template('error.html', batch=batch, why=screenshotlines['why'], title="404'd!"), 404
		else:
			screenshotlines = screenshotlines['lines']

		screenshots, longnames, manytype = self.h.find_screenshots_and_names(dirname, screenshotlines)	
		stats = self.h.row_stats(winner_row)
		guessstats = self.h.guess_stats(winner_row, dirname)
		tables = self.h.get_tables(dirname)
		#diagnostic_num, use_local_diag = max_diagnostic_num(testname)
		diagnostic_charts = self.h.get_diagnostic_charts(dirname)

		graphname = 'pamplona.jpeg'
		force_local_graph = self.h.graph_local(testname, graphname)
		nexttest = self.h.next_test(testname, batch)
		prevtest = self.h.prev_test(testname, batch)

		diag = self.h.get_diag_graphs(testname)
		

		return render_template('result_noguess.html', batch=batch, graphname=graphname, 
			isconfidence=guessstats['isconfidence'], win_by=stats['win_by'], atleast=stats['lowerbound'], 
			atmost=stats['upperbound'], winner=guessstats['winner'], loser=guessstats['loser'], 
			testname=testname, nexttest=nexttest, prevtest=prevtest, tables=tables, 
			diagnostic_graphs=diag,
			diagnostic_charts=diagnostic_charts, force_local_graph=force_local_graph, 
			manytype=manytype, imgs=screenshots, longnames=longnames, 
			dollar_pct=stats['dollar_pct'], lower_dollar=stats['lower_dollar'], 
			upper_dollar=stats['upper_dollar'])

	def show_dir(self, batch, MODE):
		#show dirname
		#Depending on the mode, do or don't display certain bits.
		showthese = self.h.all_tests(batch)
		allshots = {}
		allnames = {}
		alldates = {}
		allresults = {}
		allvarnames = {}
		for test in showthese:
			winner_row, dirname = self.h.win_dir(test)
			with open( join(dirname, 'screenshots.csv'), 'r') as fin:
				reader = csv.reader(fin, delimiter=',')
				reader.next()
				lines = list(reader)
				screenshots, longnames, manytype = self.h.find_screenshots_and_names(dirname, lines)
				allshots[test] = screenshots
				allnames[test] = longnames
				result = self.h.row_stats(winner_row)
				date = result['date']
				alldates[test] = date
				allvarnames[test] = result['variable']
				result['winner'] = winner_row['winner']
				result['loser'] = winner_row['loser']
				allresults[test] = result
		if MODE == "NOGUESS":
			template = "directory_noguess.html"
		else:
			template = "directory_guess.html"


		if self.app.debug:
			return render_template(template, mode=MODE, batch=batch, list=showthese, allshots=allshots, allnames=allnames, alldates=alldates, allresults=allresults, allvarnames=allvarnames)
		else:
			try:
				return render_template(template, mode=MODE, batch=batch, list=showthese, allshots=allshots, allnames=allnames, alldates=alldates, allresults=allresults, allvarnames=allvarnames)
			except:
				#One of the tests doesn't work and it's throwing everything off.
				return render_template('error.html', why="Sorry, there was a problem. At least one test has bad data. Sorry.", title="Oops"), 404

