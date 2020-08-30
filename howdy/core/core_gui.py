import os, sys, requests, webbrowser, logging
from requests_oauthlib import OAuth2Session
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#
from howdy.core import core, QDialogWithPrinting
from howdy.core import core_deluge, core_rsync, get_popularity_color
from howdy.music import music
from howdy.movie import get_tmdb_api, save_tmdb_api, movie
from howdy.tv import get_tvdb_api, save_tvdb_api, check_tvdb_api, get_token
from howdy.email import HowdyIMGClient

class HowdyImgurChooseAlbumWidget( QDialogWithPrinting ):
    changedAlbumSignal = pyqtSignal( str )
    
    def showHelpInfo( self ):
        pass

    def __init__( self, parent, data_imgurl, verify = True ):
        super( HowdyImgurChooseAlbumWidget, self ).__init__(
            parent, doQuit = False, isIsolated = True )
        self.hIMGClient = HowdyIMGClient( verify = verify, data_imgurl = data_imgurl )
        self.currentAlbumInfo = self.hIMGClient.get_candidate_albums( )
        self.main_album_name = self.hIMGClient.get_main_album_name( )
        #
        self.setModal( True )
        self.setWindowTitle( 'ALBUMS IN IMGUR ACCOUNT' )
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        self.albumTM = HowdyImgurChooseAlbumTableModel( self )
        self.albumTV = HowdyImgurChooseAlbumTableView( self )
        myLayout.addWidget( self.albumTV )
        #
        ##
        self.setFixedHeight( 450 )
        self.setFixedWidth( 430 )
        self.hide( )

    def add_album( self, new_album_name ):
        valid_names = set( self.currentAlbumInfo )
        if new_album_name in valid_names: return # do nothing
        self.hIMGClient.set_main_album( new_album_name )
        self.update( )

    def rename_main_album( self, new_album_name ):
        if self.main_album_name is None: return
        if self.main_album_name == new_album_name: return
        self.hIMGClient.change_album_name( new_album_name )
        self.update( )

    def delete_album( self, album_name ):
        if album_name not in set( self.currentAlbumInfo ): return
        self.hIMGClient.delete_candidate_album( album_name )
        self.update( )

    def set_main_album( self, album_name ):
        if self.main_album_name is None: return
        if self.main_album_name == album_name: return
        if len( self.currentAlbumInfo ) == 0: return
        if album_name not in self.currentAlbumInfo: return
        self.hIMGClient.set_main_album( album_name )
        self.update( )

    def update( self ):
        self.currentAlbumInfo = self.hIMGClient.get_candidate_albums( )
        self.main_album_name = self.hIMGClient.get_main_album_name( )
        self.albumTM.update( )
        self.changedAlbumSignal.emit( self.main_album_name )
        
