# -*- coding: utf-8 -*-
"""
Seismology package for SeisHub.
"""

from obspy.core import UTCDateTime
from obspy.mseed import libmseed
from seishub.core import Component, implements
from seishub.db.util import querySingleColumn, formatResults
from seishub.exceptions import InternalServerError
from seishub.packages.interfaces import IAdminPanel, IMapper
from seishub.registry.defaults import miniseed_tab
from sqlalchemy import sql
import datetime
import os
from lxml.etree import Element, SubElement as Sub
from seishub.util.xmlwrapper import toString


#class WaveformPanel(Component):
#    """
#    """
#    implements(IAdminPanel)
#
#    template = 'templates' + os.sep + 'waveforms.tmpl'
#    panel_ids = ('seismology', 'Seismology', 'waveforms', 'Waveforms')
#
#    def render(self, request):
#        data = {}
#        return data


class WaveformNetworkIDMapper(Component):
    """
    Fetches all possible network id's.
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getNetworkIds'

    def process_GET(self, request):
        return querySingleColumn(request, 'default_miniseed', 'network_id')


class WaveformStationIDMapper(Component):
    """
    Fetches all possible station id's.
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getStationIds'

    def process_GET(self, request):
        kwargs = {}
        kwargs['network_id'] = request.args0.get('network_id', None)
        return querySingleColumn(request, 'default_miniseed', 'station_id',
                                 **kwargs)


class WaveformLocationIDMapper(Component):
    """
    Fetches all possible location id's.
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getLocationIds'

    def process_GET(self, request):
        kwargs = {}
        kwargs['network_id'] = request.args0.get('network_id', None)
        kwargs['station_id'] = request.args0.get('station_id', None)
        return querySingleColumn(request, 'default_miniseed', 'location_id',
                                 **kwargs)


class WaveformChannelIDMapper(Component):
    """
    Fetches all possible channel id's.
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getChannelIds'

    def process_GET(self, request):
        kwargs = {}
        kwargs['network_id'] = request.args0.get('network_id', None)
        kwargs['station_id'] = request.args0.get('station_id', None)
        kwargs['location_id'] = request.args0.get('location_id', None)
        return querySingleColumn(request, 'default_miniseed', 'channel_id',
                                 **kwargs)


class WaveformLatencyMapper(Component):
    """
    Generates a list of latency values for each channel.
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getLatency'

    def process_GET(self, request):
        # process parameters
        columns = [
            miniseed_tab.c['network_id'], miniseed_tab.c['station_id'],
            miniseed_tab.c['location_id'], miniseed_tab.c['channel_id'],
            (datetime.datetime.utcnow() -
             sql.func.max(miniseed_tab.c['end_datetime'])).label('latency')]
        group_by = [
            miniseed_tab.c['network_id'], miniseed_tab.c['station_id'],
            miniseed_tab.c['location_id'], miniseed_tab.c['channel_id']]
        # build up query
        query = sql.select(columns, group_by=group_by, order_by=group_by)
        for col in ['network_id', 'station_id', 'location_id', 'channel_id']:
            text = request.args0.get(col, None)
            if not text:
                continue
            if '*' in text or '?' in text:
                text = text.replace('?', '_')
                text = text.replace('*', '%')
                query = query.where(miniseed_tab.c[col].like(text))
            else:
                query = query.where(miniseed_tab.c[col] == text)
        # execute query
        try:
            results = request.env.db.query(query)
        except:
            results = []
        return formatResults(request, results)

class WaveformPathMapper(Component):
    """
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getWaveformPath'

    def process_GET(self, request):
        # process parameters
        try:
            start = request.args0.get('start_datetime')
            start = UTCDateTime(start)
        except:
            start = UTCDateTime() - 60 * 20
        try:
            end = request.args0.get('end_datetime')
            end = UTCDateTime(end)
        except:
            # 10 minutes
            end = UTCDateTime()
        # build up query
        columns = [miniseed_tab.c['path'], miniseed_tab.c['file'],
                   miniseed_tab.c['network_id'], miniseed_tab.c['station_id'],
                   miniseed_tab.c['location_id'], miniseed_tab.c['channel_id']]
        query = sql.select(columns)
        for col in ['network_id', 'station_id', 'location_id', 'channel_id']:
            text = request.args0.get(col, None)
            if not text:
                continue
            if '*' in text or '?' in text:
                text = text.replace('?', '_')
                text = text.replace('*', '%')
                query = query.where(miniseed_tab.c[col].like(text))
            else:
                query = query.where(miniseed_tab.c[col] == text)
        query = query.where(miniseed_tab.c['end_datetime'] > start.datetime)
        query = query.where(miniseed_tab.c['start_datetime'] < end.datetime)
        # execute query
        try:
            results = request.env.db.query(query).fetchall()
        except:
            results = []
        # get from local waveform archive
        file_dict = {}
        for result in results:
            fname = result[0] + os.sep + result[1]
            key = '%s.%s.%s.%s' % (result[2], result[3], result[4], result[5])
            file_dict.setdefault(key, []).append(fname)
        # return as xml resource
        xml = Element("query")
        for _i in file_dict.keys():
             s = Sub(xml, "channel", id=_i)
             for _j in file_dict[_i]:
	         t = Sub(s, "file")
	         t.text = _j
        return toString(xml)

