"""Offers a simple XML-RPC dispatcher for django_xmlrpc

Author::
    Graham Binns

Credit must go to Brendan W. McAdams <brendan.mcadams@thewintergrp.com>, who
posted the original SimpleXMLRPCDispatcher to the Django wiki:
http://code.djangoproject.com/wiki/XML-RPC

New BSD License
===============
Copyright (c) 2007, Graham Binns http://launchpad.net/~codedragon

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the <ORGANIZATION> nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from inspect import getargspec

import sys

try:
    from xmlrpc.server import SimpleXMLRPCDispatcher, resolve_dotted_attribute
    from xmlrpc.client import loads, dumps, Fault
except ImportError:  # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCDispatcher, resolve_dotted_attribute
    from xmlrpclib import loads, dumps, Fault


class DjangoXMLRPCDispatcher(SimpleXMLRPCDispatcher):
    """A simple XML-RPC dispatcher for Django.

    Subclassess SimpleXMLRPCServer.SimpleXMLRPCDispatcher for the purpose of
    overriding certain built-in methods (it's nicer than monkey-patching them,
    that's for sure).
    """

    def system_methodSignature(self, method):
        """Returns the signature details for a specified method

        method
            The name of the XML-RPC method to get the details for
        """
        # See if we can find the method in our funcs dict
        # TODO: Handle this better: We really should return something more
        # formal than an AttributeError
        func = self.funcs[method]

        try:
            sig = func._xmlrpc_signature
        except:
            sig = {
                'returns': 'string',
                'args': ['string' for arg in getargspec(func)[0]],
            }

        return [sig['returns']] + sig['args']

    def _marshaled_dispatch(self, data, dispatch_method=None, path=None, request=None):
        """Dispatches an XML-RPC method from marshalled (XML) data.

        XML-RPC methods are dispatched from the marshalled (XML) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        SimpleXMLRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the preferred means
        of changing method dispatch behavior.

        copy from /usr/lib/python2.7/SimpleXMLRPCServer.py to support
        django request
        """

        try:
            params, method = loads(data)

            # generate response
            if dispatch_method is not None:
                response = dispatch_method(method, params, request)
            else:
                response = self._dispatch(method, params, request)
            # wrap response in a singleton tuple
            response = (response,)
            response = dumps(response, methodresponse=1,
                             allow_none=self.allow_none, encoding=self.encoding)
        except Fault as fault:
            response = dumps(fault, allow_none=self.allow_none,
                             encoding=self.encoding)
        except:
            # report exception back to server
            exc_type, exc_value, exc_tb = sys.exc_info()
            response = dumps(
                Fault(1, "%s:%s" % (exc_type, exc_value)),
                encoding=self.encoding, allow_none=self.allow_none,
            )

        return response

    def _dispatch(self, method, params, request=None):
        """Dispatches the XML-RPC method.

        XML-RPC calls are forwarded to a registered function that
        matches the called XML-RPC method name. If no such function
        exists then the call is forwarded to the registered instance,
        if available.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the XML-RPC method and
        its parameters as a tuple
        e.g. instance._dispatch('add',(2,3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called.

        Methods beginning with an '_' are considered private and will
        not be called.

        copy from /usr/lib/python2.7/SimpleXMLRPCServer.py to support
        django request
        """

        func = None
        try:
            # check to see if a matching function has been registered
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                # check for a _dispatch method
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    # call instance method directly
                    try:
                        func = resolve_dotted_attribute(
                            self.instance,
                            method,
                            self.allow_dotted_names
                        )
                    except AttributeError:
                        pass

        if func is not None:
            try:
                return func(request, *params)
            except TypeError:
                # try without request
                return func(*params)
        else:
            raise Exception('method "%s" is not supported' % method)


xmlrpc_dispatcher = DjangoXMLRPCDispatcher(allow_none=False, encoding=None)
