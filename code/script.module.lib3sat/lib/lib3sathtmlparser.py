# -*- coding: utf-8 -*-
import time
import json
# import xbmc
import bs4 as bs
import libmediathek3 as libMediathek
from datetime import date, datetime, timedelta


base = 'https://www.3sat.de'
api_base = 'https://api.3sat.de'
playerId = 'ngplayer_2_3'
thumbnail1_types = ['is-desktop', 'is-mobile']
thumbnail2_types = ['is-16-9', 'is-8-9']
preferred_thumbnail_type = 0 # => Desktop
preferred_resolutions = [['384w', '768w', '1280w', '1920w', '2400w'], ['240w', '640w', '1152w']]
translation = libMediathek.getTranslation


def list():
	global params
	params = libMediathek.get_params()
	mode = params.get('mode','lib3satHtmlListMain')
	# xbmc.log('%s' % mode, xbmc.LOGFATAL)
	if mode == 'lib3satHtmlPlay':
		media = modes.get(mode)()
		if media is None:
			return False
		else:
			libMediathek.play(media)
	else:
		l = modes.get(mode)()
		if not (l is None):
			libMediathek.addEntries(l)
			libMediathek.endOfDirectory()
	return True


def lib3satHtmlListMain():
	l = []
	l.append({'name':translation(31032), 'mode':'lib3satHtmlListLetters', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'lib3satHtmlListDate', '_type':'dir'})
	l.append({'name':translation(31039), 'mode':'lib3satHtmlSearch', '_type':'dir'})
	return l


def lib3satHtmlListLetters():
	# URL z.B.: https://www.3sat.de/sendungen-a-z?group=a
	mode = 'lib3satHtmlListShows'
	l = libMediathek.populateDirAZ(mode, ['#'])
	d = {}
	d['mode'] = mode
	d['name'] = '0-9'
	d['_type'] = 'dir'
	l.append(d)
	return l


def lib3satHtmlListDate():
	# URL z.B.: https://www.3sat.de/programm?airtimeDate=2019-06-21
	l = libMediathek.populateDirDate('lib3satHtmlListDateVideos')
	return l


def chooseImage(pictureList, thumbnail_type):
	if not (pictureList is None):
		for pictureItem in pictureList:
			if hasattr(pictureItem,'attrs') and (thumbnail_type[preferred_thumbnail_type] in pictureItem.attrs.get('class', [])):
				pictureSources = pictureItem.attrs.get('data-srcset', None)
				if not (pictureSources is None):
					pictures = pictureSources.split(',')
					for index, item in enumerate(pictures):
						pictures[index] = item.split(' ')
					for resolution in preferred_resolutions[preferred_thumbnail_type]:
						for picture in pictures:
							if len(picture) > 1 and picture[1] == resolution:
								return picture[0]
				# Fallback
				pictureSource = pictureItem.attrs.get('data-src', None)
				return pictureSource
	return None


def str_to_airedtime(airedtime_str):
	if not airedtime_str:	# check for None or empty string
		return None
	start = airedtime_str.split('+')
	zulutime = (len(start) == 1)
	if zulutime:
		format = '%Y-%m-%dT%H:%M:%SZ'
	else:
		format = '%Y-%m-%dT%H:%M:%S'
	try:
		airedtime = datetime.strptime(start[0], format)
	except TypeError:
		airedtime = datetime(*(time.strptime(start[0], format)[0:6]))
	if zulutime:
		tz_offset = timedelta (minutes = (time.timezone / -60) + (time.localtime().tm_isdst * 60))
		airedtime += tz_offset
	return airedtime


def getDate(date_str):
	l = []
	url = base + '/programm?airtimeDate=' + date_str
	response = libMediathek.getUrl(url)
	soup = bs.BeautifulSoup(response, 'html.parser')
	articles = soup.findAll('article', {'class': 'is-video'})
	for article in articles:
		d = {}
		name = article.find('h3')
		if not (name is None):
			d['_type'] = 'video'
			d['mode'] = 'lib3satHtmlPlay'
			d['_name'] = name.text
			airedtime_begin = str_to_airedtime(article.attrs.get('data-airtime-begin', None))
			if not (airedtime_begin is None):
				airedtime = datetime (airedtime_begin.year, airedtime_begin.month, airedtime_begin.day, airedtime_begin.hour, (airedtime_begin.minute / 5) * 5)
				d['_airedtime'] = airedtime.strftime('%H:%M')
				d['_name'] = '(' + d['_airedtime'] + ') ' + d['_name']
				airedtime_end = str_to_airedtime(article.attrs.get('data-airtime-end', None))
				if not (airedtime_end is None):
					d['duration'] = str((airedtime_end - airedtime_begin).seconds)
			plot = article.find('p', {'class': 'teaser-epg-text'})
			if not (plot is None):
				d['_plot'] = plot.text
			picture = article.find('picture')
			if not (picture is None):
				d['_thumb'] = chooseImage(picture.contents, thumbnail1_types)
			url = article.find('a', {'data-link': (lambda(x): not(x is None))})
			if not (url is None) and not (url.attrs is None):
				href = url.attrs.get('href', None)
				if not (href is None):
					d['url'] = base + href
			l.append(d)
	return l