class HowdyImgurChooseAlbumTableView( QTableView ):
    def __init__( self, parent ):
        super( HowdyImgurChooseAlbumTableView, self ).__init__( parent )
        self.parent = parent
        self.setModel( self.parent.albumTM )
        self.setShowGrid( True )
        self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setSortingEnabled( False )
        #
        self.setColumnWidth( 0, 250 )
        self.setColumnWidth( 1, 150 )
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

    def add( self ):
        val, okPressed = QInputDialog.getText( self, "Candidate New Album Name", "Name:", QLineEdit.Normal, "" )
        if val.strip( ) == "": return
        if not okPressed: return
        self.parent.add_album( val.strip( ) )

    def rename_main_album( self ):
        val, okPressed = QInputDialog.getText( self, "Rename Main Album", "Name:", QLineEdit.Normal, "" )
        if val.strip( ) == "": return
        if not okPressed: return
        self.parent.rename_main_album( val.strip( ) )

    def delete_album( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel( ).selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        album_at_row = self.parent.albumTM.get_album_at_row( row )
        self.parent.delete_album( album_at_row )

    def set_main_album( self ):
        indices_valid = filter(lambda index: index.column( ) == 0,
                               self.selectionModel( ).selectedIndexes( ) )
        row = max(map(lambda index: index.row( ), indices_valid ) )
        album_at_row = self.parent.albumTM.get_album_at_row( row )
        self.parent.set_main_album( album_at_row )

    def contextMenuEvent( self, evt ):
        menu = QMenu( self )
        addAction = QAction( 'Add', menu )
        addAction.triggered.connect( self.add )
        menu.addAction( addAction )
        if len( self.parent.currentAlbumInfo ) != 0:
            setMainAction = QAction( 'Set Main Album', menu )
            setMainAction.triggered.connect( self.set_main_album )
            menu.addAction( setMainAction )
            renameAction = QAction( 'Rename', menu )
            renameAction.triggered.connect( self.rename_main_album )
            menu.addAction( renameAction )
            deleteAction = QAction( 'Delete', menu )
            deleteAction.triggered.connect( self.delete_album )
            menu.addAction( deleteAction )
        menu.popup( QCursor.pos( ) )

class HowdyImgurChooseAlbumTableModel( QAbstractTableModel ):
    def __init__( self, parent ):
        super( HowdyImgurChooseAlbumTableModel, self ).__init__( parent )
        self.parent = parent
        self.sortedAlbumNames = [ ]
        self.main_album = None
        self.update( )

    def rowCount( self, parent ):
        return len( self.sortedAlbumNames )

    def columnCount( self, parent ):
        return 2

    def flags( self, index ):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData( self, col, orientation, role ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if col == 0: return 'ALBUM NAME'
            elif col == 1: return '# OF PICS'
        return None

    def update( self ):
        self.layoutAboutToBeChanged.emit( )
        self.sortedAlbumNames = sorted( self.parent.currentAlbumInfo )
        self.main_album = self.parent.main_album_name
        self.layoutChanged.emit( )

    def get_album_at_row( self, row ):
        assert( row >= 0 )
        assert( row < len( self.sortedAlbumNames ) )
        return self.sortedAlbumNames[ row ]
        
    def data( self, index, role ):
        if not index.isValid( ): return ""
        row = index.row( )
        col = index.column( )
        if role == Qt.BackgroundRole and self.sortedAlbumNames[ row ] == self.parent.main_album_name:
            color = QColor( "orange" )
            color.setAlphaF( 0.2 )
            return QBrush( color )
        elif role == Qt.DisplayRole:
            album_at_row = self.sortedAlbumNames[ row ]
            if col == 0: # name
                return album_at_row
            elif col == 1: # number of pics
                return len(
                    self.parent.currentAlbumInfo[ album_at_row ][ 'images' ] )

class HowdyConfigWidget( QDialogWithPrinting ):
    workingStatus = pyqtSignal( dict )
    _emitWorkingStatusDict = { }
    
    def showHelpInfo( self ):
        pass

    def getWorkingStatus( self ):
        return self._emitWorkingStatusDict.copy( )

    def __init__( self, parent, service, verify = True ):
        super( HowdyConfigWidget, self ).__init__(
            parent, isIsolated = True, doQuit = False )
        self.hide( )
        self.setModal( True )
        self.service = service
        self.verify = verify
        self.setWindowTitle( 'HOWDY %s CONFIGURATION' % service.upper( ) )

class HowdyConfigCredWidget( HowdyConfigWidget ):
    _emitWorkingStatusDict = {
        'TMDB' : False,
        'TVDB' : False,
        'IMGURL' : False,
        'GOOGLE' : True }

    def showHelpInfo( self ):
        pass

    def initHowdyConfigCredStatus( self ):
        #
        ## look for TMDB credentials
        try:
            tmdbApi = get_tmdb_api( )
            movies = movie.get_movies_by_title(
                'Star Wars', apiKey = tmdbApi, verify = self.verify )
            if len( movies ) == 0:
                raise ValueError( "Error, invalid TMDB API KEY" )
            self.tmdb_apikey.setText( tmdbApi )
            self.tmdb_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'TMDB' ] = True
        except:
            self.tmdb_apikey.setText( '' )
            self.tmdb_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'TMDB' ] = False

        #
        ## look at TVDB
        try:
            data = get_tvdb_api( )
            token = get_token( verify = self.verify, data = data )
            if token is None:
                raise ValueError("Error, invalid TVDB API keys." )
            self.tvdb_apikey.setText( data[ 'apikey' ] )
            self.tvdb_username.setText( data[ 'username' ] )
            self.tvdb_userkey.setText( data[ 'userkey' ] )
            self.tvdb_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'TVDB' ] = True
        except Exception as e:
            print( 'TVDB: %s.' % str( e ) )
            self.tvdb_apikey.setText( '' )
            self.tvdb_username.setText( '' )
            self.tvdb_userkey.setText( '' )
            self.tvdb_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'TVDB' ] = False

        #
        ## now look at the IMGURL
        def _get_creds( ):
            try:
                imgur_credentials = core.get_imgurl_credentials( )
                clientID = imgur_credentials[ 'clientID' ]
                clientSECRET = imgur_credentials[ 'clientSECRET' ]
                clientREFRESHTOKEN = imgur_credentials[ 'clientREFRESHTOKEN' ]
                mainALBUMID = ''
                if 'mainALBUMID' in imgur_credentials:
                    mainALBUMID = imgur_credentials[ 'mainALBUMID' ]
                mainALBUMNAME = ''
                if 'mainALBUMNAME' in imgur_credentials:
                    mainALBUMNAME = imgur_credentials[ 'mainALBUMNAME' ]
                return clientID, clientSECRET, clientREFRESHTOKEN, mainALBUMNAME
            except Exception as e:
                return '', '', '', ''

        clientID, clientSECRET, clientREFRESHTOKEN, mainALBUMNAME = _get_creds( )            
        try:
            if not core.check_imgurl_credentials(
                    clientID, clientSECRET, clientREFRESHTOKEN,
                    verify = self.verify ):
                raise ValueError( "Error, invalid imgurl creds.")
            self.imgurl_id.setText( clientID )
            self.imgurl_secret.setText( clientSECRET )
            self.imgurl_mainAlbumName.setText( mainALBUMNAME )
            self.imgurl_id.setStyleSheet( "QWidget {background-color: #370b4f;}" )
            self.imgurl_secret.setStyleSheet( "QWidget {background-color: #370b4f;}" )
            self.imgurl_status.setText( 'WORKING' )
            self.imgurl_seeMainAlbum.setEnabled( True )
            self._emitWorkingStatusDict[ 'IMGURL' ] = True
        except Exception as e:
            self.imgurl_id.setText( clientID )
            self.imgurl_secret.setText( clientSECRET )
            self.imgurl_mainAlbumName.setText( '' )
            self.imgurl_id.setStyleSheet( "QWidget {background-color: purple;}" )
            self.imgurl_secret.setStyleSheet( "QWidget {background-color: purple;}" )
            self.imgurl_status.setText( 'NOT WORKING' )
            self.imgurl_seeMainAlbum.setEnabled( False )
            self._emitWorkingStatusDict[ 'IMGURL' ] = False

        #
        ## now the GOOGLE
        try:
            cred1 = core.oauthGetGoogleCredentials( verify = self.verify )
            cred2 = core.oauthGetOauth2ClientGoogleCredentials( )
            if cred1 is None or cred2 is None:
                raise ValueError( "ERROR, PROBLEMS WITH GOOGLE CREDENTIALS" )
            self.google_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'GOOGLE' ] = True
        except Exception as e:
            self.google_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GOOGLE' ] = False

        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushTMDBConfig( self ):
        tmdbApi = self.tmdb_apikey.text( ).strip( )
        try:
            movies = movie.get_movies_by_title(
                'Star Wars', apiKey = tmdbApi,
                verify = self.verify )
            if len( movies ) == 0:
                raise ValueError( "Error, invalid TMDB API KEY" )
            movie.save_tmdb_api( tmdbApi )
            self.tmdb_apikey.setText( tmdbApi )
            self.tmdb_status.setText( 'WORKING' )
            self._emitWorkingStatus[ 'TMDB' ] = True
        except:
            self.tmdb_apikey.setText( '' )
            self.tmdb_status.setText( 'NOT WORKING' )
            self._emitWorkingStatus[ 'TMDB' ] = False
        logging.debug( 'got here TMDB' )
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushTVDBConfig( self ):
        apikey = self.tvdb_apikey.text( ).strip( )
        username = self.tvdb_username.text( ).strip( )
        userkey = self.tvdb_userkey.text( ).strip( )
        try:
            status = tv.save_tvdb_api(
                username, apikey, userkey, verify = self.verify )
            if status != 'SUCCESS':
                raise ValueError("Error, invalid TVDB API keys." )
            self.tvdb_apikey.setText( apikey )
            self.tvdb_username.setText( username )
            self.tvdb_userkey.setText( userkey )
            self.tvdb_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'TVDB' ] = True
        except:
            self.tvdb_apikey.setText( '' )
            self.tvdb_username.setText( '' )
            self.tvdb_userkey.setText( '' )
            self.tvdb_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'TVDB' ] = False
        logging.debug( 'got here TVDB' )
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushIMGURLConfig( self ):
        clientID = self.imgurl_id.text( ).strip( )
        clientSECRET = self.imgurl_secret.text( ).strip( )
        def checkStatus( state ):
            if state:
                self.imgurl_status.setText( 'WORKING' )
                self.imgurl_id.setStyleSheet( "QWidget {background-color: #370b4f;}" )
                self.imgurl_secret.setStyleSheet( "QWidget {background-color: #370b4f;}" )
            else:
                self.imgurl_status.setText( 'NOT WORKING' )
                self.imgurl_id.setStyleSheet( "QWidget {background-color: purple;}" )
                self.imgurl_secret.setStyleSheet( "QWidget {background-color: purple;}" )
            self._emitWorkingStatusDict[ 'IMGURL' ] = state
            self.workingStatus.emit( self._emitWorkingStatusDict )

        ioauth2dlg = ImgurOauth2Dialog( self, clientID, clientSECRET )
        ioauth2dlg.emitState.connect( checkStatus )
        ioauth2dlg.show( )
        ioauth2dlg.exec_( )

    def setIMGURLMainAlbumConfig( self ):
        data_imgurl = core.get_imgurl_credentials( )
        picaw = HowdyImgurChooseAlbumWidget(
            self, data_imgurl = data_imgurl, verify = False )
        def changeMAINNAME( newAlbumMainName ):
            self.imgurl_mainAlbumName.setText( newAlbumMainName )

        picaw.changedAlbumSignal.connect( changeMAINNAME )
        picaw.show( )
        picaw.exec_( )

    def pushGoogleConfig( self ): # this is done by button
        def checkStatus( state ):
            if state:
                self.google_status.setText( 'WORKING' )
            else:
                self.google_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GOOGLE' ] = state
            self.workingStatus.emit( self._emitWorkingStatusDict )
        goauth2dlg = GoogleOauth2Dialog( self )
        goauth2dlg.emitState.connect( checkStatus )
        goauth2dlg.show( )
        goauth2dlg.exec_( )

    def __init__( self, parent, verify = True ):
        super( HowdyConfigCredWidget, self ).__init__(
            parent, 'CREDENTIALS', verify = verify )
        #
        ## gui stuff
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## tmdb
        self.tmdb_apikey = QLineEdit( )
        self.tmdb_status = QLabel( )
        tmdbWidget = QWidget( )
        tmdbWidget.setStyleSheet("""
        QWidget {
        background-color: #0b4d4f;
        }""" )
        tmdbLayout = QGridLayout( )
        tmdbWidget.setLayout( tmdbLayout )
        tmdbLayout.addWidget( QLabel( 'TMDB' ), 0, 0, 1, 1 )
        tmdbLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        tmdbLayout.addWidget( self.tmdb_status, 0, 3, 1, 1 )
        tmdbLayout.addWidget( QLabel( 'API KEY' ), 1, 0, 1, 1 )
        tmdbLayout.addWidget( self.tmdb_apikey, 1, 1, 1, 3 )
        myLayout.addWidget( tmdbWidget )
        self.tmdb_apikey.returnPressed.connect(
            self.pushTMDBConfig )
        #
        ## tvdb
        self.tvdb_apikey = QLineEdit( )
        self.tvdb_username = QLineEdit( )
        self.tvdb_userkey = QLineEdit( )
        self.tvdb_status = QLabel( )
        tvdbWidget = QWidget( )
        tvdbWidget.setStyleSheet("""
        QWidget {
        background-color: #0b2d4f;
        }""" )
        tvdbLayout = QGridLayout( )
        tvdbWidget.setLayout( tvdbLayout )
        tvdbLayout.addWidget( QLabel( 'TVDB' ), 0, 0, 1, 1 )
        tvdbLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        tvdbLayout.addWidget( self.tvdb_status, 0, 3, 1, 1 )
        tvdbLayout.addWidget( QLabel( 'API KEY' ), 1, 0, 1, 1 )
        tvdbLayout.addWidget( self.tvdb_apikey, 1, 1, 1, 3 )
        tvdbLayout.addWidget( QLabel( 'USER NAME' ), 1, 0, 1, 1 )
        tvdbLayout.addWidget( self.tvdb_username, 1, 1, 1, 3 )
        tvdbLayout.addWidget( QLabel( 'USER KEY' ), 2, 0, 1, 1 )
        tvdbLayout.addWidget( self.tvdb_userkey, 2, 1, 1, 3 )
        myLayout.addWidget( tvdbWidget )
        self.tvdb_apikey.returnPressed.connect(
            self.pushTVDBConfig )
        self.tvdb_username.returnPressed.connect(
            self.pushTVDBConfig )
        self.tvdb_userkey.returnPressed.connect(
            self.pushTVDBConfig )
        #
        ## imgurl
        self.imgurl_id = QLineEdit( )
        self.imgurl_secret = QLineEdit( )
        self.imgurl_status = QLabel( )
        self.imgurl_oauth = QPushButton( 'CLIENT REFRESH' )
        self.imgurl_oauth.setAutoDefault( False )
        self.imgurl_mainAlbumName = QLabel( )
        self.imgurl_seeMainAlbum = QPushButton( 'MAIN ALBUMS' )
        self.imgurl_seeMainAlbum.setAutoDefault( False )
        imgurlWidget = QWidget( )
        imgurlWidget.setStyleSheet("""
        QWidget {
        background-color: #370b4f;
        }""" )
        imgurlLayout = QGridLayout( )
        imgurlWidget.setLayout( imgurlLayout )
        imgurlLayout.addWidget( QLabel( 'IMGURL' ), 0, 0, 1, 1 )
        imgurlLayout.addWidget( self.imgurl_oauth, 0, 1, 1, 2 )
        imgurlLayout.addWidget( self.imgurl_status, 0, 3, 1, 1 )
        imgurlLayout.addWidget( QLabel( 'ID' ), 1, 0, 1, 1 )
        imgurlLayout.addWidget( self.imgurl_id, 1, 1, 1, 3 )
        imgurlLayout.addWidget( QLabel( 'SECRET' ), 2, 0, 1, 1 )
        imgurlLayout.addWidget( self.imgurl_secret, 2, 1, 1, 3 )
        imgurlLayout.addWidget( QLabel( 'MAIN ALBUM NAME' ), 3, 0, 1, 1 )
        imgurlLayout.addWidget( self.imgurl_mainAlbumName, 3, 1, 2, 1 )
        imgurlLayout.addWidget( self.imgurl_seeMainAlbum, 3, 3, 1, 1 )
        myLayout.addWidget( imgurlWidget )
        #self.imgurl_id.returnPressed.connect(
        #    self.pushIMGURLConfig )
        #self.imgurl_secret.returnPressed.connect(
        #    self.pushIMGURLConfig )
        self.imgurl_oauth.clicked.connect(
            self.pushIMGURLConfig )
        self.imgurl_seeMainAlbum.clicked.connect(
            self.setIMGURLMainAlbumConfig )
        #
        ## google
        self.google_oauth = QPushButton( 'CLIENT REFRESH' )
        self.google_oauth.setAutoDefault( False )
        self.google_status = QLabel( )
        googleWidget = QWidget( )
        googleWidget.setStyleSheet("""
        QWidget {
        background-color: #450b4f;
        }""" )
        googleLayout = QHBoxLayout( )
        googleWidget.setLayout( googleLayout )
        googleLayout.addWidget( QLabel( 'GOOGLE' ) )
        googleLayout.addWidget( self.google_oauth )
        googleLayout.addWidget( self.google_status )
        myLayout.addWidget( googleWidget )
        self.google_oauth.clicked.connect(
            self.pushGoogleConfig )
        #
        ## now initialize
        self.initHowdyConfigCredStatus( ) # set everything up
        self.setFixedWidth( self.sizeHint( ).width( ) * 1.25 )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        refreshAction = QAction( 'refresh cred config', menu )
        refreshAction.triggered.connect( self.initHowdyConfigCredStatus )
        menu.addAction( refreshAction )
        helpAction = QAction( 'help', menu )
        helpAction.triggered.connect( self.showHelpInfo )
        menu.addAction( helpAction )
        menu.popup( QCursor.pos( ) )
        

