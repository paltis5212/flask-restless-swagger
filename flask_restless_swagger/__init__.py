__original_author__ = "Michael Messmore"
__original_version__ = "0.2.0"
__author__ = "Paltis"

try:
    import urlparse
except:
    from urllib import parse as urlparse

import json
from flask import jsonify, request
from flask_restless import APIManager
from flask_restless.helpers import *
from flask_swagger_ui import get_swaggerui_blueprint


def get_columns(model):
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}


sqlalchemy_swagger_type = {
    "INTEGER": "integer",
    "SMALLINT": "int32",
    "NUMERIC": "number",
    "DECIMAL": "number",
    "VARCHAR": "string",
    "TEXT": "string",
    "DATE": "date",
    "BOOLEAN": "bool",
    "BLOB": "binary",
    "BYTEA": "binary",
    "BINARY": "binary",
    "VARBINARY": "binary",
    "FLOAT": "float",
    "REAL": "float",
    "DATETIME": "date-time",
    "BIGINT": "int64",
    "ENUM": "string",
    "INTERVAL": "date-time",
}


class SwagAPIManager(object):
    swagger = {
        "openapi": "3.0.1",
        "info": {"title": "DB API", "version": ""},
        "paths": {},
        "components": {"schemas": {}},
    }

    def __init__(self, app=None, **kwargs):
        self.app = None
        self.manager = None

        if app is not None:
            self.init_app(app, **kwargs)

    def to_json(self, **kwargs):
        return json.dumps(self.swagger, **kwargs)

    def to_yaml(self, **kwargs):
        import yaml

        return yaml.dump(self.swagger, **kwargs)

    def __str__(self):
        return self.to_json(indent=4)

    @property
    def version(self):
        if "version" in self.swagger["info"]:
            return self.swagger["info"]["version"]
        return None

    @version.setter
    def version(self, value):
        self.swagger["info"]["version"] = value

    @property
    def title(self):
        if "title" in self.swagger["info"]:
            return self.swagger["info"]["title"]
        return None

    @title.setter
    def title(self, value):
        self.swagger["info"]["title"] = value

    @property
    def description(self):
        if "description" in self.swagger["info"]:
            return self.swagger["info"]["description"]
        return None

    @description.setter
    def description(self, value):
        self.swagger["info"]["description"] = value

    def add_path(self, model, **kwargs):
        name = model.__tablename__
        schema = model.__name__
        path = kwargs.get("url_prefix", "") + "/" + name
        id_path = "{0}/{{{1}Id}}".format(path, schema.lower())
        self.swagger["paths"][path] = {}

        for method in [m.lower() for m in kwargs.get("methods", ["GET"])]:
            if method == "get":
                self.swagger["paths"][path][method] = {
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "description": "searchjson",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List " + name,
                            "content": {
                                "application/vnd.api+json": {
                                    "schema": {
                                        "title": name,
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/" + name
                                        },
                                    }
                                }
                            },
                        }
                    },
                }

                if model.__doc__:
                    self.swagger["paths"][path]["description"] = model.__doc__
                if id_path not in self.swagger["paths"]:
                    self.swagger["paths"][id_path] = {}
                self.swagger["paths"][id_path][method] = {
                    "parameters": [
                        {
                            "name": schema.lower() + "Id",
                            "in": "path",
                            "description": "ID of " + schema,
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success " + name,
                            "content": {
                                "application/vnd.api+json": {
                                    "schema": {"$ref": "#/components/schemas/" + name}
                                }
                            },
                        }
                    },
                }
                if model.__doc__:
                    self.swagger["paths"][id_path]["description"] = model.__doc__
            elif method == "delete":
                if id_path not in self.swagger["paths"]:
                    self.swagger["paths"][id_path] = {}
                self.swagger["paths"][id_path][method] = {
                    "parameters": [
                        {
                            "name": schema.lower() + "Id",
                            "in": "path",
                            "description": "ID of " + schema,
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "Success", "content": {}}},
                }
                if model.__doc__:
                    self.swagger["paths"][id_path]["description"] = model.__doc__
            elif method == "patch":
                if id_path not in self.swagger["paths"]:
                    self.swagger["paths"][id_path] = {}
                self.swagger["paths"][id_path][method] = {
                    "parameters": [
                        {
                            "name": schema.lower() + "Id",
                            "in": "path",
                            "description": "ID of " + schema,
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/vnd.api+json": {
                                "schema": {"$ref": "#/components/schemas/" + schema}
                            }
                        },
                        "required": True,
                    },
                    "responses": {"200": {"description": "Success", "content": {}}},
                }
                if model.__doc__:
                    self.swagger["paths"][id_path]["requestBody"][
                        "description"
                    ] = model.__doc__
            elif method == "post":
                if id_path not in self.swagger["paths"]:
                    self.swagger["paths"][id_path] = {}
                self.swagger["paths"][path][method] = {
                    "requestBody": {
                        "content": {
                            "application/vnd.api+json": {
                                "schema": {"$ref": "#/components/schemas/" + schema}
                            }
                        },
                        "required": True,
                    },
                    "responses": {"200": {"description": "Success", "content": {}}},
                }
                if model.__doc__:
                    self.swagger["paths"][path]["requestBody"][
                        "description"
                    ] = model.__doc__

    def add_defn(self, model, **kwargs):
        name = model.__name__
        self.swagger["components"]["schemas"][name] = {
            "type": "object",
            "properties": {},
        }
        columns = get_columns(model).keys()
        for column_name, column in get_columns(model).items():
            if column_name in kwargs.get("exclude_columns", []):
                continue
            try:
                column_type = str(column.type)
                if "(" in column_type:
                    column_type = column_type.split("(")[0]

                column_defn = sqlalchemy_swagger_type[column_type]
                # date and datetime
                if column_defn in ["date", "date-time"]:
                    column_defn = {"type": "string", "format": column_defn}
                else:
                    column_defn = {"type": column_defn}

            except AttributeError:
                schema = get_related_model(model, column_name)
                if column_name + "_id" in columns:
                    column_defn = {"schema": {"$ref": schema.__name__}}
                else:
                    column_defn = {
                        "schema": {"type": "array", "items": {"$ref": schema.__name__}}
                    }

            if column.__doc__:
                column_defn["description"] = column.__doc__
            self.swagger["components"]["schemas"][name]["properties"][
                column_name
            ] = column_defn

    def init_app(self, app, doc_prefix="/dbdoc", url_prefix="/db", **kwargs):
        self.app = app
        self.manager = APIManager(self.app, url_prefix=url_prefix, **kwargs)

        @app.route(f"{doc_prefix}.json")
        def doc_json():
            # I can only get this from a request context
            scheme = request.scheme
            host = urlparse.urlparse(request.url_root).netloc
            self.swagger["servers"] = [
                {"url": f"{scheme}://{host}{url_prefix}"},
            ]
            return jsonify(self.swagger)

        # /dbdoc
        doc_blueprint = get_swaggerui_blueprint(
            f"{doc_prefix}",  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
            f"{doc_prefix}.json",
            config={"app_name": "DB API"},  # Swagger UI config overrides
        )

        app.register_blueprint(doc_blueprint)

    def create_api(self, model, **kwargs):
        self.manager.create_api(model, **kwargs)
        self.add_defn(model, **kwargs)
        self.add_path(model, **kwargs)

    def swagger_blueprint(self):
        return swagger
