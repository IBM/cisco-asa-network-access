# asa-network-access

Uses [Netmiko](https://github.com/ktbyers/netmiko) to configure one of a set of predefined object-group network instances, adding or removing a network-object so long as it falls within a predefined set of networks.

There is a command-line tool as well as a simple web-based API (using Flask-RESTful).

The predefined objects-groups ("projects") and networks are defined in _configuration.yml_ - see the sample file for format details.

The authentication to the ASA is defined in _credentials.yml_ - see the sample file for format details.

## Use case

Given an ASA providing access control between various internal environments (projects) and the "outside". It is known ahead of time what the internal environments are, as well as the network addresses for the outside connectivity - but what is not known (and which changes dynamically on demand) is which outside systems are allowed to access what inside environments.

This script can faciliate access (add/remove) for this scenario.

## CLI Usage

```
$ ./network_access.py --help
usage: network_access.py [-h] [-c] [-s] project network

positional arguments:
  project      The project to modify
  network      The network to add/remove from the project

optional arguments:
  -h, --help   show this help message and exit
  -c, --clean  Remove the specified network from the project
  -s, --save   Save the configuration after making the change
```

## API Usage

By default, *network_access_api.py* will listen on https port 8088. Send GET request to "/" URL to get basic usage help. A very basic SSL method is implemented; real certificates are recommended for production. I used *The Simplest Way To Do It* method found [in Miguel's excellent Flask tutorial](https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https).

Minimum security measures are applied; a pre-shared key is required. For production a more robust authentication mechanism is recommended.

Examples:

```
$ curl -k https://rest-server.example.com:8088/
{"usage": "Include network: <network_name> and key: <preshared_key> in the data portion of the PUT request to add or clean. URL to add a network: /add/<project_name> URL to clean network: /clean/<project_name>"}
$ curl -k -X PUT https://rest-server.example.com:8088/add/demo-project1 -d "network=10.22.11.128/27" -d "key=sh4redk3y"
{"Added": "10.22.11.128/27 to demo-project1"}
$ curl -k -X PUT https://rest-server.example.com:8088/clean/demo-project1 -d "network=10.22.11.128/27" -d "key=sh4redk3y"
{"Removed": "10.22.11.128/27 from demo-project1"}

# Attempting to add network outside of allowed range
$ curl -k -X PUT https://rest-server.example.com:8088/add/demo-project1 -d "network=192.168.54.0/24" -d "key=sh4redk3y"
{"Error": "Unable to generate configuration"}
# Missing pre-shared key
$ curl -k -X PUT https://rest-server.example.com:8088/add/demo-project1 -d "network=10.22.11.128/27"
{"Error": "Missing required data payload"}
```

## FAQ

### Wouldn't it be better to leverage the ASA API?
Perhaps, but [not all ASAs support it](https://www.cisco.com/c/en/us/td/docs/security/asa/compatibility/asamatrx.html#id_65991).

### Why is save just an option, and not something done every time?
While it is always important to save the configuration after making changes (to avoid losing the changes through an unexpected reboot for example), most of the time spent in the script will be waiting for "wr mem" to finish. This time can vary based on the complexity of the configuration and the capability (model) of the ASA, but it can be significant (from a network automation point of view). For example, running against an old 5520:

```
$ time ./network_access.py project-1 net1

real	0m1.229s
user	0m0.352s
sys	0m0.024s

$ time ./network_access.py -s project-1 net1

real	0m8.024s
user	0m7.160s
sys	0m0.024s
```
