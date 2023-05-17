import os, sys, numpy, glob, datetime, inspect
import logging, requests, time, io, PIL.Image
import pickle, gzip
from multiprocessing import Process, Manager
import pathos.multiprocessing as multiprocessing
from bs4 import BeautifulSoup
from itertools import chain
from urllib.parse import urlparse
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#
from howdy import baseConfDir
from howdy.tv import tv, get_token
from howdy.tv.tv_season_gui import HowdyTVSeasonGUI
from howdy.core import core, geoip_reader, QLabelWithSave
from howdy.core import get_formatted_size, get_formatted_duration
from howdy.core import QDialogWithPrinting, ProgressDialogThread

class HowdyTVGUIThread( ProgressDialogThread ):
    finalData = pyqtSignal( dict )
    
    def __init__( self, parent, fullURL, token, tvdb_token,
                  tvdata_on_plex = None,
                  didend = None, toGet = None, verify = False,
                  showsToExclude = [ ], num_threads = 16 ):
        super( HowdyTVGUIThread, self ).__init__(
            parent,  'PLEX TV GUI PROGRESS WINDOW' )
        self.fullURL = fullURL
        self.token = token
        self.tvdb_token = tvdb_token
        self.tvdata_on_plex = tvdata_on_plex
        self.didend = didend
        self.toGet = toGet
        self.verify = verify
        self.showsToExclude = showsToExclude
        self.num_threads = num_threads
        self.finalData.connect( parent.process_final_state )

    def reset( self, showsToExclude = [ ], eraseTVData = True ):
        self.tvdata_on_plex = None
        self.didend = None
        self.toGet = None
        self.showsToExclude = showsToExclude

    def run( self ):
        self.progress_dialog.show( )
        time0 = self.progress_dialog.t0
        final_data_out = { }
        mytxt = '0, started loading in data on %s.' % (
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        #
        libraries_dict = core.get_libraries(
            self.token, fullURL = self.fullURL, do_full = True )
        if not any(map(lambda value: 'show' in value[-1], libraries_dict.values( ) ) ):
            raise ValueError( 'Error, could not find TV shows.' )
        library_name = max(map(lambda key: libraries_dict[ key ][ 0 ],
                               filter(lambda key: libraries_dict[key][1] == 'show',
                                      libraries_dict ) ) )
        final_data_out[ 'library_name'] = library_name
        mytxt = '1, found TV library in %0.3f seconds.' % ( time.time( ) - time0 )
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        #
        if self.tvdata_on_plex is None:
            self.tvdata_on_plex = core.get_library_data(
                library_name, fullURL = self.fullURL, token = self.token,
                num_threads = self.num_threads )
        if self.tvdata_on_plex is None:
            raise ValueError( 'Error, could not find TV shows on the server.' )
        mytxt = '2, loaded TV data from Plex server in %0.3f seconds.' % (
            time.time( ) - time0 )
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        #
        ## using a stupid-ass pattern to shave some seconds off...
        manager = Manager( )
        shared_list = manager.list( )
        myLock = manager.RLock( )
        myStage = manager.Value( 'stage', 2 )
        #
        def _process_didend( ):
            if self.didend is not None:
                shared_list.append( ( 'didend', self.didend ) )
                return
            didEnd = tv.get_all_series_didend(
                self.tvdata_on_plex, verify = self.verify, tvdb_token = self.tvdb_token )
            myLock.acquire( )
            myStage.value += 1
            mytxt = '%d, added information on whether shows ended in %0.3f seconds.' % (
                myStage.value, time.time( ) - time0 )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            myLock.release( )
            shared_list.append( ( 'didend', didEnd ) )

        def _process_missing( ):
            if self.toGet is not None:
                shared_list.append( ( 'toGet', self.toGet ) )
                return
            toGet = tv.get_remaining_episodes(
                self.tvdata_on_plex, showSpecials = False,
                showsToExclude = self.showsToExclude,
                verify = self.verify, token = self.tvdb_token )
            myLock.acquire( )
            myStage.value += 1
            mytxt = '%d, found missing episodes in %0.3f seconds.' % (
                myStage.value, time.time( ) - time0 )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            myLock.release( )
            shared_list.append( ( 'toGet', toGet ) )
            
        def _process_plot_tvshowstats( ):
            tvdata_date_dict = tv.get_tvdata_ordered_by_date(
                self.tvdata_on_plex )
            years_have = set(map(lambda date: date.year, tvdata_date_dict ) )
            with multiprocessing.Pool(
                    processes = multiprocessing.cpu_count( ) ) as pool:
                figdictdata = dict( pool.map(
                    lambda year: ( year, tv.create_plot_year_tvdata(
                        tvdata_date_dict, year, shouldPlot = False ) ),
                    years_have ) )
            myLock.acquire( )
            myStage.value += 1
            mytxt = '%d, made plots of tv shows added in %d years in %0.3f seconds.' % (
                myStage.value, len( years_have ), time.time( ) - time0 )
            logging.info( mytxt )
            self.emitString.emit( mytxt )
            myLock.release( )
            shared_list.append( ( 'plotYears', figdictdata ) )
            
        jobs = [ Process( target = _process_didend ),
                 Process( target = _process_missing ) ]
        #         Process( target = _process_plot_tvshowstats ) ]
        for process in jobs: process.start( )
        for process in jobs: process.join( )
        #
        final_data = dict( shared_list )
        assert( set( final_data ) == set([ 'didend', 'toGet' ]) )
        didend = final_data[ 'didend' ]
        toGet = final_data[ 'toGet' ]
        for seriesName in self.tvdata_on_plex:
            self.tvdata_on_plex[ seriesName ][ 'didEnd' ] = didend[ seriesName ]
        final_data_out[ 'tvdata_on_plex' ] = self.tvdata_on_plex
        mytxt = '%d, finished loading in all data on %s.' % (
            myStage.value + 1,
            datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        missing_eps = dict(map(
            lambda seriesName: ( seriesName, toGet[ seriesName ][ 'episodes' ] ),
            set( self.tvdata_on_plex ) & set( toGet ) - set( self.showsToExclude ) ) )
        final_data_out[ 'missing_eps' ] = missing_eps
        self.finalData.emit( final_data_out )
        self.stopDialog.emit( ) # now stop everything
        
class HowdyTVGUI( QDialogWithPrinting ):
    mySignal = pyqtSignal( list )
    tvSeriesSendList = pyqtSignal( list )
    tvSeriesRefreshRows = pyqtSignal( list )
    emitStatusToShow = pyqtSignal( int )

    @classmethod
    def getShowSummary( cls, seriesName, tvdata_on_plex, missing_eps ):
        seasons_info = tvdata_on_plex[ seriesName ][ 'seasons' ]
        overview = tvdata_on_plex[ seriesName ][ 'summary' ]
        didend = tvdata_on_plex[ seriesName ][ 'didEnd' ]
        num_total = sum(list(
            map(lambda seasno: len( seasons_info[ seasno ][ 'episodes' ] ),
                set( seasons_info ) - set([0]))))
        if seriesName not in missing_eps: num_missing = 0
        else: num_missing = len( missing_eps[ seriesName ] )
        if didend: show_status = "Show has ended"
        else: show_status = "Show is still ongoing"
        minDate = min(
            map(lambda seasno: min(
                map(lambda epno: seasons_info[ seasno ]['episodes'][epno]['date aired' ],
                    seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0])))
        maxDate = max(
            map(lambda seasno: max(
                map(lambda epno: seasons_info[ seasno ]['episodes'][epno]['date aired' ],
                    seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) - set([0])))
        
        html = BeautifulSoup("""
        <html>
        <p>Summary for %s.</p>
        <p>%s.</p>
        <p>%02d episodes, %02d missing.</p>
        <p>First episode aired on %s.</p>
        <p>Last episode aired on %s.</p>
        <p>
        </html>""" % ( seriesName, show_status,
                       num_total, num_missing,
                       minDate.strftime( '%B %d, %Y' ),
                       maxDate.strftime( '%B %d, %Y' ) ), 'lxml' )
        body_elem = html.find_all('body')[0]
        html2 = BeautifulSoup("""
        <html>
        <body>
        </body>
        </html>""", 'lxml' )
        body2_elem = html2.find_all('body')[0]
        if len( overview ) != 0:
            summary_tag = html2.new_tag("p")
            summary_tag.string = overview
            body2_elem.append( summary_tag )
        average_duration_in_secs = numpy.array(
            list( chain.from_iterable(
                map(lambda seasno: list(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'duration' ],
                        seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) -
                    set([0]))))).mean( )
        average_size_in_bytes = numpy.array(
            list( chain.from_iterable(
                map(lambda seasno: list(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'size' ],
                        seasons_info[ seasno ]['episodes'] ) ), set( seasons_info ) -
                    set([0]))))).mean( )
        dur_tag = html.new_tag( "p" )
        dur_tag.string = "average duration of %02d episodes: %s." % (
            num_total, get_formatted_duration( average_duration_in_secs ) )
        siz_tag = html.new_tag( "p" )
        siz_tag.string = "average size of %02d episodes: %s." % (
            num_total, get_formatted_size( average_size_in_bytes ) )
        body_elem.append( dur_tag )
        body_elem.append( siz_tag )
        return html.prettify( ), html2.prettify( )

    @classmethod
    def getSummaryImg( cls, imageURL, token ):
        if imageURL is None: return None
        return core.get_pic_data( imageURL, token )

    def processTVShow( self, seriesName ):
        assert( seriesName in self.tvdata_on_plex )
        self.currentSeriesName = seriesName
        if seriesName not in self.summaryShowInfo:
            self.summaryShowInfo[ seriesName ] = HowdyTVGUI.getShowSummary(
                seriesName, self.tvdata_on_plex, self.missing_eps )
            
        if seriesName not in self.showImages:
            self.showImages[ seriesName ] = HowdyTVGUI.getSummaryImg(
                self.tvdata_on_plex[ seriesName ][ 'picurl' ],
                self.token )

        showSummary, showSummaryOverview = self.summaryShowInfo[ seriesName ]
        showImg = self.showImages[ seriesName ]
        #
        ## now put this into summary image on left, summary info on right
        if showImg is not None:
            qpm = QPixmap.fromImage( QImage.fromData( showImg ) )
            qpm = qpm.scaledToWidth( self.size( ).width( ) * 0.95 )
            self.summaryShowImage.setPixmap( qpm )
        #else: self.summaryShowImage.setPixmap( )
        else: pass
        self.summaryShowInfoAreaLeft.setHtml( showSummary )
        self.summaryShowInfoAreaRight.setHtml( showSummaryOverview )

    def resizeImage( self, scaleIndex ): # what to do when image resized
        try:
            if self.currentSeriesName not in self.tvdata_on_plex: return
            showImg = self.showImages[ self.currentSeriesName ]
            if showImg is None: return
            qpm = QPixmap.fromImage( QImage.fromData( showImg ) )
            qpm = qpm.scaledToWidth( self.size( ).width( ) * 0.95 )
            self.summaryShowImage.setPixmap( qpm )
        except: pass

    def process_final_state( self, final_data_out ):
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        self.library_name = final_data_out[ 'library_name' ]
        self.tvdata_on_plex = final_data_out[ 'tvdata_on_plex' ]
        self.missing_eps = final_data_out[ 'missing_eps' ]
        #
        self.instantiatedTVShows = { }
        self.dt = datetime.datetime.now( ).date( )
        self.filterOnTVShows = QLineEdit( '' )
        self.setWindowTitle( 'The List of TV Shows on the Plex Server' )
        self.showImages = { }
        self.summaryShowInfo = { }
        #
        self.refreshButton = QPushButton( "REFRESH TV SHOWS" )
        self.tokenLabel = QLabel( )
        self.plexURLLabel = QLabel( )
        self.locationLabel = QLabel( )
        self.processPlexInfo( )
        self.numSeriesFound = QLabel( '%d total shows satisfying criteria' %
                                      len( self.tvdata_on_plex ) )
        #
        self.tm = HowdyTVTableModel( self )
        self.tv = HowdyTVTableView( self )
        self.tm.fillOutCalculation( )
        #
        allShowsButton = QRadioButton( 'ALL SHOWS', self )
        runningShowsButton = QRadioButton( 'RUNNING', self )
        finishedShowsButton = QRadioButton( 'FINISHED', self )
        missingShowsButton = QRadioButton( 'MISSING', self )
        self.qbg = QButtonGroup( )
        self.qbg.setExclusive( True )
        self.qbg.addButton( allShowsButton, 0 )
        self.qbg.addButton( runningShowsButton, 1 )
        self.qbg.addButton( finishedShowsButton, 2 )
        self.qbg.addButton( missingShowsButton, 3 )
        allShowsButton.click( )
        self.qbg.buttonClicked.connect( self.updateStatus )
        ##
        topWidget = QWidget( )
        topLayout = QGridLayout( )
        topWidget.setLayout( topLayout )
        #
        leftTopWidget = QWidget( )
        leftTopWidget.setStyleSheet("""
        QWidget {
        background-color: #373949;
        }""" )
        leftTopLayout = QGridLayout( )
        leftTopWidget.setLayout( leftTopLayout )
        leftTopLayout.addWidget( QLabel( 'PLEX TOKEN:' ), 0, 0, 1, 1 )
        leftTopLayout.addWidget( self.tokenLabel, 0, 1, 1, 1 )
        leftTopLayout.addWidget( QLabel( 'PLEX URL:' ), 1, 0, 1, 1 )
        leftTopLayout.addWidget( self.plexURLLabel, 1, 1, 1, 1 )
        leftTopLayout.addWidget( QLabel( 'LOCATION:' ), 2, 0, 1, 1 )
        leftTopLayout.addWidget( self.locationLabel, 2, 1, 1, 1 )
        topLayout.addWidget( leftTopWidget, 0, 0, 1, 2 )
        #
        rightTopWidget = QWidget( )
        rightTopLayout = QGridLayout( )
        rightTopWidget.setLayout( rightTopLayout )
        rightTopLayout.addWidget( QLabel( 'TV SHOW FILTER' ), 0, 0, 1, 1 )
        rightTopLayout.addWidget( self.filterOnTVShows, 0, 1, 1, 5 )
        rightTopLayout.addWidget( self.refreshButton, 1, 0, 1, 1 )
        rightTopLayout.addWidget( allShowsButton, 1, 1, 1, 1 )
        rightTopLayout.addWidget( runningShowsButton, 1, 2, 1, 1 )
        rightTopLayout.addWidget( finishedShowsButton, 1, 3, 1, 1 )
        rightTopLayout.addWidget( missingShowsButton, 1, 4, 1, 1 )
        rightTopLayout.addWidget( self.numSeriesFound, 2, 0, 1, 5 )
        topLayout.addWidget( rightTopWidget, 0, 2, 1, 3 )
        #
        myLayout.addWidget( topWidget )
        ##
        myLayout.addWidget( self.tv )
        #
        botWidget = QWidget( )
        botLayout = QVBoxLayout( )
        botWidget.setLayout( botLayout )
        self.summaryShowImage = QLabelWithSave( )
        botLayout.addWidget( self.summaryShowImage )
        botLowerWidget = QWidget( )
        botLowerLayout = QHBoxLayout( )
        botLowerWidget.setLayout( botLowerLayout )
        self.summaryShowInfoAreaLeft = QTextEdit( )
        self.summaryShowInfoAreaLeft.setReadOnly( True )
        self.summaryShowInfoAreaRight = QTextEdit( )
        self.summaryShowInfoAreaRight.setReadOnly( True )
        botLowerLayout.addWidget( self.summaryShowInfoAreaLeft )
        botLowerLayout.addWidget( self.summaryShowInfoAreaRight )
        botLayout.addWidget( botLowerWidget )
        myLayout.addWidget( botWidget )
        #
        ## set size, make sure not resizable
        self.setFixedWidth( self.tv.frameGeometry( ).width( ) * 1.05 )
        self.setFixedHeight( 1000 )
        #
        ## connect actions
        self.filterOnTVShows.textChanged.connect( self.tm.setFilterString )
        self.refreshButton.clicked.connect( self.refreshTVShows )
        self.emitStatusToShow.connect( self.tm.setFilterStatus )
        self.tm.emitNumSatisfied.connect( self.showNumSatisfied )
        #
        ## connect signals on resizing
        self.indexScalingSignal.connect( self.tv.setScalingIndex )
        self.indexScalingSignal.connect( self.resizeImage )
        #
        ## now change the initThread to connect to new slot
        ## do this once done
        try: self.initThread.finalData.disconnect( )
        except: pass
        self.initThread.finalData.connect( self.process_final_state_refresh )
        #
        ## now set the final size
        self.finalSize = self.size( )
        #
        self.show( )
        self.reset_sizes( ) # get current actual size
                                
    def __init__( self, token, fullURL, tvdata_on_plex = None,
                  didend = None, toGet = None, verify = True, doLarge = False ):
        super( HowdyTVGUI, self ).__init__(
            None, isIsolated = True, doQuit = True )
        self.fullURL = fullURL
        self.token = token
        self.tvdb_token = get_token( verify = verify )
        self.verify = verify
        if not doLarge: fontSize = 13
        else: fontSize = 26
        self.setStyleSheet("""
        QWidget {
        font-family: Consolas;
        font-size: %dpx;
        }""" % fontSize )
        self.hide( )
        #
        showsToExclude = tv.get_shows_to_exclude(
            tvdata_on_plex )
        self.initThread = HowdyTVGUIThread(
            self, self.fullURL, self.token, self.tvdb_token,
            tvdata_on_plex = tvdata_on_plex,
            didend = didend, toGet = toGet, verify = verify,
            showsToExclude = showsToExclude )
        self.initThread.start( )

    def process_final_state_refresh( self, final_data_out ):
        self.library_name = final_data_out[ 'library_name' ]
        self.tvdata_on_plex = final_data_out[ 'tvdata_on_plex' ]
        self.missing_eps = final_data_out[ 'missing_eps' ]
        #
        self.tm.fillOutCalculation( )
        #
        self.initThread.stopDialog.emit( )
        
    def processPlexInfo( self ):
        self.tokenLabel.setText( self.token )
        self.plexURLLabel.setText( self.fullURL )
        ipaddr = urlparse( self.fullURL ).netloc.split(':')[0]
        if ipaddr not in ( '127.0.0.1', 'localhost' ):
            myloc = geoip_reader.city( ipaddr )
            self.locationLabel.setText( '%s, %s, %s.' % (
                myloc.city.name, myloc.subdivisions.most_specific.iso_code,
                myloc.country.name ) )
        else: self.locationLabel.setText( 'LOCALHOST' )

    def refreshTVShows( self ):
        self.initThread.startDialog.emit( 'REFRESHING TV SHOWS' )
        showsToExclude = tv.get_shows_to_exclude( )
        self.initThread.reset( showsToExclude )
        self.initThread.start( )
        #
        ## now send signals/run actions
        self.tm.setFilterString( self.filterOnTVShows.text( ) )
        self.tm.setFilterStatus( self.qbg.checkedId( ) )

    def updateStatus( self, qrb ):
        mytxt = qrb.text( )
        mymap = { 'ALL SHOWS' : 0, 'RUNNING' : 1, 'FINISHED' : 2, 'MISSING' : 3 }
        self.emitStatusToShow.emit( mymap[ mytxt ] )

    def showNumSatisfied( self, num ):
        self.numSeriesFound.setText(
            '%d total shows satisfying criteria' %
            num )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        testDir = os.path.join( baseConfDir, 'tests' )
        if not os.path.isdir( testDir ): return
        if all([ self.tvdata_on_plex is None,
                 self.missing_eps is None ]):
            return
        if self.fullURL.startswith('http://127.0.0.1'):
            tvdataFile = 'tvdata.pkl.gz'
        else:
            tvdataFile = 'tvdata_remote.pkl.gz'            
        
        def _save_out_data( ):
            if self.tvdata_on_plex is not None:
                tvdata_on_plex = self.tvdata_on_plex.copy( )
                didend = dict(map(
                    lambda seriesName:
                    ( seriesName, tvdata_on_plex[ seriesName ][ 'didEnd' ] ),
                    tvdata_on_plex ) )
                list(map(lambda seriesName: tvdata_on_plex[ seriesName ].pop( 'didEnd' ),
                         tvdata_on_plex ) )
                pickle.dump(
                    tvdata_on_plex,
                    gzip.open( os.path.join( os.path.expanduser( '~/.config/howdy/tests' ),
                                             tvdataFile ), 'wb' ) )
                pickle.dump( didend, gzip.open(
                    os.path.join( os.path.expanduser( '~/.config/howdy/tests' ),
                                  'didend.pkl.gz' ), 'wb' ) )
            if self.missing_eps is not None:
                pickle.dump(
                    self.missing_eps,
                    gzip.open( os.path.join( os.path.expanduser( '~/.config/howdy/tests' ),
                                             'toGet.pkl.gz' ), 'wb' ) )
        saveAction = QAction( 'Save TV data', menu )
        saveAction.triggered.connect( _save_out_data )
        menu.addAction( saveAction )
        menu.popup( QCursor.pos( ) )            

