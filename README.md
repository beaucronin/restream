# restreaming
Convert REST APIs to subscribable streams

I do quite a bit of work visualizing streaming data, and I have been continually frustrated with the difficulty of finding public streams to work with. First of all, there are very few public streams to work with. Even twitter, the most prominent of public real-time data sources, makes it hard to use their streaming API for anything beyond purely personal use. That said, there are a number of more-or-less public REST APIs that provide time-sensitive data - the NYT top story API, for example, and various financial data services. It would be great to have generic tooling to convert these polling-based interfaces into push services.

I want a system that has the following properties:

- I don't want to worry about maintaining processes; it should use mature, declarative devops tooling
- Implementing a new stream does not require infrastructure effort beyond what is particular to that stream - just a bit of config, and the API-specific code. And API-specific logic should be stateless and as simple as possible; preferably just transforming some JSON
- Multiple connections can be made to a stream without increasing load on the backing REST API; this is both a matter of behaving properly toward the underlying API providers, as well as a necessity for staying within the usage limits typically associated with a given API key
- Speaking of which, API keys are securely managed by a central store
