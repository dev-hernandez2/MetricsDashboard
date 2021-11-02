from os import getenv
import logging
import pymongo

from flask import Flask, render_template, request, jsonify, json

from prometheus_flask_exporter import PrometheusMetrics

from flask_pymongo import PyMongo
from jaeger_client import Config



JAEGER_HOST = getenv('JAEGER_HOST', 'localhost')

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'example-mongodb'
app.config['MONGO_URI'] = 'mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb'
mongo = PyMongo(app)

metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info('app_info', 'Application Info', version='1.0.3')

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)


endpoint_counter = metrics.counter(
    'endpoint_counter', 'Request count by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)

#==================== tracer ============================
def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'local_agent': {'reporting_host': JAEGER_HOST},
        },
        service_name=service,
    )
    return config.initialize_tracer()

tracer = init_tracer('backend')

#========================================================



@app.route('/')
@endpoint_counter
def homepage():
    with tracer.start_span('hello-world'):
        message = "Hello World"
    return message


@app.route('/api')
@endpoint_counter
def my_api():
    with tracer.start_span('api'):
        answer = "something"
    return jsonify(repsonse=answer)

@app.route('/star', methods=['POST'])
@endpoint_counter
def add_star():
  star = mongo.db.stars
  name = request.json['name']
  distance = request.json['distance']
  star_id = star.insert({'name': name, 'distance': distance})
  new_star = star.find_one({'_id': star_id })
  output = {'name' : new_star['name'], 'distance' : new_star['distance']}
  return jsonify({'result' : output})

if __name__ == "__main__":
    app.run()