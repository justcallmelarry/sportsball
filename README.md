# SPORTSBALL

A slack integration for updating start, stop, half-time and goals of WC 2018.

I am personally running the script called `google.py` as it seems more reliable than the API's tested.
It's also more basic, which is probably why the API's are having more trouble sorting the information.
This, however, means that I am spending little to no time on the other updaters, but feel free to fork away or send me a PR if you want any updates for yourself. This also means that everything covered in this readme is concerning the `google.py`-script, and the other two are deprecated.
Just updated with a breaking change, sorry for that, but old code is still available as a release (v1.0) if needed.


## Setup
You will need a `settings.json` file with the following information (located in `/settings`):

_(See `docs/settings.json.example`)_
```
{
  "slack_instances": [
    {
      "webhook": "https://hooks.slack.com/services/your/webhook/here",
      "channel": "#wc2018"
      "participants": {  //optional, see description below. currently only used by google.py
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
    "username": "Sportsball",  //that's right, it can be called anything, doesn't have to be Sportsball
    "icon_emoji": ":soccer:",
    "link_names": 1
  },
  "football-data-token": "token",  //only used by fd.py
  "hours_to_add": 0 //this is if you're running it on a server that does not have the same time zone as your local time, currently only used by google.py
}
```
_More instances of slack are supported, just add more objects with webhook and channel (and optionally participants)_

_The participants object can be added to slack_instance. Countries will then be substituted for the country name followed by the name in brackets in the Slack message for that slack_instance._

Requires: python 3.6

Modules not installed by deafult:
* aiohttp
* bs4
* dateutil (python-dateutil)

_Can be installed via requirements.txt_

### Docker
Optionally you can build and run the docker file in order to avoid having to install python3 and/or it's dependencies. Do not forget to _first create a valid `settings/settings.json`-file with the correct information_.
The Dockerfile will start an instance and run `sportsball.py`.

_The crontab seems to work so-so, so for now that part i scrapped. Please run the docker image from cron wherever it is run instead._


## How it works:
Once you start running the script it will update on today's matches, then keep running and update about new goals, half-time score and match endings (with score). It will also (hopefully) tell you if there are any red cards (at least one per team) dealt out during the match.
Once all of todays matches are ended it will exit.

Personally running it in a docker container with a crontab looking exactly like the example.

The different .py files use different ways to find out the information needed:
* `google.py` is a webscraper that uses googles real time updates
* `wc.py` uses the API of https://github.com/estiens/world_cup_json
* `fd.py` uses the API of football-data.org (a token from there is needed)


## Disclaimer
All of the updaters work on a scraper, which is inherently not a very safe way to gather information.
The code is mostly written in a few hours and then trying to monkey-patch once an error is found.
Do not use the code as a good example of python code, and keep in mind that the data it relies upon might fail, or receive updates that will force a re-write of the scrapers at any time.
