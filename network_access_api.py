"""
network_access_api.py

Simple Flask-based REST API to network_access.py

Author: Scott Strattner (sstrattn@us.ibm.com)
"""

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
        help_msg = 'URL to add a network: /add/<project_name>'
        help_msg += ' and include a network: <network_name> data in PUT request.'
        help_msg += ' URL to clean network: /clean/<project_name> and no data'
        help_msg += ' needed in the PUT request.'
        return {'usage': help_msg}

class AddNetwork(Resource):
    """
    Resource to add a network to a project
    """

    def __init__(self, **kwargs):
        self.defaults = kwargs['defaults']

    def put(self, project):
        """
        Add network here
        """
        network = request.form['network']
        configuration_set = network_access.create_config_set(self.defaults, network, project)
        if not configuration_set:
            return {'Error': 'Unable to generate configuration'}
        network_access.configure_firewall(self.defaults.credentials, configuration_set)
        return {project: network}

class CleanProject(Resource):
    """
    Resource to clean a project
    """

    def __init__(self, **kwargs):
        self.defaults = kwargs['defaults']

    def put(self, project):
        """
        Clean network here
        """
        configuration_set = network_access.clean_config_set(self.defaults, project)
        if not configuration_set:
            return {'Error': 'Unable to generate configuration'}
        network_access.configure_firewall(self.defaults.credentials, configuration_set)
        return {"project": project}

def main():
    """
    main method
    """
    my_defaults = network_access.Defaults()
    app = Flask(__name__)
    api = Api(app)

    api.add_resource(HelpScreen, '/')
    api.add_resource(AddNetwork, '/add/<string:project>',
                     resource_class_kwargs={'defaults': my_defaults})
    api.add_resource(CleanProject, '/clean/<string:project>',
                     resource_class_kwargs={'defaults': my_defaults})

    app.run(host='0.0.0.0', port=8088)

if __name__ == "__main__":
    main()
