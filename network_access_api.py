#!/usr/bin/python3
"""

network_access_api.py

Simple Flask-based REST API to network_access.py

Author: Scott Strattner (sstrattn@us.ibm.com)

© Copyright IBM Corporation 2018.

LICENSE: The MIT License https://opensource.org/licenses/MIT

"""

import logging
from flask import Flask, request
from flask_restful import Resource, Api
import network_access

class HelpScreen(Resource):
    """
    Resource to provide help message
    """

    @staticmethod
    def get():
        """
        Provide useful help here
        """
        help_msg = 'Include network: <network_name> and key: <preshared_key> in'
        help_msg += ' the data portion of the PUT request to add or clean.'
        help_msg += ' URL to add a network: /add/<project_name>'
        help_msg += ' URL to clean network: /clean/<project_name>'
        return {'usage': help_msg}

class AddNetwork(Resource):
    """
    Resource to add a network to a project
    """

    def __init__(self, **kwargs):
        self.defaults = kwargs['defaults']
        self.key = kwargs['key']

    def put(self, project):
        """
        Add network here
        """
        pre_shared_key = request.form['key']
        network = request.form['network']
        configuration_set = network_access.create_config_set(self.defaults, network, project)
        if not configuration_set or self.key != pre_shared_key:
            return {'Error': 'Unable to generate configuration'}
        network_access.configure_firewall(self.defaults.credentials, configuration_set)
        message = network + " to " + project
        return {"Added": message}

class CleanProject(Resource):
    """
    Resource to clean a project
    """

    def __init__(self, **kwargs):
        self.defaults = kwargs['defaults']
        self.key = kwargs['key']

    def put(self, project):
        """
        Clean network here
        """
        pre_shared_key = request.form['key']
        network = request.form['network']
        configuration_set = network_access.create_config_set(self.defaults, network, project, True)
        if not configuration_set or self.key != pre_shared_key:
            return {'Error': 'Unable to generate configuration'}
        network_access.configure_firewall(self.defaults.credentials, configuration_set)
        message = network + " from " + project
        return {"Removed": message}

def main():
    """
    main method
    """
    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    my_defaults = network_access.Defaults()
    my_key = 'S3cr3tK3y'
    global_values = {'defaults': my_defaults,
                     'key': my_key}
    app = Flask(__name__)
    api = Api(app)

    api.add_resource(HelpScreen, '/')
    api.add_resource(AddNetwork, '/add/<string:project>',
                     resource_class_kwargs=global_values)
    api.add_resource(CleanProject, '/clean/<string:project>',
                     resource_class_kwargs=global_values)

    app.run(host='0.0.0.0', port=8088, ssl_context='adhoc')

if __name__ == "__main__":
    main()