class WaveformCutterMapper(Component):
    """
    """
    implements(IMapper)

    mapping_url = '/seismology/waveform/getWaveform'

    def process_GET(self, request):
        # process parameters
        try:
            start = request.args0.get('start_datetime')
            start = UTCDateTime(start)
        except:
            start = UTCDateTime() - 60 * 20
        try:
            end = request.args0.get('end_datetime')
            end = UTCDateTime(end)
        except:
            # 10 minutes
            end = UTCDateTime()
        # limit time span to maximal 6 hours
        if end - start > 60 * 60 * 6:
            end = start + 60 * 60 * 6
        # build up query
        columns = [miniseed_tab.c['path'], miniseed_tab.c['file'],
                   miniseed_tab.c['network_id'], miniseed_tab.c['station_id'],
                   miniseed_tab.c['location_id'], miniseed_tab.c['channel_id']]
        query = sql.select(columns)
        for col in ['network_id', 'station_id', 'location_id', 'channel_id']:
            text = request.args0.get(col, None)
            if not text:
                continue
            if '*' in text or '?' in text:
                text = text.replace('?', '_')
                text = text.replace('*', '%')
                query = query.where(miniseed_tab.c[col].like(text))
            else:
                query = query.where(miniseed_tab.c[col] == text)
        query = query.where(miniseed_tab.c['end_datetime'] > start.datetime)
        query = query.where(miniseed_tab.c['start_datetime'] < end.datetime)
        # execute query
        try:
            results = request.env.db.query(query).fetchall()
        except:
            results = []
        # check for results
        if len(results) == 0:
            # ok lets use arclink
            return self._fetchFromArclink(request, start, end)
        # get from local waveform archive
        ms = libmseed()
        file_dict = {}
        for result in results:
            fname = result[0] + os.sep + result[1]
            key = '%s.%s.%s.%s' % (result[2], result[3], result[4], result[5])
            file_dict.setdefault(key, []).append(fname)
        data = ''
        for id in file_dict.keys():
            data += ms.mergeAndCutMSFiles(file_dict[id], start, end)
        # generate correct header
        request.setHeader('content-type', 'binary/octet-stream')
        # disable content encoding like packing!
        request.received_headers["accept-encoding"] = ""
        return data

    def _fetchFromArclink(self, request, start, end):
        """
        """
        try:
            from obspy.arclink.client import Client
        except:
            return ''
        c = Client()
        # parameters
        nid = request.args0.get('network_id')
        sid = request.args0.get('station_id')
        lid = request.args0.get('location_id', '')
        cid = request.args0.get('channel_id', '*')
        try:
            st = c.getWaveform(nid, sid, lid, cid, start, end)
        except Exception, e:
            raise InternalServerError(e)
        # merge + cut
        #st.merge()
        st.trim(start, end)
        # write to arclink directory for request
        rpath = os.path.join(self.env.getSeisHubPath(), 'data', 'arclink')
        rfile = os.path.join(rpath, 'request%d' % UTCDateTime().timestamp)
        # XXX: args have to create temp files .... issue with obspy.mseed, or
        # actually issue with ctypes not accepting StringIO as filehandler ...
        st.write(rfile, format='MSEED')
        # write to arclink directory
        for tr in st:
            # network directory
            path = os.path.join(rpath, tr.stats.network)
            self._checkPath(path)
            # station directory
            path = os.path.join(path, tr.stats.station)
            self._checkPath(path)
            # channel directory
            path = os.path.join(path, tr.stats.channel)
            self._checkPath(path)
            file = tr.getId() + '.%d.%d.mseed' % (tr.stats.starttime.timestamp,
                                                  tr.stats.endtime.timestamp)
            tr.write(os.path.join(path, file), format='MSEED')
        # generate correct header
        request.setHeader('content-type', 'binary/octet-stream')
        # disable content encoding like packing!
        request.received_headers["accept-encoding"] = ""
        # XXX: again very ugly as not StringIO can be used ...
        fh = open(rfile, 'rb')
        data = fh.read()
        fh.close()
        os.remove(rfile)
        return data

    def _checkPath(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)
