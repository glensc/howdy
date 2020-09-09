.. _howdy_config_gui_label:

=====================================================================================
|howdy_config_gui_icon| Consolidating Howdy Configuration With ``howdy_config_gui``
=====================================================================================
Although ``howdy_config_gui`` is part of ``core``, and naturally lives in :numref:`Howdy Core Functionality`, I suggest you use this configuration tool to naturally consolidate the services and settings. The final configuration data will live in an `sqlite version 3 <https://en.wikipedia.org/wiki/SQLite>`_ database that is located in ``~/.local/howdy/app.db`` and is readable only by the user (and root).

Some of the ``howdy_config_gui`` screenshots are found in :numref:`Summary of Setting Up Google Credentials` (specifically :numref:`imgur_step04_credentials`, :numref:`google_step02_refreshcredentials`, and :numref:`google_step04_oauthtokenstring`) and in :numref:`Howdy Settings Configuration` (specifically :numref:`login_step01_login` and :numref:`login_step02_settings`).

As described in :numref:`Howdy Services Configuration` and :numref:`Howdy Settings Configuration`, ``howdy_config_gui`` start with the initial dialog widget of three sets of services and settings organized into three rows: *LOGIN*, *CREDENTIALS*, and *MUSIC*. The second column shows the number of services for each service set. The third column shows that number of services that are *working*. A screen shot illuminates this.

.. _howdy_config_gui_serviceswidget:

.. figure:: howdy-config-gui-figures/howdy_config_gui_serviceswidget.png
   :width: 100%
   :align: center

The document is organized into these three sections.

* :ref:`Login Services` describes the dialog window that sets the login services.
* :ref:`Credentials Services` describes the dialog window that sets the credentials. :numref:`Choosing Main Imgur_ Album` describes how to select one's main Imgur_ album used for the storage and retrieval of images when writing newsletter emails (see :numref:`howdy_email_gui_label`).
* :ref:`Music Services` describes the dialog window that applies the settings for music services.

Login Services
--------------

As described in :numref:`Howdy Settings Configuration`, right click on the *LOGIN* row in the main widget to launch the *PLEX LOGIN CONFIGURATION* widget. The relevant screen shot, :ref:`login window <login_step01_login>`, is shown below.

.. figure:: howdy-config-settings-figures/login_step01_login.png
   :width: 100%
   :align: center

The *PLEX LOGIN CONFIGURATION* widget is organized into four services, each organized into differently colored sub-widgets. The top row of each widget gives the name of the service, and its status (working or not working). The login widget controls settings for four services:

* *PLEXLOGIN*: the username and password for your Plex_ account.
* *DELUGE*: necessary settings to access your `Deluge torrent server <Deluge_>`_.
* *JACKETT*: the URL and API key for your `Jackett torrent searching server <Jackett_>`_.
* *RSYNC*: settings used to securely copy downloaded movies and TV shows from a remote server to the Plex_ server you control.

Here is a screen shot.

.. figure:: howdy-config-gui-figures/howdy_login_mainfigure.png
   :width: 100%
   :align: center

Use your Plex_ email and password for *PLEXLOGIN*, as described in :numref:`credentials_for_plex_account`. Set up at least your Deluge server according to :numref:`Seedhost Services Setup`. Set up *JACKETT* as described in :numref:`The Jackett Server`, and more conveniently using a Jackett server provided by Seedhost (see :numref:`Seedhost Services Setup` for more details). Finally, apply *RSYNC* settings according to :numref:`Local and Remote (Seedhost) SSH Setup`.

Credentials Services
----------------------------

As described in :numref:`Summary of Setting Up Google Credentials`, right click on the *CREDENTIALS* row in the main widget to launch the *PLEX CREDENTIALS CONFIGURATION* widget. The relevant screen shot, :ref:`credentials window <imgur_step04_credentials>`, is shown below.

.. figure:: howdy-config-services-figures/google_step01_credentials.png
   :width: 100%
   :align: center

The *PLEX CREDENTIALS CONFIGURATION* widget is organized into four services: the `TMDB service <TMDB_>`_, the `TVDB service <TVDB_>`_, the `Imgur image hosting service <Imgur_>`_, and Google's services (see :numref:`Howdy Services Configuration` for a list). Here is a screen shot.

.. _howdy_credentials_mainfigure:

.. figure:: howdy-config-gui-figures/howdy_credentials_mainfigure.png
   :width: 100%
   :align: center

Apply the TMDB_ service settings according to :numref:`the_movie_database_api`. Apply the TVDB_ service settings according to :numref:`the_television_database_api`. Apply the Imgur_ settings according to :numref:`The Imgur API`. Finally, follow instructions in :numref:`Summary of Setting Up Google Credentials` to set up all six of the Google and Google-related services that Howdy uses.