class HowdyConfigLoginWidget( HowdyConfigWidget ):
    _emitWorkingStatusDict = {
        'PLEXLOGIN' : False,
        'DELUGE' : False,
        'JACKETT' : False,
        'RSYNC' : False }

    def showHelpInfo( self ):
        pass

    def initHowdyConfigLoginStatus( self ):
        #
        ## look for plex login credentials
        try:
            dat = core.checkServerCredentials(
                verify = self.verify )
            if dat is None:
                raise ValueError("Error, could not get username and password" )
            dat = core.getCredentials( verify = self.verify )
            if dat is None:
                raise ValueError("Error, could not get username and password" )
            username, password = dat
            self.server_usernameBox.setText( username )
            self.server_passwordBox.setText( password )
            self.server_statusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'PLEXLOGIN' ] = True
        except Exception as e:
            self.server_usernameBox.setText( '' )
            self.server_passwordBox.setText( '' )
            self.server_statusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'PLEXLOGIN' ] = False

        #
        ## look for the DELUGE
        try:
            client, status = core_deluge.get_deluge_client( )
            if status != 'SUCCESS':
                raise ValueError( "Error, could not get valid deluge client" )
            data = core_deluge.get_deluge_credentials( )
            if data is None:
                raise ValueError( "Error, could not get valid deluge client" )
            self.deluge_url.setText( data['url'] )
            self.deluge_port.setText( '%d' % data['port'] )
            self.last_port = data[ 'port' ]
            self.deluge_username.setText( data['username'] )
            self.deluge_password.setText( data['password'] )
            self.deluge_label.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'DELUGE' ] = True
        except:
            self.deluge_url.setText( '' )
            self.deluge_port.setText( '' )
            self.deluge_username.setText( '' )
            self.deluge_password.setText( '' )
            self.deluge_label.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'DELUGE' ] = False

        #
        ## look for JACKETT
        try:
            dat = core.get_jackett_credentials( )
            if dat is None:
                raise ValueError("Error, could not get valid Jackett credentials." )
            url, apikey = dat
            if not url.endswith('/'): url = '%s/' % url
            self.jackett_url.setText( url )
            self.jackett_apikey.setText( apikey )
            _, status = core.check_jackett_credentials(
                url, apikey, verify = self.verify )
            if status == 'SUCCESS':
                self.jackett_status.setText( 'WORKING' )
                self._emitWorkingStatusDict[ 'JACKETT' ] = True
            else:
                self.jackett_status.setText( 'NOT WORKING' )
                self._emitWorkingStatusDict[ 'JACKETT' ] = False
        except Exception as e:
            print( 'got here in JACKETT, %s.' % str( e ) )
            self.jackett_url.setText( '' )
            self.jackett_apikey.setText( '' )
            self.jackett_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'JACKETT' ] = True

        #
        ## look for RSYNC
        try:
            data = core_rsync.get_credentials( )
            if data is None:
                raise ValueError("Error, could not find rsync ssh credentials." )
            local_dir = data['local_dir']
            sshpath = data['sshpath']
            subdir = data['subdir']
            password = data['password']
            #
            ## check if good just in case
            status = core_rsync.check_credentials(
                local_dir, sshpath, password, subdir = subdir )
            if status != 'SUCCESS': raise ValueError( status )
            self.rsync_localdir.setText( local_dir )
            self.rsync_sshpath.setText( sshpath )
            self.last_rsync_sshpath = sshpath
            if subdir is None: self.rsync_subdir.setText( '' )
            else: self.rsync_subdir.setText( subdir )
            self.rsync_password.setText( password )
            self.rsync_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'RSYNC' ] = True
        except Exception as e:
            self.rsync_localdir.setText( '' )
            self.rsync_sshpath.setText( '' )
            self.last_rsync_sshpath = ''
            self.rsync_subdir.setText( '' )
            self.rsync_password.setText( '' )
            self.rsync_status.setText( str( e ) )
            self._emitWorkingStatusDict[ 'RSYNC' ] = False

        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushPlexLoginConfig( self ):
        username = self.server_usernameBox.text( ).strip( )
        password = self.server_passwordBox.text( ).strip( )
        try:
            token = core.getTokenForUsernamePassword(
                username, password, verify = self.verify )
            if token is None:
                raise ValueError( "Error, incorrect username/password" )
            core.pushCredentials( username, password )
            self.server_usernameBox.setText( username )
            self.server_passwordBox.setText( password )
            self.server_statusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'PLEXLOGIN' ] = True
        except Exception as e:
            logging.info('howdy.core.core_gui.HowdyConfigLoginWidget.pushPlexLoginConfig: Exception raised, %s.' % str( e ) )
            self.server_usernameBox.setText( '' )
            self.server_passwordBox.setText( '' )
            self.server_statusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'PLEXLOGIN' ] = False
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushDelugeConfig( self ):
        try:
            new_port = int( self.deluge_port.text( ) )
            if new_port <= 0:
                raise ValueError("invalid port value" )
            self.last_port = new_port
        except: # not an integer or bad port number
            self.deluge_port.setText( '%d' % self.last_port )

        try:
            port = int( self.deluge_port.text( ) )
            url =  self.deluge_url.text( ).strip( )
            username = self.deluge_username.text( ).strip( )
            password = self.deluge_password.text( ).strip( )
            status = core_rsync.push_credentials(
                url, port, username, password )
            if status != 'SUCCESS':
                raise ValueError("Error, invalid deluge config credentials." )
            self.deluge_port.setText( '%d' % port )
            self.deluge_url.setText( url )
            self.deluge_username.setText( username )
            self.deluge_password.setText( password )
            self.deluge_label.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'DELUGE' ] = True
        except:
            self.deluge_port.setText( '%d' % self.last_port )
            self.deluge_url.setText( '' )
            self.deluge_username.setText( '' )
            self.deluge_password.setText( '' )
            self.deluge_label.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'DELUGE' ] = False
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushJackettConfig( self ):
        url = self.jackett_url.text( ).strip( )
        apikey = self.jackett_apikey.text( ).strip( )
        if not url.endswith('/'): url = '%s/' % url
        self.jackett_url.setText( url )
        self.jackett_apikey.setText( apikey )
        try:
            status = core.store_jackett_credentials(
                url, apikey, verify = self.verify )
            if status != 'SUCCESS':
                raise ValueError("Error, invalid jackett credentials.")
            self.jackett_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'JACKETT' ] = True
        except Exception as e:
            logging.error( 'ERROR MESSAGE IN JACKETT CONFIG: %s.' % str( e ) )
            self.jackett_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'JACKETT' ] = False
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushRsyncConfig( self ):
        #
        ## check if proper format for rsync_sshpath
        try:
            local_rsync_sshpath = self.rsync_sshpath.text( ).strip( )
            if len( local_rsync_sshpath ) == 0:
                self.rsync_sshpath.setText( local_rsync_sshpath )
                self.last_rsync_sshpath = local_rsync_sshpath
            else:
                numToks = len( local_rsync_sshpath.split('@') )
                if numToks != 2:
                    raise ValueError( "Error, invalid sshpath format" )
                self.rsync_sshpath.setText( local_rsync_sshpath )
                self.last_rsync_sshpath = local_rsync_sshpath
        except:
            self.rsync_sshpath.setText( self.last_rsync_sshpath )
        
        try:
            local_dir = os.path.abspath(
                self.rsync_localdir.text( ).strip( ) )
            sshpath = self.rsync_sshpath.text( ).strip( )
            if self.rsync_subdir.text( ).strip( ) == '':
                subdir = None
            else: subdir = self.rsync_subdir.text( ).strip( )
            password = self.rsync_password.text( ).strip( )
            status = core_rsync.push_credentials(
                local_dir, sshpath, password, subdir = subdir )
            if status != 'SUCCESS':
                raise ValueError("Error, could not update credentials" )
            self.rsync_localdir.setText( local_dir )
            self.rsync_sshpath.setText( sshpath )
            if subdir is None: self.rsync_sshpath.setText( '' )
            else: self.rsync_sshpath.setText( sshpath )
            self.rsync_password.setText( password )
            self.rsync_status.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'RSYNC' ] = True
        except:
            self.rsync_localdir.setText( '' )
            self.rsync_sshpath.setText( '' )
            self.rsync_subdir.setText( '' )
            self.rsync_password.setText( '' )
            self.rsync_status.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'RSYNC' ] = False
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def __init__( self, parent, verify = True ):
        super( HowdyConfigLoginWidget, self ).__init__(
            parent, 'LOGIN', verify = verify )
        #
        ## gui stuff
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## plexlogin
        self.server_usernameBox = QLineEdit( )
        self.server_passwordBox = QLineEdit( )
        self.server_passwordBox.setEchoMode( QLineEdit.Password )
        self.server_statusLabel = QLabel( )
        plexloginWidget = QWidget( )
        plexloginWidget.setStyleSheet("""
        QWidget {
        background-color: #0b4d4f;
        }""" )
        plexloginLayout = QGridLayout( )
        plexloginWidget.setLayout( plexloginLayout )
        plexloginLayout.addWidget( QLabel( 'PLEXLOGIN' ), 0, 0, 1, 1 )
        plexloginLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        plexloginLayout.addWidget( self.server_statusLabel, 0, 3, 1, 1 )
        plexloginLayout.addWidget( QLabel( 'USERNAME' ), 1, 0, 1, 1 )
        plexloginLayout.addWidget( self.server_usernameBox, 1, 1, 1, 3 )
        plexloginLayout.addWidget( QLabel( 'PASSWORD' ), 2, 0, 1, 1 )
        plexloginLayout.addWidget( self.server_passwordBox, 2, 1, 1, 3 )
        myLayout.addWidget( plexloginWidget )
        self.server_usernameBox.returnPressed.connect(
            self.pushPlexLoginConfig )
        self.server_passwordBox.returnPressed.connect(
            self.pushPlexLoginConfig )
        #
        ## deluge
        self.deluge_url = QLineEdit( )
        self.deluge_port = QLineEdit( )
        self.deluge_username = QLineEdit( )
        self.deluge_password = QLineEdit( )
        self.deluge_password.setEchoMode( QLineEdit.Password )
        self.deluge_label = QLabel( )
        delugeWidget = QWidget( )
        delugeWidget.setStyleSheet("""
        QWidget {
        background-color: #0b2d4f;
        }""" )
        delugeLayout = QGridLayout( )
        delugeWidget.setLayout( delugeLayout )
        delugeLayout.addWidget( QLabel( 'DELUGE' ), 0, 0, 1, 1 )
        delugeLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        delugeLayout.addWidget( self.deluge_label, 0, 3, 1, 1 )
        delugeLayout.addWidget( QLabel( 'URL' ), 1, 0, 1, 1 )
        delugeLayout.addWidget( self.deluge_url, 1, 1, 1, 3 )
        delugeLayout.addWidget( QLabel( 'PORT' ), 2, 0, 1, 1 )
        delugeLayout.addWidget( self.deluge_port, 2, 1, 1, 3 )
        delugeLayout.addWidget( QLabel( 'USERNAME' ), 3, 0, 1, 1 )
        delugeLayout.addWidget( self.deluge_username, 3, 1, 1, 3 )
        delugeLayout.addWidget( QLabel( 'PASSWORD' ), 4, 0, 1, 1 )
        delugeLayout.addWidget( self.deluge_password, 4, 1, 1, 3 )
        myLayout.addWidget( delugeWidget )
        self.deluge_url.returnPressed.connect(
            self.pushDelugeConfig )
        self.deluge_port.returnPressed.connect(
            self.pushDelugeConfig )
        self.deluge_username.returnPressed.connect(
            self.pushDelugeConfig )
        self.deluge_password.returnPressed.connect(
            self.pushDelugeConfig )
        #
        ## jackett
        self.jackett_url = QLineEdit( )
        self.jackett_apikey = QLineEdit( )
        self.jackett_status = QLabel( )
        jackettWidget = QWidget( )
        jackettWidget.setStyleSheet("""
        QWidget {
        background-color: #370b4f;
        }""" )
        jackettLayout = QGridLayout( )
        jackettWidget.setLayout( jackettLayout )
        jackettLayout.addWidget( QLabel( 'JACKETT' ), 0, 0, 1, 1 )
        jackettLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        jackettLayout.addWidget( self.jackett_status, 0, 3, 1, 1 )
        jackettLayout.addWidget( QLabel( 'URL' ), 1, 0, 1, 1 )
        jackettLayout.addWidget( self.jackett_url, 1, 1, 1, 3 )
        jackettLayout.addWidget( QLabel( 'API KEY' ), 2, 0, 1, 1 )
        jackettLayout.addWidget( self.jackett_apikey, 2, 1, 1, 3 )
        myLayout.addWidget( jackettWidget )
        self.jackett_url.returnPressed.connect(
            self.pushJackettConfig )
        self.jackett_apikey.returnPressed.connect(
            self.pushJackettConfig )
        #
        ## rsync
        self.rsync_localdir = QLineEdit( )
        self.rsync_sshpath = QLineEdit( )
        self.rsync_subdir = QLineEdit( )
        self.rsync_password = QLineEdit( )
        self.rsync_password.setEchoMode( QLineEdit.Password )
        self.rsync_status = QLabel( )
        rsyncWidget = QWidget( )
        rsyncWidget.setStyleSheet("""
        QWidget {
        background-color: #450b4f;
        }""" )
        rsyncLayout = QGridLayout( )
        rsyncWidget.setLayout( rsyncLayout )
        rsyncLayout.addWidget( QLabel( 'RSYNC' ), 0, 0, 1, 1 )
        rsyncLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        rsyncLayout.addWidget( self.rsync_status, 0, 3, 1, 1 )
        rsyncLayout.addWidget( QLabel( 'LOCAL DIR' ), 1, 0, 1, 1 )
        rsyncLayout.addWidget( self.rsync_localdir, 1, 1, 1, 3 )
        rsyncLayout.addWidget( QLabel( 'SSH PATH' ), 2, 0, 1, 1 )
        rsyncLayout.addWidget( self.rsync_sshpath, 2, 1, 1, 3 )
        rsyncLayout.addWidget( QLabel( 'SUB DIR' ), 3, 0, 1, 1 )
        rsyncLayout.addWidget( self.rsync_subdir, 3, 1, 1, 3 )
        rsyncLayout.addWidget( QLabel( 'PASSWORD' ), 4, 0, 1, 1 )
        rsyncLayout.addWidget( self.rsync_password, 4, 1, 1, 3 )
        myLayout.addWidget( rsyncWidget )
        self.rsync_localdir.returnPressed.connect(
            self.pushRsyncConfig )
        self.rsync_sshpath.returnPressed.connect(
            self.pushRsyncConfig )
        self.rsync_subdir.returnPressed.connect(
            self.pushRsyncConfig )
        self.rsync_password.returnPressed.connect(
            self.pushRsyncConfig )
        #
        ## now initialize
        self.initHowdyConfigLoginStatus( ) # set everything up
        self.setFixedWidth( jackettWidget.sizeHint( ).width( ) * 1.7 )

    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        refreshAction = QAction( 'refresh login config', menu )
        refreshAction.triggered.connect( self.initHowdyConfigLoginStatus )
        menu.addAction( refreshAction )
        helpAction = QAction( 'help', menu )
        helpAction.triggered.connect( self.showHelpInfo )
        menu.addAction( helpAction )
        menu.popup( QCursor.pos( ) )

