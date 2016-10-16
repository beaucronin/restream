# restreaming
Convert REST APIs to subscribable streams

I do quite a bit of work visualizing streaming data, and I have been continually frustrated with the difficulty of finding public streams to work with. First of all, there are very few public streams to work with. Even twitter, the most prominent of public real-time data sources, makes it hard to use their streaming API for anything beyond purely personal use. That said, there are a number of more-or-less public REST APIs that provide time-sensitive data - the NYT top story API, for example, and various financial data services. It would be great to have generic tooling to convert these polling-based interfaces into push services.

I want a system that has the following properties:

- I don't want to worry about maintaining processes; it should use mature, declarative devops tooling
- Implementing a new stream does not require infrastructure effort beyond what is particular to that stream - just a bit of config, and the API-specific code. And API-specific logic should be stateless and as simple as possible; preferably just transforming some JSON
- Multiple connections can be made to a stream without increasing load on the backing REST API; this is both a matter of behaving properly toward the underlying API providers, as well as a necessity for staying within the usage limits typically associated with a given API key
- Speaking of which, API keys are securely managed by a central store

## Subscribing to channels

First, open a websocket connection to a restream server. For example, to connect to the public restream server:

```javascript
var ws = new WebSocket('ws://sockets.embeddingjs.org/channels')
ws.onmessage = (m) => console.log(m)
```

Now subscribe to a channel:

```javascript
ws.send(JSON.stringify({ action: 'subscribe', channel: 'nyt-top' }))
```

A single client can subscribe to multiple channels, and unsubscribe as well. 

Some channels take optional or required parameters. For example, to subscribe to the changes made to an individual tweet (such as favorite and retweet counts), use the following:

```javascript
let m = {
	action: 'subscribe',
	channel: 'twitter-status',
	params: { id: '785164371995615232' }
}
ws.send(JSON.stringify(m))
```

Note that when params are sent, the param names and values should be considered part of the channel identifier. To unsubscribe to a particular channel, you need to send an unsubscribe message with the same `channel` and `param` settings.

To stop all messages, you can send `{ action: 'unsubscribe_all' }`.

### Message types

TODO

## Architecture

```
                     +-----------------------------------------------------------------------------------------+
                     | AWS                                                                                     |
                     |                                                                                         |
                     |  +-----------------------------------------------------------+     +-----------------+  |    +------------+
                     |  | ALB                                                       |     | Lambda          | <---> | REST       |
                     |  |  +-----------------------+     +-----------------------+  | +-> | Fetcher 1       |  |    | Endpoint 1 |
                     |  |  | ECS Instance          |     | ECS Instance          |  | |   +-----------------+  |    +------------+
+-------------+      |  |  |  +-----------------+  |     |  +-----------------+  |  | |                        |
| Client      |      |  |  |  | Pushpin         |  |     |  | Backend         +-------+   +-----------------+  |    +------------+
| (Browser)   |      |  |  |  |                 |  |     |  |                 |  |  |     | Lambda          | <---> | REST       |
|             | <-----------> +-7999       5561-+ <-------> +-5000            +---------> | Fetcher 2       |  |    | Endpoint 2 |
|             |      |  |  |  |                 |  |     |  |                 |  |  |     +-----------------+  |    +------------+
|             |      |  |  |  |                 |  |     |  |                 +-------+                        |
|             |      |  |  |  |                 |  |     |  |                 |  |  | |   +-----------------+  |    +------------+
+-------------+      |  |  |  +-----------------+  |     |  +-----------------+  |  | +-> | Lambda          | <---> | REST       |
                     |  |  +-----------------------+     +-----------------------+  |     | Fetcher 3       |  |    | Endpoint 3 |
                     |  +-----------------------------------------------------------+     +-----------------+  |    +------------+
                     |                                                                                         |
                     +-----------------------------------------------------------------------------------------+
```

The architecture of Restream is driven by the design requirements outlined in the introduction. The main components are:

