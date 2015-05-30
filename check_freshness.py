#!/usr/bin/python
# -*- coding: utf-8 -*-
########################################################################
# Date : May 28th, 2015
# Author  : Marc Schwöbel ( mcschwoebel at gmail.com )
# Licence : GPL 2 - http://www.gnu.org/licenses/gpl-2.0.txt
# TODO : Code optimizing, Testing, Feature Adding
# Changelog:
# 0.1    -  Initial Version
# 0.2    -  Fix PerfData Output
########################################################################

__version__ = '0.2'

import MySQLdb as mdb
import sys
import argparse

class ArgumentParserError(Exception): pass

class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

parser = ThrowingArgumentParser()
parser.description = "Check freshness of Icinga2 Service checks"
parser.add_argument("-H", "--Hostname", action="store", dest="Hostname", help="MySQL Server (ip or hostname)", required=True)
parser.add_argument("-d", "--database", action="store", dest="database", default="icinga", help="Icinga2 MySQL databasename [default: %(default)s]")
parser.add_argument("-u", "--user", action="store", dest="user", help="MySQL Login username", required=True)
parser.add_argument("-p", "--password", action="store", dest="password", help="MySQL Login password", required=True)    
parser.add_argument("-w", "--warning", action="store", dest="warn_threshold", help="Warning threshold! Count of Jobs when Warning State is issued. [default: %(default)s]", default="1")
parser.add_argument("-c", "--critical", action="store", dest="crit_threshold", help="Critical threshold! Count of Jobs when Warning Critical is issued. [default: %(default)s]", default="1")
parser.add_argument("-wp", "--warningpuffer", action="store", dest="warn_puffer", help="Warning puffer in percentage (30%%) or minutes (2). Base for warning is the check interval plus puffer [default: %(default)s]", default="30%")
parser.add_argument("-cp", "--criticalpuffer", action="store", dest="crit_puffer", help="Critical puffer in percentage (50%%) or minutes (5). Base for critical is the check interval plus puffer  [default: %(default)s]", default="50%")
parser.add_argument("-V", "--Version", action="version", version="%(prog)s {version}".format(version=__version__), help="Displays the current Version of this Script")
parser.add_argument("-v", "--verbose", action="store_true", help="Returns additional information - Hostnames of rotten Services")
parser.add_argument("-vv", "--vverbose", action="store_true", help="Returns additional information - Hostnames and Servicenames of rotten Services")
parser.add_argument("--allhosts", action="store_true", help="If set all hosts are checked, if not set only reachable hosts are checked")
parser.add_argument("--allservices", action="store_true", help="If set all services are checked for their freshness, if not set only services with active checks enabled are checked")
try:
    arguments = parser.parse_args()
except ArgumentParserError, exc:
    print "UNKNOWN: " + exc.message
    sys.exit(3)

if arguments.warn_puffer.endswith("%"):
    wm = "PC"
else:
    wm = "PP"

allhosts = "1"
if arguments.allhosts:
    allhosts = "NULL"

allservices = "1"
if arguments.allservices:
    allservices = "NULL"

if arguments.crit_puffer.endswith("%"):
    cm = "PC"
else:
    cm = "PP"

warnpuffer = arguments.warn_puffer.replace("%", "")
critpuffer = arguments.crit_puffer.replace("%", "")

