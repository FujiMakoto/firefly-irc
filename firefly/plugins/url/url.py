# coding=utf-8
import socket
import re
import logging

from urllib2 import urlopen, URLError, HTTPError
from urlparse import urlparse

from bs4 import BeautifulSoup


class UrlParser:
    """
    URL parsing and services
    """
    def __init__(self):
        """
        Initialize a new URL Plugin instance
        """
        self.log = logging.getLogger('firefly.plugins.url')
        # URL matching regex
        # http://daringfireball.net/2010/07/improved_regex_for_matching_urls
        self.url_regex = re.compile('((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s'
                                    '()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{}'
                                    ';:\'".,<>?«»“”‘’]))', re.IGNORECASE)

    def _match_first_url(self, message):
        """
        Attempt to match the first URL in a supplied message

        Args:
            message(str): The message to search

        Returns:
            str or None
        """
        self.log.debug('Attempting to match the first URL in a message')
        url = self.url_regex.search(message)
        if url:
            url = url.group(0)
            self.log.info('URL match found, returning: ' + url)
            return url

        self.log.debug('No URL match found')
        return None

    def _fetch_partial_page(self, url, page_bytes=8192):
        """
        Attempt to download the first specified bytes of a web page

        Args:
            url(str): The URL to download
            bytes(int): The size in bytes to download

        Returns:
            str or None
        """
        # Download the first <bytes> of the web page
        self.log.debug('Attempting to download the first {bytes} bytes of {url}'.format(bytes=page_bytes, url=url))
        try:
            page = urlopen(url, timeout=3).read(page_bytes)
        except HTTPError as e:
            page = None
            self.log.info('HTTP Error {code}: {reason}'.format(code=str(e.code), reason=str(e.reason)))
        except URLError as e:
            page = None
            self.log.info('URL Error: ' + str(e.reason))
        except socket.timeout:
            page = None
            self.log.info('HTTP request timed out')

        return page

    def _get_title_from_page(self, page):
        """
        Fetch the title of an HTML web page

        Args:
            page(str): The HTML page to parse

        Returns:
            str or None
        """
        self.log.debug('Attempting to parse the HTML page title')
        title = None
        soup = BeautifulSoup(page, 'lxml')
        if soup.title:
            title = soup.title.string

        # Debug stuff
        if title:
            self.log.info('Found the title: ' + title)
        else:
            self.log.debug('No title found')

        return title

    @staticmethod
    def _format_title(url, title):
        """
        Format a specified title string

        Args:
            title(str): The title string to format

        Returns:
            str
        """
        title = ''.join(title.splitlines())
        title = 'Title: ' + str(title).strip()
        host = urlparse(url).netloc
        if host:
            title += ' (at {host})'.format(host=host)

        return title

    def get_title_from_url(self, url, formatted=True):
        """
        Return the HTML web page title of the specified URL

        Args:
            url(str): The URL to parse

        Returns:
            str or None
        """
        # Make sure our URL has a valid schema
        if not re.match('^https?://.+', url):
            url = 'http://' + url

        # Attempt to download the first 4096 bytes of the web page
        page = self._fetch_partial_page(url)
        if not page:
            return

        # Fetch the title
        title = self._get_title_from_page(page)

        # Apply formatting
        if formatted and title:
            title = self._format_title(url, title)

        # Return the title
        return title

    def get_title_from_message(self, message, formatted=True):
        """
        Parse a message for a URL and return the title of the page if found

        Args:
            message(str): The message to parse
            formatted(bool): Apply formatting to the returned title string

        Returns:
            str or None
        """
        # Attempt to fetch the first URL in our message
        url = self._match_first_url(message)
        if not url:
            return

        # Fetch and return the title
        return self.get_title_from_url(url, formatted)