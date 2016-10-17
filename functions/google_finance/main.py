import sys
sys.path.append('./site-packages')
import requests
import json

BASE_URL = 'http://finance.google.com/finance/info?client=ig&q={}'

def lambda_function(event, context):
	if event['call'] == 'metadata':
		return {
			'name': 'google-finance',
			'description': 'Google Finance quotes',
			'id_field': 't',
			'api_url': 'http://finance.google.com/finance/info?client=ig&q={}',
			'doc_url': '',
			'poll_interval': 10
		}
	elif event['call'] == 'fetch':
		symbols = event.get('params', {}).get('symbols', '')
		resp = requests.get(BASE_URL.format(symbols))
		if resp.status_code == 200:
			result = json.loads(resp.text[3:]) # need to skip the weird leading slashes
			return {
				'status_code': 200,
				'result': result
			}
		else:
			return {
				'status_code': resp.status_code,
				'result': resp.text
			}

