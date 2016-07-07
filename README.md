# Rally-Vagrant

Rally-Vagrant allows to run scenarios on an OpenStack deployed with Discovery-Vagrant.

## Deploy OpenStack on a virtual machine with Discovery-Vagrant

Where to find [Discovery-Vagrant](https://github.com/BeyondTheClouds/discovery-vagrant).

## Running

* Get a scenario from rally on [this page](https://github.com/openstack/rally/tree/master/samples/tasks/scenarios)
* Launch benchmarking with
```bash
python rally.py config.json "pathtoscenario"
```

You can also test several scenarios :
` python rally.py config.json scenario1 scenario2...`

* You can also choose to first deploy a Discovery-Vagrant machine as follows :
```bash
python rally.py --vagrant config.json "pathtoscenario"
```
Add the `-m` option if you want to use my version of Discovery-Vagrant, and `--mlog` to enable the logging.


## More information

```
Wrapper for Rally to use with Discovery-Vagrant

Usage:
    rally.py [--vagrant | --vagrant [-m|--mlog]] <config> <file>... [-h | --help][--version]

Options:
    -h --help       Show this screen
    --version       Show version
    --vagrant       Deploys a Discovery-Vagrant machine before executing tests (about an hour execution)
    -m              Uses my version of Discovery-Vagrant
    --mlog          Uses my version of Discovery-Vagrant with logs

Arguments:
    <config>        The config file to use
    <file>          The scenarios Rally will use
```

