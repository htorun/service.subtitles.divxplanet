# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
from xbmc import log
import mechanize
import cookielib
import re
import string
import time
from BeautifulSoup import BeautifulSoup

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__ = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__ = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)


def getmediaurl(mediaargs):
    title = re.sub(" \(?(.*.)\)", "", mediaargs[1])
    if mediaargs[2] != "":
        query = "site:divxplanet.com inurl:sub/m \"%s ekibi\" intitle:\"%s\" intitle:\"(%s)\"" % (mediaargs[0], title, mediaargs[2])
    else:
        query = "site:divxplanet.com inurl:sub/m \"%s ekibi\" intitle:\"%s\"" % (mediaargs[0], title)
    br = mechanize.Browser()
    log("Divxplanet: Finding media %s" % query)
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    br.open("http://www.google.com")
    # Select the search box and search for 'foo'
    br.select_form('f')
    br.form['q'] = query
    br.submit()
    page = br.response().read()
    soup = BeautifulSoup(page)

    linkdictionary = []
    query.replace(" ", "-")
    for li in soup.findAll('li', attrs={'class': 'g'}):
        slink = li.find('a')
        sspan = li.find('span', attrs={'class': 'st'})
        if slink:
            linkurl = re.search(r"/url\?q=(http://divxplanet.com/sub/m/[0-9]{3,8}/.*.\.html).*", slink["href"])
            if linkurl:
                linkdictionary.append({"text": sspan.getText().encode('utf8'), "name": mediaargs[0], "url": linkurl.group(1)})
                log("Divxplanet: found media: %s" % (linkdictionary[0]["url"]))
    if len(linkdictionary) > 0:
        return linkdictionary[0]["url"]
    else:
        return ""


def search(sitem):
    tvshow = sitem["tvshow"]
    year = sitem["year"]
    season = sitem["season"]
    episode = sitem["episode"]
    title = sitem["title"]

    # Build an adequate string according to media type
    if len(tvshow) != 0:
        log("Divxplanet: searching subtitles for %s %s %s %s" % (tvshow, year, season, episode))
        tvurl = getmediaurl(["dizi", tvshow, year])
        log("Divxplanet: got media url %s" % tvurl)
        if tvurl != "":
            divpname = re.search(r"http://divxplanet.com/sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)
            season = int(season)
            episode = int(episode)
            # Browser
            br = mechanize.Browser()

            # Cookie Jar
            cj = cookielib.LWPCookieJar()
            br.set_cookiejar(cj)

            # Browser options
            br.set_handle_equiv(True)
            # br.set_handle_gzip(True)
            br.set_handle_redirect(True)
            br.set_handle_referer(True)
            br.set_handle_robots(False)

            # Follows refresh 0 but not hangs on refresh > 0
            br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

            # User-Agent (this is cheating, ok?)
            br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

            url = br.open(tvurl)
            html = url.read()
            soup = BeautifulSoup(html)
            subtitles_list = []
            i = 0
            # /sub/s/281212/Hannibal.html
            for link in soup.findAll('a', href=re.compile("/sub/s/.*./%s.html" % divpname)):
                addr = link.get('href')
                info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
                if info:
                    tse = info[0].div.findAll("b", text="%d" % season)
                    tep = info[0].div.findAll("b", text="%02d" % episode)
                    lantext = link.parent.find("br")
                    lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                    if tse and tep and lan and lantext:
                        language = lan[0]["title"]
                        if language[0] == "e":
                            language = "English"
                            lan_short = "en"
                        else:
                            language = "Turkish"
                            lan_short = "tr"
                        filename = "%s S%02dE%02d %s.%s" % (tvshow, season, episode, title, lan_short)
                        description = info[1].getText().encode('utf8')
                        litem = xbmcgui.ListItem(label=language,
                                                    label2=description,
                                                    iconImage="0",
                                                    thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
                        )
                        litem.setProperty("hearing_imp", '{0}'.format("false").lower())
                        subtitles_list.append(litem)
                        url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" \
                              % (__scriptid__, addr, lan_short, filename)
                        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=litem, isFolder=False)
            br.close()
            log("Divxplanet: found %d subtitles" % (len(subtitles_list)))
    else:
        log("Divxplanet: searching subtitles for %s %s" % (title, year))
        tvurl = getmediaurl(["film", title, year])
        if tvurl == '':
            tvurl = getmediaurl(["film", title, int(year)+1])
            log("Divxplanet: searching subtitles for %s %s" % (title, int(year)+1))
        if tvurl == '':
            tvurl = getmediaurl(["film", title, int(year)-1])
            log("Divxplanet: searching subtitles for %s %s" % (title, int(year)-1))
        log("Divxplanet: got media url %s" % tvurl)
        divpname = re.search(r"http://divxplanet.com/sub/m/[0-9]{3,8}/(.*.)\.html", tvurl).group(1)
        # Browser
        br = mechanize.Browser()

        # Cookie Jar
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        # Browser options
        br.set_handle_equiv(True)
        # br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but not hangs on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # User-Agent (this is cheating, ok?)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

        url = br.open(tvurl)
        html = url.read()
        soup = BeautifulSoup(html)
        subtitles_list = []
        i = 0
        # /sub/s/281212/Hannibal.html
        for link in soup.findAll('a', href=re.compile("/sub/s/.*./%s.html" % divpname)):
            addr = link.get('href')
            info = link.parent.parent.nextSibling.nextSibling.findAll("td", colspan="3")
            if info:
                lantext = link.parent.find("br")
                lan = link.parent.parent.findAll("img", title=re.compile("^.*. (subtitle|altyazi)"))
                if lan and lantext:
                    language = lan[0]["title"]
                    if language[0] == "e":
                        language = "English"
                        lan_short = "en"
                    else:
                        language = "Turkish"
                        lan_short = "tr"
                    description = "no-description"
                    if info[0].getText() != "":
                        description = info[0].getText().encode('utf8')
                    filename = "%s.%s" % (title, lan_short)
                    log("Divxplanet: found a subtitle with description: %s" % description)
                    litem = xbmcgui.ListItem(label=language,
                                             label2=description,
                                             iconImage="0",
                                             thumbnailImage=xbmc.convertLanguage(language, xbmc.ISO_639_1)
                    )
                    litem.setProperty( "hearing_imp", '{0}'.format("false").lower() ) # set to "true" if subtitle is for hearing impared
                    subtitles_list.append(litem)
                    url = "plugin://%s/?action=download&link=%s&lang=%s&description=%s" % \
                          (__scriptid__, addr, lan_short, filename)
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=litem, isFolder=False)
        br.close()
        log("Divxplanet: found %d subtitles" % (len(subtitles_list)))


