from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json
import logging
import os
import random
import sys


class WorldCupSlackReporter:
    def __init__(self):
        self.today_url = 'https://www.google.se/search?q=world+cup+today&hl=en'
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        self.hours_to_add = 0
        self.matches = {}
        self.sleep = 43200

        self.sem = asyncio.Semaphore(5)
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
        self.logger = logging.getLogger(__file__)
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.project_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

        self.slack_instances = []
        self.slack_payload = None
        self.output = True

    async def url_get(self, url):
        '''
        a normal web page download, with headers to make us look like a normal browser
        the response i checked, and if not OK raises an exception
        if all is OK, return a beautifulsoup'd page
        '''
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
    def emojify(phrase):
        '''
        EMOJIFY ALL THE THINGS!
        yeah i know the dict looks like poo poo, but now at least it doesnt take up 50 rows
        '''
        emojis = {
            '08:00': ':clock8:', '09:00': ':clock9:', '10:00': ':clock10:',
            '11:00': ':clock11:', '12:00': ':clock12:', '13:00': ':clock1:',
            '14:00': ':clock2:', '15:00': ':clock3:', '16:00': ':clock4:',
            '17:00': ':clock5:', '18:00': ':clock6:', '19:00': ':clock7:',
            '20:00': ':clock8:', '21:00': ':clock9:', '22:00': ':clock10:',
            'Already started': ':repeat:', 'Already ended': ':checkered_flag:',
            'Russia': ':flag-ru:', 'Saudi Arabia': ':flag-sa:',
            'Egypt': ':flag-eg:', 'Uruguay': ':flag-uy:',
            'Morocco': ':flag-ma:', 'Iran': ':flag-ir:',
            'Portugal': ':flag-pt:', 'Spain': ':flag-es:',
            'France': ':flag-fr:', 'Australia': ':flag-au:',
            'Argentina': ':flag-ar:', 'Iceland': ':flag-is:',
            'Peru': ':flag-pe:', 'Denmark': ':flag-dk:',
            'Croatia': ':flag-hr:', 'Costa Rica': ':flag-cr:',
            'Serbia': ':flag-rs:', 'Germany': ':flag-de:',
            'Mexico': ':flag-mx:', 'Brazil': ':flag-br:',
            'Switzerland': ':flag-ch:', 'Sweden': ':flag-se:',
            'South Korea': ':flag-kr:', 'Belgium': ':flag-be:',
            'Panama': ':flag-pa:', 'Tunisia': ':flag-tn:',
            'England': ':flag-england:', 'Colombia': ':flag-co:',
            'Japan': ':flag-jp:', 'Poland': ':flag-pl:',
            'Senegal': ':flag-sn:', 'Nigeria': ':flag-ng:'

        }
        return emojis.get(phrase, ':question:')

    @staticmethod
    def calc_seconds(timestring):
        try:
            hour = int(timestring[:2])
            minute = int(timestring[-2:])
        except Exception:
            return 5
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now:  # if the target is before now, add one day
            target += timedelta(days=1)
        diff = target - now
        diff -= timedelta(seconds=600)
        return diff.seconds

    @staticmethod
    def get_info(match, conlist):
        '''
        in order to not have to type .contents[] a hundred times
        '''
        for i in conlist:
            match = match.contents[i]
        return match

    @staticmethod
    def goalfixer(goal):
        '''
        checks that there is a number present or returns 0
        '''
        if '(' in goal:
            rg = goal.replace(' ', '').replace(')', '')
            goal = rg.split('(')
            try:
                goal = (int(goal[0]), int(goal[1]))
            except Exception:
                goal = (0, 0)
        else:
            try:
                goal = (int(goal[0]), None)
            except Exception:
                goal = (0, None)
        return goal

    def _output(self, *message):
        if self.output:
            m = '{}\n'.format(' '.join(message))
            sys.stdout.write(m)
            with open(os.path.join(self.project_path, 'logs', 'banana.log'), 'a+') as logfile:
                logfile.write(f'{datetime.now()}: {m}')

    def status(self, text, match, conlist):
        '''
        adds text to status if present, else just returns text
        '''
        try:
            text += self.get_info(match, conlist).text.lower()
        except Exception:
            text = text
        return text

    async def get_todays_matches(self):
        '''
        set up all of todays matches
        preferably run in the morning to give everyone a schedule to look forward to
        '''
        try:
            page = await self.url_get(self.today_url)
        except ConnectionError as e:
            self.logger.error(e)
            return
        matches = page.findAll('div', class_='imspo_mt__mtc-no')
        message = 'Today\'s matches:\n'
        for match in matches:
            status = 0
            match = match.contents[0]
            hteam = self.get_info(match, [4, 1, 1, 0]).text
            hteamgoals = self.goalfixer(self.get_info(match, [4, 1, 0]).text)
            ateam = self.get_info(match, [5, 1, 1, 0]).text
            ateamgoals = self.goalfixer(self.get_info(match, [5, 1, 0]).text)
            match_type = self.get_info(match, [1, 0, 0, 2]).text
            try:
                when = self.get_info(match, [2, 2, 0, 0, 0]).contents
                when = when[0].text, when[1].text
            except Exception as e:
                statustext = self.status('', match, [2, 2, 0])
                if not any(x in statustext for x in ('today', 'live', 'half')):
                    continue
                when = ('Today', 'Already started') if 'ft' not in statustext else ('Today', 'Already ended')
                status = 1 if 'started' in when[1] else 2
            if when[0] not in ('Idag', 'Today'):
                continue
            start_time = (datetime.strptime(when[1], '%H:%M') + timedelta(hours=self.hours_to_add)).strftime('%H:%M') if 'Already' not in when[1] else when[1]
            self.sleep = min(self.sleep, self.calc_seconds(start_time))
            match_id = hteam + ateam
            if match_id not in self.matches:
                self.matches[match_id] = {
                    'score': f'{hteamgoals[0]} - {ateamgoals[0]}',
                    'goalcount': hteamgoals[0] + ateamgoals[0],
                    'event_ids': [],
                    'status': status,
                    'hteam': hteam,
                    'ateam': ateam,
                    'half-time': False,
                    'redflag': {
                        'h': False,
                        'a': False
                    },
                    'match_type': match_type.lower()
                }
            hinfo = self.get_info(match, [4, 1, 1, 0, 2, 0])
            ainfo = self.get_info(match, [5, 1, 1, 0, 2, 0])
            if hinfo.get('style') != 'display:none' and not self.matches.get(match_id).get('redflag').get('h'):
                self.matches[match_id]['redflag']['h'] = True
            if ainfo.get('style') != 'display:none' and not self.matches.get(match_id).get('redflag').get('a'):
                self.matches[match_id]['redflag']['a'] = True
            add_score = ' vs ' if 'Already' not in when[1] else f' {hteamgoals[0]} - {ateamgoals[0]} '
            if all([hteamgoals[1], ateamgoals[1]]):
                add_score = add_score.replace('-', f'({hteamgoals[1]}) - ({ateamgoals[1]})')
            self._output(f'{self.matches.get(match_id)}')
            message += f'{self.emojify(start_time)} *{start_time}*: {hteam} {self.emojify(hteam)}{add_score}{self.emojify(ateam)} {ateam} ({match_type})\n'
        if message == 'Today\'s matches:\n':
            self.sleep = 0
            return
        self._output(f'sleeping {self.sleep} seconds ({str(timedelta(seconds=self.sleep))})')
        asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def get_current_matches(self):
        '''
        main logic for getting updates in ongoing matches
        '''
        try:
            page = await self.url_get(self.today_url)
        except ConnectionError as e:
            self.logger.error(e)
            return
        matches = page.findAll('div', class_='imspo_mt__mtc-no')
        local_matches = []
        for match in matches:
            match = match.contents[0]
            message = ''
            hteam = self.get_info(match, [4, 1, 1, 0]).text
            hteamgoals = self.goalfixer(self.get_info(match, [4, 1, 0]).text)
            ateam = self.get_info(match, [5, 1, 1, 0]).text
            ateamgoals = self.goalfixer(self.get_info(match, [5, 1, 0]).text)
            match_id = hteam + ateam
            if match_id not in self.matches:
                continue
            self._output(f'{hteam} {hteamgoals[0]} - {ateamgoals[0]} {ateam}')
            local_matches.append(match_id)
            status = ''
            status = self.status(status, match, [2, 2, 0])
            self._output(f'{match_id} status: {status}')
            hinfo = self.get_info(match, [4, 1, 1, 0, 2, 0])
            ainfo = self.get_info(match, [5, 1, 1, 0, 2, 0])
            if hinfo.get('style') != 'display:none' and not self.matches.get(match_id).get('redflag').get('h'):
                message += f'{hteam} just received a red card!\n'
                self.matches[match_id]['redflag']['h'] = True
                self._output(f'{hteam} red flag update')
            if ainfo.get('style') != 'display:none' and not self.matches.get(match_id).get('redflag').get('a'):
                message += f'{ateam} just received a red card!\n'
                self.matches[match_id]['redflag']['a'] = True
                self._output(f'{ateam} red flag update')
            score = f'{hteamgoals[0]} - {ateamgoals[0]}'

            if any(x in status for x in ('live', 'pågår')) and self.matches.get(match_id).get('status') == 0:
                message += f'{hteam} {self.emojify(hteam)} vs {self.emojify(ateam)} {ateam} just started!\n'
                self.matches[match_id]['status'] = 1
                self._output(f'{match_id} match start update')

            if self.matches.get(match_id).get('status') in (0, 2):
                continue

            if score != self.matches.get(match_id).get('score'):
                message += f'GOOOOOOOAL!\n{hteam} {self.emojify(hteam)} {hteamgoals[0]} - {ateamgoals[0]} {self.emojify(ateam)} {ateam}\n'
                if (hteamgoals[0] + ateamgoals[0]) <= self.matches.get(match_id).get('goalcount'):
                    message = message.replace('GOOOOOOOAL!', 'Score update:')
                self.matches[match_id]['goalcount'] = hteamgoals[0] + ateamgoals[0]
                self.matches[match_id]['score'] = score
                self._output(f'{match_id} goal update')

            if any(x in status for x in ('half–time', 'halvtid', 'ht', 'half')) and not self.matches.get(match_id).get('half-time'):
                self.matches[match_id]['half-time'] = True
                message += f'Half-time: {hteam} {self.emojify(hteam)} {hteamgoals[0]} vs {ateamgoals[0]} {self.emojify(ateam)} {ateam}\n'
                self._output(f'{match_id} half-time update')

            if any(x in status for x in ('ended', 'full-time', 'ft', 'full')):
                hwin = self.get_info(match, [4, 2, 0])
                awin = self.get_info(match, [5, 2, 0])
                if hwin.get('style') == 'display:none' and awin.get('style') == 'display:none' and 'group' not in self.matches.get(match_id).get('match_type'):
                    continue
                separator = '-'
                if all([hteamgoals[1], ateamgoals[1]]):
                    separator = separator.replace('-', f'({hteamgoals[1]}) - ({ateamgoals[1]})')
                message += f'Match ended! Final score:\n{hteam} {self.emojify(hteam)} {hteamgoals[0]} {separator} {ateamgoals[0]} {self.emojify(ateam)} {ateam}\n'
                self.matches[match_id]['status'] = 2
                self._output(f'{match_id} end of match update')
            asyncio.ensure_future(self._slack_output(message.rstrip()))

    async def monitor(self):
        '''
        assure that current matches are scraped regularily
        scraping is done between 55 and 87 seconds randomly in order to potentially avoid suspicious acitivity
        '''
        if len(self.matches) > 0:
            all_done = False
        else:
            all_done = True
        while not all_done:
            asyncio.ensure_future(self.get_current_matches())
            await asyncio.sleep(random.choice(range(55, 87)))
            if all([x.get('status') == 2 for k, x in self.matches.items()]):
                all_done = True

    async def _slack_output(self, message):
        '''
        sends message to all the slack clients
        '''
        async def _send(url, output):
            try:
                async with self.sem, self.session.post(url, data=output) as response:
                    return await response.read(), response.status
            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(e)
        for si in self.slack_instances:
            output = dict(self.slack_payload)
            if si.get('participants'):
                for country, name in si.get('participants').items():
                    newtext = f'{country} ({name})'
                    message = message.replace(country, newtext)
            output['text'] = message
            output['channel'] = si.get('channel')
            asyncio.ensure_future(_send(si.get('webhook'), json.dumps(output)))