class HowdyConfigMusicWidget( HowdyConfigWidget ):
    _emitWorkingStatusDict = {
        'GMUSIC' : False,
        'LASTFM' : False,
        'GRACENOTE' : False,
        'MUSICBRAINZ' : False }

    def showHelpInfo( self ):
        pass

    def initHowdyConfigMusicStatus( self ):
        #
        ## look for gmusic credentials
        try:
            mmg = music.get_gmusicmanager( verify = self.verify )
            self.gmusicStatusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'GMUSIC' ] = True
        except ValueError as e:
            self.gmusicStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GMUSIC' ] = False

        #
        ## look for lastfm credentials
        try:
            lastFMCreds = music.HowdyLastFM.get_lastfm_credentials( )
            self.lastfmAPIKey.setText( lastFMCreds[ 'api_key' ] )
            self.lastfmAPISecret.setText( lastFMCreds[ 'api_secret' ] )
            self.lastfmAppName.setText( lastFMCreds[ 'application_name' ] )
            self.lastfmUserName.setText( lastFMCreds[ 'username' ] )
            self.lastfmStatusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'LASTFM' ] = True
        except ValueError as e:
            self.lastfmAPIKey.setText( '' )
            self.lastfmAPISecret.setText( '' )
            self.lastfmAppName.setText( '' )
            self.lastfmUserName.setText( '' )
            self.lastfmStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'LASTFM' ] = False

        #
        ## now look for gracenote credentials
        try:
            clientID, userID = music.HowdyMusic.get_gracenote_credentials( )
            self.gracenoteToken.setText( userID )
            self.gracenoteStatusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'GRACENOTE' ] = True
        except ValueError as e:
            self.gracenoteToken.setText( '' )
            self.gracenoteStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GRACENOTE' ] = False

        #
        ## set up musicbrainz API access credentials
        # first, get email from plex server credentials
        email = None
        dat = core.getCredentials( verify = self.verify )
        if dat is not None:
            email, _ = dat
            self.musicbrainzEmail.setText( email )
        else: self.musicbrainzEmail.setText( '' )
        try:
            if email is not None:
                mb_data = music.MusicInfo.get_set_musicbrainz_useragent(
                    email )
                self.musicbrainzStatusLabel.setText( 'WORKING' )
                self._emitWorkingStatusDict[ 'MUSICBRAINZ' ] = True
            else:
                mb_data = music.MusicInfo.get_set_musicbrainz_useragent(
                    '' )
                self.musicbrainzStatusLabel.setText( 'NOT WORKING' )
                self._emitWorkingStatusDict[ 'MUSICBRAINZ' ] = False
            mb_app_name = mb_data[ 'appname' ]
            mb_version = mb_data[ 'version' ]
            self.musicbrainzAppName.setText( mb_app_name )
            self.musicbrainzVersion.setText( mb_version )
        except Exception as e:
            self.musicbrainzAppName.setText( '' )
            self.musicbrainzVersion.setText( '' )
            self.musicbrainzStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'MUSICBRAINZ' ] = False

    def pushGoogleConfig( self ): # this is done by button
        def checkStatus( state ):
            if state:
                self.gmusicStatusLabel.setText( 'WORKING' )
            else:
                self.gmusicStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GOOGLE' ] = state
            self.workingStatus.emit( self._emitWorkingStatusDict )
        goauth2dlg = GoogleOauth2Dialog( self )
        goauth2dlg.emitState.connect( checkStatus )
        goauth2dlg.show( )
        goauth2dlg.exec_( )

    def pushGracenoteToken( self ):
        client_ID = self.gracenoteToken.text( ).strip( )
        self.gracenoteToken.setText( client_ID )
        try:
            music.HowdyMusic.push_gracenote_credentials( client_ID )
            self.gracenoteStatusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'GRACENOTE' ] = True
        except:
            self.gracenoteStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'GRACENOTE' ] = False
        self.workingStatus.emit( self._emitWorkingStatusDict )
        
    def pushLastFMToken( self ):
        api_data = {
            'api_key' : self.lastfmAPIKey.text( ).strip( ),
            'api_secret' : self.lastfmAPISecret.text( ).strip( ),
            'application_name' : self.lastfmAppName.text( ).strip( ),
            'username' : self.lastfmUserName.text( ).strip( ) }
        plexlastFM = music.HowdyLastFM( api_data )
        data, status = plexlastFM.get_album_info(
            'Air', 'Moon Safari' ) # this should always work
        if status != 'SUCCESS':
            self.lastfmAPIKey.setText( '' )
            self.lastfmAPISecret.setText( '' )
            self.lastfmAppName.setText( '' )
            self.lastfmUserName.setText( '' )
            self.lastfmStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'LASTFM' ] = False
        else:
            self.lastfmAPIKey.setText( api_data[ 'api_key' ] )
            self.lastfmAPISecret.setText( api_data[ 'api_secret' ] )
            self.lastfmAppName.setText( api_data[ 'application_name' ] )
            self.lastfmUserName.setText( api_data[ 'username' ] )
            music.HowdyLastFM.push_lastfm_credentials(
                api_data )
            self.lastfmStatusLabel.setText( 'WORKING' )
            self._emitWorkingStatusDict[ 'LASTFM' ] = True
        self.workingStatus.emit( self._emitWorkingStatusDict )

    def pushMusicBrainzUserAgent( self ):
        appname = self.musicbrainzAppName.text( ).strip( )
        version = self.musicbrainzVersion.text( ).strip( )
        email = self.musicbrainzEmail.text( ).strip( )
        if any(map(lambda tok: tok == '', ( appname, version, email ) ) ):
            self.musicbrainzAppName.setText( '' )
            self.musicbrainzVersion.setText( '' )
            self.musicbrainzStatusLabel.setText( 'NOT WORKING' )
            self._emitWorkingStatusDict[ 'MUSICBRAINZ' ] = False
            self.workingStatus.emit( self._emitWorkingStatusDict )
            return
        #
        ## all fields nonzero, good to go
        music.MusicInfo.push_musicbrainz_useragent( appname, version )
        music.MusicInfo.get_set_musicbrainz_useragent( email )
        self.musicbrainzStatusLabel.setText( 'WORKING' )
        self._emitWorkingStatusDict[ 'MUSICBRAINZ' ] = True
        self.workingStatus.emit( self._emitWorkingStatusDict )
        
        
    def __init__( self, parent, verify = True ):
        super( HowdyConfigMusicWidget, self ).__init__(
            parent, 'MUSIC', verify = verify )
        #
        self.gmusicStatusLabel = QLabel( )
        self.google_oauth = QPushButton( 'CLIENT REFRESH' )
        # needed so that returnPressed does not trigger a clicked event
        self.google_oauth.setAutoDefault( False )
        #
        self.lastfmAPIKey = QLineEdit( )
        self.lastfmAPIKey.setEchoMode( QLineEdit.Password )
        self.lastfmAPISecret = QLineEdit( )
        self.lastfmAPISecret.setEchoMode( QLineEdit.Password )
        self.lastfmAppName = QLineEdit( )
        self.lastfmUserName = QLineEdit( )
        self.lastfmStatusLabel = QLabel( )
        #
        self.gracenoteToken = QLineEdit( )
        self.gracenoteToken.setEchoMode( QLineEdit.Password )
        self.gracenoteStatusLabel = QLabel( )
        #
        self.musicbrainzEmail = QLabel( )
        self.musicbrainzAppName = QLineEdit( )
        self.musicbrainzVersion = QLineEdit( )
        self.musicbrainzStatusLabel = QLabel( )
        #
        self.initHowdyConfigMusicStatus( ) # set everything up
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        #
        ## 1/4
        bkgColor = get_popularity_color( 0.1 ).name( )
        gmusicWidget = QWidget( )
        gmusicWidget.setStyleSheet("""
        QWidget {
        background-color: %s;
        }""" % bkgColor )
        gmusicLayout = QGridLayout( )
        gmusicWidget.setLayout( gmusicLayout )
        gmusicLayout.addWidget( QLabel( 'GMUSIC CONFIG' ), 0, 0, 1, 1 )
        gmusicLayout.addWidget( self.google_oauth, 0, 1, 1, 2 )
        gmusicLayout.addWidget( self.gmusicStatusLabel, 0, 3, 1, 1 )
        self.google_oauth.clicked.connect(
            self.pushGoogleConfig )
        myLayout.addWidget( gmusicWidget )
        #
        ## 2/4
        bkgColor = get_popularity_color( 0.2 ).name( )
        lastfmWidget = QWidget( )
        lastfmWidget.setStyleSheet("""
        QWidget {
        background-color: %s;
        }""" % bkgColor )
        lastfmLayout = QGridLayout( )
        lastfmWidget.setLayout( lastfmLayout )
        lastfmLayout.addWidget( QLabel( 'LASTFM TOKENS' ), 0, 0, 1, 1 )
        lastfmLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        lastfmLayout.addWidget( self.lastfmStatusLabel, 0, 3, 1, 1 )
        lastfmLayout.addWidget( QLabel( 'API KEY' ), 1, 0, 1, 1 )
        lastfmLayout.addWidget( self.lastfmAPIKey, 1, 1, 1, 3 )
        lastfmLayout.addWidget( QLabel( 'API SEC' ), 2, 0, 1, 1 )
        lastfmLayout.addWidget( self.lastfmAPISecret, 2, 1, 1, 3 )
        lastfmLayout.addWidget( QLabel( 'API APPNAME' ), 3, 0, 1, 1 )
        lastfmLayout.addWidget( self.lastfmAppName, 3, 1, 1, 3 )
        lastfmLayout.addWidget( QLabel( 'API USERNAME' ), 4, 0, 1, 1 )
        lastfmLayout.addWidget( self.lastfmUserName, 4, 1, 1, 3 )
        myLayout.addWidget( lastfmWidget )
        #
        ## 3/4
        bkgColor = get_popularity_color( 0.3 ).name( )
        gracenoteWidget = QWidget( )
        gracenoteWidget.setStyleSheet("""
        QWidget {
        background-color: %s;
        }""" % bkgColor )
        gracenoteLayout = QGridLayout( )
        gracenoteWidget.setLayout( gracenoteLayout )
        gracenoteLayout.addWidget( QLabel( 'GRACENOTE TOKEN' ), 6, 0, 1, 1 )
        gracenoteLayout.addWidget( self.gracenoteToken, 6, 1, 1, 2 )
        gracenoteLayout.addWidget( self.gracenoteStatusLabel, 6, 3, 1, 1 )
        myLayout.addWidget( gracenoteWidget )
        #
        ## 4/4
        bkgColor = get_popularity_color( 0.4 ).name( )
        musicbrainzWidget = QWidget( )
        musicbrainzWidget.setStyleSheet("""
        QWidget {
        background-color: %s;
        }""" % bkgColor )
        musicbrainzLayout = QGridLayout( )
        musicbrainzWidget.setLayout( musicbrainzLayout )
        musicbrainzLayout.addWidget( QLabel( 'MUSICBRAINZ USER AGENT' ), 0, 0, 1, 1 )
        musicbrainzLayout.addWidget( QLabel( ), 0, 1, 1, 2 )
        musicbrainzLayout.addWidget( self.musicbrainzStatusLabel, 0, 3, 1, 1 )
        musicbrainzLayout.addWidget( QLabel( 'EMAIL' ), 1, 0, 1, 1 )
        musicbrainzLayout.addWidget( self.musicbrainzEmail, 1, 1, 1, 3 )
        musicbrainzLayout.addWidget( QLabel( 'APP NAME' ), 2, 0, 1, 1 )
        musicbrainzLayout.addWidget( self.musicbrainzAppName, 2, 1, 1, 3 )
        musicbrainzLayout.addWidget( QLabel( 'APP VERSION' ), 3, 0, 1, 1 )
        musicbrainzLayout.addWidget( self.musicbrainzVersion, 3, 1, 1, 3 )
        myLayout.addWidget( musicbrainzWidget )
        #
        ## signals
        self.gracenoteToken.returnPressed.connect(
            self.pushGracenoteToken )
        self.lastfmAPIKey.returnPressed.connect(
            self.pushLastFMToken )
        self.lastfmAPISecret.returnPressed.connect(
            self.pushLastFMToken )
        self.lastfmAppName.returnPressed.connect(
            self.pushLastFMToken )
        self.lastfmUserName.returnPressed.connect(
            self.pushLastFMToken )
        self.musicbrainzAppName.returnPressed.connect(
            self.pushMusicBrainzUserAgent )
        self.musicbrainzVersion.returnPressed.connect(
            self.pushMusicBrainzUserAgent )
        #
        self.setFixedWidth( self.sizeHint( ).width( ) )
        
    def contextMenuEvent( self, event ):
        menu = QMenu( self )
        refreshAction = QAction( 'refresh music config', menu )
        refreshAction.triggered.connect( self.initHowdyConfigMusicStatus )
        menu.addAction( refreshAction )
        helpAction = QAction( 'help', menu )
        helpAction.triggered.connect( self.showHelpInfo )
        menu.addAction( helpAction )
        menu.popup( QCursor.pos( ) )
        