class HowdyTVTableView( QTableView ):
    def __init__( self, parent ):
        super( HowdyTVTableView, self ).__init__( parent )
        self.parent = parent
        self.proxy = HowdyTVQSortFilterProxyModel( self, self.parent.tm )
        self.setModel( self.proxy )
        self.selectionModel( ).currentRowChanged.connect(
            self.processCurrentRow )
        #
        self.setShowGrid( True )
        self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row        
        self.setSortingEnabled( True )
        #
        self.setColumnWidth(0, 210 )
        self.setColumnWidth(1, 120 )
        self.setColumnWidth(2, 120 )
        self.setColumnWidth(3, 120 )
        self.setColumnWidth(4, 120 )
        self.setColumnWidth(5, 120 )
        self.setFixedWidth( 1.05 * ( 210 * 1 + 120 * 5 ) )
        #
        toBotAction = QAction( self )
        toBotAction.setShortcut( 'End' )
        toBotAction.triggered.connect( self.scrollToBottom )
        self.addAction( toBotAction )
        #
        toTopAction = QAction( self )
        toTopAction.setShortcut( 'Home' )
        toTopAction.triggered.connect( self.scrollToTop )
        self.addAction( toTopAction )
        #
        ## now do the same thing for contextMenuEvent with action
        popupAction = QAction( self )
        popupAction.setShortcut( 'Ctrl+Shift+S' )
        popupAction.triggered.connect( self.popupTVSeries )
        self.addAction( popupAction )

    def setScalingIndex( self, scaleIndex ):
        self.setColumnWidth(0, 210 * 1.05**scaleIndex )
        for colno in range(1, 6):
            self.setColumnWidth( colno, 120 * 1.05**scaleIndex )
        self.setFixedWidth( 1.05 * ( 210 * 1 + 120 * 5 ) * 1.05**scaleIndex )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        infoAction = QAction( 'Information', menu )
        infoAction.triggered.connect( self.popupTVSeries )
        menu.addAction( infoAction )
        menu.popup( QCursor.pos( ) )

    def popupTVSeries( self ):
        index_valid_proxy = max(filter(lambda index: index.column( ) == 0,
                                       self.selectionModel().selectedIndexes( ) ) )
        index_valid = self.proxy.mapToSource( index_valid_proxy )
        self.parent.tm.infoOnTVSeriesAtRow( index_valid.row( ) )

    def processCurrentRow( self, newIndex, oldIndex = None ):
        row_valid = self.proxy.mapToSource( newIndex ).row( )
        #
        ## episode data emit this row here
        self.parent.tm.emitRowSelected.emit( row_valid )

