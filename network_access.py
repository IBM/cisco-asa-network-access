#!/usr/bin/python3
"""

network_access.py

Uses Netmiko module to configure ASA firewall, adding/removing
requested network-object to/from specified object-group network.

Author: Scott Strattner (sstrattn@us.ibm.com)

References:
https://cyruslab.net/2017/10/10/update-cisco-asa-object-group-with-netmiko/

© Copyright IBM Corporation 2018.

LICENSE: The MIT License https://opensource.org/licenses/MIT

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
        self.convert_networks()
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

    def convert_networks(self):
        """
        For each predefined network listing, convert to a valid
        ip network object, for later comparison.
        """
        if 'networks' not in self.config:
            return None
        valid_networks = []
        for net_entry in self.config['networks']:
            try:
                logging.debug('Attempting to convert %s to valid network', net_entry)
                network = ipaddress.ip_network(net_entry)
                valid_networks.append(network)
            except ValueError as val_err:
                logging.debug('Unable to convert %s to network: %s', net_entry, val_err)
        self.config['networks'] = valid_networks
        return None

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

    def network_in_range(self, network_to_match):
        """
        Given a requested network to add/remove from a project,
        return that network if it falls within one of the predefined networks,
        otherwise None.
        """
        try:
            network = ipaddress.ip_network(network_to_match)
        except ValueError as val_err:
            logging.debug('Unable to convert requested network to valid IP: %s', val_err)
            return None
        for net_entry in self.return_values('networks'):
            logging.debug('Checking if %s is in %s', str(network), str(net_entry))
            try:
                supernet = network.supernet(new_prefix=net_entry.prefixlen)
                if supernet == net_entry:
                    logging.debug('Got match for %s', str(net_entry))
                    return network
            except ValueError as val_err:
                logging.debug('Unable to compare networks: %s', val_err)
        return None


def fill_config_set(network_object, object_group, clean=False):
    """
    Return filled out list of configuration to send to ASA.
    When adding to a project, network_object should be a string (one network).
    When cleaning a project, network_object should be a list (of network strings).
    """
    object_group = 'object-group network ' + object_group
    config_set = [object_group]
    network_string = 'network-object ' + network_object
    if clean:
        network_string = 'no ' + network_string
    config_set.append(network_string)
    logging.debug('Using configuration set: %s', str(config_set))
    return config_set

def create_config_set(configuration, network, project, clean=False):
    """
    Given a network (string) and project (string),
    create a configuration set (list of commands to ASA).
    """
    net_address = configuration.network_in_range(network)
    project_group = configuration.return_match_or_none('projects', project)
    if not net_address or not project_group:
        logging.debug('Unable to find either %s or %s in configuration', network, project)
        return None
    if int(net_address.prefixlen) == 32:
        net_address = 'host ' + str(net_address.network_address)
    else:
        net_address = str(net_address.network_address) + ' ' + str(net_address.netmask)
    logging.debug('Using network address %s', net_address)
    return fill_config_set(net_address, project_group, clean)

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
    parser.add_argument("network", help="The network to add/remove from the project")
    parser.add_argument("-c", "--clean", help="Remove the specified network from the project",
                        action="store_true", default=False)
    parser.add_argument("-s", "--save", help="Save the configuration after making the change",
                        action="store_true", default=False)
    args = parser.parse_args()
    my_defaults = Defaults()
    configuration_set = create_config_set(my_defaults, args.network, args.project, args.clean)
    if not configuration_set:
        print("Unable to generate valid configuration. Run in debug mode to troubleshoot.")
        exit(-1)
    configure_firewall(my_defaults.credentials, configuration_set, args.save)

if __name__ == "__main__":
    main()
