#!/usr/bin/env python3

import sys, os
from plexcore import plexcore_deluge
from optparse import OptionParser

def main( ):
    act_args = sys.argv[1:]
    #
    ## by first set of names
    if act_args[0] in ( '-h', '--help' ):
        print("Possible commands: info, rm, add, pause, resume, push")
        return
    client, status = plexcore_deluge.get_deluge_client( )
    if status != 'SUCCESS':
        print("ERROR, COULD NOT GET VALID DELUGE CLIENT.")
        return
    if act_args[0] == 'info':
        if any(map(lambda tok: tok == "*", act_args[1:] ) ):
            torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
        elif len( act_args ) == 1:
            torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
        else: torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, act_args[1:] )
        torrentInfo = plexcore_deluge.deluge_get_torrents_info( client )
        infos = list(map(lambda torrentId: plexcore_deluge.deluge_format_info(
            torrentInfo[ torrentId ], torrentId ), torrentIds ) )
        if len( infos ) != 0:
            print( '%s\n' % '\n'.join(map(lambda info: '%s\n' % info, infos)))
    elif act_args[0] == 'resume':
        if any(map(lambda tok: tok == "*", act_args[1:] ) ):
            torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
        else: torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, act_args[1:] )
        plexcore_deluge.deluge_resume_torrent( client, torrentIds )
    elif act_args[0] == 'pause':
        if any(map(lambda tok: tok == "*", act_args[1:] ) ):
            torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
        else: torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, act_args[1:] )
        plexcore_deluge.deluge_pause_torrent( client, torrentIds )
    elif act_args[0] == 'rm':
        if any(map(lambda tok: tok == "*", act_args[1:] ) ):
            torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, [ "*" ] )
        else: torrentIds = plexcore_deluge.deluge_get_matching_torrents( client, act_args[1:] )
        #
        parser = OptionParser( )
        parser.add_option('--remove_data', action='store_true', default=False,
                          help = "remove the torrent's data" )
        opts, args = parser.parse_args( act_args[1:] )
        plexcore_deluge.deluge_remove_torrent(client, torrentIds, remove_data = opts.remove_data )
    elif act_args[0] == 'push':
        parser = OptionParser( )
        parser.add_option('--host', dest='url', action='store', type=str, default = 'localhost',
                          help = 'URL of the deluge server. Default is localhost.' )
        parser.add_option('--port', dest='port', action='store', type=int, default = 12345,
                          help = 'Port for the deluge server. Default is 12345.' )
        parser.add_option('--username', dest='username', action='store', type=str, default = 'admin',
                          help = 'Username to login to the deluge server. Default is admin.' )
        parser.add_option('--password', dest='password', action='store', type=str, default = 'admin',
                          help = 'Password to login to the deluge server. Default is admin.' )
        opts, args = parser.parse_args( act_args[1:] )
        status = plexcore_deluge.push_deluge_credentials( opts.url, opts.port, opts.username, opts.password )
        if status != 'SUCCESS': print( status )
    elif act_args[0] == 'add': # adds a single thing
        assert( len( act_args ) > 1 )
        candidate_add = act_args[1]
        print( candidate_add )
        if candidate_add.startswith( 'magnet' ): # is magnet
            plexcore_deluge.deluge_add_magnet_file( client, candidate_add )
            return
        if plexcore_deluge.deluge_is_url( candidate_add ): # is an URL
            plexcore_deluge.deluge_add_url( client, candidate_add )
            return
        if plexcore_deluge.deluge_is_torrent_file( candidate_add ): # is a torrent file
            plexcore_deluge.deluge_add_torrent_file( client, candidate_add )

        
if __name__=='__main__':
    main( )