def lib3satHtmlListDateVideos():
	if 'datum' in params:
		day = date.today() - timedelta(int(params['datum']))
		yyyy_mm_dd = day.strftime('%Y-%m-%d')
	else:
		ddmmyyyy = libMediathek.dialogDate()
		yyyy_mm_dd = ddmmyyyy[4:8] + '-' + ddmmyyyy[0:2] + '-' + ddmmyyyy[2:4]
	l = getDate(yyyy_mm_dd)
	return l


def getAZ(url):
	l = []
	response = libMediathek.getUrl(url)
	soup = bs.BeautifulSoup(response, 'html.parser')
	articles = soup.findAll('article')
	for article in articles:
		d = {}
		name_link = article.find('a',  {'class': 'teaser-title-link'})
		if not (name_link is None) and not (name_link.attrs is None):
			href = name_link.attrs.get('href', None)
			name_attr = article.find('p',  {'class': 'a--headline'})
			if len(name_attr) > 0 and not (href is None):
				name = name_attr.text
				d['_type'] = 'video'
				d['mode'] = 'lib3satHtmlPlay'
				d['_name'] = name
				d['_plot'] = name
				d['url'] = base + href
				picture = article.find('picture')
				if not (picture is None):
					d['_thumb'] = chooseImage(picture.contents, thumbnail2_types)
				l.append(d)
	return l


def lib3satHtmlListShows():
	libMediathek.sortAZ()
	url = base + '/sendungen-a-z?group=' + params['name'].lower()
	l = getAZ(url)
	return l


def lib3satHtmlSearch():
	search_string = libMediathek.getSearchString()
	if search_string:
		url = base + '/suche?q=' +search_string
		l = getAZ(url)
		return l
	else:
		return None


def grepItem(target):
	if target['profile'] == 'http://zdf.de/rels/not-found':
		return False
	if not ('contentType' in target):
		return False
	d = {}
	d['_name'] = target['title']
	d['_plot'] = target['teasertext']
	if target['contentType'] == 'clip':
		try:
			d['url'] = api_base + target['mainVideoContent']['http://zdf.de/rels/target']['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',playerId)
			if 'duration' in target['mainVideoContent']['http://zdf.de/rels/target']:
				d['_duration'] = str(target['mainVideoContent']['http://zdf.de/rels/target']['duration'])
			d['_type'] = 'clip'
			d['mode'] = 'lib3satHtmlPlay'
		except: d = False
	elif target['contentType'] == 'episode':
		try:
			if 'mainVideoContent' in target:
				content = target['mainVideoContent']['http://zdf.de/rels/target']
			elif 'mainContent' in target:
				content = target['mainContent'][0]['videoContent'][0]['http://zdf.de/rels/target']
			d['url'] = api_base + content['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',playerId)
			if 'duration' in content:
				d['_duration'] = str(content['duration'])
			d['_type'] = 'video'
			d['mode'] = 'lib3satHtmlPlay'
		except: d = False
	else:
		log('Unknown target type: ' + target['contentType'])
		d = False
	return d


def getU(url, api_token):
	# xbmc.log('api_token %s, url = %s' % (api_token, url), xbmc.LOGFATAL)
	header = { 'Api-Auth' : 'Bearer ' + api_token }
	response = libMediathek.getUrl(url,header)
	return response


def getVideoUrl(url, api_token):
	d = {}
	d['media'] = []
	response = getU(url,api_token)
	j = json.loads(response)
	for caption in j.get('captions',[]):
		if caption['format'] == 'ebu-tt-d-basic-de':
			d['subtitle'] = [{'url':caption['uri'], 'type':'ttml', 'lang':'de', 'colour':True}]
		#elif caption['format'] == 'webvtt':
		#	d['subtitle'] = [{'url':caption['uri'], 'type':'webvtt', 'lang':'de', 'colour':False}]
	for item in j['priorityList']:
		if item['formitaeten'][0]['type'] == 'h264_aac_ts_http_m3u8_http':
			for quality in item['formitaeten'][0]['qualities']:
				if quality['quality'] == 'auto':
					d['media'].append({'url':quality['audio']['tracks'][0]['uri'], 'type': 'video', 'stream':'HLS'})
	return d


def lib3satHtmlPlay(url = None):
	result = None
	if url is None:
		url = params['url']
	response = libMediathek.getUrl(url)
	soup = bs.BeautifulSoup(response, 'html.parser')
	playerbox = soup.find('div', {'class': 'b-playerbox'})
	if not (playerbox is None) and (hasattr(playerbox,'attrs')):
		jsb_str = playerbox.attrs.get('data-zdfplayer-jsb', None)
		if not (jsb_str is None):
			jsb = json.loads(jsb_str)
			content_link = jsb['content']
			api_token = jsb['apiToken']
		 	content_response = getU(content_link, api_token)
		 	target = json.loads(content_response)
		 	j = grepItem(target)
		 	result = getVideoUrl(j['url'], api_token)
	return result


modes = {
	'lib3satHtmlListMain': lib3satHtmlListMain,
	'lib3satHtmlListLetters': lib3satHtmlListLetters,
	'lib3satHtmlListDate': lib3satHtmlListDate,
	'lib3satHtmlListDateVideos': lib3satHtmlListDateVideos,
	'lib3satHtmlSearch': lib3satHtmlSearch,
	'lib3satHtmlListShows': lib3satHtmlListShows,
	'lib3satHtmlPlay': lib3satHtmlPlay,
}