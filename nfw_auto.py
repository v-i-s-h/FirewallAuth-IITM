# Auto reloader

import requests
import re
import time

# Disable SSL certificate warning for firewall
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


##### !! Configure LDAP account
ldapId   = '<put_userid_here>'
ldapPwd  = '<put_password_here>'

enableDebug = False

dnsTestUrl  = 'http://nfw.iitm.ac.in'
dnsFailed   = False

connTestUrl = 'http://connectivitycheck.gstatic.com/generate_204'
isConnected = False

nfw_server 	= '10.25.0.9'
magicUrl    = 'http://invalidurl/'

# Variables to save tokens
tkn_login       = None
tkn_keepAlive   = None
tkn_logout      = None

url_keepAlive   = None
url_logout      = None

try:
    ###################### Check whether DNS lookup is working #####################
    try:
        resp = requests.get( dnsTestUrl, verify=False, allow_redirects=False )
    except requests.ConnectionError as err:
        # DNS not working -  set flag
        dnsFailed = True

    ###################### Check connectivity and get magic URL ####################
    # Try a simple URL and get magic URL
    resp = requests.get( connTestUrl, verify = False, allow_redirects = False )
    if enableDebug:
        print 'Getting Magic URL'
        print '    Requested        :', connTestUrl
        print '    Response code    :', resp.status_code
        print '    Response         :', resp.text
    if resp.status_code == 204: # We are already connected
        isConnected = True
        if enableDebug:
            print 'Connection Active'
    elif resp.status_code == 303:   # We got the magic url
        magicUrl = resp.headers['Location']
    else:
        print 'Unknown status code: ', response.status_code

    if enableDebug:
        print 'Magic URL: ', magicUrl

    fwToken     = re.search( 'fgtauth\?(.+)', magicUrl )
    if fwToken:
        tkn_login   = fwToken.group(1)
    if enableDebug and not isConnected:
        print 'Firewall token: ', tkn_login

    # Edit Host
    if dnsFailed:   # Put hardcoded IP
        magicUrl = re.sub( r'nfw.iitm.ac.in', nfw_server, magicUrl )
    if enableDebug:
        print 'Final magic url: ', magicUrl

    ########################## Request Login Form ##################################
    # Just request a form so that token will be activated at server
    if not isConnected:
        fakeHeader = {
                    'Host': 'nfw.iitm.ac.in:1003',
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
        }
        try:
            resp = requests.get( magicUrl, headers=fakeHeader, verify=False, allow_redirects=False )
            # Parse here to build form elements
        except requests.ConnectionError as err:
            print 'Error Requesting login page: ', err

    ############################ Login with magic URL ###############################
    if not isConnected:
        # Assemeble login details
        loginDetails = {
            '4Tredir': 'http://google.com/',
            'magic': fwToken.group(1),
            'username': ldapId,
            'password': ldapPwd 
        }
        fakeHeader = {
            "Host": "nfw.iitm.ac.in:1003",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://nfw.iitm.ac.in:1003/" + "fgtauth?" + tkn_login,
            "Connection": "keep-alive"
        }
        
        # Start new session
        fwSession = requests.Session()
        try:
            resp = fwSession.post( magicUrl, headers=fakeHeader, data=loginDetails, verify=False, allow_redirects=False )
            # Parse and get tokens
            # print resp.text
            accessUrl = re.search( r'location.href="(.+keepalive\?.+)"', resp.text )
            if accessUrl:
                url_keepAlive = accessUrl.group(1)
            else:
                print "No keepalive url found"
            accessUrl = re.search( r'location.href="(.+logout\?.+)"', resp.text )
            if accessUrl:
                url_logout = accessUrl.group(1)
            else:
                print "No logout token found"
        except requests.ConnectionError as err:
            print 'Error at Login: ', err

        if dnsFailed:
            # Substitute IP for url
            url_keepAlive   = re.sub( r'nfw.iitm.ac.in', nfw_server, url_keepAlive )
            url_logout      = re.sub( r'nfw.iitm.ac.in', nfw_server, url_logout )

        if enableDebug:
            print "KeepAlive : ", url_keepAlive
            print "Logout    : ", url_logout

        # Repeat every 200 seconds
        while True:
            try:
                resp = requests.get( url_keepAlive, verify=False, allow_redirects=False )
                print "Keep alive request returned code ", resp.status_code
            except requests.ConnectionError as err:
                print "Erorr with keepalive: ", err
            time.sleep( 200 )

    else:
        if enableDebug:
            print 'Connection Available'
except KeyboardInterrupt:
    if url_logout:
        try:
            resp = requests.get( url_logout, verify=False, allow_redirects=False )
        except requests.ConnectionError as err:
            print "Error loggin out: ", err
    print "Exiting..."