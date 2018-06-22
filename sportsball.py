from app import google as sportsball  # other choices are fd and wc, just replace google
import asyncio
import json
import os
import sys


async def main(file):
    '''
    just starts up the class run it until all of todays matches are done
    feel free to use the class in other ways if preferred
    you can specify another settings file than settings.json as an argument, for testing purposes
    '''
    WCS = sportsball.WorldCupSlackReporter()
    if not file:
        with open(os.path.join(WCS.project_path, 'settings', 'settings.json'), 'r') as settings_file:
            settings = json.load(settings_file)
    else:
        with open(file, 'r') as settings_file:
            settings = json.load(settings_file)
    WCS.slack_instances = settings.get('slack_instances')
    WCS.slack_payload = settings.get('slack_payload')
    # WCS.headers = {'X-Auth-Token': settings.get('football-data-token')}  # uncomment if using fd.py
    WCS.hours_to_add = settings.get('hours_to_add') if settings.get('hours_to_add') else 0  # only for google.py
    await WCS.get_todays_matches()
    await asyncio.sleep(WCS.sleep)
    await WCS.monitor()
    await WCS.session.close()

if __name__ == '__main__':
    try:
        file = sys.argv[1]
    except Exception:
        file = None
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(file))
    loop.close()