#
## main configuration dialog
## we look at the following login settings
class HowdyConfigGUI( QDialogWithPrinting ):
    class HowdyConfigTableView( QTableView ):
        def __init__( self, parent ):
            super( HowdyConfigGUI.HowdyConfigTableView, self ).__init__( parent )
            assert( isinstance( parent, QDialogWithPrinting ) )
            self.parent = parent
            self.setModel( self.parent.tm )
            #self.selectionModel( ).currentRowChanged.connect(
            #    self.processCurrentRow )
            #
            self.setShowGrid( True )
            self.verticalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
            self.horizontalHeader( ).setSectionResizeMode( QHeaderView.Fixed )
            self.setSelectionBehavior( QAbstractItemView.SelectRows )
            self.setSelectionMode( QAbstractItemView.SingleSelection ) # single row
            #
            self.setColumnWidth(0, 90 )
            self.setColumnWidth(1, 90 )
            self.setColumnWidth(2, 90 )
            self.setFixedWidth( 1.25 * ( 90 * 3 ) )
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

        def contextMenuEvent( self, event ):
            def popupConfigInfo( ):
                index_valid = max(
                    filter(lambda index: index.column( ) == 0,
                           self.selectionModel().selectedIndexes( ) ) )
                self.parent.tm.plexConfigAtRow( index_valid.row( ) )
            menu = QMenu( self )
            popupAction = QAction( 'Plex config category', menu )
            popupAction.triggered.connect( popupConfigInfo )
            menu.addAction( popupAction )
            menu.popup( QCursor.pos( ) )

    class HowdyConfigTableModel( QAbstractTableModel ):
        _columnNames = [ 'service', 'tot num.', 'num working' ]
        
        def __init__( self, parent ):
            super( HowdyConfigGUI.HowdyConfigTableModel, self ).__init__( parent )
            self.parent = parent
            self.data = { }
            #
            ## now add in the data -- service, number total, number working
            # row 0: LOGIN
            for idx, pcwidget in enumerate([
                    self.parent.loginWidget,
                    self.parent.credWidget,
                    self.parent.musicWidget]):
                working = pcwidget.getWorkingStatus( )
                self.data[idx] = [
                    pcwidget.service,
                    len( working ),
                    len(list(filter(lambda tok: working[tok] is True,
                                    working))) ]

            #
            ## populate the table
            self.beginInsertRows( QModelIndex( ), 0, 2 )
            self.endInsertRows( )

        def rowCount( self, parent ):
            return len( self.data )

        def columnCount( self, parent ):
            return 3

        def headerData( self, col, orientation, role ):
            if orientation == Qt.Horizontal and role == Qt.DisplayRole:
                return self._columnNames[ col ]

        def data( self, index, role ):
            if not index.isValid( ): return None
            row = index.row( )
            col = index.column( )
            datum = self.data[ row ]
            if role == Qt.BackgroundRole:
                if datum[ 2 ] < datum[ 1 ]:
                    color = get_popularity_color( 0.5 )
                    return QBrush( color )
            elif role == Qt.DisplayRole:
                return datum[ col ]

        def plexConfigAtRow( self, row ):
            if row == 0: self.parent.loginWidget.show( )
            elif row == 1: self.parent.credWidget.show( )
            elif row == 2: self.parent.musicWidget.show( )

        def _setWidgetWorkingStatus( self, working, row ):
            assert( row in ( 0, 1, 2 ) )
            self.layoutAboutToBeChanged.emit( )
            datum = self.data[ row ]
            datum[1] = len( working )
            datum[2] = len(list(filter(lambda tok: working[tok] is True,
                                     working)))
            self.layoutChanged.emit( )

        def setLoginWidgetWorkingStatus( self, working ):
            self._setWidgetWorkingStatus( working, 0 )

        def setCredWidgetWorkingStatus( self, working ):
            self._setWidgetWorkingStatus( working, 1 )

        def setMusicWidgetWorkingStatus( self, working ):
            self._setWidgetWorkingStatus( working, 2 )
                
            
    def __init__( self, verify = True ):
        #
        ## initialization of this data
        super(QDialogWithPrinting, self ).__init__( None )
        self.setWindowTitle( 'HOWDY CONFIGURATION WIDGET' )
        self.credWidget = HowdyConfigCredWidget( self, verify = verify )
        self.loginWidget= HowdyConfigLoginWidget( self, verify = verify )
        self.musicWidget= HowdyConfigMusicWidget( self, verify = verify )
        #
        ##
        self.tm = HowdyConfigGUI.HowdyConfigTableModel( self )
        self.tv = HowdyConfigGUI.HowdyConfigTableView( self )
        #
        ## connect signals
        self.credWidget.workingStatus.connect( self.tm.setCredWidgetWorkingStatus )
        self.loginWidget.workingStatus.connect( self.tm.setLoginWidgetWorkingStatus )
        self.musicWidget.workingStatus.connect( self.tm.setMusicWidgetWorkingStatus )
        #
        myLayout = QVBoxLayout( )
        self.setLayout( myLayout )
        myLayout.addWidget( self.tv )
        self.setFixedHeight( self.tv.sizeHint( ).height( ) * 0.85 )
        self.setFixedWidth( self.tv.sizeHint( ).width( ) * 1.25 )
        self.show( )
    

