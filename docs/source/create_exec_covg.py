#!/usr/bin/env python3

import tabulate, os, logging
from optparse import OptionParser

logger = logging.getLogger( )
logger.setLevel( logging.INFO )

_coverage_dict = {
    'plex_core_cli.py' : True,
    'plex_deluge_console.py' : True,
    'plex_resynclibs.py' : True,
    'plex_store_credentials.py' : True,
    'rsync_subproc.py' : True,
    #
    'plex_config_gui.py' : True,
    'plex_core_gui.py' : False,
    'plex_create_texts.py' : False,
    #
    'get_plextvdb_batch.py' : True,
    'get_tv_tor.py' : True,
    'plex_tvdb_epinfo.py' : True,
    'plex_tvdb_epname.py' : True,
    'plex_tvdb_futureshows.py' : True,
    'plex_tvdb_plots.py' : True,
    #
    'plex_tvdb_totgui.py' : False,
    #
    'get_mov_tor.py' : True,
    #
    'plex_tmdb_totgui.py' : False,
    #
    'plex_music_album.py' : True,
    'plex_music_metafill.py' : True,
    'plex_music_songs.py' : True,
    'upload_to_gmusic.py' : True,
    #
    'plex_email_notif.py' : True,
    #
    'plex_email_gui.py' : False }

def _create_cell( execs ):
    assert( len(set(execs) - set( _coverage_dict ) ) == 0 )
    assert( all(map(lambda exc: exc.endswith( '.py' ), execs ) ) )
    def _make_str( exc ):
        if _coverage_dict[ exc ]:
            return '- :ref:`%s <%s>` |cbox|' % ( exc, '%s_label' % exc )
        else:
            return '- :ref:`%s <%s>`' % ( exc, '%s_label' % exc )
    return '\n'.join( map(_make_str, execs ) )

_table = [
    ( "``plexcore``",
      _create_cell([ 'plex_core_cli.py', 'plex_deluge_console.py', 'plex_resynclibs.py',
                     'plex_store_credentials.py', 'rsync_subproc.py' ]),
      _create_cell([ 'plex_config_gui.py', 'plex_core_gui.py', 'plex_create_texts.py' ] ) ),
    ( "``plextvdb``",
      _create_cell([ 'get_plextvdb_batch.py', 'get_tv_tor.py', 'plex_tvdb_epinfo.py', 'plex_tvdb_epname.py',
                     'plex_tvdb_futureshows.py', 'plex_tvdb_plots.py' ]),
      _create_cell([ 'plex_tvdb_totgui.py' ] ) ),
    ( "``plextmdb``",
      _create_cell([ 'get_mov_tor.py' ]),
      _create_cell([ 'plex_tmdb_totgui.py' ]) ),
    ( "``plexmusic``",
      _create_cell([ 'plex_music_album.py', 'plex_music_metafill.py', 'plex_music_songs.py', 'upload_to_gmusic.py' ]),
      _create_cell([ ]) ),
    ( "``plexemail``",
      _create_cell([ 'plex_email_notif.py' ]), _create_cell([ 'plex_email_gui.py' ]) )
]

_table_tvtorrents = [
    ( "`EZTV.IO`_", ":py:meth:`get_tv_torrent_eztv_io <plextvdb.plextvdb_torrents.get_tv_torrent_eztv_io>`", False ),
    ( "Zooqle_", ":py:meth:`get_tv_torrent_zooqle <plextvdb.plextvdb_torrents.get_tv_torrent_zooqle>`", True ),
    ( "RARBG_", ":py:meth:`get_tv_torrent_rarbg <plextvdb.plextvdb_torrents.get_tv_torrent_rarbg>`", False ),
    ( "Torrentz_", ":py:meth:`get_tv_torrent_torrentz <plextvdb.plextvdb_torrents.get_tv_torrent_torrentz>`", False ),
    ( "KickAssTorrents_", ":py:meth:`get_tv_torrent_kickass <plextvdb.plextvdb_torrents.get_tv_torrent_kickass>`", False ),
    ( "`The Pirate Bay`_", ":py:meth:`get_tv_torrent_tpb <plextvdb.plextvdb_torrents.get_tv_torrent_tpb>`", False ),
    ( "Jackett_ torrent search", ":py:meth:`get_tv_torrent_jackett <plextvdb.plextvdb_torrents.get_tv_torrent_jackett>`", True )
]

