import sys
sys.path.append('./site-packages')
import requests

BASE_URL = "https://api.nytimes.com/svc/topstories/v2/{}.json?api-key={}"

def lambda_function(event, context):
	if event['call'] == 'metadata':
		return {
			'name': 'nyt-top',
			'description': 'New York Times top stories',
			'id_field': 'short_url',
			'api_url': 'https://api.nytimes.com/svc/topstories/v2/{}.json',
			'doc_url': 'https://developer.nytimes.com/top_stories_v2.json',
			'keys': ['api-key'],
			'poll_interval': 100 # 1000 calls per day rate limit
		}
	elif event['call'] == 'fetch':
		resp = requests.get(BASE_URL.format(event.get('params', {}).get('section', 'home'), event['keys']['api-key']))
		if resp.status_code == 200:
			return {
				'status_code': 200,
				'result': resp.json()['results']
			}
		else:
			return {
				'status_code': resp.status_code,
				'result': resp.text
			}

