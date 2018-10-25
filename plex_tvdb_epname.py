#!/usr/bin/env python3

import signal
from plexcore import signal_handler
signal.signal( signal.SIGINT, signal_handler)
from plextvdb import plextvdb
from optparse import OptionParser

def main( ):
    parser = OptionParser( )
    parser.add_option('-s', '--series', dest = 'series', type=str, action='store',
                      help = 'The name of the series' )
    parser.add_option('-e', '--epstring', dest='epstring', type=str, action='store',
                      help = 'The episode string, in the form S%02dE%02d.' )
    parser.add_option('--summary', dest='do_summary', action='store_true', default = False,
                      help = 'If chosen, get a summary of all the seasons and episodes for the SERIES.')
    parser.add_option('-S', '--season', dest='season', action='store', type=int,
                      help = 'If chosen, get a list of all episode titles for this season of the SERIES.')
    parser.add_option('--noverify', dest='do_noverify', action='store_true', default = False,
                      help = 'If chosen, do not verify the SSL connection.')
    opts, args = parser.parse_args( )
    assert( opts.series is not None )
    if opts.do_summary:
        seriesName = opts.series.strip( )
        epdicts = plextvdb.get_tot_epdict_tvdb( seriesName, verify = not opts.do_noverify, showFuture = True )
        if epdicts is None:
            print('Error, could not find %s' % seriesName)
            return
        seasons = set( range( 1, max( epdicts.keys( ) ) + 1 ) ) & set( epdicts.keys( ) )
        print( '%d episodes for %s' % ( sum(map(lambda seasno: len( epdicts[ seasno ] ), seasons ) ),
                                        seriesName ) )
        for seasno in sorted( seasons ):
            print('SEASON %02d: %d episodes' % ( seasno, len( epdicts[ seasno ] ) ) )
    elif opts.season is not None:
        seriesName = opts.series.strip( )
        epdicts = plextvdb.get_tot_epdict_tvdb( seriesName, verify = not opts.do_noverify, showFuture = True )
        if epdicts is None:
            print( 'Error, could not find %s' % seriesName )
            return
        if opts.season not in epdicts:
            print( 'Error, season %02d not in %s.' % ( opts.season, seriesName ) )
            return
        print('%d episodes in SEASON %02d of %s.' % ( len( epdicts[ opts.season ] ), opts.season, seriesName ) )
        for epnum in sorted( epdicts[ opts.season ] ):
            title, airedDate = epdicts[ opts.season ][ epnum ]
            print( 'Episode %02d/%02d: %s (%s)' % (
                epnum, len( epdicts[ opts.season ] ),
                title, airedDate.strftime( '%A, %d %B %Y' ) ) )
    else:
        assert( opts.epstring is not None )
        seriesName = opts.series.strip( )
        token = plextvdb.get_token( verify = not opts.do_noverify )
        series_id = plextvdb.get_series_id( seriesName, token, verify = not opts.do_noverify )
        if series_id is None:
            print( 'Error, could not find %s' % seriesName )
            return
        seasepstring = opts.epstring.strip( ).upper( )
        if not seasepstring[0] == 'S':
            print( 'Error, first string must be an s or S.' )
            return
        seasepstring = seasepstring[1:]
        splitseaseps = seasepstring.split('E')[:2]
        if len( splitseaseps ) != 2:
            print( 'Error, string must have a SEASON and EPISODE part.' )
            return
        try:
            seasno = int( splitseaseps[0] )
        except:
            print( 'Error, invalid season number.' )
            return
        try:
            epno = int( splitseaseps[1] )
        except:
            print( 'Error, invalid episode number.' )
            return
        data = plextvdb.get_episode_name( series_id, seasno, epno, token )
        if data is None:
            print( 'Error, could not find SEASON %02d, EPISODE %02d, in %s.' % (
                seasno, epno, seriesName ) )
            return
        epname, fa = data
        print('%s (%s)' % ( epname, fa.strftime('%A, %d %B %Y' ) ) )
            
if __name__=='__main__':
    main( )
        
        
