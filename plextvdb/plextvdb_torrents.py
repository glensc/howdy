import requests, re, threading, cfscrape, os, time
from bs4 import BeautifulSoup
from tpb import CATEGORIES, ORDERS
from requests.compat import urljoin
from plexemail.plexemail import get_formatted_size
from . import plextvdb
from plexcore.plexcore import get_maximum_matchval, get_jackett_credentials
from plexcore import plexcore_deluge

def _return_error_couldnotfind( name ):
    return None, 'FAILURE, COULD NOT FIND ANY TV SHOWS WITH SEARCH TERM %s' % name

def _return_error_raw( msg ):
    return None, msg

def get_tv_torrent_zooqle( name, maxnum = 10 ):
    assert( maxnum >= 5 )
    names_of_trackers = map(lambda tracker: tracker.replace(':', '%3A').replace('/', '%2F'), [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://open.demonii.com:1337',
        'udp://tracker.pomf.se:80/announce',
        'udp://torrent.gresille.org:80/announce',
        'udp://11.rarbg.com/announce',
        'udp://11.rarbg.com:80/announce',
        'udp://open.demonii.com:1337/announce',
        'udp://tracker.openbittorrent.com:80',
        'http://tracker.ex.ua:80/announce',
        'http://tracker.ex.ua/announce',
        'http://bt.careland.com.cn:6969/announce',
        'udp://glotorrents.pw:6969/announce'
    ])
    tracklist = ''.join(map(lambda tracker: '&tr=%s' % tracker, names_of_trackers ) )
    def _get_magnet_link( info_hash, title ):
        download_url = "magnet:?xt=urn:btih:" + info_hash + "&dn=" + '+'.join(title.split()) + tracklist
        return download_url
    candname = re.sub("'", '', name )
    url = 'https://zooqle.com/search'
    params = { 'q' : '+'.join( candname.split() + [ 'category%3ATV', ] ),
               'fmt' : 'rss' }
    paramurl = '?' + '&'.join(map(lambda tok: '%s=%s' % ( tok, params[ tok ] ),
                                  params ) )
    fullurl = urljoin( url, paramurl )
    response = requests.get( fullurl )
    if response.status_code != 200:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    myxml = BeautifulSoup( response.content, 'lxml' )
    def is_valid_elem( elem ):
        names = set(map(lambda elm: elm.name, elem.find_all( ) ) )
        return len( names & set([ 'torrent:infohash',
                                  'torrent:seeds',
                                  'torrent:peers',
                                  'torrent:contentlength' ]) ) == 4
    cand_items = filter(lambda elem: len( elem.find_all('title' ) ) >= 1 and
                        is_valid_elem( elem ) and
                        get_maximum_matchval( max( elem.find_all('title' ) ).get_text( ), candname ) >= 80,
                        myxml.find_all('item'))
    def get_num_forelem( elem, name ):
        valid_elm = list(filter(lambda elm: elm.name == 'torrent:%s' % name, elem ) )
        if len( valid_elm ) == 0: return None
        valid_elm = valid_elm[ 0 ]
        return int( valid_elm.get_text( ) )
    def get_infohash( elem ):
        valid_elm = list(filter(lambda elm: elm.name == 'torrent:infohash', elem ) )
        if len( valid_elm ) == 0: return None
        valid_elm = valid_elm[ 0 ]
        return valid_elm.get_text( ).lower( )
    
    items_toshow = list( map(lambda elem: { 'title' : '%s (%s)' % ( max( elem.find_all('title' ) ).get_text( ),
                                                                    get_formatted_size( get_num_forelem( elem, 'contentlength' ) ) ),
                                            'seeders' : get_num_forelem( elem, 'seeds' ),
                                            'leechers' : get_num_forelem( elem, 'peers' ),
                                            'link' : _get_magnet_link( get_infohash( elem ),
                                                                       max( elem.find_all('title' ) ).get_text( ) ) },
                             cand_items ) )
    if len( items_toshow ) == 0:
        return None, 'ERROR, COULD NOT FIND ZOOQLE TORRENTS FOR %s' % candname
    return sorted( items_toshow, key = lambda item: -item['seeders'] - item['leechers'] )[:maxnum], 'SUCCESS'

