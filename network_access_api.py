from flask import Flask
from flask_restful import Resource, Api
import network_access

class HelpScreen(Resource):
    def get(self):
        return None

class AddNetwork(Resource):
    def put(self, project):
        network = request.form('network')
        return None

class CleanProject(Resource):
    def put(self, project):
        return None

def main():
    """
    Entry point for calling directly
    """
    my_defaults = network_access.Defaults()
    app = Flask(__name__)
    api = Api(app)

    api.add_resource(HelpScreen, '/')
    api.add_resource(AddNetwork, '/add/<string:project>')
    api.add_resource(CleanProject, '/clean/<string:project>')

    app.run()

if __name__ == "__main__":
    main()