#
## check to see if we have a local plex server
def _checkForLocal( ):
    try:
        response = requests.get( 'http://localhost:32400' )
        if response.status_code == 200:
            return 'http://localhost:32400', None
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None

def returnToken( doLocal = True, verify = True, checkWorkingServer = True ):    
    #
    ## now check if we have server credentials
    val = core.checkServerCredentials(
        verify = verify, doLocal = doLocal,
        checkWorkingServer = checkWorkingServer )
    if val is not None:
        fullurl, token = val
        return fullurl, token
    
    dlg = UsernamePasswordServerDialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return dlg.fullurl, dlg.token

def returnGoogleAuthentication( ):
    status, message = core.oauthCheckGoogleCredentials( )
    if status: return status
    dlg = GoogleOauth2Dialog( )
    result = dlg.exec_( )
    if result != QDialog.Accepted:
        sys.exit( 0 )
    return True

class UsernamePasswordServerDialog( QDialog ):
    def __init__( self, doLocal = True, verify = True ):
        super( UsernamePasswordServerDialog, self ).__init__( )
        self.fullurl = ''
        self.token = None
        self.setModal( True )
        self.setWindowTitle( 'PLEX SERVER USERNAME/PASSWORD' )
        mainLayout = QGridLayout( )
        self.setLayout( mainLayout )
        self.doLocal = doLocal
        self.verify = verify
        #
        self.server_usernameBox = QLineEdit( )
        self.server_passwordBox = QLineEdit( )
        self.server_statusLabel = QLabel( "" )
        self.server_passwordBox.setEchoMode( QLineEdit.Password )
        mainLayout.addWidget( QLabel( "USERNAME" ), 0, 0, 1, 1 )
        mainLayout.addWidget( self.server_usernameBox, 0, 1, 1, 2 )
        mainLayout.addWidget( QLabel( "PASSWORD" ), 1, 0, 1, 1 )
        mainLayout.addWidget( self.server_passwordBox, 1, 1, 1, 2 )
        mainLayout.addWidget( self.server_statusLabel, 2, 0, 1, 3 )
        self.server_usernameBox.returnPressed.connect( self.server_checkUsernamePassword )
        self.server_passwordBox.returnPressed.connect( self.server_checkUsernamePassword )
        #
        ##
        self.setFixedWidth( self.sizeHint().width() )
        self.setFixedHeight( self.sizeHint().height() )
    
    #
    ## clear all credential information
    def clearCreds( self ):
        self.server_usernameBox.setText( '' )
        self.server_passwordBox.setText( '' )
    #
    ## do plex server checking
    def server_checkUsernamePassword( self ):        
        self.server_usernameBox.setText( str( self.server_usernameBox.text( ) ).strip( ) )
        self.server_passwordBox.setText( str( self.server_passwordBox.text( ) ).strip( ) )
        #
        ## now check that this is a valid username and password
        username = str( self.server_usernameBox.text( ) ).strip( )
        password = str( self.server_passwordBox.text( ) ).strip( )
        token = core.getTokenForUsernamePassword( username, password, verify = self.verify )
        if token is None:
            self.server_statusLabel.setText( 'ERROR: wrong credentials.' )
            return
        self.token = token
        #
        ## now look for the server
        dat = core.get_all_servers( self.token )
        if dat is None: self.fullURL = ''
        else:
            name = max(filter(lambda name: dat[ name ][ 'owned' ], dat ) )
            self.fullURL = dat[ name ][ 'url' ]
        core.pushCredentials( username, password )
        self.clearCreds( )
        self.accept( )

