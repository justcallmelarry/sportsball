import aiohttp
import asyncio
import logging
import json
import sys
import os
import time
from dateutil import parser


class WorldCupSlackReporter:
    def __init__(self):
        self.today_url = 'http://worldcup.sfg.io/matches/today'
        self.curmatch_url = 'http://worldcup.sfg.io/matches/current'
        self.results_url = 'http://worldcup.sfg.io/matches/results'

        self.sem = asyncio.Semaphore(5)
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
        self.logger = logging.getLogger(__file__)
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.slack_instances = []
        self.slack_payload = None
        self.update_rate = 90

        self.matches = {}
        self.event_types = {
            'goal-own': 'Oh no, [player] just scored a goal on the wrong side of the field!',
            'yellow-card': '[player] just received a yellow card',
            'red-card': '[player] just received a red card',
            'goal': '[player] just scored a goooooooal!',
            'goal-penalty': '[player] gets a goal penalty'
        }

    async def api_get(self, url):
        async def _get(url):
            try:
                async with self.sem, self.session.get(url) as response:
                    return await response.read(), response.status
            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(e)
                return e, 999
        response = await _get(url)
        if response[1] != 200:
            raise ConnectionError(f'did not get a 200 response: {response[0]}')
        return json.loads(response[0])

    async def get_todays_matches(self):
        try:
            matches = await self.api_get(self.today_url)
        except ConnectionError as e:
            self.logger.error(e)
        message = 'Today we are looking forward to:\n'
        for match in matches:
            hteam = match.get('home_team').get('country')
            ateam = match.get('away_team').get('country')
            venue = match.get('location') + ', ' + match.get('venue')
            start_time = parser.parse(match.get('datetime')).strftime('%H:%M')
            match_id = match.get('home_team').get('code') + match.get('away_team').get('code')
            if match_id not in self.matches:
                self.matches[match_id] = {
                    'score': '0 - 0',
                    'event_ids': [],
                    'status': 0,
                    'time': None
                }
            message += f'{start_time}: {hteam} vs {ateam} @ {venue}\n'
        asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def get_current_matches(self):
        try:
            matches = await self.api_get(self.today_url)
        except ConnectionError as e:
            self.logger.error(e)
        for match in matches:
            message = ''
            hteam = match.get('home_team').get('country')
            hteamgoals = match.get('home_team').get('goals')
            ateam = match.get('away_team').get('country')
            ateamgoals = match.get('away_team').get('goals')
            score = f'{hteamgoals} - {ateamgoals}'
            match_id = match.get('home_team').get('code') + match.get('away_team').get('code')

            if match.get('status') == 'in progress' and self.matches.get(match_id).get('status') == 0:
                message += f'{hteam} vs {ateam} just started!\n'
                self.matches[match_id]['status'] = 1
                self.matches[match_id]['time'] = time.time()

            if self.matches.get(match_id).get('status') == 2:
                continue
            events = match.get('home_team_events') + match.get('away_team_events')
            for eid in sorted(events, key=lambda x: x.get('id')):
                if eid.get('id') in self.matches.get(match_id).get('event_ids'):
                    continue
                self.matches[match_id]['event_ids'].append(eid.get('id'))
                event_text = self.event_types.get(eid.get('type_of_event')).replace('[player]', eid.get('player'))
                if not event_text:
                    continue
                message += f'{hteam} (vs {ateam}): {event_text}\n'
            if score != self.matches.get(match_id).get('score'):
                message += f'GOOOOAL! {hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['score'] = score
            if match.get('status') == 'completed' or match.get('winner'):
                message += f'Match ended! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['status'] = 2
            timediff = time.time() - self.matches.get(match_id).get('time')
            if timediff > 7200:
                message += f'Match (probably) ended (120 minutes since start)! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['status'] = 2
            asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def monitor(self):
        asyncio.ensure_future(self.get_current_matches())
        await asyncio.sleep(self.update_rate)
        asyncio.ensure_future(self.monitor())

    @staticmethod
    def _output(*message):
        sys.stdout.write('{}\n'.format(' '.join(message)))

    async def _slack_output(self, message):
        async def _send(url, output):
            try:
                async with self.sem, self.session.post(url, data=output) as response:
                    return await response.read(), response.status
            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(e)
        for si in self.slack_instances:
            output = dict(self.slack_payload)
            output['text'] = message
            output['channel'] = si.get('channel')
            asyncio.ensure_future(_send(si.get('webhook'), json.dumps(output)))


async def main():
    WCS = WorldCupSlackReporter()
    with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'settings.json'), 'r') as settings_file:
        settings = json.loads(settings_file.read())
        WCS.slack_instances = settings.get('slack_instances')
        WCS.slack_payload = settings.get('slack_payload')
    await WCS.get_todays_matches()
    asyncio.ensure_future(WCS.monitor())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
