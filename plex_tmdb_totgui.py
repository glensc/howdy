#!/usr/bin/env python3

import sys, signal
# code to handle Ctrl+C, convenience method for command line tools
def signal_handler( signal, frame ):
    print( "You pressed Ctrl+C. Exiting...")
    sys.exit( 0 )
signal.signal( signal.SIGINT, signal_handler )
from plexcore import plexcore
from plextmdb import plextmdb_totgui
from optparse import OptionParser
import logging, PyQt4.QtGui, os, qdarkstyle

def main(debug = False, doLocal = True, doLarge = False, verify = True):
    app = PyQt4.QtGui.QApplication([])
    app.setStyleSheet( qdarkstyle.load_stylesheet_pyqt( ) )
    if debug: logging.basicConfig( level = logging.DEBUG )
    fullurl, token = plexcore.checkServerCredentials(
        doLocal = doLocal, verify = verify )    
    tmdb_mygui = plextmdb_totgui.TMDBTotGUI( fullurl, token, doLarge = doLarge,
                                             verify = verify )
    result = app.exec_( )
    return tmdb_mygui

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--large', dest='do_large', action='store_true',
                      default = False, help = 'Run with large fonts to help with readability.' )
    parser.add_option('--local', dest='do_local', action='store_true',
                      default = False, help = 'Check for locally running plex server.')
    parser.add_option('--debug', dest='do_debug', action='store_true',
                      default = False, help = 'Run debug mode if chosen.')
    parser.add_option('--noverify', dest='do_verify', action='store_false',
                      default = True, help = 'Do not verify SSL transactions if chosen.')    
    opts, args = parser.parse_args( )
    main( debug = opts.do_debug, doLocal = opts.do_local, doLarge = opts.do_large, verify = opts.do_verify )