_table_movietorrents = [
    ( "`EZTV.IO`_", ":py:meth:`get_movie_torrent_eztv_io <plextmdb.plextmdb_torrents.get_movie_torrent_eztv_io>`", False ),
    ( "Zooqle_", ":py:meth:`get_movie_torrent_zooqle <plextmdb.plextmdb_torrents.get_movie_torrent_zooqle>`", True ),
    ( "RARBG_", ":py:meth:`get_movie_torrent_rarbg <plextmdb.plextmdb_torrents.get_movie_torrent_rarbg>`", False ),
    ( "KickAssTorrents_", ":py:meth:`get_movie_torrent_kickass <plextmdb.plextmdb_torrents.get_movie_torrent_kickass>`", False ),
    ( "`The Pirate Bay`_", ":py:meth:`get_movie_torrent_tpb <plextmdb.plextmdb_torrents.get_movie_torrent_tpb>`", False ),
    ( "Jackett_ torrent search", ":py:meth:`get_movie_torrent_jackett <plextmdb.plextmdb_torrents.get_movie_torrent_jackett>`", True ),
    ( "`YTS API`_", ":py:meth:`get_movie_torrent <plextmdb.plextmdb_torrents.get_movie_torrent>`", True )
]

_table_showconfig_settings = [
    ( "|main_config_gui|", "|login_config_gui|", "|credentials_config_gui|", "|music_config_gui|" ),
    ( "`12 total settings <sec_main_config_gui_>`_",
      "`4 login settings <sec_login_config_gui_>`_",
      "`4 credential settings <sec_credentials_config_gui_>`_",
      "`4 music settings <sec_music_config_gui_>`_" ) ]

_table_showexample_plexmusicsongs = [
    ( "|plex_music_songs_clip1|", "|plex_music_songs_clip2|", "|plex_music_songs_clip3|" ),
    ( "`Example of using the executable, plex_music_songs.py downloading by artist and songs <plex_music_songs_clip1_>`_",
     "`Example of using the executable, plex_music_songs.py downloading by artist and album <plex_music_songs_clip2_>`_",
     "`Example of using the executable, plex_music_songs.py downloading by separate list of artists and songs <plex_music_songs_clip3_>`_" ) ]

if __name__ == '__main__':
    
    print( 'WHICH CLIs and GUIs FINISHED\n' )
    print( '%s\n' % ''.join( ['-'] * 50 ) )
    print( tabulate.tabulate( _table, [ 'Functionality', 'CLI', 'GUI' ], tablefmt = 'rst' ) )
    print('\n\n\n')
    print( 'WHICH TV TORRENT SERVICES WORK\n' )
    print( '%s\n' % ''.join( ['-'] * 50 ) )
    print( tabulate.tabulate( _table_tvtorrents, [ "Torrent Service", "Search Method", "Does It Work?" ],
                              tablefmt = 'rst' ) )
    print('\n\n\n')
    print( 'WHICH TV TORRENT SERVICES WORK\n' )
    print( '%s\n' % ''.join( ['-'] * 50 ) )
    print( tabulate.tabulate( _table_movietorrents, [ "Torrent Service", "Search Method", "Does It Work?" ],
                              tablefmt = 'rst' ) )
    print('\n\n\n')
    print( 'WHICH CONFIGURATION SETTINGS\n' )
    print( '%s\n' % ''.join( ['-'] * 50 ) )
    print( tabulate.tabulate( _table_showconfig_settings, tablefmt = 'rst' ) )
    


