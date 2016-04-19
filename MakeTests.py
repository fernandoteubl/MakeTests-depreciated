#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main():
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--verbose", help="Inctrease output verbosity (most verbose: -vvv).", default=0, action="count")
	parser.add_argument("-c", "--config", help="Config file input (JSON format).", type=str, default="config.json")
	parser.add_argument("-i", "--interactive", help="Interactive answers.", action="store_true")
	parser.add_argument("-a", "--all", help="Create a PDF with all questions with a specific ID. Arg.: <id>.", type=str)
	parser.add_argument("-q", "--question", help="View results of specific question. Arg.: <group>:<question>:<args_id>")
	parser.add_argument("-d", "--debug", help="View results of algorithm of a specific question. Arg.: <group>:<question>:<arg1>[:<arg2>[:...]]")
	parser.add_argument("-r", "--replaces", help="Set a replace string for .tex file. Arg.: <key>=<value> [<key>=<value> [...]]", type=str, action="append", nargs='+')
	parser.add_argument("--create", help="Create a dummy repository and config file.", action="store_true")

	args = parser.parse_args()

	try:
		if args.create:
			createDummy()
			return
	
		import json
		try:
			with open(args.config) as f:
				data = json.load(f)
		except FileNotFoundError:
			raise Exception("Config file '{}' not found! Use -c argument to specify a config file or --create argument to create a dummy project.".format(args.config))
		except Exception as e:
			raise Exception("Config parser error: {}".format(e))
		
		if args.verbose > 1:
			print("Config file {} loaded.".format(args.config))

		# Load modules (.py questions)
		import os
		os.chdir(os.path.dirname(os.path.realpath(args.config)))

		questions = loadModules(data['repository'])
		if args.verbose > 1:
			print("There is {} group of questions loaded from repository {}:".format(len(questions), data['repository']))
			for g in questions:
				import collections
				if type(questions[g]) is collections.OrderedDict:
					print("  Group '{}': {} questions:".format(g, len(questions[g])))
					for q in questions[g]:
						print("    {}".format(q))

		# --QUESTION
		if args.question != None:
			try:
				g, q, i = args.question.split(':')
			except Exception as e:
				raise Exception("Argument error. Usage: --debug <group>:<question>:<id>")
			if not g in questions:
				raise Exception("There is no group '{}'.".format(g))
			elif not q in questions[g]:
				raise Exception("There is no question '{}' in group '{}'.".format(q, g))
			elif not "answer" in dir(questions[g][q]):
				raise Exception("There is not 'answer' method on question '{}:{}'.".format(g,q))
			if args.verbose:
				print("The answer of question '{}' from group '{}' with id '{}' is:".format(q, g, i))
			print(questions[g][q].answer(i, debug=True))
			return

		# --DEBUG
		if args.debug != None:
			try:
				a = args.debug.split(':')
				g, q = a[0], a[1]
				i = a[2:] if len(a) > 3 else a[2]
			except Exception as e:
				raise Exception("Argument error. Usage: --debug <group>:<question>:<arg1>[:<arg2>[:...]]")
			if not g in questions:
				raise Exception("There is no group '{}'.".format(g))
			elif not q in questions[g]:
				raise Exception("There is no question '{}' in group '{}'.".format(q, g))
			elif not "algorithm" in dir(questions[g][q]):
				raise Exception("There is not 'algorithm' method on question '{}:{}'.".format(g,q))
			if args.verbose:
				print("The result of algorithm '{}' from group '{}' with args '{}' is:".format(q, g, i))

			from timeit import default_timer as timer
			start = timer()
			r = questions[g][q].algorithm(i, debug = (True if args.verbose > 0 else False))
			end = timer()
			print(r)
			if args.verbose:
				print("Time elapsed: {:6.12f}s.".format(end - start))  

			return

		# --INTERACTIVE
		if args.interactive:
			while True:
				try:
					ID = int(input("Enter an ID (press Ctrl+C to exit): "))					
					for q in loadQuestions(data['questions'], questions, ID):
						print("  {:>16}.{:<16} = {:<32} ({})".format(q['group'], q['filename'], q['module'].answer(ID, debug=False), q['prefix']))
				except ValueError:
					print("Invalid ID!")
				except KeyboardInterrupt:
					print("")
					return

		# Load replaces strings for .tex
		replaces = data['tex']['replaces']
		if args.replaces != None:
			for rs in args.replaces:
				for r in rs:
					k, v = r.split('=')
					replaces[k] = v
		replaces['%TOTAL%'] = str(len(data['questions']))

		if args.verbose > 1:
			print("Replaces:")
			for r in replaces:
				print ("  {:40}= {}".format(r, replaces[r]))

		def doReplaces(s):
			ret = []
			if type(s) is str:
				for k, v in replaces.items():
					s = s.replace(k, v)
				ret.append(s)
			else:
				for i in s:
					ret += doReplaces(i)
			return ret


		# All questions PDF
		if args.all:
			if args.verbose > 0:
				print("Build pdf with all questions and id = {}".format(args.all))
			replaces['%ID%']     = args.all
			all_tex  = doReplaces(data['tex']['preamble'])
			all_tex += doReplaces(data['tex']['all']['header'])
			
			c = 0
			for g in questions:
				if args.verbose > 2:
					print("  Adding group \"{}\":".format(g))
				for q in questions[g]:
					if args.verbose > 2:
						print("    Adding question \"{}\"...".format(q))
					c += 1
					replaces['%COUNT%']  = str(c)
					replaces['%GROUP%']  = g.replace("_", "\\_")
					replaces['%NAME%']   = q.replace("_", "\\_")
					replaces['%ANSWER%'] = str(questions[g][q].answer(args.all))
					
					all_tex += doReplaces(data['tex']['all']['question'])
					all_tex.append(questions[g][q].question(args.all, answer_area = False))
					all_tex += doReplaces(data['tex']['all']['answer'])
					all_tex += doReplaces(data['tex']['all']['next'])
			
			all_tex += doReplaces(data['tex']['all']['footer'])
			all_tex += doReplaces(data['tex']['termination'])
			
			if args.verbose > 2:
				print ("========== LaTeX generated All BEGIN ========")
				for l in all_tex:
					print(l)
				print ("========== LaTeX generated All END ==========")
			
			ret, out = tex2pdf(all_tex, data['output']['all'], data['tex']['includes'])
			if not ret:
				raise Exception(out)
			return

		# Get list of students
		f = open(data['input']['students'], 'r')
		students = []
		for s in f.readlines():
			s = s.replace(' ', '\t')
			sp   = s.split()
			id   = sp[0]
			name = " ".join(sp[1:])
			students.append([id, name])
		f.close()

		if args.verbose:
			print("There is {} students on '{}' file".format(len(students), data['input']['students']))

		# Print tests PDF
		tests_tex = []
		tests_tex += doReplaces(data['tex']['preamble'])
		for id, name in students:
			if args.verbose > 1:
				print("Generate test to {} ({})".format(name, id))

			replaces['%ID%']   = id
			replaces['%NAME%'] = name
			
			tests_tex += doReplaces(data['tex']['test']['header'])
			
			c = 0
			for q in loadQuestions(data['questions'], questions, id):
				c += 1
				replaces['%COUNT%'] = str(c)
				replaces['%PREFIX%'] = q['prefix']

				tests_tex += doReplaces(data['tex']['test']['before'])
				tests_tex.append(q['module'].question(id, answer_area = True))
				tests_tex += doReplaces(data['tex']['test']['after'])

			tests_tex += doReplaces(data['tex']['test']['footer'])
		tests_tex += doReplaces(data['tex']['termination'])

		if args.verbose > 2:
			print ("========== LaTeX generated Tests BEGIN ========")
			for l in tests_tex:
				print(l)
			print ("========== LaTeX generated Tests END ==========")

		ret, out = tex2pdf(tests_tex, data['output']['tests'], data['tex']['includes'])
		if not ret:
			raise Exception(out)

		if args.verbose:
			print("All tests generated on '{}'".format(data['output']['tests']))

		# Print template PDF
		template_tex = []		
		template_tex += data['tex']['preamble']
		template_tex += data['tex']['template']['header']
		for id, name in students:
			if args.verbose > 1:
				print("Generate template to {} ({})".format(name, id))

			replaces['%ID%']    = id
			replaces['%NAME%']  = name

			template_tex += doReplaces(data['tex']['template']['student'])

			c = 0
			for q in loadQuestions(data['questions'], questions, id):
				c += 1
				replaces['%COUNT%']  = str(c)
				replaces['%PREFIX%'] = q['prefix']
				replaces['%ANSWER%'] = str(q['module'].answer(id))

				template_tex += doReplaces(data['tex']['template']['answer'])

			template_tex += doReplaces(data['tex']['template']['next'])

		template_tex += doReplaces(data['tex']['template']['footer'])
		template_tex += doReplaces(data['tex']['termination'])

		if args.verbose > 2:
			print ("========== LaTeX generated Template BEGIN ========")
			for l in template_tex:
				print(l)
			print ("========== LaTeX generated Template END ==========")

		ret, out = tex2pdf(template_tex, data['output']['template'], data['tex']['includes'])
		if not ret:
			raise Exception(out)

		if args.verbose:
			print("Template of all tests generated on '{}'".format(data['output']['template']))
			

	except Exception as e:
		if args.verbose > 1:
			import traceback
			print("===== BEGIN ERROR =====")
			for e in e.args:
				print (e)
			print("=== TRACEBACK ERROR ===")
			print(traceback.format_exc())
			print("====== END ERROR ======")
		elif args.verbose:
			for e in e.args:
				print (e)
		else:
			print("Failure. Add -v or -vv argument for more information.")