def normalizestring(s):
    return unicodedata.normalize('NFKD', unicode(unicode(s, 'utf-8'))).encode('ascii','ignore')


def download(link, lng, filename):
    log("Divxplanet: o yoldayiz %s" % link)
    subtitle_list = []

    packed = True
    dlurl = "http://divxplanet.com%s" % link
    language = lng
    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    # br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent (this is cheating, ok?)
    br.addheaders = [(
        'User-agent',
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
    )]

    html = br.open(dlurl).read()
    br.select_form(name="dlform")
    r = br.submit()
    if r.info().has_key('Content-Disposition'):
        # If the response has Content-Disposition, we take file name from it
        lname = r.info()['Content-Disposition'].split('filename=')[1]
        if lname[0] == '"' or lname[0] == "'":
            lname = lname[1:-1]
    elif r.url != dlurl: 
        # if we were redirected, the real file name we take from the final URL
        lname = url2name(r.url)
    else:
        lname = ""

    log("Divxplanet: Fetching subtitles using url %s" % dlurl)
    local_tmp_file = os.path.join(__temp__, lname)
    
    try:
        log("Divxplanet: Saving subtitles to '%s'" % (local_tmp_file))
        if not os.path.exists(__temp__):
            os.makedirs(__temp__)
        local_file_handle = open(local_tmp_file, "wb")
        local_file_handle.write(br.response().get_data())
        local_file_handle.close()
    except:
        log("Divxplanet: Failed to save subtitle to %s" % (local_tmp_file))
    if packed:
        files = os.listdir(__temp__)
        init_filecount = len(files)
        max_mtime = 0
        filecount = init_filecount
        # determine the newest file from __temp__
        for f in files:
            if string.split(f,'.')[-1] in ['srt','sub']:
                mtime = os.stat(os.path.join(__temp__, f)).st_mtime
                if mtime > max_mtime:
                    max_mtime =  mtime
        init_max_mtime = max_mtime
        time.sleep(2)  # wait 2 seconds so that the unpacked files are at least 1 second newer
        xbmc.executebuiltin("XBMC.Extract(" + local_tmp_file + "," + __temp__ + ")")
        waittime = 0
        while (filecount == init_filecount) and (waittime < 20) and (init_max_mtime == max_mtime): # nothing yet extracted
            time.sleep(1)  # wait 1 second to let the builtin function 'XBMC.extract' unpack
            files = os.listdir(__temp__)
            filecount = len(files)
            # determine if there is a newer file created in __temp__ (marks that the extraction had completed)
            for f in files:
                if string.split(f, '.')[-1] in ['srt', 'sub']:
                    mtime = os.stat(os.path.join(__temp__, f)).st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
            waittime += 1
        if waittime == 20:
            log("Divxplanet: Failed to unpack subtitles in '%s'" % __temp__)
        else:
            log("Divxplanet: Unpacked files in '%s'" % __temp__)
            for f in files:
                # there could be more subtitle files in __temp__, so make sure we get the newly created subtitle file
                if (string.split(f, '.')[-1] in ['srt', 'sub']) and (os.stat(os.path.join(__temp__, f)).st_mtime > init_max_mtime):
                    log("Divxplanet: Unpacked subtitles file '%s'" % (f.encode("utf-8")))
                    subs_file = os.path.join(__temp__, f)
                    subtitle_list.append(subs_file)
    log("Divxplanet: Subtitles saved to '%s'" % local_tmp_file)
    br.close()
    return subtitle_list


def get_params():
    param = dict()
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        prms = paramstring
        cleanedparams = prms.replace('?', '')
        if prms[len(prms)-1] == '/':
            prms = prms[0:len(prms)-2]
        pairsofparams = cleanedparams.split('&')
        param = dict()
        for i in range(len(pairsofparams)):
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param

params = get_params()

if params['action'] == 'search':
    item = dict()
    item['temp']               = False
    item['rar']                = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
    item['tvshow']             = normalizestring(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title']              = normalizestring(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['3let_language']      = []

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = normalizestring(xbmc.getInfoLabel("VideoPlayer.Title"))

    if item['episode'].lower().find("s") > -1:
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    subs = download(params["link"], params["lang"], params["description"])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub, listitem=listitem, isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