class ImgurOauth2Dialog( QDialogWithPrinting ):
    emitState = pyqtSignal( bool )

    def __init__( self, parent, imgur_clientId, imgur_clientSECRET ):
        if parent is not None:
            super( ImgurOauth2Dialog, self ).__init__(
                parent, isIsolated = True, doQuit = False )
            self.verify = parent.verify
        else:
            super( ImgurOauth2Dialog, self ).__init__(
                None, isIsolated = True, doQuit = True )
            self.verify = False
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT IMGUR OAUTH2 CREDENTIALS' )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        self.imgur_clientId = imgur_clientId
        self.imgur_clientSECRET = imgur_clientSECRET
        #
        mainLayout.addWidget( QLabel(
            '\n'.join([
                       'FILL OUT THE MAIN URL (IN BROWSER BAR)',
                       'TO WHICH YOU ARE REDIRECTED IN THE END.'  ])))
        #
        authWidget = QWidget( )
        authLayout = QGridLayout( )
        authWidget.setLayout( authLayout )
        self.authCredentials = QLineEdit( )
        # self.authCredentials.setEchoMode( QLineEdit.Password )
        authLayout.addWidget( QLabel( 'URL:' ), 0, 0, 1, 1 )
        authLayout.addWidget( self.authCredentials, 0, 1, 1, 6 )
        mainLayout.addWidget( authWidget )
        #
        self.statusLabel = QLabel( )
        mainLayout.addWidget( self.statusLabel )
        #
        self.authCredentials.returnPressed.connect( self.check_authCredentials )
        self.setFixedWidth( 600 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        #
        ## now perform the launch window
        auth_url = 'https://api.imgur.com/oauth2/authorize'
        imgur = OAuth2Session( self.imgur_clientId )
        authorization_url, self.state = imgur.authorization_url(
            auth_url, verify = self.verify )
        webbrowser.open_new_tab( authorization_url )
        self.hide( )

    def check_authCredentials( self ):
        self.statusLabel.setText( '' )
        self.authCredentials.setText( str( self.authCredentials.text( ) ).strip( ) )
        response_url = str( self.authCredentials.text( ) )
        try:
            token_url = 'https://api.imgur.com/oauth2/token'
            imgur = OAuth2Session(
                client_id = self.imgur_clientId,
                state = self.state )
            token = imgur.fetch_token(
                token_url, client_secret = self.imgur_clientSECRET,
                authorization_response = response_url, verify = self.verify )
            self.authCredentials.setText( '' )
            stat =  core.store_imgurl_credentials(
                self.imgur_clientId,
                self.imgur_clientSECRET,
                token[ 'refresh_token' ] )
            assert( stat == 'SUCCESS' )
            self.accept( )
            self.emitState.emit( True )
        except Exception as e:
            logging.error( str( e ) )
            self.statusLabel.setText( 'ERROR: INVALID AUTHORIZATION CODE.' )
            self.authCredentials.setText( '' )
            self.emitState.emit( False )
        self.close( )

class GoogleOauth2Dialog( QDialogWithPrinting ):
    emitState = pyqtSignal( bool )
    
    def __init__( self, parent ):
        super( GoogleOauth2Dialog, self ).__init__(
            parent, isIsolated = True, doQuit = False )
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT GOOGLE OAUTH2 CREDENTIALS' )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        #
        mainLayout.addWidget( QLabel( 'TOOL TO STORE GOOGLE SETTINGS AS OAUTH2 TOKENS.' ) )
        #
        authWidget = QWidget( )
        authLayout = QGridLayout( )
        authWidget.setLayout( authLayout )
        self.authCredentials = QLineEdit( )
        self.authCredentials.setEchoMode( QLineEdit.Password )
        authLayout.addWidget( QLabel( 'CREDENTIALS:' ), 0, 0, 1, 1 )
        authLayout.addWidget( self.authCredentials, 0, 1, 1, 4 )
        mainLayout.addWidget( authWidget )
        #
        self.statusLabel = QLabel( )
        mainLayout.addWidget( self.statusLabel )
        #
        self.authCredentials.returnPressed.connect( self.check_authCredentials )
        self.setFixedWidth( 550 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        #
        self.flow, url = core.oauth_generate_google_permission_url( )
        webbrowser.open_new_tab( url )
        self.hide( )
        
    def check_authCredentials( self ):
        self.statusLabel.setText( '' )
        self.authCredentials.setText( str( self.authCredentials.text( ) ).strip( ) )
        authorization_code = str( self.authCredentials.text( ) )
        try:
            credentials = self.flow.step2_exchange( authorization_code )
            core.oauth_store_google_credentials( credentials )
            self.authCredentials.setText( '' )
            self.accept( )
            self.emitState.emit( True )
        except:
            self.statusLabel.setText( 'ERROR: INVALID AUTHORIZATION CODE.' )
            self.authCredentials.setText( '' )
            self.emitState.emit( False )
        self.close( )

class GMusicMobileClientOauth2Dialog( QDialogWithPrinting ):
    def __init__( self, parent ):
        super( GoogleOauth2Dialog, self ).__init__(
            parent, isIsolated = True, doQuit = False )
        self.setModal( True )
        self.setWindowTitle( 'PLEX ACCOUNT GOOGLE MUSIC MOBILECLIENT CREDENTIALS' )
        mainLayout = QVBoxLayout( )
        self.setLayout( mainLayout )
        self.verify = parent.verify
        #
        mainLayout.addWidget( QLabel( 'TOOL TO STORE GOOGLE MUSIC MOBILECLIENT AS OAUTH2 TOKENS.' ) )
        #
        authWidget = QWidget( )
        authLayout = QGridLayout( )
        authWidget.setLayout( authLayout )
        self.authCredentials = QLineEdit( )
        self.authCredentials.setEchoMode( QLineEdit.Password )
        authLayout.addWidget( QLabel( 'CREDENTIALS:' ), 0, 0, 1, 1 )
        authLayout.addWidget( self.authCredentials, 0, 1, 1, 4 )
        mainLayout.addWidget( authWidget )
        #
        self.statusLabel = QLabel( )
        mainLayout.addWidget( self.statusLabel )
        #
        self.authCredentials.returnPressed.connect( self.check_authCredentials )
        self.setFixedWidth( 550 )
        self.setFixedHeight( self.sizeHint( ).height( ) )
        #
        self.flow, url = music.oauth_generate_google_permission_url( )
        webbrowser.open_new_tab( url )
        self.hide( )

    def check_authCredentials( self ):
        self.statusLabel.setText( '' )
        self.authCredentials.setText( str( self.authCredentials.text( ) ).strip( ) )
        authorization_code = str( self.authCredentials.text( ) )
        try:
            if not self.verify: http = httplib2.Http( disable_ssl_certificate_validation = True )
            else: http = httplib2.Http( )
            credentials = self.flow.step2_exchange( authorization_code, http = http )
            music.oauth_store_google_credentials( credentials )
            self.authCredentials.setText( '' )
            self.accept( )
            self.emitState.emit( True )
        except:
            self.statusLabel.setText( 'ERROR: INVALID AUTHORIZATION CODE.' )
            self.authCredentials.setText( '' )
            self.emitState.emit( False )
        self.close( )