class HowdyTVQSortFilterProxyModel( QSortFilterProxyModel ):
    def __init__( self, parent, model ):
        super( HowdyTVQSortFilterProxyModel, self ).__init__( parent )
        self.setSourceModel( model )
        model.emitFilterChanged.connect( self.invalidateFilter )

    def sort( self, ncol, order ):
        self.sourceModel( ).sort( ncol, order )

    def filterAcceptsRow( self, rowNumber, sourceParent ):
        return self.sourceModel( ).filterRow( rowNumber )

class HowdyTVTableModel( QAbstractTableModel ):
    _headers = [ "TV Series", "Start Date", "Last Date",
                 "Seasons", "Episodes", "Missing" ]
    emitFilterChanged = pyqtSignal( )
    emitRowSelected = pyqtSignal( int )
    emitNumSatisfied = pyqtSignal( int )
    
    def __init__( self, parent = None ):
        super( HowdyTVTableModel, self ).__init__( parent )
        self.parent = parent # is the GUI that contains all the data
        self.actualTVSeriesData = [ ]
        self.sortColumn = 0
        self.filterStatus = 0 # 0, show everything; 1, show only tv series w/missing eps
        self.filterRegexp = QRegExp(
            '.', Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitRowSelected.connect( self.summaryOnTVShowAtRow )
        self.fillOutCalculation( )

    def infoOnTVSeriesAtRow( self, actualRow ):
        seriesData = self.actualTVSeriesData[ actualRow ]
        seriesName = seriesData[ 'seriesName' ]
        if seriesName not in self.parent.instantiatedTVShows:
            self.parent.instantiatedTVShows[ seriesName ] = HowdyTVShowGUI(
                seriesName, self.parent.tvdata_on_plex,
                self.parent.missing_eps, self.parent.tvdb_token,
                self.parent.token, parent = self.parent,
                verify = self.parent.verify )
        tvdbsi = self.parent.instantiatedTVShows[ seriesName ]
        result = tvdbsi.exec_( )

    def summaryOnTVShowAtRow( self, actualRow ):
        self.parent.processTVShow(
            self.actualTVSeriesData[
                actualRow ][ 'seriesName' ] )

    def filterRow( self, rowNumber ):
        data = self.actualTVSeriesData[ rowNumber ]        
        if self.filterStatus == 1: # running shows
            if data[ 'didEnd' ]: return False
        elif self.filterStatus == 2: # finished shows
            if not data[ 'didEnd' ]: return False
        elif self.filterStatus == 3: # shows with missing episodes
            if data[ 'numMissing' ] == 0: return False
        return self.filterRegexp.indexIn( data[ 'seriesName' ] ) != -1
            
    def setFilterStatus( self, filterStatus ):
        self.filterStatus = filterStatus
        self.sort( 0, Qt.AscendingOrder )
        self.emitFilterChanged.emit( )
        self.emitNumSatisfied.emit(
            len(list(filter(lambda row: self.filterRow( row ),
                            range( len( self.actualTVSeriesData ) ) ) ) ) )
        
    def setFilterString( self, text ):
        mytext = str( text ).strip( )
        if len( mytext ) == 0:
            mytext = '.'
        self.filterRegexp = QRegExp(
            mytext, Qt.CaseInsensitive, QRegExp.RegExp )
        self.emitFilterChanged.emit( )
        self.emitNumSatisfied.emit(
            len(list(filter(lambda row: self.filterRow( row ),
                            range( len( self.actualTVSeriesData ) ) ) ) ) )
        
    def rowCount( self, parent ):
        return len( self.actualTVSeriesData )

    def columnCount( self, parent ):
        return 6

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[ col ]
        return None

    def fillOutCalculation( self ):
        #
        ## now put in the actual data.
        self.actualTVSeriesData = [ ]
        tvdata_on_plex = self.parent.tvdata_on_plex
        missing_eps = self.parent.missing_eps
        for seriesName in sorted( tvdata_on_plex ):
            seasons_info = tvdata_on_plex[ seriesName ][ 'seasons' ]
            startDate = min( map(
                lambda seasno: min(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'date aired' ],
                        seasons_info[seasno]['episodes'] ) ), set(seasons_info) - set([0]) ) )
            endDate = max( map(
                lambda seasno: max(
                    map(lambda epno: seasons_info[ seasno ]['episodes'][ epno ][ 'date aired' ],
                        seasons_info[ seasno ]['episodes'] ) ), set(seasons_info) - set([0]) ) )
            seasons = len( seasons_info.keys( ) )
            numEps = sum( map(
                lambda seasno: len( seasons_info[ seasno ][ 'episodes' ] ),
                seasons_info ) )
            dat = { 'seriesName' : seriesName,
                    'startDate' : startDate,
                    'endDate' : endDate,
                    'seasons' : seasons,
                    'numEps' : numEps,
                    'didEnd' : tvdata_on_plex[ seriesName ][ 'didEnd' ],
                    'numMissing' : 0 }
            if seriesName in missing_eps:
                dat[ 'numMissing' ] = len( missing_eps[ seriesName ] )
            self.actualTVSeriesData.append( dat )

        #
        ## first remove all rows that exist
        initRowCount = self.rowCount( None )
        self.beginRemoveRows( QModelIndex( ), 0, initRowCount - 1 )
        self.endRemoveRows( )
        #
        ## now add in the data
        self.beginInsertRows( QModelIndex( ), 0, len( self.actualTVSeriesData ) - 1 )
        self.endInsertRows( )
        self.sort(0, Qt.AscendingOrder ) # triggers the fillout of rows and columns
        
    def sort( self, col, order ):
        self.layoutAboutToBeChanged.emit( )
        self.sortColumn = col
        colMapping = { 0 : 'seriesName', 1 : 'startDate', 2 : 'endDate' }
        if col in ( 0, 1, 2 ):
            self.actualTVSeriesData.sort(
                key = lambda dat: dat[ colMapping[ col ] ] )
        self.layoutChanged.emit( )
        
    #
    ## engine code, actually show data in the table
    def data( self, index, role ):
        if not index.isValid( ):
            return ""
        row = index.row( )
        col = index.column( )
        data = self.actualTVSeriesData[ row ].copy( )
        #
        ## color background role
        if role == Qt.BackgroundRole:
            if data[ 'didEnd' ]:
                return QBrush( QColor( '#282a36' ) ) # change using cwheet to yellow-like
            elif data[ 'numMissing' ] > 0 and col == 5:
                return QBrush( QColor( "#873600" ) )
            else: return QBrush( QColor( '#6272a4' ) )
        elif role == Qt.DisplayRole:
            if col == 0: # series name
                return data[ 'seriesName' ]
            elif col == 1: # start date
                return data[ 'startDate' ].strftime('%Y %b %d')
            elif col == 2: # end date
                return data[ 'endDate' ].strftime('%Y %b %d')
            elif col == 3: # number of seasons
                return data[ 'seasons' ]
            elif col == 4: # number of eps
                return data[ 'numEps' ]
            elif col == 5:
                return data[ 'numMissing' ]