- A [pushpin](http://pushpin.org/) process (run from a [docker container](https://github.com/fanout/docker-pushpin) published at [fanout/pushpin](https://hub.docker.com/r/fanout/pushpin/)) to handle websocket connections, and to publish events on a given to the clients subscribed to that channel.
- A backend process (run from a [docker container](https://github.com/beaucronin/restream/blob/master/backend/Dockerfile) published at [beaucronin/restream-backend](https://hub.docker.com/r/beaucronin/restream-backend/)) that manages subscriptions and tracks the state associated with each channel. This includes making sure that exactly one polling loop is enabled for each channel that currently has subscribers. This process is implemented as a [tornado web server](https://github.com/beaucronin/restream/blob/master/backend/web/app.py), and it uses
    - A Dynamo table to persist items for each channel, so that the backend process can differentiate between new, updated, and unchanged items.
    - An S3 object to store the API keys for each endpoint.
- An AWS Application Load Balancer that provides a single public address for the service, and that directs traffic by port
- An AWS Elastic Container Service cluster that contains the instances hosting the pushpin and backend process containers
- A collection of simple AWS Lambda "fetcher" functions, each of which is responsible for getting data from a single REST endpoint.

While this capability has not been developed, this architecture should enable significant scaling without muc drama - either by changing the instance types of the ECS cluster, and/or by changing the number of instances managed by the ALB and the ECS cluster. This latter, horizontal scaling option would require the use of a shared-memory caching layer such as ElasticCache to allow different backend instances to share connection state, but this wouldn't be a big deal to implement.

## Installing and Deploying

Restream makes heavy use of AWS capabilities (Lambda, Dynamo, ECS, S3, ...), so you'll want to make sure you have an AWS account whose credentials are properly configured for the CLI. If that sounds intimidating, then these install instructions are unlikely to provide enough detail.

Restream uses [Apex](http://apex.run/) to manage Lambda functions, and [terraform](https://www.terraform.io/docs/index.html) to define its AWS infrastructure. You'll need to install both of these if you want to deply your own instance of the service. Then you can do something like the following:

1. Clone this repo
2. Create a `infrastructure/terraform.tfvars` based on the template `terraform.tfvars.template` that contains your AWS keys, subnet IDs, etc.
3. Create the infra:

	```bash
	apex infra plan
	apex infra apply
	```

4. Build and deploy the Lambda functions:

	```bash 
	FIXME build script (cd functions/funcname; pip install -r requirements.txt -t )
	apex deploy
	```

If all goes well, that should be it. The service will be available at the public DNS name of the ALB that was created, and you may want to create a DNS alias with a friendlier name (for example, the public service is available at [http://sockets.embeddingjs.org:7999/](http://sockets.embeddingjs.org:7999/))

**Note that these AWS resources will incur hourly costs - the minimum config uses two t2.micro instances and an ALB.** So you're looking at about $35/month just to start, not including usage-dependent charges like bandwidth and Lambda calls.

## Adding a new channel

Whether for your own Restream instance or as a contribution to the public deployment (for example, by submitting a PR for this repo), adding a new endpoint fetcher is easy - just create a Lambda function that obeys a simple contract. The simplest thing is to look at an existing fetcher, such as the one NYT Top Stories:

```python
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
		resp = requests.get(BASE_URL.format(event.get('section', 'home'), event['keys']['api-key']))
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

```

All fetchers must be able to handle two kinds of requests. 

- A `metadata` request should simply return an object that describes the function; this information is used to configure the behavior of the restream service. 
- A `fetch` request should query the fetcher's endpoint, using the keys contained in `event['keys']`, and any parameters contained in `event['params']`. It should return a list of JSON-serializable items.

That's about it - fetchers should be simple and stateless.

One thing to keep in mind is that many APIs are rate-limited, so you'll want to set the `poll-interval` value to respect those limits. For example, an interval of 100 seconds will result in about 864 calls per day, which is under the NYT's API limit of 1000 per day.

### Add the keys

Many APIs require keys to access them, whether for security reasons or to enable rate limiting. Restream provides a central mechanism for securely storing and distributing these keys, which is a simple json file stored in an S3 location specified by the `keys_bucket` and `keys_object` teraform variables. An example keys file might look like:

```json
{
	"nyt-top": {
		"api-key": "abcd"
	},
	"nyt-newswire": {
		"api-key": "efgh"
	},
	"twitter-status": {
		"consumer-key": "lskfjlsdkf",
		"consumer-secret": "sdkgjlsdkgjlsdkgjlsdg",
		"access-token": "sdlkjlskdfjlsdkfjsldkfs",
		"access-token-secret": "sldkjlsdkfjsldkfjsldkfjsldkf"
	}
}
``` 

Each fetcher has a top-level entry, with a dict containing the key entries used in the fetch process. Note that if two fetchers share keys, their activity may count toward the same rate limits.