def get_tv_torrent_rarbg( name, maxnum = 10, verify = True ):
    candidate_seriesname = ' '.join( name.strip().split()[:-1] )
    epstring = name.strip().split()[-1].upper()
    if not epstring[0] == 'S':
        status = 'Error, first string must be an s or S.'
        return None, status
    epstring = epstring[1:]
    splitseaseps = epstring.split('E')[:2]
    if len( splitseaseps ) != 2:
        status = 'Error, string must have a SEASON and EPISODE part.'
        return None, status
    try:
        seasno = int( splitseaseps[0] )
    except:
        status = 'Error, invalid season number.'
        return None, status
    try:
        epno = int( splitseaseps[1] )
    except:
        status = 'Error, invalid episode number.'
        return None, status
    
    tvdb_token = plextvdb.get_token( verify = verify )
    series_id = plextvdb.get_series_id( candidate_seriesname, tvdb_token,
                                        verify = verify )
    if series_id is None:
        series_ids = plextvdb.get_possible_ids( candidate_seriesname,
                                                tvdb_token, verify = verify )
        if series_ids is None or len( series_ids ) == 0:
            status = 'ERROR, PLEXTVDB could find no candidate series that match %s' % \
                     candidate_seriesname
            return None, status
        series_id = series_ids[ 0 ]
    #
    ## got app_id and apiurl from https://www.rubydoc.info/github/epistrephein/rarbg/master/RARBG/API
    apiurl = "https://torrentapi.org/pubapi_v2.php"
    response = requests.get(apiurl,
                            params={ "get_token": "get_token",
                                     "format": "json",
                                     "app_id": "rarbg-rubygem" }, verify = verify )
    if response.status_code != 200:
        status = '. '.join([ 'ERROR, problem with rarbg.to: %d' % response.status_code,
                             'Unable to connect to provider.' ])
        return None, status
    token = response.json( )[ 'token' ]
    params = { 'mode' : 'search', 'search_tvdb' : series_id, 'token' : token,
               'format' : 'json_extended', 'category' : 'tv', 'app_id' : 'rarbg-rubygem',
               'search_string' : 'E'.join( splitseaseps ), 'limit' : 100 }
    #
    ## wait 4 seconds
    ## this is a diamond hard limit for RARBG
    time.sleep( 4.0 )
    response = requests.get( apiurl, params = params, verify = verify )
    if response.status_code != 200:
        status = '. '.join([ 'ERROR, problem with rarbg.to: %d' % response.status_code,
                             'Unable to connect to provider.' ])
        return None, status
    data = response.json( )
    if 'torrent_results' not in data:
        status = '\n'.join([ 'ERROR, RARBG.TO could not find any torrents for %s %s.' %
                             ( candidate_seriesname, 'E'.join( splitseaseps ) ),
                             'data = %s' % data ])
        return None, status
    data = list( filter(lambda elem: 'title' in elem, data['torrent_results']) )
    filtered_data = list( filter(lambda elem: 'E'.join( splitseaseps ) in elem['title'] and
                                 '720p' in elem['title'] and 'HDTV' in elem['title'], data ) )
    if len( filtered_data ) == 0:
        filtered_data = list( filter(lambda elem: 'E'.join( splitseaseps ) in elem['title'], data ) )
    filtered_data = list(filtered_data)[:maxnum]
    if len( filtered_data ) == 0:
        status = 'ERROR, RARBG.TO could not find any torrents for %s %s.' % (
            candidate_seriesname, 'E'.join( splitseaseps ) )
        return None, status
    def get_num_seeders( elem ):
        if 'seeders' in elem: return elem['seeders']
        return 1
    def get_num_leechers( elem ):
        if 'leechers' in elem: return elem['leechers']
        return 1
    items = list( map(lambda elem: { 'title' : elem['title'], 'link' : elem['download'],
                                     'seeders' : get_num_seeders( elem ),
                                     'leechers' : get_num_leechers( elem ) },
                filtered_data ) )
    return items, 'SUCCESS'

