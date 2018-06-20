# SPORTSBALL

A slack integration for updating start, stop, half-time and goals of WC 2018.

I am personally running the script called `google.py` as it seems more reliable than the API's tested.
It's also more basic, which is probably why the API's are having more trouble sorting the information.
This, however, means that I am spending little to no time on the other updaters, but feel free to fork away or send me a PR if you want any updates for yourself.


### Setup
You will need a `settings.json` file with the following information (located in the same folder):
(See settings.json.example)
```
{
  "slack_instances": [
    {
      "webhook": "https://hooks.slack.com/services/your/webhook/here",
      "channel": "#wc2018"
      "participants": {
            "Argentina": "Jason",
            "Australia": "Euan",
            "Belgium": "Ian",
            ...
            "Switzerland": "Russ",
            "Tunisia": "Neil",
            "Uruguay": "Gill"
        }
    }
  ],
  "slack_payload": {
    "username": "Sportsball",
    "icon_emoji": ":soccer:",
    "link_names": 1
  },
  "football-data-token": "token",
  "hours_to_add": 0 //this is if you're running it on a server that does not have the same time zone as your local time
}
```
_More instances of slack are supported, just add more dicts with webhook and channel_

_Optionally, a participants array can be added to slack_instance. Countries will then be substituted for the country name followed by the name in brackets in the Slack message_

Requires: python 3.6

Modules not installed by deafult:
* aiohttp
* dateutil (python-dateutil)


### How it works:
Once you start running the script it will update on today's matches, then keep running and update about new goals, half-time score and match endings (with score).
Personally running it on a server with a cronjob that starts a screen with the script at 9 in the morning, then kills the screen in the evening.

The different .py files use different ways to find out the information needed:
* `wc.py` uses the API of https://github.com/estiens/world_cup_json
* `fd.py` uses the API of football-data.org (a token from there is needed)
* `google.py` is a webscraper that uses googles real time updates


### Disclaimer
All of the updaters work on a scraper, which is inherently not a very safe way to gather information.
The code is mostly written in a few hours and then trying to monkey-patch once an error is found.
Do not use the code as a good example of python code, and keep in mind that the data it relies upon might fail.
