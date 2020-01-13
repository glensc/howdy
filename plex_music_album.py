#!/usr/bin/env python3

import sys, signal
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
import codecs, os, tabulate, logging
from plexmusic import plexmusic
from plexemail import emailAddress
from optparse import OptionParser

def main( ):
    parser = OptionParser( )
    parser.add_option( '-a', '--artist', dest='artist_name', type=str, action='store',
                      help = 'Name of the artist to get album image for.' )
    parser.add_option( '-A', '--album', dest='album_name', type=str, action='store',
                      help = 'Name of the album to get album image for.' )
    parser.add_option( '--songs', dest='do_songs', action='store_true', default = False,
                      help = 'If chosen, get the song listing instead of downloading the album image.')
    parser.add_option( '--formatted', dest='do_formatted', action='store_true', default = False,
                      help = ' '.join([
                          'If chosen, print the song listing in a format recognized by plex_music_metafill.py',
                          'for downloading a collection of songs.' ]) )
    parser.add_option( '--albums', dest='do_albums', action='store_true', default = False,
                       help = 'If chosen, then get a list of all the songs in all studio albums for the artist.' )
    parser.add_option( '--debug', dest='do_debug', action='store_true', default=False,
                       help = 'Run with debug mode turned on.' )
    parser.add_option( '--noverify', dest='do_verify', action='store_false', default = True,
                       help = 'If chosen, do not verify SSL connections.' )
    parser.add_option( '--musicbrainz', dest='do_musicbrainz', action='store_true', default = False,
                       help = ' '.join([
                           'If chosen, use Musicbrainz to get the artist metadata.',
                           'Note that this is expensive, and is always applied when the --albums flag is set.' ]))
    opts, args = parser.parse_args( )
    plexmusic.MusicInfo.get_set_musicbrainz_useragent( emailAddress )
    plexmusic.MusicInfo.set_musicbrainz_verify( verify = opts.do_verify )
    assert( opts.artist_name is not None )
    if not opts.do_albums: assert( opts.album_name is not None )
    logger = logging.getLogger( )
    if opts.do_debug: logger.setLevel( logging.DEBUG )
    #
    ##    
    plastfm = plexmusic.PlexLastFM( verify = opts.do_verify )
    if opts.do_albums:
        mi = plexmusic.MusicInfo( opts.artist_name.strip( ) )
        mi.print_format_album_names( )
        return
    
    if not opts.do_songs: # just get the song image
        if opts.do_musicbrainz:
            mi = plexmusic.MusicInfo( opts.artist_name.strip( ) )
            _, status = mi.get_album_image( opts.album_name )
        else:
            _, status = plastfm.get_album_image( opts.artist_name, opts.album_name )
        if status != 'SUCCESS':
            print( status )
        return

    #
    ## now get song listing, --songs is chosen
    if opts.do_musicbrainz:
        mi = plexmusic.MusicInfo( opts.artist_name.strip( ) )
        track_listing, status = mi.get_song_listing(
            opts.album_name )
    else:
        track_listing, status = plastfm.get_song_listing(
            opts.artist_name, album_name = opts.album_name )
    if status != 'SUCCESS':
        print( status )
        return

    if not opts.do_formatted:
        print( '\n%s\n' %
               tabulate.tabulate( track_listing, headers = [ 'Song', 'Track #' ] ) )
    else:
        print( '\n%s\n' % ';'.join(map(lambda title_trkno: title_trkno[0], track_listing)) )

if __name__ == '__main__':
    try:
        main( )
    except Exception as e:
        print( e )
