#!/usr/bin/python3
"""

network_access.py

Uses Netmiko module to configure ASA firewall, adding/removing
requested network-object to/from specified object-group network.

Author: Scott Strattner (sstrattn@us.ibm.com)

References:
https://cyruslab.net/2017/10/10/update-cisco-asa-object-group-with-netmiko/

"""

import logging
import argparse
import ipaddress
import yaml
from netmiko import ConnectHandler

class Defaults:
    """
    Container to load and store default file information
    """

    CONF_FILE = "configuration.yml"
    CRED_FILE = "credentials.yml"

    def __init__(self, configuration=None, credentials=None):
        if configuration:
            self.config = Defaults.load_file(configuration)
        else:
            self.config = Defaults.load_file(Defaults.CONF_FILE)
        if credentials:
            self.credentials = Defaults.load_file(credentials)
        else:
            self.credentials = Defaults.load_file(Defaults.CRED_FILE)
        if not self.config or not self.credentials:
            raise ValueError()
        # Adding the following seems to slightly reduce the time to complete
        self.credentials['global_delay_factor'] = .2

    @staticmethod
    def load_file(info_file):
        """
        Return dict of YAML file contents
        """
        return_dict = None
        try:
            with open(info_file) as l_f:
                try:
                    return_dict = yaml.load(l_f)
                except yaml.YAMLError as ymle:
                    logging.debug(str(ymle))
        except IOError as ioe:
            logging.debug(str(ioe))
        return return_dict

    def return_values(self, conf_key):
        """
        Given a key in configuration, return the value, or
        None if key is not found.
        """
        if conf_key in self.config:
            return self.config[conf_key]
        return None

    def return_match_or_none(self, conf_key, match_string):
        """
        Search for key in configuration. If found, search each
        entry in the value list for the match_string key and return
        the value for that entry (or None if not found)
        """
        if conf_key not in self.config:
            return None
        for conf_entry in self.return_values(conf_key):
            if match_string in conf_entry:
                return conf_entry[match_string]
        return None


def fill_config_set(network_object, object_group, clean=False):
    """
    Return filled out list of configuration to send to ASA.
    When adding to a project, network_object should be a string (one network).
    When cleaning a project, network_object should be a list (of network strings).
    """
    object_group = 'object-group network ' + object_group
    if not clean:
        network_object = [network_object]
    config_set = [object_group]
    for net_obj in network_object:
        network_string = 'network-object ' + net_obj
        if clean:
            network_string = 'no ' + network_string
        config_set.append(network_string)
    logging.debug('Using configuration set: %s', str(config_set))
    return config_set

def create_config_set(configuration, network, project):
    """
    Given a network (string) and project (string),
    create a configuration set (list of commands to ASA).
    """
    net_address = configuration.return_match_or_none('networks', network)
    project_group = configuration.return_match_or_none('projects', project)
    if not net_address or not project_group:
        logging.debug('Unable to find either %s or %s in configuration', network, project)
        return None
    try:
        net_address = ipaddress.ip_network(net_address)
        if int(net_address.prefixlen) == 32:
            net_address = 'host ' + str(net_address.network_address)
        else:
            net_address = str(net_address.network_address) + ' ' + str(net_address.netmask)
    except ValueError:
        logging.debug('Invalid network %s', net_address)
        return None
    return fill_config_set(net_address, project_group)

def clean_config_set(configuration, project):
    """
    Given a project (string), go through all defined networks and remove
    them from the object-group. Returns the configuration set to perform
    this task.
    """
    networks_to_clean = []
    project_group = configuration.return_match_or_none('projects', project)
    if not project_group:
        logging.debug('Unable to find project %s for cleanup', project)
        return None
    for net in configuration.return_values('networks'):
        net_address = list(net.values())[0]
        try:
            net_address = ipaddress.ip_network(net_address)
            if int(net_address.prefixlen) == 32:
                net_address = 'host ' + str(net_address.network_address)
            else:
                net_address = str(net_address.network_address) + ' ' + str(net_address.netmask)
            logging.debug('Adding network %s to cleanup', net_address)
            networks_to_clean.append(net_address)
        except ValueError:
            logging.debug('Ignoring invalid network %s for cleanup', net_address)
    return fill_config_set(networks_to_clean, project_group, True)

def configure_firewall(credentials, config_set=None, save=False):
    """
    Send commands to ASA via Netmiko
    """
    with ConnectHandler(**credentials) as asa:
        asa.enable()
        asa.config_mode()
        if config_set:
            asa.send_config_set(config_set, delay_factor=.2)
        if save:
            asa.send_command_expect('wr mem')

def main():
    """
    Method to run if called directly
    """
    #logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="The project to modify")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-n", "--network", type=str,
                       help="The network to add to the specified project")
    group.add_argument("-c", "--clean", help="Remove all defined networks from specified project",
                       action="store_true", default=False)
    parser.add_argument("-s", "--save", help="Save the configuration after making the change",
                        action="store_true", default=False)
    args = parser.parse_args()
    my_defaults = Defaults()
    if args.clean:
        configuration_set = clean_config_set(my_defaults, args.project)
    else:
        if not args.network:
            print('Need to provide a network to add to project')
            exit(-1)
        configuration_set = create_config_set(my_defaults, args.network, args.project)
    if not configuration_set:
        print("Unable to generate valid configuration. Run in debug mode to troubleshoot.")
        exit(-1)
    configure_firewall(my_defaults.credentials, configuration_set, args.save)

if __name__ == "__main__":
    main()
