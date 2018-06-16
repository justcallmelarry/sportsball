# SPORTSBALL

A slack integration that uses the API of https://github.com/estiens/world_cup_json in order to update the latest events of the wc (2018).


### Setup
You will need a `settings.json` file with the following information (located in the same folder):
```
{
  "slack_instances": [
    {
      "webhook": "https://hooks.slack.com/services/your/webhook/here",
      "channel": "#wc2018"
    }
  ],
  "slack_payload": {
    "username": "Sportsball",
    "icon_emoji": ":soccer:",
    "link_names": 1
  }
}
```
_More instances of slack are supported, just add more dicts with webhook and channel_

Requires: python 3.6

Modules not installed by deafult:
* aiohttp
* dateutil (python-dateutil)


### How it works:
Once you start running the script it will update on today's matches, then keep running and update about new goals, half-time score and match endings (with score).
Personally running it on a server with a cronjob that starts a screen with the script at 9 in the morning, then kills the screen in the evening.
