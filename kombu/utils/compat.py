import sys

############## __builtin__.all ##############################################

try:
    all([True])
    all = all
except NameError:
    def all(iterable):  # noqa
        for item in iterable:
            if not item:
                return False
        return True

############## __builtin__.any ##############################################

try:
    any([True])
    any = any
except NameError:
    def any(iterable):  # noqa
        for item in iterable:
            if item:
                return True
        return False

############## collections.OrderedDict #######################################

import weakref
try:
    from collections import MutableMapping
except ImportError:
    from UserDict import DictMixin as MutableMapping  # noqa
from itertools import imap as _imap
from operator import eq as _eq


class _Link(object):
    """Doubly linked list."""
    __slots__ = 'prev', 'next', 'key', '__weakref__'


class CompatOrderedDict(dict, MutableMapping):
    """Dictionary that remembers insertion order"""
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular
    # dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly
    # linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # The prev/next links are weakref proxies (to prevent circular
    # references).
    # Individual links are kept alive by the hard reference in self.__map.
    # Those hard references disappear when a key is deleted from
    # an OrderedDict.

    __marker = object()

    def __init__(self, *args, **kwds):
        """Initialize an ordered dictionary.

        Signature is the same as for regular dictionaries, but keyword
        arguments are not recommended because their insertion order is
        arbitrary.

        """
        if len(args) > 1:
            raise TypeError("expected at most 1 arguments, got %d" % (
                                len(args)))
        try:
            self.__root
        except AttributeError:
            # sentinel node for the doubly linked list
            self.__root = root = _Link()
            root.prev = root.next = root
            self.__map = {}
        self.update(*args, **kwds)

    def clear(self):
        "od.clear() -> None.  Remove all items from od."
        root = self.__root
        root.prev = root.next = root
        self.__map.clear()
        dict.clear(self)

    def __setitem__(self, key, value):
        "od.__setitem__(i, y) <==> od[i]=y"
        # Setting a new item creates a new link which goes at the end of the
        # linked list, and the inherited dictionary is updated with the new
        # key/value pair.
        if key not in self:
            self.__map[key] = link = _Link()
            root = self.__root
            last = root.prev
            link.prev, link.next, link.key = last, root, key
            last.next = root.prev = weakref.proxy(link)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        """od.__delitem__(y) <==> del od[y]"""
        # Deleting an existing item uses self.__map to find the
        # link which is then removed by updating the links in the
        # predecessor and successor nodes.
        dict.__delitem__(self, key)
        link = self.__map.pop(key)
        link.prev.next = link.next
        link.next.prev = link.prev

    def __iter__(self):
        """od.__iter__() <==> iter(od)"""
        # Traverse the linked list in order.
        root = self.__root
        curr = root.next
        while curr is not root:
            yield curr.key
            curr = curr.next

    def __reversed__(self):
        """od.__reversed__() <==> reversed(od)"""
        # Traverse the linked list in reverse order.
        root = self.__root
        curr = root.prev
        while curr is not root:
            yield curr.key
            curr = curr.prev

    def __reduce__(self):
        """Return state information for pickling"""
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__root
        del(self.__map, self.__root)
        inst_dict = vars(self).copy()
        self.__map, self.__root = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def update(self, other=(), **kwds):
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, "keys"):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    def pop(self, key, default=__marker):
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def values(self):
        return [self[key] for key in self]

    def items(self):
        return [(key, self[key]) for key in self]

    def itervalues(self):
        for key in self:
            yield self[key]

    def iteritems(self):
        for key in self:
            yield (key, self[key])

    def iterkeys(self):
        return iter(self)

    def keys(self):
        return list(self)

    def popitem(self, last=True):
        """od.popitem() -> (k, v)

        Return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO
        order if false.

        """
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            if sys.platform.startswith("java"):
                key = self.keys()[-1]
            else:
                key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __repr__(self):
        "od.__repr__() <==> repr(od)"
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        "od.copy() -> a shallow copy of od"
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        """OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None)."""
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        """od.__eq__(y) <==> od==y.  Comparison to another OD is
        order-sensitive while comparison to a regular mapping
        is order-insensitive."""
        if isinstance(other, OrderedDict):
            return len(self) == len(other) and \
                   all(_imap(_eq, self.iteritems(), other.iteritems()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = CompatOrderedDict  # noqa

############## queue.LifoQueue ##############################################
from Queue import Queue


class LifoQueue(Queue):

    def _init(self, maxsize):
        self.queue = []
        self.maxsize = maxsize

    def _qsize(self, len=len):
        return len(self.queue)

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()