def loadQuestions(data, questions, ID):
	import random
	random.seed(int(ID))

	# Shuffle questions from each group
	listQuest = dict()
	for g in questions:
		l = [q for q in questions[g]]
		random.shuffle(l)
		listQuest[g] = l

	result = []
	for d in data:
		grp = d['group']
		if not grp in listQuest:
			raise Exception("Group '{}' didn't exist".format(grp))
		if len(listQuest[grp]) == 0:
			raise Exception("There is no more questions from '{}' group".format(d['group']))
		d['filename'] = listQuest[grp][0] # Filename of question
		d['module']   = questions[grp][listQuest[grp][0]] # Module of question
		listQuest[grp].pop(0)
		result.append(d)
	return result

def loadModulesAbs(path):
	try:
		import os, sys
		modules = dict()
		for x in os.listdir(path):
			if os.path.isfile(os.path.join(path, x)):
				if x.endswith(".py"): # New module found!
					from importlib import import_module
					module_name = os.path.splitext(x)[0] # Remove extension '.py'.
					sys.path.insert(0, path)
					modules[module_name] = import_module(module_name)
					sys.path.pop(0)
					del sys.modules[module_name] # Removing module, in case of future repeated module name.
				else: # Other file type.
					pass # Nothing to do...
			else: # Is directory.
				tmp = loadModulesAbs(os.path.join(path, x))
				if len(tmp) > 0: # Ignore if there is no modules.
					modules[x] = tmp
		import collections # standard dict() is unordered. Using OrderedDict.
		return collections.OrderedDict(sorted(modules.items(), key=lambda t: t[0]))
	except FileNotFoundError as e:
		raise Exception("ERROR on loadModules: [{}] {} (\"{}\").".format(e.errno, e.strerror, path))

