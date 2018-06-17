from dateutil import parser
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
import logging
import os
import time
from bs4 import BeautifulSoup as BS


class WorldCupSlackReporter:
    def __init__(self):
        self.today_url = 'http://worldcup.sfg.io/matches/today'

        self.schedule_url = 'https://www.google.se/search?q=world+cup+schedule'
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        self.hours_to_add = 0

        self.sem = asyncio.Semaphore(5)
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
        self.logger = logging.getLogger(__file__)
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.filepath = os.path.abspath(os.path.dirname(__file__))
        self.slack_instances = []
        self.slack_payload = None
        self.update_rate = 60

        self.matches = {}
        self.event_types = {
            'goal-own': '[country]: Oh no, [player] just scored a goal on the wrong side of the field!',
            'yellow-card': '[country]: [player] just received a yellow card',
            'red-card': '[country]: [player] just received a red card',
            'goal': '[country]: [player] just scored a goooooooal!',
            'goal-penalty': '[country]: [player] gets a goal penalty'
        }

    async def url_get(self, url):
        async def _get(url):
            try:
                async with self.sem, self.session.get(url, headers=self.headers) as response:
                    return await response.read(), response.status
            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(e)
                return e, 999
        response = await _get(url)
        if response[1] != 200:
            raise ConnectionError(f'did not get a 200 response: {response[0]}')
        the_page = BS(response[0], 'html.parser')
        return the_page

    @staticmethod
    def get_info(match, conlist):
        for i in conlist:
            match = match.contents[i]
        return match.text

    async def get_todays_matches(self):
        try:
            page = await self.url_get(self.schedule_url)
        except ConnectionError as e:
            self.logger.error(e)
            return
        matches = page.findAll('div', class_='imspo_mt__mtc-no')
        message = 'Today\'s matches:\n'
        for match in matches:
            started = False
            match = match.contents[0]
            hteam = self.get_info(match, [2, 1, 1, 0])
            ateam = self.get_info(match, [4, 1, 1, 0])
            match_type = self.get_info(match, [1, 0, 0, 2])
            try:
                when = match.contents[0].contents[4].contents[0].contents[0].contents[0].contents
                when = when[0].text, when[1].text
            except Exception as e:
                started = True
                when = ('Today', 'Already started')
            if when[0] not in ('Idag', 'Today'):
                continue
            start_time = (datetime.strptime(when[1], '%H:%M') + timedelta(hours=self.hours_to_add)).strftime('%H:%M') if when[1] != 'Already started' else when[1]
            match_id = hteam + ateam
            if match_id not in self.matches:
                self.matches[match_id] = {
                    'score': '0 - 0',
                    'event_ids': [],
                    'status': 0 if not started else 1,
                    'time': None if not started else time.time(),
                    'half-time': False
                }
            message += f'{start_time}: {hteam} vs {ateam} ({match_type})\n'
        asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def get_current_matches(self):
        try:
            page = await self.url_get(self.schedule_url)
        except ConnectionError as e:
            self.logger.error(e)
            return
        matches = page.findAll('div', class_='imspo_mt__mtc-no')
        for match in matches:
            match = match.contents[0]
            message = ''
            hteam = self.get_info(match, [2, 1, 1, 0])
            hteamgoals = self.get_info(match, [2, 1, 0])
            ateam = self.get_info(match, [4, 1, 1, 0])
            ateamgoals = self.get_info(match, [4, 1, 0])
            match_id = hteam + ateam
            if match_id not in self.matches:
                continue
            try:
                status = match.contents[0].contents[4].contents[0].contents[1].contents[0].text
            except Exception:
                status = ''
            try:
                status += match.contents[0].contents[4].contents[0].contents[1].contents[2].text
            except Exception:
                status = status
            status = status.lower()
            print(status)
            score = f'{hteamgoals} - {ateamgoals}'

            if any(x in status.lower() for x in ('live', 'pågår')) and self.matches.get(match_id).get('status') == 0:
                message += f'{hteam} vs {ateam} just started!\n'
                self.matches[match_id]['status'] = 1
                self.matches[match_id]['time'] = time.time()

            if self.matches.get(match_id).get('status') in (0, 2):
                continue

            if any(x in status for x in ('half-time', 'halvtid', 'ht')) and not self.matches.get(match_id).get('half-time'):
                self.matches[match_id]['half-time'] = True
                message += f'Half-time: {hteam} {hteamgoals} vs {ateamgoals} {ateam}\n'

            if score != self.matches.get(match_id).get('score'):
                message += f'GOOOOOOOAL!\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['score'] = score

            if any(x in status for x in ('ended', 'full-time', 'ft')):
                message += f'Match ended! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
                self.matches[match_id]['status'] = 2
            timediff = time.time() - self.matches.get(match_id).get('time')
            if timediff > 9000:
                message += f'Match (probably) ended (2.5h since start)! Final score:\n{hteam} {hteamgoals} - {ateamgoals} {ateam}\n'
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


async def main():
    WCS = WorldCupSlackReporter()
    with open(os.path.join(WCS.filepath, 'settings.json'), 'r') as settings_file:
        settings = json.loads(settings_file.read())
        WCS.slack_instances = settings.get('slack_instances')
        WCS.slack_payload = settings.get('slack_payload')
        WCS.hours_to_add = settings.get('hours_to_add')
    await WCS.get_todays_matches()
    await asyncio.sleep(5)
    asyncio.ensure_future(WCS.monitor())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
    loop.close()
