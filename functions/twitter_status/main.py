import sys
sys.path.append('./site-packages')
from twython import Twython

def lambda_function(event, context):
    if event['call'] == 'metadata':
        return {
            'name': 'twitter-status',
            'description': 'Twitter changes to a particular status',
            'id_field': 'id_str',
            'api_url': 'https://api.twitter.com/1.1/statuses/show.json?id={}',
            'doc_url': 'https://dev.twitter.com/rest/reference/get/statuses/show/%3Aid',
            'keys': ['consumer-key', 'consumer-secret', 'access-token', 'access-token-secret'],
            'poll_interval': 10
        }
    elif event['call'] == 'fetch':
        twitter = Twython(
            event['keys']['consumer-key'],
            event['keys']['consumer-secret'],
            event['keys']['access-token'],
            event['keys']['access-token-secret'])
        status = twitter.show_status(id=event['params']['id'])
        return {
            'status_code': 200,
            'result': [status]
        }