def get_tv_torrent_torrentz( name, maxnum = 10, verify = True ):
    names_of_trackers = map(lambda tracker: tracker.replace(':', '%3A').replace('/', '%2F'), [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://open.demonii.com:1337',
        'udp://tracker.pomf.se:80/announce',
        'udp://torrent.gresille.org:80/announce',
        'udp://11.rarbg.com/announce',
        'udp://11.rarbg.com:80/announce',
        'udp://open.demonii.com:1337/announce',
        'udp://tracker.openbittorrent.com:80',
        'http://tracker.ex.ua:80/announce',
        'http://tracker.ex.ua/announce',
        'http://bt.careland.com.cn:6969/announce',
        'udp://glotorrents.pw:6969/announce'
    ])
    tracklist = ''.join(map(lambda tracker: '&tr=%s' % tracker, names_of_trackers ) )
    #
    def try_int( candidate, default_value=0):
        """
        Try to convert ``candidate`` to int, or return the ``default_value``.
        :param candidate: The value to convert to int
        :param default_value: The value to return if the conversion fails
        :return: ``candidate`` as int, or ``default_value`` if the conversion fails
        """
        
        try:
            return int(candidate)
        except (ValueError, TypeError):
            return default_value
    def _split_description(description):
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])
    #
    url = 'https://torrentz2.eu/feed'
    search_params = {'f': name }
    scraper = cfscrape.create_scraper( )
    response = scraper.get( url, params = search_params, verify = verify )
    if response.status_code != 200:
        return None, 'FAILURE, request for %s did not work.' % name
    if not response.content.startswith(b'<?xml'):
        return None, 'ERROR, request content is not a valid XML block.'
    html = BeautifulSoup( response.content, 'lxml' )
    items = []
    for item in html('item'):
        if item.category and 'tv' not in item.category.get_text(strip=True).lower():
            continue
        title = item.title.get_text(strip=True)
        t_hash = item.guid.get_text(strip=True).rsplit('/', 1)[-1]
        if not all([title, t_hash]):
            continue
        download_url = "magnet:?xt=urn:btih:" + t_hash + "&dn=" + '+'.join(title.split()) + tracklist
        torrent_size, seeders, leechers = _split_description(item.find('description').text)
        if get_maximum_matchval( title, name ) < 80: continue
        myitem = {'title': title, 'link': download_url, 'seeders': seeders,
                  'leechers': leechers }
        items.append(myitem)
    if len( items ) == 0:
        return _return_error_couldnotfind('FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name)
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    items = items[:maxnum]
    return items, 'SUCCESS'

def get_tv_torrent_jackett( name, maxnum = 10, minsize = None, maxsize = None, keywords = [ ], keywords_exc = [ ] ):
    import validators
    data = get_jackett_credentials( )
    if data is None:
        return _return_error_raw('FAILURE, COULD NOT GET JACKETT SERVER CREDENTIALS')
    url, apikey = data
    endpoint = 'api/v2.0/indexers/all/results/torznab/api'
    response = requests.get( urljoin( url, endpoint ),
                             params = { 'apikey' : apikey, 'q' : name, 'cat' : '5000' } ) # tv shows
    if response.status_code != 200:
        return _return_error_raw( 'FAILURE, PROBLEM WITH JACKETT SERVER ACCESSIBLE AT %s.' % url )
    html = BeautifulSoup( response.content, 'lxml' )
    if len( html.find_all('item') ) == 0:
        return _return_error_raw( 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name )
    items = [ ]
    
    def _get_magnet_url( item ):
        magnet_url = item.find( 'torznab:attr', { 'name' : 'magneturl' } )
        if magnet_url is not None and 'magnet' in magnet_url['value']:
            return magnet_url['value']
        #
        ## not found it here, must go into URL
        url2 = item.find('guid')
        if url2 is None: return None
        url2 = url2.text
        if not validators.url( url2 ): return None
        resp2 = requests.get( url2 )
        if resp2.status_code != 200: return None
        h2 = BeautifulSoup( resp2.content, 'lxml' )
        valid_magnet_links = set(map(lambda elem: elem['href'],
                                     filter(lambda elem: 'href' in elem.attrs and 'magnet' in elem['href'], h2.find_all('a'))))
        if len( valid_magnet_links ) == 0: return None
        return max( valid_magnet_links )
        
    for item in html('item'):
        title = item.find('title')
        if title is None: continue
        title = title.text
        torrent_size = item.find('size')
        if torrent_size is not None:
            torrent_size = float( torrent_size.text ) / 1024**2
        seeders = item.find( 'torznab:attr', { 'name' : 'seeders' } )
        if seeders is None: seeders = -1
        else: seeders = int( seeders[ 'value' ] )
        leechers = item.find( 'torznab:attr', { 'name' : 'peers' } )
        if leechers is None: leechers = -1
        else: leechers = int( leechers[ 'value' ] )
        #
        ## now do one of two things to get the magnet URL
        magnet_url = _get_magnet_url( item )
        if magnet_url is None: continue
        myitem = { 'title' : title,
                   'seeders' : seeders,
                   'leechers' : leechers,
                   'link' : magnet_url }
        if torrent_size is not None:
            myitem[ 'title' ] = '%s (%0.1f MiB)' % ( title, torrent_size )
            myitem[ 'torrent_size' ] = torrent_size
        items.append( myitem )

    items = sorted(items, key = lambda elem: elem['seeders'] + elem['leechers' ] )[::-1]
    #
    ## now perform the filtering
    if any(map(lambda tok: tok is not None, [ minsize, maxsize ])):
        items = list(filter(lambda elem: 'torrent_size' in elem, items ))
        if minsize is not None:
            items = list(filter(lambda elem: elem['torrent_size'] > minsize, items ) )
        if maxsize is not None:
            items = list(filter(lambda elem: elem['torrent_size'] < maxsize, items ) )
    if len( keywords ) != 0:
        items = list(filter(lambda elem: any(map(lambda tok: tok.lower( ) in elem['title'].lower( ), keywords ) ) and
                            not any(map(lambda tok: tok.lower( ) in elem['title'].lower( ), keywords_exc ) ),
                            items ) )
    if len( items ) == 0:
        return _return_error_raw( 'FAILURE, NO TV SHOWS OR SERIES SATISFYING CRITERIA FOR GETTING %s' % name )
        
    return items[:maxnum], 'SUCCESS'

def get_tv_torrent_kickass( name, maxnum = 10 ):
    from KickassAPI import Search, Latest, User, CATEGORY, ORDER
    names_of_trackers = map(lambda tracker: tracker.replace(':', '%3A').replace('/', '%2F'), [
        'http://mgtracker.org:2710/announce',
        'http://tracker.internetwarriors.net:1337/announce',
        'http://37.19.5.139:6969/announce',
        'http://37.19.5.155:6881/announce',
        'http://p4p.arenabg.ch:1337/announce',
        'udp://tracker.zer0day.to:1337/announce',
        'udp://tracker.coppersurfer.tk:6969/announce',
        'http://109.121.134.121:1337/announce',
        'udp://tracker.opentrackr.org:1337/announce',
        'http://5.79.83.193:2710/announce',
        'udp://p4p.arenabg.com:1337/announce',
        'udp://explodie.org:6969/announce',
        'http://tracker.sktorrent.net:6969/announce',
        'udp://tracker.leechers-paradise.org:6969/announce',
        'http://mgtracker.org:6969/announce',
        'http://tracker.opentrackr.org:1337/announce',
        'http://p4p.arenabg.com:1337/announce',
        'udp://9.rarbg.com:2710/announce',
        'http://tracker.mg64.net:6881/announce',
        'http://explodie.org:6969/announce' ] )
    tracklist = ''.join(map(lambda tracker: '&tr=%s' % tracker, names_of_trackers ) )
    def get_size( lookup ):
        size_string = lookup.size
        if size_string.lower().endswith('mib'):
            return float( size_string.lower().split()[0] )
        elif size_string.lower().endswith('kib'):
            return float( size_string.lower().split()[0] ) / 1024
        elif size_string.lower().endswith('gib'):
            return float( size_string.lower().split()[0] ) * 1024
        else: return 0.0
    try:
        lookups = [ ]
        data = Search( name, category = CATEGORY.TV )
        for page in range(1, min( 11, 1 + int( data.url.max_page ) ) ):
            data.url.set_page( page )
            lookups += list( filter(lambda lookup: get_maximum_matchval( lookup.name, name ) >= 90 and
                                lookup.torrent_link is not None, data.list( ) ) )
        lookups = sorted( lookups, key = lambda lookup: get_maximum_matchval( lookup.name, name ) )[:maxnum]
        #lookups = sorted( filter(lambda lookup: #'720p' in lookup.name and
        #                         # get_size( lookup ) >= 100.0 and
        #                         get_maximum_matchval( lookup.name, name ) >= 90 and
        #                         lookup.torrent_link is not None,
        #                         Search( name, category = CATEGORY.TV ) ),
        #                  key = lambda lookup: get_size( lookup ) )[:maxnum]
        if len(lookups) == 0: return None, 'FAILURE, COULD FIND NOTHING THAT MATCHES %s' % name
    except Exception as e:
        return None, 'FAILURE: %s' % e

    def create_magnet_link( lookup ):
        info_hash = os.path.basename( lookup.torrent_link ).lower( )
        download_url = ''.join([ "magnet:?xt=urn:btih:%s" % info_hash,
                                 "&dn=%s" % '+'.join( lookup.name.split( ) ),
                                 tracklist ])
        return download_url

    items_toshow = list( map(lambda lookup: {
        'title' : '%s (%s)' % ( lookup.name, lookup.size ),
        'seeders' : -1,
        'leechers' : -1,
        'link' : create_magnet_link( lookup ) }, lookups ) )
    
    return items_toshow, 'SUCCESS'

def get_tv_torrent_tpb( name, maxnum = 10, doAny = False ):
    #surl = urljoin( 'https://thepiratebay3.org', 's/' )
    surl = 'https://thepiratebay.org'
    if not doAny:
        cat = CATEGORIES.VIDEO.TV_SHOWS
    else:
        cat = CATEGORIES.VIDEO.ALL
    search_params = { "q" : name, "type" : "search",
                      "orderby" : ORDERS.SIZE.DES, "page" : 0,
                      "category" : cat }

    response_arr = [ None, ]
    def fill_response( response_arr ):
        response_arr[ 0 ] = requests.get( surl, params = search_params, verify = False )

    e = threading.Event( )
    t = threading.Thread( target = fill_response, args = ( response_arr, ) )
    t.start( )
    t.join( 30 )
    e.set( )
    t.join( )
    response = max( response_arr )
    if response is None: return None, 'FAILURE TIMED OUT'
    if response.status_code != 200:
        return _return_error_raw( 'FAILURE STATUS CODE = %d' % response.status_code )
        
    def process_column_header(th):
        if th.a:
            return th.a.get_text(strip=True)
        if not result:
            return th.get_text(strip=True)

    def try_int(candidate, default_value=0):
        """
        Try to convert ``candidate`` to int, or return the ``default_value``.
        :param candidate: The value to convert to int
        :param default_value: The value to return if the conversion fails
        :return: ``candidate`` as int, or ``default_value`` if the conversion fails
        """
        
        try:
            return int(candidate)
        except (ValueError, TypeError):
            return default_value

    html = BeautifulSoup( response.content, 'lxml' )
    torrent_table = html.find("table", id="searchResult")
    torrent_rows = torrent_table("tr") if torrent_table else []
    if len( torrent_rows ) < 2:
        return _return_error_couldnotfind( name )
    labels = list(map(lambda label: process_column_header(label),
                      torrent_rows[0]("th") ) )
    items = []
    for result in torrent_rows[1:]:
        try:
            cells = result('td')
            
            title = result.find(class_='detName').get_text(strip = True )
            download_url = result.find(title='Download this torrent using magnet')['href']
            if 'magnet:?' not in download_url:
                continue
            if not all([ title, download_url ]):
                continue
            seeders = try_int(cells[labels.index("SE")].get_text(strip=True))
            leechers = try_int(cells[labels.index("LE")].get_text(strip=True))
            #
            ## Convert size after all possible skip scenarios
            torrent_size = cells[labels.index("Name")].find(class_="detDesc").get_text(strip=True).split(", ")[1]
            torrent_size = re.sub(r"Size ([\d.]+).+([KMGT]iB)", r"\1 \2", torrent_size)
            #size = convert_size(torrent_size, units = ["B", "KB", "MB", "GB", "TB", "PB"]) or -1
            size = torrent_size
            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
            #item = {'title': title, 'link': download_url, 'seeders': seeders, 'leechers': leechers }
            items.append(item)
        except Exception as e:
            print(e)
            continue
    if len( items ) == 0:
        return _return_error_couldnotfind( name )
    items.sort(key=lambda d: try_int(d.get('seeders', 0)) +
               try_int(d.get('leechers')), reverse=True)
    return items[:maxnum], 'SUCCESS'

def get_tv_torrent_best( name, maxnum = 10 ):
    items = [ ]
    assert( maxnum >= 5 )
    items_1, status = get_tv_torrent_tpb( name, maxnum = maxnum )
    if status == 'SUCCESS':
        print( len(items) )
        items += items_1
    items_1, status = get_tv_torrent_torrentz( name, maxnum = maxnum )
    if status == 'SUCCESS':
        items += items_1
    print( 'LENGTH OF ALL ITEMS = %d' % len( items ) )
    if len( items ) == 0:
        print( "Error, could not find anything with name = %s" % name )
        return None, None # could find nothing
    item = max( items, key = lambda item: item['seeders'] + item['leechers'] )
    return item['title'], item[ 'link' ]

def _finish_and_clean_working_tvtorrent_download( totFname, client, torrentId, tor_info ):
    from fabric import Connection
    media_file = max(tor_info[b'files'], key = lambda elem: elem[b'size'] )
    file_name = os.path.join( 'downloads', media_file[b'path'].decode('utf-8') )
    suffix = os.path.basename( file_name ).split('.')[-1].strip( )
    new_file = os.path.join( 'downloads', '%s.%s' % ( os.path.basename( totFname ), suffix ) )
    uname = client.username
    host = client.host
    with Connection( host, user = uname ) as conn:
        #
        ## first copy the file from src to destination
        cmd = 'cp "%s" "%s"' % ( file_name, new_file )
        try: r = conn.run( cmd, hide = True )
        except: return None, 'ERROR, could not properly run %s.' % cmd
        cmd = 'chmod 644 "%s"' % new_file
        try: r = conn.run( cmd, hide = True )
        except: return None, 'ERROR, could not properly run %s.' % cmd
        #
        ## if ends in mp4
        if suffix == 'mp4':
            cmd = '~/.local/bin/mp4tags -s "" "%s"' % new_file
            try: r = conn.run( cmd, hide = True )
            except: return None, 'Error, could not properly run %s.' % cmd
        #
        ## now delete the deluge connection
        plexcore_deluge.deluge_remove_torrent( client, [ torrentId ], remove_data = True )
        return '%s.%s' % ( os.path.basename( totFname ), suffix ), 'SUCCESS'

def worker_process_download_tvtorrent( tvTorUnit, client = None, maxtime_in_secs = 14400, kill_if_fail = False,
                                       num_iters = 1 ):
    time0 = time.time( )
    def kill_failing( torrentId ):
        if not kill_if_fail: return
        plexcore_deluge.deluge_remove_torrent( client, [ torrentId ], remove_data = kill_if_fail )
        
    assert( maxtime_in_secs > 0 )
    def create_status_dict( status, status_message ):
        assert( status in ('SUCCESS', 'FAILURE' ) )
        return {
            'status' : status,
            'message' : status_message,
            'time' : time.time( ) - time0
        }
    torFileName = tvTorUnit[ 'torFname' ]
    totFname = tvTorUnit[ 'totFname' ]
    minSize = tvTorUnit[ 'minSize' ]
    maxSize = tvTorUnit[ 'maxSize' ]
    if client is None:
        client, status = plexcore_deluge.get_deluge_client( )
        if client is None:
            return None, create_status_dict( 'FAILURE', 'cannot create or run a valid deluge RPC client.' )
    #
    ## now get list of torrents, choose "top" one
    data, status = get_tv_torrent_jackett( torFileName, maxnum = 100, keywords = [ 'x264', 'x265', '720p' ],
                                           minsize = minSize, maxsize = maxSize, keywords_exc = [ 'xvid' ])
    if status != 'SUCCESS': return None, create_status_dict( 'FAILURE', status )
    print( 'got %d candidates for %s in %0.3f seconds' % ( len(data), torFileName, time.time( ) - time0 ) )
    failing_reasons = [ ]
    numiters, rem = divmod( maxtime_in_secs, 30 )
    if rem != 0: numiters += 1
    
    def process_single_iteration( data, idx ):
        mag_link = data[ idx ]['link']
        #
        ## download the top magnet link
        torrentId = plexcore_deluge.deluge_add_magnet_file( client, mag_link )
        if torrentId is None:
            return None, create_status_dict( 'FAILURE',
                                             'could not add idx = %s, magnet_link = %s, for candidate = %s' % (
                                                 idx, mag_link, torFileName ) )
        time00 = time.time( )
        for jdx in range( numiters ):
            time.sleep( 30 )
            torrent_info = plexcore_deluge.deluge_get_torrents_info( client )
            if torrentId not in torrent_info:
                kill_failing( torrentId )
                return None, create_status_dict( 'FAILURE', 'ERROR, COULD NOT GET IDX = %d, TORRENT ID = %s.' % (
                    idx, torrentId.decode('utf-8').lower()[:6] ) )
            tor_info = torrent_info[ torrentId ]
            status = tor_info[ b'state'].decode('utf-8').upper( )
            progress = tor_info[ b'progress']
            print( 'after %0.3f seconds, attempt #%d, for %s: status = %s, progress = %0.1f%%' % (
                time.time( ) - time00, idx + 1, torFileName, status, progress ) )
            if status in ( 'SEEDING', 'PAUSED' ): # now let's be ambitious and create the new file
                fullFname, status = _finish_and_clean_working_tvtorrent_download(
                    totFname, client, torrentId, tor_info )
                if status != 'SUCCESS':
                    kill_failing( torrentId )
                    return None, create_status_dict( 'FAILURE', status )
                return fullFname, create_status_dict(
                    'SUCCESS',
                    'attempt #%d successfully downloaded %s' % (
                        idx + 1, torFileName ) )
        #
        ## did not finish in time
        kill_failing( torrentId )
        return None, create_status_dict( 'FAILURE',
                                         'failed to download idx = %d, %s after %0.3f seconds' % (
                                             idx, torFileName, time.time( ) - time00 ) )
    for idx in range( num_iters ):
        dat, status_dict = process_single_iteration( data, idx )
        if dat is not None:
            return dat, status_dict
        failing_reasons.append( status_dict[ 'message' ] )
    #
    ## final failing condition
    return None, create_status_dict( 'FAILURE','\n'.join( failing_reasons ) )
                                     
