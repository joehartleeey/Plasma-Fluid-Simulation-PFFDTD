from skyfield.api import load

max_days = 7.0         # download again once 7 days old
name = 'inputs/orbits/iss.json'

base = 'https://celestrak.org/NORAD/elements/gp.php'
url = base + '?CATNR=25544&FORMAT=json-pretty'

if not load.exists(name) or load.days_old(name) >= max_days:
    load.download(url, filename=name)