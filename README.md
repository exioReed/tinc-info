# tinc-info

Toolchain to send commands and requests to tincd's control socket and parse
information retrieved from it in python.

Please note: I started this project to learn python in the first place.

## Install
```
$ git clone https://github.com/exioReed/tinc-info.git
$ cd tinc-info
$ pip install .
```
or
```
$ python setup.py
```

## Example
Lets assume that $NETNAME is the netname of your tinc VPN.

```python
from tinctools import connection, parse

# fetch
tincctl = connection.Control('$NETNAME')
tincctl.connect()
tincctl.authenticate()
meta_conn_data = tincctl.communicate(connection.Request.DUMP_CONNECTIONS)

# parse
tincinfo = parse.TincInfo()
tincinfo.parse_connections(data=meta_conn_data)

for mc in tincinfo.connections:
    print('meta connection with {}'.format(mc['node']))
```