Choosing Main Imgur_ Album
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The *IMGUR* panel in the *PLEX CREDENTIALS CONFIGURATION* widget has a row that shows the main Imgur_ album -- that contains the PNG images that can accessed, added, and removed -- used by :ref:`howdy_email_gui_label` to insert images. The middle :py:class:`QLabel <PyQt5.QtWidgets.QLabel>` says the name of the main Imgur_ album that is being used; in :numref:`howdy_credentials_mainfigure` this is ``MAIN IMGUR ALBUM``. The button labeled ``MAIN ALBUMS`` launches a GUI that allows us to choose, among other things, the main Imgur_ album to use for choosing images. In this GUI, the album names are shown alphabetically.

.. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_main.png
   :width: 100%
   :align: center

This GUI can do four things: :ref:`add a new album (and make it the main Imgur album) <add_album>`, :ref:`select an existing album as the main Imgur album <select_album>`, :ref:`delete an existing Imgur album <delete_album>`, and :ref:`rename the main Imgur album <rename_album>`. These all occur through a popup menu triggered with a right click.

.. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_choices.png
   :width: 100%
   :align: center

.. _add_album:

* We can add a new album, and make it the new Imgur_ album, by choosing the ``Add`` option in the popup menu. We give it a name different from the other Imgur_ albums; if we choose a name that matches, then nothing happens. The new album is created, with (naturally) no images in it, and is made the MAIN Imgur_ album.

  .. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_add.png
     :width: 100%
     :align: center

.. _select_album:

* We can set the main Imgur_ album, by choosing the ``Set Main Option`` in the popup menu and selecting (in BLUE) the album.

  .. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_setmain.png
     :width: 100%
     :align: center

.. _delete_album:

* We can delete the Imgur_ album, by choosing the ``Delete`` option in the popup menu. This choice also removes all pictures in this album.

  * If the album we delete is *NOT* the main Imgur_ album, then only that album's entry in this table is removed.
  * If the album we delete is the main Imgur_ album, then the main Imgur_ album's entry is removed, *AND* the new main Imgur_ album is alphabetically the first of the remaining albums.
  * If there was previously only *one* album, then the table is empty and there are no main Imgur_ albums with this account. Images can be used only after :ref:`creating an Imgur album <add_album>` and then adding new images to it as shown in :ref:`howdy_email_gui_label`.

  :numref:`howdy_imgurlchoosealbum_delete` demonstrates what happens when we delete a non-main album.

  .. _howdy_imgurlchoosealbum_delete:

  .. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_delete.png
     :width: 100%
     :align: center

.. _rename_album:

* And we can rename the main Imgur_ album, by choosing the ``Rename`` option in the popup menu. This new name cannot be any of the album names currently in the Imgur_ account, otherwise nothing occurs.

  .. figure:: howdy-config-gui-figures/howdy_imgurlchoosealbum_rename.png
     :width: 100%
     :align: center


Music Services
----------------------------
Right click on the *MUSIC* row in the main widget to launch the *PLEX MUSIC CONFIGURATION WIDGET*. Here is a screen shot.

.. figure:: howdy-config-gui-figures/howdy_credentials_selectmusic.png
  :width: 100%
  :align: center

The *PLEX MUSIC CONFIGURATION* widget is organized into four services, each organized into differently colored sub-widgets: GMUSIC (the `unofficial Google Music API service <https://unofficial-google-music-api.readthedocs.io/en/latest>`_), the `LastFM music metadata service <https://www.last.fm/api>`_, the `Gracenote music metadata service <https://developer.gracenote.com/web-api>`_, and the `MusicBrainz music metadata service <https://musicbrainz.org/>`_. Here is a screen shot.

.. figure:: howdy-config-gui-figures/howdymusic_mainfigure.png
  :width: 100%
  :align: center

:numref:`Summary of Setting Up Google Credentials` describes how to set up *GMUSIC*, since the unofficial Google Play API uses Google's services infrastructure. Copy the relevant information for *LASTFM* and *GRACENOTE* according to :numref:`The Gracenote and LastFM APIs`.

Public access to the MusicBrainz service requires a `valid user agent <https://musicbrainz.org/doc/XML_Web_Service/Rate_Limiting#Provide_meaningful_User-Agent_strings>`_. Howdy uses the `musicbrainzngs <https://python-musicbrainzngs.readthedocs.io>`_ Python module to access the MusicBrainz web service. This module requires an user agent with three elements:

* email address.
* version number.
* app version (as a string).

The email address is taken from the login email for your Plex_ account. You can *probably* put nearly any non-empty string into the *APP VERSION* and *APP NAME* dialog boxes.

.. |howdy_config_gui_icon| image:: howdy-config-gui-figures/howdy_config_gui_SQUARE_VECTA.svg
   :width: 50
   :align: middle

.. _Plex: https://plex.tv
.. _Deluge: https://en.wikipedia.org/wiki/Deluge_(software)
.. _Jackett: https://github.com/Jackett/Jackett
.. _Imgur: https://imgur.com
.. _TMDB: https://www.themoviedb.org
.. _TVDB: https://www.thetvdb.com
