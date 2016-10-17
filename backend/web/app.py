import threading, time
import logging
import json
import datetime
import os
from base64 import b64encode

from deepdiff import DeepDiff

import tornado.ioloop, tornado.web

from pubcontrol import Item

from gripcontrol import decode_websocket_events, GripPubControl
from gripcontrol import encode_websocket_events, WebSocketEvent
from gripcontrol import websocket_control_message, WebSocketMessageFormat

import boto3


lambda_client = boto3.client('lambda')
dynamo_client = boto3.client('dynamodb')
s3_client = boto3.client('s3')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# NOTE: localhost will not work as hostname, even in dev
PUSHPIN_HOSTNAME = os.getenv('PUSHPIN_HOSTNAME')
PUSHPIN_PORT = os.getenv('PUSHPIN_PORT', '5561')
RESTREAM_LAMBDA_PREFIX = 'restreamable'
KEYS_BUCKET = os.getenv('KEYS_BUCKET','restream-data')
KEYS_OBJECT = os.getenv('KEYS_OBJECT','keys.json')
ITEM_TABLE = os.getenv('MESSAGE_CACHE_TABLE', 'RestreamMessageCache')
CONNECTION_TTL = int(os.getenv('CONNECTION_TTL', 1800)) # 30 minute default TTL on each connection

pub = GripPubControl({
    'control_uri': 'http://{}:{}'.format(PUSHPIN_HOSTNAME, PUSHPIN_PORT)
})

channel_counts = {}
channel_processors = {}
global channel_keys
channel_keys = {}
connection_channels = {}
connection_lastseen = {}

FETCH_UPDATE_TIMEOUT = 600 # seconds

def increment_channel_count(channel_id):
    count = channel_counts.get(channel_id, 0)
    channel_counts[channel_id] = count + 1
    logger.debug('{} count inc to {}'.format(channel_id, channel_counts[channel_id]))


def decrement_channel_count(channel_id):
    count = channel_counts.get(channel_id, 0)
    if count <= 0:
        logger.warning('channel count already {}'.format(count))
        channel_counts[channel_id] = 0
    else:
        channel_counts[channel_id] = count - 1
    logger.debug('{} count dec to {}'.format(channel_id, channel_counts[channel_id]))


def is_channel_active(channel_id):
    return channel_counts.get(channel_id, 0) > 0


def process_subscribe(command, channel_fetchers, connection_id):
    """
    Add a subscription for the given channel: update its refcount, and start the
    fetch periodic callback if it doesn't exist yet.
    """
    channel = command['channel']
    channel_id = command['channel_id']
    channel_params = command['params']

    increment_channel_count(channel_id)
    if connection_id not in connection_channels:
        connection_channels[connection_id] = []
    connection_channels[connection_id].append(channel_id)
    if channel_id not in channel_processors:
        def channel_callback():
            fetch_channel(channel, channel_params, channel_id, channel_fetchers[channel])

        if channel in channel_fetchers:
            delay = 100 * 1000
            if 'poll_interval' in channel_fetchers[channel]:
                delay = channel_fetchers[channel]['poll_interval'] * 1000
                logger.info('Polling interval for {} set to {} seconds'.format(channel, delay / 1000))
            else:
                logger.warn('No polling interval found for {}'.format(channel))
            channel_callback() # run once immediately
            pcb = tornado.ioloop.PeriodicCallback(channel_callback, delay)
            pcb.start()
            channel_processors[channel_id] = pcb
        else:
            logger.warn('no fetcher found for channel {}'.format(channel))


def process_unsubscribe(channel_id, connection_id):
    """
    Remove a subscription for the given channel: update its refcount, and stop the
    fetch periodic callback if the refcount is now 0
    """
    decrement_channel_count(channel_id)
    connection_channels[connection_id].remove(channel_id)
    if not is_channel_active(channel_id):
        if channel_id in channel_processors:
            pcb = channel_processors[channel_id]
            pcb.stop()
            del channel_processors[channel_id]


