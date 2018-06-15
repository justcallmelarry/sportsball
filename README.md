# SPORTSBALL

A slack integration that uses the API of https://github.com/estiens/world_cup_json in order to update the latest events of the wc (2018).


Needs a `settings.json` file with the following information:
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


Requires: python 3.6
Modules not installed by deafult:
* aiohttp
* dateutil (python-dateutil)