def loadModules(relative_path):
	import os
	return loadModulesAbs(os.path.realpath(os.path.join(os.getcwd(), relative_path)))



def tex2pdf(tex_str, output, includes = []):
	import os, sys, subprocess, shlex, shutil

	full_output = os.path.join(os.path.dirname(os.path.realpath('__file__')), output)

	import datetime
	tmp_dir = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%H%M%S')
	tmp_dir = os.path.join('/tmp/', "tmp_" + output + "_" + tmp_dir) # os.path.join(os.path.dirname(os.path.realpath('__file__')), "tmp_"+tmp_dir)

	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)

	# Link directories from incluldes
	for i in includes:
		os.symlink(os.path.join(os.path.dirname(os.path.realpath('__file__')),i), os.path.join(tmp_dir, os.path.basename(i))) # shutil.copytree

	cwd = os.getcwd()
	os.chdir(tmp_dir)

	filename = 'source'
	with open(filename + '.tex', 'w') as f:
		for line in tex_str:
			f.write(str(line))
			f.write('\n')

	proc = subprocess.Popen(shlex.split("pdflatex -halt-on-error -file-line-error -output-format=pdf {}".format(filename + '.tex')), stdout=subprocess.PIPE, stderr=sys.stdout.buffer)
	proc_out = proc.communicate()[0].decode('utf-8')

	if os.path.isfile(filename + '.pdf'):
		shutil.move(filename + '.pdf', full_output)

	os.chdir(cwd)
	shutil.rmtree(tmp_dir)

	return proc.returncode == 0, proc_out