query = """Select SR.host_object_id,
           SR.host_alias,
           SR.service_object_id,
           SR.service_display_name,
           SR.service_last_check,
           SR.check_interval,
           SR.retry_interval,
           SR.max_check_attempts,
           SR.retry_check_interval,
           SR.max_warn_freshness_time,
           SR.max_crit_freshness_time,
           CASE WHEN max_crit_freshness_time < now() THEN
                'CRITICAL'
                WHEN max_warn_freshness_time < now() THEN
                'WARNING'
           ELSE
                NULL
           END AS State
            FROM
            (SELECT 
            ICS.host_object_id,
            IH.alias AS host_alias,
            ICS.service_object_id,
            ICS.display_name AS service_display_name,
            ISS.last_check AS service_last_check,
            ICS.check_interval,
            ICS.retry_interval,
            ICS.max_check_attempts,
            ISS.retry_check_interval,
            CASE WHEN '""" + wm + """'='PP' THEN
                ISS.last_check + INTERVAL (ICS.check_interval + """ + warnpuffer + """) MINUTE 
            ELSE
                 ISS.last_check  + INTERVAL ((ICS.check_interval*60) + (ICS.check_interval/100.0*""" + warnpuffer + """)*60) second
            END AS max_warn_freshness_time,
            CASE WHEN '""" + cm + """'='PP' THEN
                ISS.last_check + INTERVAL (ICS.check_interval + """ + critpuffer + """) MINUTE 
            ELSE
                 ISS.last_check  + INTERVAL ((ICS.check_interval*60) + (ICS.check_interval/100.0*""" + critpuffer + """)*60) second
            END AS max_crit_freshness_time
        FROM
            icinga_services ICS
                INNER JOIN
            icinga_objects IO ON IO.object_id = ICS.service_object_id
                INNER JOIN
            icinga_servicestatus ISS ON ISS.service_object_id = ICS.service_object_id
                INNER JOIN
            (SELECT 
                SIH.display_name, SIH.alias, SIH.host_object_id
            FROM
                icinga_hosts SIH
            INNER JOIN icinga_hoststatus IHS ON IHS.host_object_id = SIH.host_object_id
            INNER JOIN icinga_objects SIO ON SIO.object_id = SIH.host_object_id
            WHERE
                SIO.is_active = 1
                AND IHS.is_reachable = IFNULL(""" + allhosts + """,IHS.is_reachable)) IH ON IH.host_object_id = ICS.host_object_id
        WHERE
            IO.is_active = 1
            AND ICS.active_checks_enabled = IFNULL(""" + allservices + """,ICS.active_checks_enabled)) SR
        WHERE SR.max_warn_freshness_time < now() OR
              SR.max_crit_freshness_time < now()
        order by State, host_alias, service_display_name
        """

def run():
    con = mdb.connect(arguments.Hostname, arguments.user, arguments.password, arguments.database)
    cur = con.cursor(mdb.cursors.DictCursor)
   
    try: 
        cur.execute(query)
        results = cur.fetchall()

        warningResults = filter(lambda x: "WARNING" in x["State"], results)
        criticalResults = filter(lambda x: "CRITICAL" in x["State"], results) 
        
        criCount = len(criticalResults)
        warnCount = len(warningResults)
        perfdataC = " | criticalstate=" + str(criCount) + ";" + str(arguments.warn_threshold) + ";" + str(arguments.crit_threshold)
        perfdataW = " warningstate=" + str(warnCount) + ";" + str(arguments.warn_threshold) + ";" + str(arguments.crit_threshold)
        longoutput = ""
        
        if arguments.verbose:
            hosts = sorted(set(map(lambda x: x["host_alias"], results)))
            hostString = "\n".join([str(x) for x in hosts])
            if hostString:
                longoutput = "\nHosts with rotten Services:\n" + hostString + "|"
        elif arguments.vverbose:
            services = [str(x["host_alias"]) + ": " + str(x["service_display_name"]) + " - " + str(x["State"]) + ": " + str(x["service_last_check"])  for x in results]
            servicesString = "\n".join([str(x) for x in services])
            longoutput = "\nDetailed information about rotten Services:\n" + servicesString + "|"
        
        if criCount >= int(arguments.crit_threshold) or warnCount >= int(arguments.crit_threshold):
            print "Services CRITICAL - Count rotten Services: " + str((criCount + warnCount)) + perfdataC + longoutput + perfdataW
            sys.exit(2)
        elif warnCount >= int(arguments.warn_threshold) or criCount >= int(arguments.warn_threshold):
            print "Services WARNING - Count half-rotten Services: " + str((criCount + warnCount)) + perfdataC + longoutput + perfdataW
            sys.exit(1)
        else:
            print "Services OK - No rotten Services" + str(criCount) + perfdataC + longoutput + perfdataW
            sys.exit(0)
    except mdb.Error, e:
        print "Unknown: %d: %s" % (e.args[0], e.args[1])
        sys.exit(3)
    
    finally:
        
        if con:
            con.close()

if __name__ == '__main__':
    run()
