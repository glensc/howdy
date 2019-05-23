#!/usr/bin/env python3

import signal, logging, sys, os, pickle, gzip, qdarkstyle
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from functools import reduce
mainDir = reduce(lambda x,y: os.path.dirname( x ), range(2),
                 os.path.abspath( __file__ ) )
sys.path.append( mainDir )
from optparse import OptionParser
from plexcore import plexcore
from plextmdb import plextmdb_gui
from PyQt4.QtGui import QApplication

def main(info = False, doLocal = True, verify = True ):
    app = QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if info: logging.basicConfig( level = logging.INFO )
    fullurl, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )
    movie_data_rows = pickle.load( gzip.open( 'movie_data_rows.pkl.gz', 'rb' ) )
    tmdbgui = plextmdb_gui.TMDBGUI( token, fullurl, movie_data_rows, verify = verify )
    result = app.exec_( )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--info', dest='do_info', action='store_true',
                      default = False, help = 'Run info mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')
    opts, args = parser.parse_args( )
    main( info = opts.do_info, doLocal = opts.do_local, verify = opts.do_verify )
