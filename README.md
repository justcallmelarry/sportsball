# SPORTSBALL

A slack integration for updating start, stop, half-time and goals of WC 2018.


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
  },
  "football-data-token": "token",
  "hours_to_add": 0
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

The different .py files use different ways to find out the information needed:
* wc.py uses the API of https://github.com/estiens/world_cup_json
* fd.py uses the API of football-data.org (a token from there is needed)
* google.py is a webscraper that uses googles real time updates