def createDummy():
	question_content = """
# Generate a specific variable for each ID
def makeVar(ID):
	import random
	random.seed(int(ID))
	return [random.randrange(100,1000,10), random.randrange(2,5,1)]

# Algorithm requested (template).
def algorithm(n, debug = False):
	if debug:
		print("n[0] is {} and n[1] is {}".format(n[0],n[1]))
	return int(n[0]) ** int(n[1])

# Return the answer for a specific ID.
def answer(ID, debug = False):
	return str(algorithm(makeVar(ID), debug = debug)) + ((" [ID = {}, Var = {}]".format(ID, makeVar(ID))) if debug else "")

# Make a question using LaTeX
def question(ID, answer_area = False):
	def verify(x):
		return '''{\n\\color{gray}\\textit{(\\textbf{Verify:} If the value was $''' + str(x[0]) + '''^''' + str(x[1]) + '''$, the answer should be ''' + str(algorithm(x)) + ''')}}'''
	area = '''\n\n\\begin{tabularx}{\\textwidth}{|X|}\\hline \\\\ \\\\ \\hline\\end{tabularx}\n'''
	var = makeVar(ID)

	quest = "How much is the equation $" + str(var[0]) + "^" + str(var[1]) + "$?"

	return quest + verify([99, 6]) + (area if answer_area else "")
"""

	config_content = """
{
	"repository":"Questions",
	"input":{
		"students":"students.txt"
	},
	"output":{
		"tests":"Tests.pdf",
		"template":"Template.pdf",
		"all":"AllQuestions.pdf"},
	"questions":[
		{"group":"Easy", "prefix":"Weight 1"}
	],
	"tex":{
		"replaces":{
			"%UNIVERSITY%": "University of XYZ",
			"%TEST_NAME%":  "First avaliation",
			"%COURSE%":     "Programming",
			"%PROFESSOR%":  "John",
			"%CLASS%":      "A-2",
			"%DATE%":       "Today"
		},
		"includes": [
			"img"
		],
		"preamble": [
			"\\documentclass[twoside,a4paper,12pt]{article}",
			"\\usepackage[english,brazilian]{babel}",
			"\\usepackage[utf8]{inputenc}",
			"\\usepackage[T1]{fontenc}",
			"\\usepackage[top=20mm, bottom=20mm, left=20mm, right=20mm]{geometry}",
			"\\usepackage{framed}",
			"\\usepackage{color}",
			"\\usepackage{xcolor}",
			"\\usepackage{array}",
			"\\usepackage{tabularx}",
			"\\usepackage{longtable}",
			"\\usepackage{multirow}",
			"\\usepackage{amsmath}",
			"\\usepackage{graphicx}",
			"\\usepackage{enumitem}",
			"\\newcommand{\\myemph}[1]{\\textbf{#1}}",
			"\\renewcommand{\\emph}[1]{\\myemph{#1}}",
			"\\begin{document}",
			"\\thispagestyle{empty}",
			"\\pagestyle{empty}",
			""
		],
		"termination": [
			"\\end{document}"
		],
		"test":{
			"header": [
				"",
				"\\begin{tabular}{|p{2cm}|p{13cm}|}",
				"\\hline",
				"\\multirow{5}{*}{\\includegraphics[width=2cm]{img/logo.jpeg}} & \\\\",
				"                         & \\multicolumn{1}{c|}{{\\LARGE\\textbf{%UNIVERSITY%}}} \\\\",
				"                         & \\multicolumn{1}{c|}{{\\large\\textbf{%TEST_NAME%}}} \\\\",
				"                         & \\multicolumn{1}{c|}{{\\large\\textbf{%COURSE%}}} \\\\",
				"                         & \\multicolumn{1}{c|}{{\\normalsize\\textbf{Prof.} %PROFESSOR%}} \\\\",
				"\\hline",
				" \\multicolumn{2}{|c|}{",
					"\\begin{tabular}{p{7cm} p{3cm} p{5cm}}",
					"\\multicolumn{2}{l}{\\textbf{Name:} %NAME%} & \\textbf{ID:} %ID% \\\\",
					"\\textbf{Ass:} \\underline{\\hspace{6cm}} & \\textbf{Class:} %CLASS% & \\textbf{Date:} %DATE% \\\\",
					"\\end{tabular}",
				"} \\\\",
				"\\hline",
				"\\end{tabular}",
				"",
				"{\\Large\\textbf{Recommendations:}}",
				"\\begin{itemize}[noitemsep, topsep=0pt]",
				"\\item Recommendation 1;",
				"\\item Recommendation 2.",
				"\\end{itemize}",
				""
			],
			"before": [
				"\\textbf{Question %COUNT% (%PREFIX%):}"
			],
			"after": [
				""
			],
			"footer": [
				"\\cleardoublepage{}"
			]
		},
		"template":{
			"header": [
				"",
				"\\begin{center}",
				"\\begin{tabular}{|c|}",
				"\\hline",
				"{\\Huge\\textbf{GABARITO}} \\\\",
				"\\hline",
				"\\end{tabular}",
				"\\end{center}",
				""
			],
			"student": [
				"\\begin{tabularx}{\\textwidth}{|p{0cm}*{%TOTAL%}{|X}|}",
				"\\hline",
				"\\multirow{2}{*}{} & \\multicolumn{%TOTAL%}{|c|}{\\textbf{%NAME% (%ID%)}} \\\\",
				"\\hline"
			],
			"answer": [
				" & {\\scriptsize\\textbf{%COUNT%:}} {\\small %ANSWER%}"
			],
			"next": [
				" \\\\ ",
				"\\hline",
				"\\end{tabularx}",
				""
			],
			"footer": [
				""
			]
		},
		"all":{
			"header": [
				"",
				"\\begin{center}",
				"\\begin{tabular}{|c|}",
				"\\hline",
				"{\\Huge\\textbf{Questions (ID = %ID%)}} \\\\",
				"\\hline",
				"\\end{tabular}",
				"\\end{center}",
				""
			],
			"question":  [
				"\\begin{tabularx}{\\textwidth}{|X|}",
				"\\hline",
				"\\textbf{Group ``%GROUP%'', question ``%NAME%''} \\\\",
				"\\hline"
			],
			"answer": [
				"\\\\",
				"\\hline",
				"\\textbf{Answer:} %ANSWER% \\\\"
			],
			"next": [
				"\\hline",
				"\\end{tabularx}",
				"",
				""
			],
			"footer": [
				""
			]
		}
	}
}
"""

	logo_content_base64 = "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"

	import os
	if os.path.exists("config.json"):
		print("'config.json' already exist.")
		return
		return
		
	if 	os.path.exists("Questions"):
		print("'Questions' already exist.")
		return
		
	if 	os.path.exists("students.txt"):
		print("'students.txt' already exist.")
		return
		
	if 	os.path.exists("img"):
		print("'img' already exist.")
		return
		
	with open("config.json", "w") as f:
		f.write(config_content.replace("\\", "\\\\"))
	os.makedirs("Questions")
	os.makedirs("Questions/Easy")
	with open("Questions/Easy/Power.py", "w") as f:
		f.write(question_content.replace("\\", "\\\\"))
	with open("students.txt", "w") as f:
		import random, string
		for i in range(10):
			name = random.choice(string.ascii_uppercase) + "".join(random.choice(string.ascii_lowercase) for _ in range(random.randrange(4,8)))
			mid =random.choice(string.ascii_uppercase) + "".join(random.choice(string.ascii_lowercase) for _ in range(random.randrange(4,8)))
			last =random.choice(string.ascii_uppercase) + "".join(random.choice(string.ascii_lowercase) for _ in range(random.randrange(4,8)))
			f.write("{} {} {} {}\n".format(random.randrange(10000, 99999), name, mid, last))
	os.makedirs("img")
	with open("img/logo.jpeg", "wb") as f:
		import base64
		f.write(base64.b64decode(logo_content_base64))
		

if __name__ == "__main__":
	main()
