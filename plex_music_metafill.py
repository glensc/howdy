#!/usr/bin/env python3

from __future__ import unicode_literals
import codecs, sys, os
from plexmusic import plexmusic
from optparse import OptionParser

def choose_youtube_item( name, maxnum = 10 ):
    youtube = plexmusic.get_youtube_service( )
    videos = plexmusic.youtube_search( youtube, name, max_results = maxnum )
    if len( videos ) != 1:
        sortdict = { idx + 1 : item for (idx, item) in enumerate(videos) }
        if sys.version_info.major == 2:
            bs = codecs.encode( 'Choose YouTube video:\n%s\n' %
                                '\n'.join(map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                                              sorted( sortdict ) ) ), 'utf-8' )
            iidx = raw_input( bs )
        else:
            bs = 'Choose YouTube video:\n%s\n' % '\n'.join(
                map(lambda idx: '%d: %s' % ( idx, sortdict[ idx ][ 0 ] ),
                    sorted( sortdict ) ) )
            iidx = input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the YouTube videos. Exiting...')
                return None
            _, youtubeURL = sortdict[ iidx ]
        except:
            print('Error, did not choose a valid integer. Exiting...')
            return None
    elif len( videos ) == 1:
        _, youtubeURL = videos[0]
    else:
        print('Could find no YouTube videos: %s' % name)
        return None
    return youtubeURL

def main( ):
    parser = OptionParser( )
    parser.add_option( '--songs', dest='song_names', type=str, action='store',
                       help = 'Names of the song to put into M4A files. Separated by ;' )
    parser.add_option( '--artist', dest='artist_name', type=str, action='store',
                       help = 'Name of the artist to put into the M4A file.' )
    parser.add_option( '--maxnum', dest='maxnum', type=int, action='store',
                       default = 10, help =
                       'Number of YouTube video choices to choose for your song.' +
                       ' Default is 10.' )
    opts, args = parser.parse_args( )
    assert(all(map(lambda tok: tok is not None,
                   ( opts.song_names, opts.artist_name ) ) ) )
    #
    ## first get music metadata
    pm = plexmusic.PlexMusic( )

    song_names = map(lambda song_name: song_name.strip( ), opts.song_names.split(';'))

    for song_name in song_names:
        try:
            data_dict, status = pm.get_music_metadata( song_name = song_name,
                                                       artist_name = opts.artist_name )
            if status != 'SUCCESS':
                print( status )
                continue
        except Exception as e:
            print( e )
            continue
        artist_name = data_dict[ 'artist' ]
        song_name = data_dict[ 'song' ]
        print( 'ACTUAL ARTIST: %s' % artist_name )
        print( 'ACTUAL SONG: %s' % song_name )
        #
        ## now get the youtube song selections
        youtubeURL = choose_youtube_item( '%s %s' % ( artist_name, song_name ),
                                          maxnum = opts.maxnum )
        if youtubeURL is None:
            continue
        #
        ## now download the song into the given filename
        filename = '%s.%s.m4a' % ( artist_name, song_name )
        plexmusic.get_youtube_file( youtubeURL, filename )
        #
        ## now fill out the metadata
        plexmusic.fill_m4a_metadata( filename, data_dict )
        #
        ##
        os.chmod( filename, 0o644 )
    
if __name__=='__main__':
    main( )
        
