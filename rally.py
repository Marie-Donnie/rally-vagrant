"""Wrapper for Rally to use with Discovery-Vagrant

Usage:
    rally.py [--vagrant | --vagrant [-m|--mlog]] <config> ( --file=<file> | <file>... ) [-h | --help][--version]

Options:
    -h --help       Show this screen
    --version       Show version
    --vagrant       Deploys a Discovery-Vagrant machine before executing tests (about an hour execution)
    -m              Uses my version of Discovery-Vagrant
    --mlog          Uses my version of Discovery-Vagrant with logs
    --file=<file>   Uses a file containing a list of scenarios

Arguments:
    <config>        The config file to use
    <file>          The scenarios Rally will use

"""


#!/usr/bin/env python

import traceback
import logging, time, datetime, signal
import os, sys, math
from time import sleep
import json
import re
import tempfile

import jinja2
from docopt import docopt

from string import Template

# Default values
RALLY_INSTALL_URL = 'https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh'
DEFAULT_RALLY_GIT = 'https://git.openstack.org/openstack/rally'
DEFAULT_DISCO_VAG_GIT = 'https://github.com/BeyondTheClouds/discovery-vagrant.git'
MARIE_DISCO_VAG_GIT = 'https://github.com/Marie-Donnie/discovery-vagrant.git'

# Time to wait before and after running a benchmark (seconds)
idle_time = 30

defaults = {}
defaults['env_user'] = 'marie'
defaults['os-region'] = 'RegionOne'
defaults['os-user-domain'] = 'default'
defaults['os-admin-domain'] = 'default'
defaults['os-project-domain'] = 'default'

COLOR = '\033[94m'
ENDC = '\033[0m'

class rally_vagrant():

	def __init__(self):
		"""Define options for the experiment"""
                self.argus = docopt(__doc__, version = 'Rally-vagrant 2.0')
                print(self.argus)

	def run(self):
		"""Perform experiment"""
                print("test")

		# Load the configuration file
		try:
			with open(self.argus['<config>']) as config_file:
				self.config = json.load(config_file)
		except:
			print("Error reading configuration file")
			t, value, tb = sys.exc_info()
			print str(t) + " " + str(value)
			exit(3)
                        
		# Put default values
		for key in defaults:
			if not key in self.config['authentication'] or self.config['authentication'][key] == "":
				self.config['authentication'][key] = defaults[key]
				print("Using default value '%s' for '%s'" % (self.config['authentication'][key], key))

			if not 'rally-git' in self.config or self.config['rally-git'] == '':
				self.config['rally-git'] = DEFAULT_RALLY_GIT
				print("Using default Git for Rally: %s " % self.config['rally-git'])

                if self.argus['--vagrant']:
                        self._vagrant_deploy()
                        
		try:
			self.rally_deployed = False

			# Deploying the host and Rally
			self.setup_host()
			
			# This will be useful in a bit
                        dt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
                        self.result_dir = os.path.join(os.getcwd(), "../results/%s" % dt)
                        if not os.path.exists(self.result_dir):
                                os.makedirs(self.result_dir)

			experiment = {}
			experiment['start'] = int(time.time())

			# Launch the benchmarks

                        if self.argus['--file'] is not None:
                                list_bench = self.argus['--file']
                                if not os.path.isfile(list_bench):
                                        list_bench = os.path.join(os.getcwd(), '../', self.argus['--file'])
                                if os.path.isfile(list_bench):
                                        with open(list_bench, 'r') as bench_file:
                                                benchmarks = [line.strip() for line in bench_file]
                                else:
                                        print("Can't read %s" % self.argus['--file']) 
                        else:
                                benchmarks = self.argus['<file>']
                                
                        print(benchmarks)

			n_benchmarks = len(benchmarks)
			i_benchmark = 0
			for bench_file in benchmarks:
				if not os.path.isfile(bench_file):
                                        if not os.path.isfile(os.path.join(os.getcwd(), bench_file)):
                                                print("Ignoring %s which is not a file" % bench_file)
                                                continue
                                        else:
                                                bench_file = os.path.join(os.getcwd(), bench_file)
				i_benchmark += 1
				print("%s[%d/%d] Preparing benchmark %s %s" % (COLOR, i_benchmark, n_benchmarks, bench_file, ENDC))

				cmd = "rally task start %s" % (bench_file)
				

				print("[%d/%d] Running benchmark %s" % (i_benchmark, n_benchmarks, bench_file))

				bench_basename = os.path.basename(bench_file)
                                
				# This is it
				rally_task = os.system(cmd)

				if rally_task != 0:
					print("Error while running benchmark")
					continue
				else:
                                        # Getting the results back
                                        self._get_logs(bench_basename)

				print(COLOR+'----------------------------------------'+ENDC)
                                
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

			print("Installing rally from %s" % self.config['rally-git'])
                        os.system("bash install_rally.sh -d 'rally' -y --url %s" % self.config['rally-git'])

		else:
			print("Rally %s is already installed" % test_p.stdout.rstrip())


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

		print("Rally has been deployed correctly")


	def _get_logs(self, bench_file):

		# Generating the HTML file
		print("Getting the results into " + self.result_dir)
		html_file = os.path.splitext(bench_file)[0] + '.html'
		dest = os.path.join(self.result_dir, html_file)
		result = os.system("rally task report --out=" + dest)

		
		if result != 0:
			print("Could not generate the HTML result file")

		else:
			print("Wrote " + dest)

		# Get the metrics from Rally		
		metrics_file = os.path.join(self.result_dir, os.path.splitext(bench_file)[0] + '.json')
		result = os.system("rally task results")
                

		if result != 0:
			print("Could not get the metrics back")

		else:
			# The json is on the standard output of the process
                        os.system("rally task results > %s" % metrics_file)

			print("Wrote " + metrics_file)
                        
 

	def _render_template(self, template_path, vars):
		template_loader = jinja2.FileSystemLoader(searchpath='../templates/')
		template_env = jinja2.Environment(loader=template_loader)
		template = template_env.get_template(template_path)
		
		f = tempfile.NamedTemporaryFile('w', delete=False)
		f.write(template.render(vars))
		f.close()
		
		return f.name

        def _vagrant_deploy(self):
                # check if Vagrant and Virtualbox is installed
                vbox_absent = (os.system("VBoxManage --version"))
                vagrant_absent = (os.system("vagrant --version"))
                if vbox_absent:
                        print("Must have VirtualBox installed")
			exit()
                if vagrant_absent:
                        print("Must have Vagrant installed")
			exit()
                # download the correct repository
                print("Downloading Discovery-Vagrant")
                dl = DEFAULT_DISCO_VAG_GIT
                if self.argus['-m']:
                        print("My version")
                        dl = MARIE_DISCO_VAG_GIT
                if self.argus['--mlog']:
                        print("My version with logs")
                        dl = "-b my-versions "+ MARIE_DISCO_VAG_GIT
                os.system("git clone %s" % dl)
                print(dl)

                # deploy Discovery-Vagrant
                try :
                        print("Deploying Discovery-Vagrant")
                        os.system("cd discovery-vagrant ; ./deploy.sh")
                        
                except Exception as e:
			t, value, tb = sys.exc_info()
			print str(t) + " " + str(value)
			traceback.print_tb(tb)
                        exit()
                        
###################
# Main
###################
if __name__ == "__main__":
	#print("Execo version: " + EX._version.__version__)
	engine = rally_vagrant()
	engine.run()
   
