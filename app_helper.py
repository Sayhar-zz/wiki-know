#!/usr/bin/env python
import csv
from os.path import isfile, join
from os import walk
import urllib2
from random import choice, shuffle
from glob import glob
from time import strftime, gmtime
import re

#app_helper.py
#called by app_functions.py and hello.py

GUESSNODIFF = "__guess_no_difference__"

class app_helper:
	def __init__(self, theapp, s3):
		self.app = theapp
		self.alltests_cache = dict()
		self.NOSHOT = list()
		if s3:
			import flask_s3
			self.url_for = flask_s3.url_for
		else:
			import flask
			self.url_for = flask.url_for


	#PUBLIC FACING:
	def get_guessnone(self):
		return GUESSNODIFF

	def win_dir(self, testname):
		#Given a testname, return a winner row and a dirname
		dirname = join('static', 'report',testname)
		winner_row = self._get_row(dirname)
		return winner_row, dirname


	def row_stats(self, winner_row):
		d = dict()
		d['win_by'] = float(winner_row['bestguess'])
		d['lowerbound'] = float(winner_row['lowerbound'])
		d['upperbound'] = float(winner_row['upperbound'])
		try:
			d['dollar_pct'] = float(winner_row['dollarimprovementpct'])
			d['lower_dollar'] = float(winner_row['dollarlowerpct'])
			d['upper_dollar'] = float(winner_row['dollarupperpct'])
		except:
			d['dollar_pct'] = "Not calculated"
			d['lower_dollar'] = "Not calculated"
			d['upper_dollar'] = "Not calculated"
		date = winner_row['time']
		date = gmtime(float(date))
		d['date'] = strftime("%a, %d %b %Y %H:%M:%S UTC", date)
		return(d)


	def guess_stats(self, winner_row, dirname, guess=None):
		d = dict()
		isconfidence = self._is_confident(winner_row)
		d['isconfidence'] = isconfidence
		d['guessedcorrectly'], d['leancorrectly'], d['winner'], d['loser'] = self._true_results(winner_row, dirname, isconfidence, guess)
		return(d)


	def get_tables(self, filename):
		try:
			tables = list()
			f = open(join(filename, 'reportA.html'), 'r')
			tables.append(f.read())
			f.close()
			f = open(join(filename,'reportB.html'), 'r')
			tables.append(f.read())
			f.close()
			f = open(join(filename,'reportD.html'), 'r')
			tables.append(f.read())
			f.close()
			f = open(join(filename,'reportE.html'), 'r')
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

	def graph_local(self, testname, graphname):
		use_local = False
		file_or_url_name = join('report',testname, graphname)
		exists, isurl = self._exists_and_is_url(self.url_for('static', filename=file_or_url_name))
		#if it's not on the server, fallback to trying local file
		if(not exists & isurl):
			use_local = True
		return use_local

	def get_diag_graphs(self, testname):
		diag_types = self._diagnostic_types(testname)
		diag = {}
		for diag_type in diag_types:
			diagnostic_num, use_local_diag = self._max_diagnostic_num(testname, diag_type)
			diag[diag_type] = {'num':diagnostic_num, 'local':use_local_diag}
		return diag



	def get_diagnostic_charts(self, directory):
		names = glob(directory + '/diagnostic_data*.html')
		toreturn = list()
		for name in names:
			f = open(name, 'r')
			toreturn.append(f.read())
			f.close()
		return toreturn


	def next_test(self, thistest, batch):
		#assume all_tests is already sorted, so we just need to find the next one.
		if not self.test_in_batch(thistest, batch):
			return "wrong batch"
		alltests = self.all_tests(batch)
		thisindex = alltests.index(thistest)
		nextindex = thisindex +1
		if(nextindex < len(alltests) ):
			next = alltests[nextindex]
		else:
			#return None
			next = "fin"
		return next

	def prev_test(self, thistest, batch):
		#assume all_tests is already sorted, so we just need to find the next one.
		if not self.test_in_batch(thistest, batch):
			return "wrong batch"
		alltests = self.all_tests(batch)
		thisindex = alltests.index(thistest)
		previndex = thisindex -1
		if(previndex > 0):
			prev = alltests[previndex]
		else:
			return None
		return prev

	def screenshot_lines(self, dirname):
		try:
			with open(join(dirname, 'screenshots.csv'), 'r') as fin:
				reader = csv.reader(fin, delimiter=',')
				reader.next()
				lines = list(reader)
		except:
			return list(error=True, why="No such test: "+testname)

		#so "lines" = lines in screenshots.csv

		if(len(set(zip(*lines)[1])) != 2):
			#if there are not 2 variations
			return dict(error=True, why="Wrong number of screenshots: "+testname)

		return dict(error=False, lines=lines)



	def find_screenshots_and_names(self, dirname, lines):
		screenshots = {}
		longnames = {}
		#manytype: if there are multiple screenshots, is it multivariate or combo?
		manytype = "multivariate"
		#remember, 'line' = line in screenshots.csv

		for line in lines:
			varname = unicode(line[1])
			desc = self._real_value(varname, dirname)
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

		self.NOSHOT = self._get_or_set_noshot_url()
		for val in screenshots:
			if screenshots[val] == []:
				screenshots[val].append(self.NOSHOT)

		return screenshots, longnames, manytype




	def all_tests(self, batch):
		if(batch not in self.alltests_cache):
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
				self.alltests_cache['chronological'] = list()
				for time in sorted_timekey_list:
					self.alltests_cache['chronological'].append(time_dict[time])
				#reverse sort
				sorted_timekey_list.sort(reverse=True)
				self.alltests_cache['reverse'] = list()
				for time in sorted_timekey_list:
					self.alltests_cache['reverse'].append(time_dict[time])

			elif batch == 'random':
				test_list = walk(join("static", "report")).next()[1]
				shuffle(test_list)
				self.alltests_cache[batch] = test_list

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
				self.alltests_cache['descending'] = descending
				self.alltests_cache['ascending'] = ascending
			
			elif batch == 'english' or batch == 'foreign':
				english_test_list = list()
				foreign_gibberish = list()
				chron = self.all_tests("chronological")


				for testname in chron:
					m = join("static", "report", testname, 'meta.csv')
					try:
						with open(m, 'r') as fin:
							reader = csv.DictReader(fin)
							r = reader.next()
							lang = r['language'].lower()
							if lang == 'yy' or lang == 'en':
								english_test_list.append(testname)
							else:
								foreign_gibberish.append(testname)
					except:
						pass

				self.alltests_cache['english'] = english_test_list
				self.alltests_cache['foreign'] = foreign_gibberish			
			
			else:
				try:
					test_list = list()
					filename = join('static', 'order', batch+ '.txt')
					with open(filename, 'r') as fin:
						for line in fin:
							test_list.append(line.rstrip())

					self.alltests_cache[batch] = test_list
				except:
					print 'input order wrong'
					sealltests_cache[batch] = list()

		return self.alltests_cache[batch]

	def test_in_batch(self, thistest, batch):
		alltests = self.all_tests(batch)
		if thistest not in alltests:
			return False
		return True




	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#Called by hello.py


	def first_test(self, batch):
		#Thanks to: http://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
		test_list = self.all_tests(batch)
		#assume all_tests() already sorts
		if not test_list:
			return 'error'
		else:
			result = test_list[0]
			return result


	def find_random_test(self, batch):
		possibilities = self.all_tests(batch)
		randtest = choice(possibilities)
		return randtest


	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############

	#PRIVATE:

	def _is_confident(self, winrow):
		lowbound = winrow['lowerbound']
		if float(lowbound) < 0: #if there is no clear winner
			return False
		return True

	def _get_row(self, dirname):
		try:
			with open(join(dirname, 'meta.csv'), 'r') as fin:
				reader = csv.DictReader(fin, delimiter=',')
				row_dict = reader.next() #skip header
				return row_dict
		except:
			return None



	def _true_results(self, winrow, dirname, isconfidence, guess=None):
		winner = winrow['winner']
		loser = winrow['loser']
		guessedcorrectly = False
		leancorrectly = False
		if guess is not None:
			if not isconfidence:
				if guess == GUESSNODIFF:
					guessedcorrectly = True
			else: #if there is a clear winner
				if(guess.lower() == winner.lower()):
					guessedcorrectly = True
			if guess.lower() == winner.lower():
				leancorrectly = True
		else:
			guessedcorrectly = None
			leancorrectly = None

		winner = self._real_value(winner, dirname).decode('utf-8') #delete the decoding after the next batch of decoding by R
		loser = self._real_value(loser, dirname).decode('utf-8') #delete the decoding after the next batch of decoding by R
		return guessedcorrectly, leancorrectly, winner, loser

	def _is_url(self, f_or_url):
		isurl = False
		if(f_or_url[0:4] == 'http'):
			isurl = True
		return isurl

	def _exists_url(self, file_or_url):
		#print "does" + file_or_url + "exist?"
		try:
			f = urllib2.urlopen(urllib2.Request(file_or_url))
			#print ('yes')
			return True
		except:
			#print('no')
			return False

	def _exists_file(self, file_or_url):
		try:
			with open(file_or_url[1:]): #because of the weird way self.url_for works (it prefixes a forward slash to "static/...")
				return True
		except IOError:
				return False

	def _exists_and_is_url(self, file_or_url):
		#Given a url or file, try to fetch that item, and return if it exists or not
		is_a_url = self._is_url(file_or_url)


		if(is_a_url):
			return self._exists_url(file_or_url), True
		else:
			return self._exists_file(file_or_url), False


	def _max_diagnostic_num(self, testname, diag_type):
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
			exists, isurl = self._exists_and_is_url(self.url_for('static', filename=file_or_url_name))
			#if it's not on the server, fallback to trying local file
			if(isurl and not exists):
				#print ('isurl and not exists')
				#print ('isurl = '+ str(isurl))
				#print ('exists = '+ str(exists))
				exists, isurl = self._exists_and_is_url(join('/static', file_or_url_name))
				if(exists):
					use_local = True
				#the slash is needed to mimic the bad behavior of self.url_for

			if exists:
				#print(file_or_url_name)
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

	def _real_value(self, value_slug, dirname):
		#given a short value, and the dirname (static/report/testname), look up the long description
		try:
			with open(join(dirname, 'val_lookup.csv'), 'r') as fin:
				reader = csv.reader(fin, delimiter=',')
				reader.next() #skip header
				lookup = dict(reader)
				return lookup[value_slug]
		except:
			return value_slug




	def _get_or_set_noshot_url(self):
		if not self.NOSHOT:
			self.NOSHOT = self.url_for('static', filename='img/noshot.gif')
			#exists, isurl = exists_and_is_url(self.NOSHOT)
			#if(not exists):
			#	self.NOSHOT = local_self.url_for('static', filename='img/noshot.gif')
		return self.NOSHOT

	def _diagnostic_types(self, testname):
		type_re = r"diagnostic_(?P<type>.*)_[0-9]*\.jpeg$"
		files = walk(join("static","report",testname)).next()[2]
		alltypes = [""]
		for filename in files:
			matches = re.match(type_re, filename)
			if matches:
				diagtype = matches.group('type')
				alltypes.append(diagtype)
		alltypes = list(set(alltypes))
		return alltypes


	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############
	#############

