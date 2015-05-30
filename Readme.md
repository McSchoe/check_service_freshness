# check_freshness

before i start with the plugin description... this was my first python script (my world was windows until few days ago) :-)  Iam open and thankful for any feedback. 
Ive tested few scenarios on my Server but i didnt create any tests for it. Please let me know if you find a bug. 

check_freshness is an Icinga2 Plugin to check if all service checks are running. 
> Requires Icingaweb2 with mysql DB as Backend

Main problem is if Host is running but the Icinga2 client is not running (Windows and Linux machines) Icinga2 will display the last check results which are probably green... but if you check the "last check" time on one Service you will see that it was not executed for a long time (as long the service is not running)

This plugin checks all Services if they are executed in their defined interval plus a defined puffer.

```
usage: check_freshness.py [-h] -H HOSTNAME [-d DATABASE] -u USER -p PASSWORD
                          [-w WARN_THRESHOLD] [-c CRIT_THRESHOLD]
                          [-wp WARN_PUFFER] [-cp CRIT_PUFFER] [-V] [-v] [-vv]
                          [--allhosts] [--allservices]
                          
-h, --help            show this help message and exit
  -H HOSTNAME, --Hostname HOSTNAME
                        MySQL Server (ip or hostname)
  -d DATABASE, --database DATABASE
                        Icinga2 MySQL databasename [default: icinga]
  -u USER, --user USER  MySQL Login username
  -p PASSWORD, --password PASSWORD
                        MySQL Login password
  -w WARN_THRESHOLD, --warning WARN_THRESHOLD
                        Warning threshold! Count of Jobs when Warning State is
                        issued. [default: 1]
  -c CRIT_THRESHOLD, --critical CRIT_THRESHOLD
                        Critical threshold! Count of Jobs when Warning
                        Critical is issued. [default: 1]
  -wp WARN_PUFFER, --warningpuffer WARN_PUFFER
                        Warning puffer in percentage (30%) or minutes (2).
                        Base for warning is the check interval plus puffer
                        [default: 30%]
  -cp CRIT_PUFFER, --criticalpuffer CRIT_PUFFER
                        Critical puffer in percentage (50%) or minutes (5).
                        Base for critical is the check interval plus puffer
                        [default: 50%]
  -V, --Version         Displays the current Version of this Script
  -v, --verbose         Returns additional information - Hostnames of rotten
                        Services
  -vv, --vverbose       Returns additional information - Hostnames and
                        Servicenames of rotten Services
  --allhosts            If set all hosts are checked, if not set only
                        reachable hosts are checked
  --allservices         If set all services are checked for their freshness,
                        if not set only services with active checks enabled
                        are checked
```
##Example

* Service load - check interval = 2 minutes
* WARN_PUFFER = 25%
* CRIT_PUFFER = 50%

> if the last check was executed 2 minutes and 30 seconds ago it will return as **warningstate** (check interval + (2/100*25))

> if the last check was executed 3 minutes ago it will return as **criticalstate** (check interval + (2/100*50))

##Installation

Download the check_freshness.py Script and definde the command and Service for it on the Icinga2 Server.
###command.conf###
```
object CheckCommand "freshness" {
    import "plugin-check-command"
    command = [
                PluginDir + "/check_freshness.py"
        ]

    arguments = {
                "-H" = "$f_mysqlserver$"
                "-d" = "$f_icingadatabase$"
                "-u" = "$f_mysqluser$"
                "-p" = "$f_mysqlpassword$"
                "-w" = "$f_warnth$"
                "-c" = "$f_critth$"
                "-wp" = "$f_warnpuffer$"
                "-cp" = "$f_critpuffer$"
                "-v" =  {
                         set_if = "$f_verbose$"
                        }
                "-vv" =  {
                         set_if = "$f_vverbose$"
                        }
        }
    vars.f_mysqlserver = "localhost"
    vars.f_warnpuffer = "30%"
    vars.f_critpuffer = "50%"
    vars.f_warnth = "1"
    vars.f_critth = "1"
}

```
###service.conf###
```
apply Service "CheckRottenServices" {
  import "generic-service"
  check_command = "freshness"
  display_name = "Rotten Services"

  vars.f_icingadatabase = "icinga"
  vars.f_mysqluser = "testuser"
  vars.f_mysqlpassword = "testpass"
  vars.f_verbose = "1"
  assign  where host.name == "ICINGASERVER"
}

```

>Licence : GPL 2 - http://www.gnu.org/licenses/gpl-2.0.txt

