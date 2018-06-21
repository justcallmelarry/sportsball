from dateutil import parser
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
import logging
import os
import time


class WorldCupSlackReporter:
    def __init__(self):
        self.today_url = 'http://worldcup.sfg.io/matches/today'

        self.sem = asyncio.Semaphore(5)
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
        self.logger = logging.getLogger(__file__)
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.project_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self.slack_instances = []
        self.slack_payload = None
        self.update_rate = 90

        self.matches = {}
        self.event_types = {
            'goal-own': '[country]: Oh no, [player] just scored a goal on the wrong side of the field!',
            'yellow-card': '[country]: [player] just received a yellow card',
            'red-card': '[country]: [player] just received a red card',
            'goal': '[country]: [player] just scored a goooooooal!',
            'goal-penalty': '[country]: [player] gets a goal penalty'
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
        with open(os.path.join(self.project_path, 'logs', 'match-requests.log'), 'a+') as logfile:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data = json.dumps(json.loads(response[0]))
            logfile.write(f'{now}: {data}\n')
        return json.loads(response[0])

    async def get_todays_matches(self):
        try:
            matches = await self.api_get(self.today_url)
        except ConnectionError as e:
            self.logger.error(e)
        message = 'Today\'s matches:\n'
        for match in matches:
            hteam = match.get('home_team').get('country')
            ateam = match.get('away_team').get('country')
            venue = match.get('location') + ', ' + match.get('venue')
            start_time = (parser.parse(match.get('datetime')) + timedelta(hours=2)).strftime('%H:%M')
            match_id = match.get('home_team').get('code') + match.get('away_team').get('code')
            if match_id not in self.matches:
                self.matches[match_id] = {
                    'score': 0,
                    'goals': {'h': 0, 'a': 0},
                    'event_ids': [],
                    'status': 0,
                    'time': None,
                    'half-time': False
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

            score = hteamgoals + ateamgoals
            match_id = match.get('home_team').get('code') + match.get('away_team').get('code')
            if hteamgoals < self.matches.get(match_id).get('goals').get('h'):
                hteamgoals = self.matches.get(match_id).get('goals').get('h')
            if ateamgoals < self.matches.get(match_id).get('goals').get('a'):
                ateamgoals = self.matches.get(match_id).get('goals').get('a')

            if match.get('status') == 'in progress' and self.matches.get(match_id).get('status') == 0:
                message += f'{hteam} vs {ateam} just started!\n'
                self.matches[match_id]['status'] = 1
                self.matches[match_id]['time'] = time.time()

            if self.matches.get(match_id).get('status') == 2:
                continue
            for item in match.get('home_team_events'):
                item['code'] = match.get('home_team').get('code')
            for item in match.get('away_team_events'):
                item['code'] = match.get('away_team').get('code')
            events = match.get('home_team_events') + match.get('away_team_events')
            for eid in sorted(events, key=lambda x: x.get('id')):
                if eid.get('id') in self.matches.get(match_id).get('event_ids'):
                    continue
                self.matches[match_id]['event_ids'].append(eid.get('id'))
                event_text = self.event_types.get(eid.get('type_of_event'), '').replace('[player]', eid.get('player')).replace('[country]', eid.get('code'))
                if event_text == '':
                    continue
                message += f'{event_text}\n'
            if match.get('time') == 'half-time' and not self.matches.get(match_id).get('half-time'):
                self.matches[match_id]['half-time'] = True
                message += f'Half-time: {hteam} {hteamgoals} vs {ateamgoals} {ateam}\n'
            if score > self.matches.get(match_id).get('score'):
                message += f'Score update: {hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['score'] = score
            if match.get('status') == 'completed' or match.get('winner') or match.get('time') == 'full-time':
                message += f'Match ended! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['status'] = 2
            if self.matches.get(match_id).get('status') == 1:
                timediff = time.time() - self.matches.get(match_id).get('time')
                if timediff > 9000:
                    message += f'Match (probably) ended (2h since start)! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                    self.matches[match_id]['status'] = 2
            asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def monitor(self):
        asyncio.ensure_future(self.get_current_matches())
        await asyncio.sleep(self.update_rate)
        asyncio.ensure_future(self.monitor())

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
