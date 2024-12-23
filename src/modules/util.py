# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import asyncio
from typing import Optional
import aiorpcx

class InvalidPassword(Exception):
    def __init__(self, message: Optional[str] = None):
        self.message = message

    def __str__(self):
        if self.message is None:
            return "Incorrect password"
        else:
            return str(self.message)

def to_bytes(something, encoding='utf8') -> bytes:
    """
    cast string to bytes() like object, but for python2 support it's bytearray copy
    """
    if isinstance(something, bytes):
        return something
    if isinstance(something, str):
        return something.encode(encoding)
    elif isinstance(something, bytearray):
        return bytes(something)
    else:
        raise TypeError("Not a string or bytes like object")

def to_string(x, enc) -> str:
    if isinstance(x, (bytes, bytearray)):
        return x.decode(enc)
    if isinstance(x, str):
        return x
    else:
        raise TypeError("Not a string or bytes like object")

def assert_bytes(*args):
    """
    porting helper, assert args type
    """
    try:
        for x in args:
            assert isinstance(x, (bytes, bytearray))
    except Exception:
        print('assert bytes failed', list(map(type, args)))
        raise

class WalletFileException(Exception):
    def __init__(self, message='', *, should_report_crash: bool = False):
        Exception.__init__(self, message)
        self.should_report_crash = should_report_crash

def versiontuple(v):
    return tuple(map(int, (v.split("."))))

class ESocksProxy(aiorpcx.SOCKSProxy):
    # note: proxy will not leak DNS as create_connection()
    # sets (local DNS) resolve=False by default

    async def open_connection(self, host=None, port=None, **kwargs):
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(loop=loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
        transport, _ = await self.create_connection(
            lambda: protocol, host, port, **kwargs)
        writer = asyncio.StreamWriter(transport, protocol, reader, loop)
        return reader, writer

    @classmethod
    def from_network_settings(cls, network: Optional['Network']) -> Optional['ESocksProxy']:
        if not network or not network.proxy:
            return None
        proxy = network.proxy
        username, pw = proxy.get('user'), proxy.get('password')
        if not username or not pw:
            # is_proxy_tor is tri-state; None indicates it is still probing the proxy to test for TOR
            if network.is_proxy_tor:
                auth = aiorpcx.socks.SOCKSRandomAuth()
            else:
                auth = None
        else:
            auth = aiorpcx.socks.SOCKSUserAuth(username, pw)
        addr = aiorpcx.NetAddress(proxy['host'], proxy['port'])
        if proxy['mode'] == "socks4":
            ret = cls(addr, aiorpcx.socks.SOCKS4a, auth)
        elif proxy['mode'] == "socks5":
            ret = cls(addr, aiorpcx.socks.SOCKS5, auth)
        else:
            raise NotImplementedError  # http proxy not available with aiorpcx
        return ret

