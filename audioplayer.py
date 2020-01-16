#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, version 3.
 This program is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 General Public License for more details.
 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import asyncio, json, argparse
from aiohttp import web
from pydub import AudioSegment
from simpleaudio import play_buffer


class AudioPlayer:

    def __init__(self):
        self.songs = {}
        self.plays = {}
        self.playlist = {}

    def load_playlist(self, playlist):

        # stop current plays
        for s in self.songs:
            self.stop(s)

        # load new song list
        songs = {}
        plays = {}

        for song, path in playlist.items():
            songs[song] = AudioSegment.from_file(path)
            plays[song] = None

        self.songs, self.plays, self.playlist = songs, plays, playlist

    def play(self, song):
        self.plays[song] = self._play_with_simpleaudio(self.songs[song])

    def stop(self, song):
        if self.plays[song] is not None:
            self.plays[song].stop()

    @property
    def statuses(self):
        sta = {k: (v is not None and v.is_playing())
               for k, v in self.plays.items()}
        return {k: 'playing' if v else 'stopped' for k, v in sta.items()}

    def _play_with_simpleaudio(self, seg):
        return play_buffer(seg.raw_data,
                           num_channels=seg.channels,
                           bytes_per_sample=seg.sample_width,
                           sample_rate=seg.frame_rate)


class AudioPlayerServer(AudioPlayer):

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.add_routes([web.get('/playlist', self.handle_get_playlist)])
        self.app.add_routes([web.get('/statuses', self.handle_get_statuses)])
        self.app.add_routes([web.post('/', self.handle_post)])

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = web.AppRunner(self.app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, self.host, self.port)
        loop.run_until_complete(site.start())
        print(f'Server on {self.host}:{self.port}')
        loop.run_forever()

    async def handle_get_playlist(self, request):
        return web.Response(content_type='application/json',
                            text=json.dumps(self.playlist))

    async def handle_get_statuses(self, request):
        return web.Response(content_type='application/json',
                            text=json.dumps(self.statuses))

    async def handle_post(self, request):
        params = await request.post()
        if params['type'] == 'start':
            self.play(song=params['song'])
            return web.Response(content_type='application/json', text='done')
        elif params['type'] == 'stop':
            self.stop(song=params['song'])
            return web.Response(content_type='application/json', text='done')


if __name__ == '__main__':

    # parse arguments
    parser = argparse.ArgumentParser(description='escaperoom audioplayer')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host for the HTTP server (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8082,
                        help='Port for HTTP server (default: 8082)')
    parser.add_argument('PLAYLIST', type=str,
                        help='JSON list of song with filepathes')
    args = parser.parse_args()

    # start server
    server = AudioPlayerServer(host=args.host, port=args.port)
    server.load_playlist(json.load(open(args.PLAYLIST)))
    server.run()
