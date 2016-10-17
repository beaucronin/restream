import sys
sys.path.append('./site-packages')
import requests

BASE_URL = 'https://query.yahooapis.com/v1/public/yql?q=select * from yahoo.finance.quote where symbol in ("{}")&format=json&env=store://datatables.org/alltableswithkeys'

def lambda_function(event, context):
	if event['call'] == 'metadata':
		return {
			'name': 'yahoo-finance',
			'description': 'Yahoo Finance quotes',
			'id_field': 'Symbol',
			'api_url': '',
			'doc_url': '',
			'poll_interval': 10
		}
	elif event['call'] == 'fetch':
		symbols = event.get('params', {}).get('symbols', '')
		resp = requests.get(BASE_URL.format(symbols))
		if resp.status_code == 200:
			result = resp.json()['query']['results']['quote']
			if len(symbols.split(',')) == 1:
				result = [result]
			return {
				'status_code': 200,
				'result': result
			}
		else:
			return {
				'status_code': resp.status_code,
				'result': resp.text
			}

