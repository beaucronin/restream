# Restream Pushpin

To run this container locally for dev and testing purposes, use the command:

```bash
docker run -p 7999:7999 -p 5561:5561 -e "target=<localhost ip>:5000" fanout/pushpin
```

Note that using just `localhost` doesn't seem to work - you may need to use the local IP of your machine.