class HowdyTVShowGUIThread( ProgressDialogThread ):
    seriesWidgetsSignal = pyqtSignal( int )
    fillOutGUI = pyqtSignal( )
    
    def __init__( self, parent, sorted_seasons ):
        super( HowdyTVShowGUIThread, self ).__init__(
            parent, 'GETTING TV SHOW INFO FOR %s.' % parent.seriesName )
        self.seriesWidgetsSignal.connect(
            parent.fillOutSeriesWidget )
        self.fillOutGUI.connect( parent.fillOutGUI )
        self.sorted_seasons = sorted( set( sorted_seasons ) )
        self.seriesName = parent.seriesName

    def run( self ):
        self.progress_dialog.show( )
        time0 = self.progress_dialog.t0
        seasons_widgets = { }
        step = 0
        mytxt = '%d, started loading in season data for %s on %s.' % (
            step, self.seriesName, datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        step += 1
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        #
        for season in self.sorted_seasons:
            self.seriesWidgetsSignal.emit( season )
            mytxt = '%d, added %s season %d / %d in %0.3f seconds.' % (
                step, self.seriesName, season, len( self.sorted_seasons ), time.time( ) - time0 )
            step += 1
            logging.info( mytxt )
            self.emitString.emit( mytxt )
        #
        ## now done
        mytxt = '%d, finished loading in season data for %s on %s.' % (
            step, self.seriesName, datetime.datetime.now( ).strftime( '%B %d, %Y @ %I:%M:%S %p' ) )
        logging.info( mytxt )
        self.emitString.emit( mytxt )
        self.fillOutGUI.emit( )
        self.stopDialog.emit( )
        

class HowdyTVShowGUI( QDialogWithPrinting ):
    def __init__( self, seriesName, tvdata, missing_eps,
                  tvdb_token, plex_token,
                  parent = None, verify = True ):
        super( HowdyTVShowGUI, self ).__init__( parent, doQuit = False,
                                             isIsolated = True )
        if parent is not None:
            assert( isinstance( parent, QDialogWithPrinting ) )
        self.setModal( True )
        assert( seriesName in tvdata )
        self.seriesName = seriesName
        self.tvdata = tvdata
        self.missing_eps = missing_eps
        self.tvdb_token = tvdb_token
        self.plex_token = plex_token
        self.parent = parent
        self.verify = verify
        seriesInfo = tvdata[ seriesName ]
        sorted_seasons = sorted( set( seriesInfo[ 'seasons' ] ) - set([ 0 ]) )
        self.series_widgets = { }
        #
        ## cannot get this type of threading to work, perhaps b/c creates new widgets
        #self.tvdbsguithread = HowdyTVShowGUIThread( self, sorted_seasons )
        #self.tvdbsguithread.start( )
        for season in sorted_seasons:
            self.fillOutSeriesWidget( season )
            logging.info( 'added %s season %d / %d.' % (
                seriesName, season, len( sorted_seasons ) ) )
        self.fillOutGUI( )

    def fillOutSeriesWidget( self, season ):
        self.series_widgets[ season ] = HowdyTVSeasonGUI(
            self.seriesName, season, self.tvdata, self.missing_eps, self.tvdb_token,
            self.plex_token, verify = self.verify, parent = self.parent )

    def fillOutGUI( self ):
        self.setWindowTitle( self.seriesName )
        sorted_seasons = sorted( self.series_widgets )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## top widget contains a set of seasons in a QComboBox
        topWidget = QWidget( )
        topLayout = QHBoxLayout( )
        topWidget.setLayout( topLayout )
        #
        topLeftWidget = QWidget( )
        topLeftLayout = QHBoxLayout( )
        topLeftWidget.setLayout( topLeftLayout )
        topLeftLayout.addWidget( QLabel( self.seriesName ) )
        topLayout.addWidget( topLeftWidget )
        #
        topRightWidget = QWidget( )
        topRightLayout = QHBoxLayout( )
        topRightWidget.setLayout( topRightLayout )
        topRightLayout.addWidget( QLabel( "SEASON" ) )
        seasonSelected = QComboBox( self )
        seasonSelected.addItems(
            list(map(lambda seasno: '%d' % seasno,
                     sorted_seasons)))
        seasonSelected.setEnabled( True )
        seasonSelected.setEditable( False )
        seasonSelected.setCurrentIndex( 0 )
        topRightLayout.addWidget( seasonSelected )
        topLayout.addWidget( topRightWidget )
        #
        myLayout.addWidget( topWidget )
        #
        ## now a stacked layout
        self.seasonWidget = QStackedWidget( )
        for season in sorted( self.series_widgets ):
            self.seasonWidget.addWidget( self.series_widgets[ season ] )
        first_season = min( self.series_widgets )
        myLayout.addWidget( self.seasonWidget )
        #
        ## set size
        self.setFixedWidth( self.series_widgets[ first_season ].sizeHint( ).width( ) * 1.05 )
        self.setFixedHeight( 800 )
        #
        ## connect
        def selectSeason( idx ):
            self.seasonWidget.setCurrentIndex( idx )
        seasonSelected.installEventFilter( self )
        seasonSelected.currentIndexChanged.connect( selectSeason )
        for season in self.series_widgets:
            self.indexScalingSignal.connect(
                self.series_widgets[ season ].rescale )
        ##
        self.show( )
