#!/usr/bin/env python3

from httplib2 import Http
from argparse import ArgumentParser
#
from plexstuff.plexcore import plexcore

def main( ):
    parser = ArgumentParser( )
    parser.add_argument( '--noverify', dest='do_verify', action='store_false', default = True,
                       help = 'If chosen, do not verify SSL connections.' )
    args = parser.parse_args( )
    flow, url = plexcore.oauth_generate_google_permission_url( )
    print( 'Please go to this URL in a browser window: %s' % url )
    bs = '\n'.join([ 'After giving permission for Google services on your behalf,',
                     'type in the access code:' ] )
    access_code = input( bs )
    try:
        if args.do_verify: http = Http( )
        else: http = Http( disable_ssl_certificate_validation = True )
        credentials = flow.step2_exchange( access_code, http = http )
        plexcore.oauth_store_google_credentials( credentials )
        print( 'Success. Stored GOOGLE credentials.' )
    except:
        print( 'Error: invalid authorization code.' )
        return
    
if __name__=='__main__':
    main( )