def parse_message(msg):
    """
    Parse a serialized control message from a client, and return a valid command
    object that includes a channel_id with the params encoded.
    """
    try: 
        obj = json.loads(msg)
        if 'action' not in obj:
            return {
                '__restream_type': 'error',
                'message': 'No action found in control message'
            }
        elif obj['action'].lower() not in ['subscribe', 'unsubscribe', 'unsubscribe-all']:
            return {
                '__restream_type': 'error',
                'message': 'Action {} not recognized'.format(obj['action'])
            }
        obj['__restream_type'] = 'action'
        obj['params'] = obj.get('params', {})
        obj['params_encoding'] = serialize_params(obj.get('params', {}))
        obj['channel_id'] = obj['channel'] + '_' + obj['params_encoding']
        return obj
    except (TypeError, ValueError,KeyError) as e:
        logger.info('Badly formed control message: '+str(msg))
        return {
            '__restream_type': 'error',
            'message': 'Badly formed control message: {}'.format(e.message)
        }


def serialize_params(params):
    """
    Return a serialized representation of a canonicalized channel params object. This
    can be used for equality comparisons via simple string equality.
    """
    sorted_keys = sorted(params)
    out = ''
    for k in sorted_keys:
        out = out + b64encode(k.lower()) + b64encode(str(params[k]))
    return out


def now():
    return datetime.datetime.now().isoformat()


def fetch_channel(channel, params, channel_id, fetcher_meta):
    """
    - Get items for the channel using the fetcher function.
    - Store any new items in the dynamo cache. 
    - If new items were received, publish them to the channel's current subscribers.
    """

    logger.info('Polling {}'.format(channel))
    # call Lambda, async
    if fetcher_meta is None:
        logger.warn('fetcher for channel {} not found'.format(channel))
    id_field = fetcher_meta['id_field']
    # TODO consider async via coroutine?
    ret = lambda_client.invoke(
        FunctionName=fetcher_meta['function_name'],
        Payload=json.dumps(
            {
                'call': 'fetch',
                'channel': channel,
                'params': params,
                'keys': channel_keys.get(channel, {})
            }).encode('utf-8'))
    resp = json.loads(ret['Payload'].read())

    # add new items to Dynamo
    status_code = resp.get('status_code', 500)
    if status_code != 200:
        logger.warn('{} returned {}: {}'.format(channel, status_code, resp.get('result', '')))
        logger.warn(json.dumps(resp))
        return
    timestamp = now()
    out_items = []
    for item in resp['result']:
        data = json.dumps(item)
        logger.info(item)
        if id_field not in item:
            logger.info('Item does not contain id field {} - skipping'.format(id_field))
            continue
        put_resp = dynamo_client.put_item(
            TableName=ITEM_TABLE,
            ReturnValues="ALL_OLD",
            Item={
                "ChannelItemId": { "S": channel + "/" + str(item[id_field]) },
                "Timestamp": { "S": timestamp },
                "Data": { "S" : data }
            })

        # publish item if it has not been seen before, or if it has been seen before but changed
        if "Attributes" in put_resp and "Data" in put_resp["Attributes"]:
            old_data = put_resp["Attributes"]["Data"]["S"]
            old_item = json.loads(old_data)
            ddiff = DeepDiff(old_item, item, ignore_order=True)

            if ddiff == {}:
                logger.debug('item {} is unchanged'.format(item[id_field]))
            else:
                logger.debug('item {} is updated'.format(item[id_field]))
                # logger.debug(json.dumps(ddiff, indent=2))
                item['__restream_type'] = 'updated_item'
                item['__restream_diff'] = ddiff
                out_items.append(Item(WebSocketMessageFormat(json.dumps(item))))
                
        else:
            logger.debug('item {} is new'.format(item[id_field]))
            item['__restream_type'] = 'new_item'
            out_items.append(Item(WebSocketMessageFormat(json.dumps(item))))

    # publish new items to subscribers
    for item in out_items:
        pub.publish(channel_id, item)


def check_connections():
    now = datetime.datetime.now()
    conns = list(connection_lastseen.keys())
    for conn in conns:
        if (now - conns[conn]).seconds > CONNECTION_TTL and conn in connection_channels:
            disconnect_all(conn)


def disconnect_all(connection_id):
    for channel_id in connection_channels[connection_id]:
        logger.info('disconnect {} from {}'.format(connection_id, channel_id))
        process_unsubscribe(channel_id, connection_id)


class MainHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.fetch_timestamp = None
        self.channel_fetchers = {}
        # self.channel_keys
        self.load_fetchers()

    def post(self):
