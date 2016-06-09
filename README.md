# Rally-Vagrant

Rally-Vagrant allows to run scenarios on an OpenStack deployed with Discovery-Vagrant.

## Deploy OpenStack on a virtual machine with Discovery-Vagrant

https://github.com/BeyondTheClouds/discovery-vagrant

## Running

* Get a scenario from rally https://github.com/openstack/rally/tree/master/samples/tasks/scenarios
* Launch benchmarking with
` python rally-g5k.py config.json "pathtoscenario"`
