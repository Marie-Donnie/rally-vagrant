#!/usr/bin/env python

import traceback
import logging, time, datetime, signal
import pprint, os, sys, math
pp = pprint.PrettyPrinter(indent=4).pprint
from time import sleep
import json
import re
import tempfile

import jinja2

from optparse import OptionParser
from string import Template
from execo_engine import logger


# Default values
default_job_name = 'Rally'
job_path = "/root/"
RALLY_INSTALL_URL = 'https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh'
DEFAULT_RALLY_GIT = 'https://git.openstack.org/openstack/rally'

# Time to wait before and after running a benchmark (seconds)
idle_time = 30

defaults = {}
defaults['env_user'] = 'marie'
defaults['os-region'] = 'RegionOne'
defaults['os-user-domain'] = 'default'
defaults['os-admin-domain'] = 'default'
defaults['os-project-domain'] = 'default'


class rally_g5k():

	def __init__(self):
		"""Define options for the experiment"""

                parser = OptionParser()
                parser.add_option("-k", dest="keep_alive",
				help="Keep the reservation alive.",
				action="store_true")

		parser.add_option("-f", "--force-deploy", dest="force_deploy", default=False,
				action="store_true",
				help="Deploy the node without checking if it is already deployed. (default: %(defaults)s)")
		parser.add_option("-v", "--rally-verbose", dest="verbose", default=False,
				action="store_true",
				help="Make Rally produce more insightful output. (default: %(defaults))")
                (self.options, self.args) = parser.parse_args()

	def run(self):
		"""Perform experiment"""
		logger.detail(self.options)

		# Checking the options
		if len(self.args) < 2:
			self.parser.print_help()
			exit(1)

		# Load the configuration file
		try:
			with open(self.args[0]) as config_file:
				self.config = json.load(config_file)
		except:
			logger.error("Error reading configuration file")
			t, value, tb = sys.exc_info()
			print str(t) + " " + str(value)
			exit(3)

		# Put default values
		for key in defaults:
			if not key in self.config['authentication'] or self.config['authentication'][key] == "":
				self.config['authentication'][key] = defaults[key]
				logger.info("Using default value '%s' for '%s'" % (self.config['authentication'][key], key))

			if not 'rally-git' in self.config or self.config['rally-git'] == '':
				self.config['rally-git'] = DEFAULT_RALLY_GIT
				logger.info("Using default Git for Rally: %s " % self.config['rally-git'])

		try:
			self.rally_deployed = False


			# Deploying the host and Rally
			self.setup_host()
			
			# This will be useful in a bit
                        dt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
                        self.result_dir = os.path.join(os.getcwd(), "rally/results/%s" % dt)
                        if not os.path.exists(self.result_dir):
                                os.makedirs(self.result_dir)

			experiment = {}
			experiment['start'] = int(time.time())

			# Launch the benchmarks

			n_benchmarks = len(self.args[1:])
			i_benchmark = 0
			for bench_file in self.args[1:]:
				if not os.path.isfile(bench_file):
					logger.warn("Ignoring %s which is not a file" % bench_file)
					continue

				i_benchmark += 1
				logger.info("[%d/%d] Preparing benchmark %s" % (i_benchmark, n_benchmarks, bench_file))

				v = ''
				if self.options.verbose:
					v = '-d'
				cmd = "rally %s task start %s" % (v, bench_file)
				

				logger.info("[%d/%d] Running benchmark %s" % (i_benchmark, n_benchmarks, bench_file))

				bench_basename = os.path.basename(bench_file)
                                
				# This is it
				rally_task = os.system(cmd)

				if rally_task != 0:
					logger.error("Error while running benchmark")
					continue
				else:
                                        # Getting the results back
                                        self._get_logs(bench_basename)

				logger.info('----------------------------------------')
		except Exception as e:
			t, value, tb = sys.exc_info()
			print str(t) + " " + str(value)
			traceback.print_tb(tb)

		exit()

	def setup_host(self):
		# Test if rally is installed
		test_p = os.system('rally version')
		# test_p.ignore_exit_code = True
		# test_p.nolog_exit_code = True
		# test_p.run()

		if test_p != 0:
			# Install rally
                        if not os.path.exists("./repos"):
                                os.mkdir("./repos")
                        os.chdir('repos')
                        os.system("curl -sO %s" % RALLY_INSTALL_URL)

			logger.info("Installing rally from %s" % self.config['rally-git'])
                        os.system("bash install_rally.sh -d 'rally' -y --url %s" % self.config['rally-git'])

		else:
			logger.info("Rally %s is already installed" % test_p.stdout.rstrip())


                # Activate the virtual environment
                activate_this_file = "./rally/bin/activate_this.py"
                execfile(activate_this_file, dict(__file__=activate_this_file))

		# Setup the deployment file
		vars = {
			"controller": self.config['authentication']['controller'],
			"os_region": self.config['authentication']['os-region'],
			"os_username": self.config['authentication']['os-username'],
			"os_password": self.config['authentication']['os-password'],
			"os_tenant": self.config['authentication']['os-tenant'],
			"os_user_domain": self.config['authentication']['os-user-domain'],
			"os_admin_domain": self.config['authentication']['os-admin-domain'],
			"os_project_domain": self.config['authentication']['os-project-domain']
		}                
                
 		# Create a Rally deployment
                rally_deployment = self._render_template('deployment_existing.json', vars)
                os.system("rally deployment create --filename %s --name %s" % (rally_deployment, self.config['deployment_name']))

		self.rally_deployed = True

		logger.info("Rally has been deployed correctly")


	def _get_logs(self, bench_file):
                # activate_this_file = "rally/bin/activate_this.py"

                # execfile(activate_this_file, dict(__file__=activate_this_file))
		# Generating the HTML file
		logger.info("Getting the results into " + self.result_dir)
		html_file = os.path.splitext(bench_file)[0] + '.html'
		dest = os.path.join(self.result_dir, html_file)
		result = os.system("rally task report --out=" + html_file)
                # print ("--------------------SALUT JE SUIS LA !!--------------------")
                # print("html : %s" % html_file)
                # print("dest : %s" % dest)
                # print("resultat : %s" % result)
		
		if result != 0:
			logger.error("Could not generate the HTML result file")

			# if result.processes[0].stderr:
			# 	logger.error(result.processes[0].stderr)
		else:
			# Downloading the HTML file

			# EX.Get(self.host, [html_file], local_location=dest, connection_params={'user': 'root'}).run()
			logger.info("Wrote " + dest)

		# Get the metrics from Rally
		
		metrics_file = os.path.join(self.result_dir, os.path.splitext(bench_file)[0] + '.json')
		result = os.system("rally task results")
                # print ("--------------------SALUT JE SUIS LA AUSSI !!--------------------")
                # print("metric : %s" % metrics_file)
                # print("resultat : %s" % result)  
                

		if result != 0:
			logger.error("Could not get the metrics back")

			# if result.processes[0].stderr:
			# 	logger.error(result.processes[0].stderr)
		else:
			# The json is on the standard output of the process
                        os.system("rally task results > %s" % metrics_file)
			# with open(metrics_file, 'w') as f:
			# 	f.write(os.system("rally task results"))
			logger.info("Wrote " + metrics_file)
                        
 

	def _render_template(self, template_path, vars):
		template_loader = jinja2.FileSystemLoader(searchpath='../templates/')
		template_env = jinja2.Environment(loader=template_loader)
		template = template_env.get_template(template_path)
		
		f = tempfile.NamedTemporaryFile('w', delete=False)
		f.write(template.render(vars))
		f.close()
		
		return f.name

	def _run_or_abort(self, cmd, host, error_message, tear_down=True, conn_params=None):
		"""Attempt to run a command on the given host. If the command fails,
		error_message and the process error output will be printed.

		In addition, if tear_down is True, the tear_down() method will be
		called and the process will exit with return code 1"""

		if conn_params:
			p = os.system(cmd, host, conn_params)
		else:
			p = os.system(cmd, host)
		p.run()

		if p.exit_code != 0:
			logger.warn(error_message)

			if p.stderr is not None:
				logger.warn(p.stderr)

			logger.info(' '.join(p.cmd))

			if tear_down:
				self.tear_down()
				exit(1)



###################
# Main
###################
if __name__ == "__main__":
	#print("Execo version: " + EX._version.__version__)
	engine = rally_g5k()
	engine.run()
   