#####################################
        # FIXME add connection last seen timestamp
        connection_id = self.request.headers['Connection-Id']
        in_events = decode_websocket_events(self.request.body)
        out_events = []
        if len(in_events) == 0:
            return

        logger.debug(in_events[0].type)
        if in_events[0].type == 'OPEN':
            out_events.append(WebSocketEvent('OPEN'))
            out_events.append(WebSocketEvent('TEXT', 'm:' +
                json.dumps({'__restream_type': 'ready'})))
        elif in_events[0].type == 'TEXT':
            msg = in_events[0].content
            logger.debug(msg)
            command = parse_message(msg)
            if command['__restream_type'] == 'error':
                out_events.append(WebSocketEvent('TEXT', 'm:' + json.dumps(command)))
            elif command['action'] == 'subscribe':
                if connection_id in connection_channels and command['channel_id'] in connection_channels[connection_id]:
                    logger.info("Connection {} already subscribed to {}".format(
                        connection_id, command['channel_id']))
                else:
                    out_events.append(WebSocketEvent('TEXT', 'm:' +
                        json.dumps({'__restream_type': 'subscribe', 'channel': command['channel']})))
                    out_events.append(WebSocketEvent('TEXT', 'c:' +
                        websocket_control_message('subscribe', {'channel': command['channel_id']})))
                    process_subscribe(command, self.channel_fetchers, connection_id)
                    logger.info('subscribe {} to {}'.format(connection_id, command['channel_id']))
            elif command['action'] == 'unsubscribe':
                if connection_id not in connection_channels or command['channel_id'] not in connection_channels[connection_id]:
                    logger.info("Connection {} not subscribed to {}; won't unsubscribe".format(
                        connection_id, command['channel_id']))
                else:
                    out_events.append(WebSocketEvent('TEXT', 'm:' +
                        json.dumps({'__restream_type': 'unsubscribe', 'channel': command['channel']})))
                    out_events.append(WebSocketEvent('TEXT', 'c:' +
                        websocket_control_message('unsubscribe', {'channel': command['channel_id']})))
                    process_unsubscribe(command['channel_id'], connection_id)
                    logger.info('unsubscribe {} from {}'.format(connection_id, command['channel_id']))
        elif in_events[0].type == 'DISCONNECT' or in_events[0].type == 'CLOSE':
            out_events.append(WebSocketEvent(in_events[0].type))
            if connection_id in connection_channels:
                disconnect_all(connection_id)
        else:
            logger.info('event type not recognized: '+in_events[0].type)

        self.write(encode_websocket_events(out_events))
        self.set_header('Sec-WebSocket-Extensions', 'grip')
        self.set_header('Content-Type', 'application/websocket-events')
        self.finish()

    get = post

    def load_fetchers(self):
        """
        Iterate over all lambdas defined for the AWS account, invoking those that
        have the right prefix to obtain their metadata. This should be called on app
        startup, and whenever the fetcher functions may have changed. Also load the
        keys from S3.
        """
        now = datetime.datetime.now()
        if self.fetch_timestamp is not None and now - self.fetch_timestamp < FETCH_UPDATE_TIMEOUT:
            logger.debug("fetchers don't need reload")
            return

        self.channel_fetchers = load_fetcher_metadata()

        keys_resp = s3_client.get_object(Bucket=KEYS_BUCKET, Key=KEYS_OBJECT)
        for k, v in json.loads(keys_resp['Body'].read()).items():
            channel_keys[k] = v 
        self.fetch_timestamp = now


def load_fetcher_metadata():
    logger.info('loading fetcher metadata')
    metadata = {}
    functions = lambda_client.list_functions()['Functions']
    for func in functions:
        if func['FunctionName'].startswith(RESTREAM_LAMBDA_PREFIX):
            logger.info('Storing metadata for function {}'.format(func['FunctionName']))
            resp = lambda_client.invoke(
                FunctionName = func['FunctionName'],
                Payload = json.dumps(
                    {
                        'call': 'metadata'
                    }).encode('utf-8'))
            lambda_meta = json.loads(resp['Payload'].read())
            lambda_meta['function_name'] = func['FunctionName']
            metadata[lambda_meta['name']] = lambda_meta
    return metadata


class InfoHandler(tornado.web.RequestHandler):
    def get(self):
        metadata = load_fetcher_metadata()
        self.write(json.dumps(metadata, indent=2))
        self.finish()


def make_app():
    return tornado.web.Application([
        (r"/channels", MainHandler),
        (r"/", InfoHandler)
    ])


if __name__ == "__main__":
    logger.info("Starting server")
    app = make_app()
    app.listen(5000)
    tornado.ioloop.IOLoop.current().start()
