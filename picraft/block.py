# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# An alternate Python Minecraft library for the Rasperry-Pi
# Copyright (c) 2013-2016 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
The block module defines the :class:`Block` class, which is used to represent
the type of a block and any associated data it may have, and the class which is
used to implement the :attr:`~picraft.world.World.blocks` attribute on the
:class:`~picraft.world.World` class.

.. note::

    All items in this module, except the compatibility constants, are available
    from the :mod:`picraft` namespace without having to import
    :mod:`picraft.block` directly.

The following items are defined in the module:

Block
=====

.. autoclass:: Block(id, data)


Compatibility
=============

Finally, the module also contains compatibility values equivalent to those
in the mcpi.block module of the reference implementation. Each value represents
the type of a block with no associated data:

===================  ====================  =====================
AIR                  FURNACE_ACTIVE        MUSHROOM_RED
BED                  FURNACE_INACTIVE      NETHER_REACTOR_CORE
BEDROCK              GLASS                 OBSIDIAN
BEDROCK_INVISIBLE    GLASS_PANE            REDSTONE_ORE
BOOKSHELF            GLOWING_OBSIDIAN      SAND
BRICK_BLOCK          GLOWSTONE_BLOCK       SANDSTONE
CACTUS               GOLD_BLOCK            SAPLING
CHEST                GOLD_ORE              SNOW
CLAY                 GRASS                 SNOW_BLOCK
COAL_ORE             GRASS_TALL            STAIRS_COBBLESTONE
COBBLESTONE          GRAVEL                STAIRS_WOOD
COBWEB               ICE                   STONE
CRAFTING_TABLE       IRON_BLOCK            STONE_BRICK
DIAMOND_BLOCK        IRON_ORE              STONE_SLAB
DIAMOND_ORE          LADDER                STONE_SLAB_DOUBLE
DIRT                 LAPIS_LAZULI_BLOCK    SUGAR_CANE
DOOR_IRON            LAPIS_LAZULI_ORE      TNT
DOOR_WOOD            LAVA                  TORCH
FARMLAND             LAVA_FLOWING          WATER
FENCE                LAVA_STATIONARY       WATER_FLOWING
FENCE_GATE           LEAVES                WATER_STATIONARY
FIRE                 MELON                 WOOD
FLOWER_CYAN          MOSS_STONE            WOOD_PLANKS
FLOWER_YELLOW        MUSHROOM_BROWN        WOOL
===================  ====================  =====================

Use these compatibility constants by importing the block module explicitly.
For example::

    >>> from picraft import block
    >>> block.AIR
    <Block "air" id=0 data=0>
    >>> block.TNT
    <Block "tnt" id=46 data=0>
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
)

try:
    from itertools import izip as zip
except ImportError:
    pass
str = type('')

import io
import warnings
from math import sqrt
from collections import namedtuple
from itertools import cycle

from pkg_resources import resource_stream
from .exc import EmptySliceWarning
from .vector import Vector, vector_range
from .entity import Entity

import re
from random import choice
from .blockdata import *


def _read_block_data(filename_or_object):
    if isinstance(filename_or_object, str):
        stream = io.open(filename_or_object, 'rb')
    else:
        stream = filename_or_object
    for line in stream:
        line = line.decode('utf-8').strip()
        if line and not line.startswith('#'):
            id, data, pi, pocket, name, description = line.split(None, 5)
            yield int(id), int(data), bool(int(pi)), bool(int(pocket)), name, description


def _read_block_color(filename_or_object):
    if isinstance(filename_or_object, str):
        stream = io.open(filename_or_object, 'rb')
    else:
        stream = filename_or_object
    int2color = lambda n: ((n & 0xff0000) >> 16, (n & 0xff00) >> 8, n & 0xff)
    for line in stream:
        line = line.decode('utf-8').strip()
        if line and not line.startswith('#'):
            id, data, color = line.split(None, 2)
            yield int(id), int(data), int2color(int(color, 16))


class Block(namedtuple('Block', ('id', 'data'))):
    """
    Represents a block within the Minecraft world.

    Blocks within the Minecraft world are represented by two values: an *id*
    which defines the type of the block (air, stone, grass, wool, etc.) and an
    optional *data* value (defaults to 0) which means different things for
    different block types (e.g.  for wool it defines the color of the wool).

    Blocks are represented by this library as a :func:`~collections.namedtuple`
    of the *id* and the *data*. Calculated properties are provided to look up
    the :attr:`name` and :attr:`description` of the block from a database
    derived from the Minecraft wiki, and classmethods are defined to construct
    a block definition from an :meth:`id <from_id>` or from alternate things
    like a :meth:`name <from_name>` or an :meth:`RGB color <from_color>`::

        >>> Block.from_id(0, 0)
        <Block "air" id=0 data=0>
        >>> Block.from_id(2, 0)
        <Block "grass" id=2 data=0>
        >>> Block.from_name('stone')
        <Block "stone" id=1 data=0>
        >>> Block.from_color('#ffffff')
        <Block "wool" id=35 data=0>

    The default constructor attempts to guess which classmethod to call based
    on the following rules (in the order given):

    1. If the constructor is passed a string beginning with '#' that is 7
       characters long, it calls :meth:`from_color`

    2. If the constructor is passed a tuple containing 3 values, it calls
       :meth:`from_color`

    3. If the constructor is passed a string (not matching the case above)
       it calls :meth:`from_name`

    4. Otherwise the constructor calls :meth:`from_id` with all given
       parameters

    This means that the examples above can be more easily written::

        >>> Block(0, 0)
        <Block "air" id=0 data=0>
        >>> Block(2, 0)
        <Block "grass" id=2 data=0>
        >>> Block('stone')
        <Block "stone" id=1 data=0>
        >>> Block('#ffffff')
        <Block "wool" id=35 data=0>

    Aliases are provided for compatibility with the official reference
    implementation (AIR, GRASS, STONE, etc)::

        >>> import picraft.block
        >>> picraft.block.WATER
        <Block "flowing_water" id=8 data=0>

    .. automethod:: from_color

    .. automethod:: from_id

    .. automethod:: from_name

    .. attribute:: id

        The "id" or type of the block. Each block type in Minecraft has a
        unique value. For example, air blocks have the id 0, stone, has id 1,
        and so forth. Generally it is clearer in code to refer to a block's
        :attr:`name` but it may be quicker to use the id.

    .. attribute:: data

        Certain types of blocks have variants which are dictated by the data
        value associated with them. For example, the color of a wool block
        is determined by the *data* attribute (e.g. white is 0, red is 14,
        and so on).

    .. autoattribute:: pi

    .. autoattribute:: pocket

    .. autoattribute:: name

    .. autoattribute:: description

    .. attribute:: COLORS

        A class attribute containing a sequence of the colors available for
        use with :meth:`from_color`.

    .. attribute:: NAMES

        A class attribute containing a sequence of the names available for
        use with :meth:`from_name`.
    """

    __slots__ = ()

    _BLOCKS_DB = {
        (id, data): (pi, pocket, name, description)
        for (id, data, pi, pocket, name, description) in
        _read_block_data(resource_stream(__name__, 'block.data'))
    }

    _BLOCKS_BY_ID = {
        id: (pi, pocket, name)
        for (id, data), (pi, pocket, name, description) in _BLOCKS_DB.items()
        if data == 0
    }

    _BLOCKS_BY_NAME = {
        name: id
        for (id, data), (pi, pocket, name, description) in _BLOCKS_DB.items()
        if data == 0
    }

    _BLOCKS_BY_COLOR = {
        color: (id, data)
        for (id, data, color) in
        _read_block_color(resource_stream(__name__, 'block.color'))
    }

    COLORS = _BLOCKS_BY_COLOR.keys()
    NAMES = _BLOCKS_BY_NAME.keys()

    def __new__(cls, *args, **kwargs):
        if len(args) >= 1:
            a = args[0]
            if isinstance(a, bytes):
                a = a.decode('utf-8')
            if isinstance(a, str) and len(a) == 7 and a.startswith('#'):
                return cls.from_color(*args, **kwargs)
            elif isinstance(a, tuple) and len(a) == 3:
                return cls.from_color(*args, **kwargs)
            elif isinstance(a, str):
                return cls.from_name(*args, **kwargs)
            else:
                return cls.from_id(*args, **kwargs)
        else:
            if 'id' in kwargs:
                return cls.from_id(**kwargs)
            elif 'name' in kwargs:
                return cls.from_name(**kwargs)
            elif 'color' in kwargs:
                return cls.from_color(**kwargs)
        raise TypeError('invalid combination of arguments for Block')

    @classmethod
    def from_string(cls, s):
        try:
            id_, data = s.split(',', 1)
        except AttributeError:
            print(f"Block.from_string failed. Was passed None. Air block returned.")
            id_, data = 0, 0
        return cls.from_id(int(id_), int(data))

    @classmethod
    def from_id(cls, id, data=0):
        """
        Construct a :class:`Block` instance from an *id* integer. This may be
        used to construct blocks in the classic manner; by specifying a number
        representing the block's type, and optionally a data value. For
        example::

            >>> from picraft import *
            >>> Block.from_id(1)
            <Block "stone" id=1 data=0>
            >>> Block.from_id(2, 0)
            <Block "grass" id=2 data=0>

        The optional *data* parameter defaults to 0. Note that calling the
        default constructor with an integer parameter is equivalent to calling
        this method::

            >>> Block(1)
            <Block "stone" id=1" data=0>
        """
        return super(Block, cls).__new__(cls, id, data)

    @classmethod
    def from_name(cls, name, data=0):
        """
        Construct a :class:`Block` instance from a *name*, as returned by the
        :attr:`name` property. This may be used to construct blocks in a more
        "friendly" way within code. For example::

            >>> from picraft import *
            >>> Block.from_name('stone')
            <Block "stone" id=1 data=0>
            >>> Block.from_name('wool', data=2)
            <Block "wool" id=35 data=2>

        The optional *data* parameter can be used to specify the data component
        of the new :class:`Block` instance; it defaults to 0. Note that calling
        the default constructor with a string that doesn't start with "#" is
        equivalent to calling this method::

            >>> Block('stone')
            <Block "stone" id=1 data=0>
        """
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        try:
            id_ = cls._BLOCKS_BY_NAME[name]
        except KeyError:
            raise ValueError('unknown name %s' % name)
        return cls(id_, data)

    @classmethod
    def from_color(cls, color, exact=False):
        """
        Construct a :class:`Block` instance from a *color* which can be
        represented as:

        * A tuple of ``(red, green, blue)`` integer byte values between 0 and
          255
        * A tuple of ``(red, green, blue)`` float values between 0.0 and 1.0
        * A string in the format '#rrggbb' where rr, gg, and bb are hexadecimal
          representations of byte values.

        If *exact* is ``False`` (the default), and an exact match for the
        requested color cannot be found, the nearest color (determined simply
        by Euclidian distance) is returned. If *exact* is ``True`` and an exact
        match cannot be found, a :exc:`ValueError` will be raised::

            >>> from picraft import *
            >>> Block.from_color('#ffffff')
            <Block "wool" id=35 data=0>
            >>> Block.from_color('#ffffff', exact=True)
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
              File "picraft/block.py", line 351, in from_color
                if exact:
            ValueError: no blocks match color #ffffff
            >>> Block.from_color((1, 0, 0))
            <Block "wool" id=35 data=14>

        Note that calling the default constructor with any of the formats
        accepted by this method is equivalent to calling this method::

            >>> Block('#ffffff')
            <Block "wool" id=35 data=0>
        """
        if isinstance(color, bytes):
            color = color.decode('utf-8')
        if isinstance(color, str):
            try:
                if not (color.startswith('#') and len(color) == 7):
                    raise ValueError()
                color = (
                    int(color[1:3], 16),
                    int(color[3:5], 16),
                    int(color[5:7], 16))
            except ValueError:
                raise ValueError('unrecognized color format: %s' % color)
        else:
            try:
                r, g, b = color
            except (TypeError, ValueError):
                raise ValueError('expected three values in color')
            if 0.0 <= r <= 1.0 and 0.0 <= g <= 1.0 and 0.0 <= b <= 1.0:
                color = tuple(int(n * 255) for n in color)
        try:
            id_, data = cls._BLOCKS_BY_COLOR[color]
        except KeyError:
            r, g, b = color
            if exact:
                raise ValueError(
                    'no blocks match color #%06x' % (r << 16 | g << 8 | b))
            diff = lambda block_color: sqrt(
                sum((c1 - c2) ** 2 for c1, c2 in zip(color, block_color)))
            matched_color = sorted(cls._BLOCKS_BY_COLOR, key=diff)[0]
            id_, data = cls._BLOCKS_BY_COLOR[matched_color]
        return cls(id_, data)

    def __repr__(self):
        try:
            return '<Block "%s" id=%d data=%d>' % (self.name, self.id, self.data)
        except KeyError:
            return '<Block id=%d data=%d>' % (self.id, self.data)

    @property
    def pi(self):
        """
        Returns a bool indicating whether the block is present in the Pi
        Edition of Minecraft.
        """
        return self._BLOCKS_BY_ID[self.id][0]

    @property
    def pocket(self):
        """
        Returns a bool indicating whether the block is present in the Pocket
        Edition of Minecraft.
        """
        return self._BLOCKS_BY_ID[self.id][1]

    @property
    def name(self):
        """
        Return the name of the block. This is a unique identifier string which
        can be used to construct a :class:`Block` instance with
        :meth:`from_name`.
        """
        return self._BLOCKS_BY_ID[self.id][2]

    @property
    def description(self):
        """
        Return a description of the block. This string is not guaranteed to be
        unique and is only intended for human use.
        """
        try:
            return self._BLOCKS_DB[(self.id, self.data)][3]
        except KeyError:
            return self._BLOCKS_DB[(self.id, 0)][3]


class Blocks(object):
    """
    This class implements the :attr:`~picraft.world.World.blocks` attribute.
    """

    def __init__(self, connection):
        self._connection = connection

    def __repr__(self):
        return '<Blocks>'

    def _get_blocks(self, vrange):
        return [
            # Block.from_string('%d,0' % int(i))
            Block2.from_string('%s' % i)
            for i in self._connection.transact(
                'world.getBlocks(%d,%d,%d,%d,%d,%d)' % (
                    vrange.start.x, vrange.start.y, vrange.start.z,
                    vrange.stop.x - vrange.step.x,
                    vrange.stop.y - vrange.step.y,
                    vrange.stop.z - vrange.step.z)
            ).split(',')
        ]

    def _get_block_loop(self, vrange):
        return [
            # Block.from_string(
            Block2.from_string(
                self._connection.transact(
                    'world.getBlockWithData(%d,%d,%d)' %
                    (v.x, v.y, v.z)))
            for v in vrange
        ]

    def __getitem__(self, index):
        if isinstance(index, slice):
            index = vector_range(index.start, index.stop, index.step)
        if isinstance(index, vector_range):
            vrange = index
            if not vrange:
                warnings.warn(EmptySliceWarning(
                    "ignoring empty slice passed to blocks"))
            elif (
                abs(vrange.step) == Vector(1, 1, 1) and
                vrange.order == 'zxy' and
                self._connection.server_version == 'raspberry-juice'):
                # Query for a simple unbroken range (getBlocks fast-path)
                # against a Raspberry Juice server
                return self._get_blocks(vrange)
            else:
                # Query for any other type of range (non-unit step, wrong
                # order, etc.)
                return self._get_block_loop(vrange)
        else:
            try:
                index.x, index.y, index.z
            except AttributeError:
                # Query for an arbitrary collection of vectors
                return self._get_block_loop(index)
            else:
                # Query for a single vector
                # return Block.from_string(
                return Block2.from_string(
                    self._connection.transact(
                        'world.getBlockWithData(%d,%d,%d)' %
                        (index.x, index.y, index.z)))

    def _set_blocks(self, vrange, block_or_entity):
        assert vrange.step == Vector(1, 1, 1)
        block_or_entity.set_blocks(self._connection, vrange.start, vrange.stop)

        # self._connection.send(
        #     'world.setBlocks(%d,%d,%d,%d,%d,%d,%d,%d)' % (
        #         vrange.start.x, vrange.start.y, vrange.start.z,
        #         vrange.stop.x - 1, vrange.stop.y - 1, vrange.stop.z - 1,
        #         block.id, block.data))

    def _set_block_loop(self, vrange, blocks_or_entities):
        for v, b in zip(vrange, blocks_or_entities):
            b.set_block(self._connection, v)
            # self._connection.send(
            #     'world.setBlock(%d,%d,%d,%d,%d)' % (
            #         v.x, v.y, v.z, b.id, b.data))

    def __setitem__(self, index, value):
        r = None
        if isinstance(index, slice):
            index = vector_range(index.start, index.stop, index.step)
        if isinstance(index, vector_range):
            vrange = index
            if not vrange:
                warnings.warn(EmptySliceWarning(
                    "ignoring empty slice passed to blocks"))
            else:
                try:
                    # Test for a single block
                    if isinstance(value, Block2):
                        value.block_name
                    elif isinstance(value, Entity):
                        value.type_id
                except AttributeError:
                    # Assume multiple blocks have been specified for the range
                    self._set_block_loop(vrange, value)
                else:
                    # We're dealing with a single block for a simple unbroken
                    # range (setBlocks fast-path)
                    if abs(vrange.step) == Vector(1, 1, 1):
                        r = self._set_blocks(vrange, value)
                    else:
                        r = self._set_block_loop(vrange, (value,) * len(vrange))
        else:
            try:
                # Test for a single block / entity
                if isinstance(value, Block2):
                    value.block_name
                elif isinstance(value, Entity):
                    value.type_id
                # value.id, value.data
            except AttributeError:
                # Assume multiple blocks have been specified with a collection
                # of vectors
                self._set_block_loop(index, value)
            else:
                try:
                    index.x, index.y, index.z
                except AttributeError:
                    # Assume a single block has been specified for a collection
                    # of vectors
                    self._set_block_loop(index, cycle((value,)))
                else:
                    # A single block for a single vector
                    r = value.set_block(self._connection, index)
                    # self._connection.send(
                    #     'world.setBlock(%d,%d,%d,%d,%d)' % (
                    #         index.x, index.y, index.z, value.id, value.block_name))
        return  r

class BlockDescriptor(object):
    signature = 'CraftBlockData'
    std_namespace = "minecraft"

    def __init__(self, block_descriptor):
        """
        Pattern needs to match two type of block descriptor. One where block data information is shared
        and one where no block data is present. Like

        CraftBlockData{minecraft:jungle_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]}
        and
        CraftBlockData{minecraft:air}

        :param block_descriptor:
        """
        self.pattern = '(' + self.signature + '\{(.+):(.+?)(\[.+\])?\})'
        self._block_descriptor = block_descriptor
        self._namespace = None
        self._block_name = None
        self._block_data = {}
        self.parse_from()

    @classmethod
    def from_string(cls, block_descriptor):
        return cls(block_descriptor)

    @classmethod
    def block_data_to_string(cls, block_name, block_data, brackets=True, delimter=",", namespace=None):
        namespace = cls.std_namespace if namespace is None else namespace
        r = []
        for k, v in block_data.items():
            r.append(f"{k}={v}")
        params = delimter.join(r)
        params = "[" + params + "]" if brackets else params
        namespace_component = f"{namespace}:" if namespace else namespace
        return f"{namespace_component}{block_name.lower()}{params}" if r else ""

    @classmethod
    def to_string(cls, block_name, block_data):
        return f"{cls.signature}" + "{" + f"{cls.std_namespace}:{block_name}" + f"{cls.block_data_to_string(block_name, block_data)}" + "}"

    @property
    def block_descriptor(self):
        return self._block_descriptor

    @block_descriptor.setter
    def block_descriptor(self, value):
        self._block_descriptor = value

    @property
    def namespace(self):
        return self._namespace

    @property
    def block_name(self):
        return self._block_name

    @property
    def block_data(self):
        return self._block_data

    def parse_from(self, block_desriptor=None):
        block_desriptor = block_desriptor if block_desriptor else self._block_descriptor
        match = re.search(self.pattern, block_desriptor)
        if not (match):
            raise ValueError("This block details were not returned in the expected format: %s" % block_desriptor)
        _, self._namespace, self._block_name, block_data_text = match.groups()
        if block_data_text:
            block_data_text = block_data_text.replace("[", "").replace("]", "")
            block_data_list = block_data_text.split(',')
        else:
            block_data_list = []
        for o in block_data_list:
            k, v = o.split('=')
            self.block_data[k] = v
        return (self._namespace, self._block_name, self.block_data)


class Block2Base(object):
    def __init__(self, block_name=None, block_data=None, validators=None, strict=True, **kwargs):
        self._block_name = block_name.upper() if block_name else block_name
        self._block_data = {} if block_data is None else block_data
        self._validators = {} if validators is None else validators
        self._strict = strict
        for k, v in kwargs.items():
            self._block_data[k] = v

    def add_validator(self, name, default_value, validator):
        name = name.lower()
        self._validators[name] = (default_value, validator)
        # If we got a default value for this block data name then set it
        if default_value:
            self._block_data[name] = default_value
        return self

    def set_block_data(self, name, value, override_strict=False):
        strict_mode = self._strict and not override_strict
        name = name.lower()
        valid_key = True
        if name not in self._validators.keys():
            print(f"block_data with an unknown key is being set: Block:{self._block_name}, key:{name}")
            valid_key = False
        if valid_key:
            # Validate here
            default_value, validator = self._validators[name]
            if not validator.valid_value(value) and self.strict:
                raise ValueError(
                    '%s is not a valid value for block data %s in Block %s. Valid values are: %s' %
                    (wrap_in_quote(value), wrap_in_quote(name), wrap_in_quote(self._block_name),
                     validator.formatted_valid_values())
                )
        self._block_data[name] = value
        return self

    def get_block_data_info(self, name, override_strict=False):
        """
        Return the meta information for block_data
        :param name: the name of the block data item
        :param override_strict: Whether we should raise errors for block data that is not found.
        :return: tuple of name, current value and validator for this block data item
        """
        strict_mode = self._strict and not override_strict
        name = name.lower()
        if (name not in self._validators.keys() or name not in self._block_data):
            # We haven't found the key
            if strict_mode:
                raise ValueError(
                    'The block data item %s is unknown in block: %s' % (wrap_in_quote(name), self._block_name)
                )
            else:
                print(f"Warning block_data value for {name} was not found in block {self._block_name}.")
                current_value = ""
                validator = None
        else:
            current_value = self._block_data[name]
            validator = self._validators[name][1]
        return name, current_value, validator

    def cycle_block_data(self, name):
        name, current_value, validator = self.get_block_data_info(name)
        new_value = validator.cycle_value(current_value)
        self.set_block_data(name, new_value)

    def random_block_data(self, name):
        name, current_value, validator = self.get_block_data_info(name)
        new_value = validator.random_value()
        self.set_block_data(name, new_value)

    def valid_values(self, name):
        name, current_value, validator = self.get_block_data_info(name)
        return list(validator.all_valid_values())

    def document(self, print_it=False):
        r = f"Valid block_data values for block: '{self._block_name}'...\n"
        if self._validators:
            for k, v in self._validators.items():
                default_value, validator = v
                r += f"{validator.document(k, default_value)}"
        if print_it:
            print(r)

    @property
    def strict(self):
        return self._strict

    @strict.setter
    def string(self, value):
        self._strict = value

    @classmethod
    def from_string(cls, block_desriptor):
        bd = BlockDescriptor(block_desriptor)
        new = cls(bd.block_name, bd.block_data)
        return new

    def to_string(self):
        # Re-write the block_descriptor
        return BlockDescriptor.to_string(self._block_name, self._block_data)

    def __repr__(self):
        return '<Block2Base %s>' % (self.block_name)

    def set_block(self, connection, vector):
        if self._block_data:
            cmd = 'world.setBlockWithBlocData(%d,%d,%d,%s,%s)' % (
                vector.x,
                vector.y,
                vector.z,
                self._block_name.upper(),
                BlockDescriptor.block_data_to_string(
                    self._block_name,
                    self._block_data,
                    brackets=True,
                    delimter="/"
                )
            )
        else:
            cmd = 'world.setBlock(%d,%d,%d,%s)' % (
                vector.x, vector.y, vector.z, self._block_name.upper()
            )
        print(f"set_block: About to send this command: {cmd}")
        connection.send(
            cmd
        )

    def set_blocks(self, connection, vector_from, vector_to):
        if self._block_data:
            cmd = 'world.setBlocksWithData(%d,%d,%d,%d,%d,%d,%s,%s)' % (
                vector_from.x,
                vector_from.y,
                vector_from.z,
                vector_to.x,
                vector_to.y,
                vector_to.z,
                self._block_name.upper(),
                BlockDescriptor.block_data_to_string(
                    self._block_name,
                    self._block_data,
                    brackets=True,
                    delimter="/"
                )
            )
        else:
            cmd = 'world.setBlocks(%d,%d,%d,%d,%d,%d,%s)' % (
                vector_from.x, vector_from.y, vector_from.z,
                vector_to.x, vector_to.y, vector_to.z,
                self._block_name.upper()
            )
        print(f"set_blocks: About to send this command: {cmd}")
        connection.send(
            cmd
        )

    def set_block_with_data(self, connection):
        pass

    def set_blocks_with_data(self, connection):
        pass

    @property
    def block_data(self):
        return self._block_data

    @block_data.setter
    def block_data(self, value):
        self._block_data = value

    @property
    def block_name(self):
        return self._block_name

    @block_name.setter
    def block_name(self, block_name, value):
        self._block_name = value


class Block2(Block2Base):
    pass


class BlockRepository(object):
    def __init__(self):
        self._blocks = {}
        self._attribute_index = {}

    def get_block(self, name):
        block_details = self._blocks.get(name.lower(), None)
        return block_details.get('block', None) if block_details is not None else None

    def normalise(self, value):
        return value.lower() if isinstance(value, str) else value

    def add(self, block, category=None, sub_category=None, block_id=0, block_data=0, **kwargs):
        """
        Add a block to the repository, recording the main category and sub-category associated with it. Optionally
        recording a series of key-value pairs associated with the block. For each key-value pair the block is added to
        a list of blocks that each share the same key value paid.

        For example.

        BockRepository.add(
            LIGHT_BLUE_GLAZED_TERRACOTTA,
            category = 'natural',
            subcategory = 'decorative',
            luminosity = False,
            obey_physics = True,
            blast_resistance = 7,
            colour = 'light_blue'
            etc.
        )
            >>> # Structure is
            >>> self._attribute_index[key][value] = [block_details_for_key_value, block_details_for_key_value, etc.]

        :param block:
        :param category:
        :param sub_category:
        :param kwargs:
        :return:
        """
        name = block.block_name.lower()
        category = self.normalise(category)
        sub_category = self.normalise(sub_category)

        # Create the block details dict
        block_details = {
            'block': block,
            'name': name,
            'category': category,
            'sub_category': sub_category
        }
        for k, v in kwargs.items():
            block_details[self.normalise(k)] = self.normalise(v)

        # Initialise stuff

        self._blocks[name] = block_details

        # Now create the analysis key stuff
        kwargs['category'] = category
        kwargs['sub_category'] = sub_category
        if 'block_id' not in kwargs:
            kwargs['block_id'] = block_id
        if 'block_data' not in kwargs:
            kwargs['block_data'] = block_data


        for k, v in kwargs.items():
            key = self.normalise(k)
            value = self.normalise(v)

            if key == 'block':
                print("Keyword block is not allowed. Skipping.")
                next
            if key not in self._attribute_index:
                self._attribute_index[key] = {}
            if value not in self._attribute_index[key]:
                self._attribute_index[key][value] = list()
            self._attribute_index[key][value].append(block_details)

    def get_all_block_details(self, attribute=None, value=None):
        attribute_to_match = self.normalise(attribute)
        value_to_match = self.normalise(value)
        result = []
        for attribute_key, matches_for_value_dict in self._attribute_index.items():
            # attribute key might be 'colour'
            for value_key, list_of_block_details in matches_for_value_dict.items():
                # value key might be 'orange#
                # List of blocks is exactly that
                if attribute_to_match and value_to_match:
                    if (attribute_key != attribute_to_match) or (value_key != value_to_match):
                        continue
                elif attribute_to_match:
                    if (attribute_key != attribute_to_match):
                        continue
                elif value_to_match:
                    if (value_key != value_to_match):
                        continue
                # If we've got here then we've either matched everything that was passed or nothing was passed
                for block_details in list_of_block_details:
                    if block_details not in result:
                        result.append(block_details)
        return result

    def get_all_blocks(self, attribute=None, value=None):
        result = [x.get('block') for x in self.get_all_block_details(attribute=attribute, value=value)]
        return result

    def get_random_block(self, attribute=None, value=None):
        return choice(self.get_all_blocks(attribute=attribute, value=value))

repo = BlockRepository()

# WHITE
# ORANGE
# MAGENTA
# LIGHT_BLUE
# YELLOW
# LIME
# PINK
# GRAY
# SILVER
# CYAN
# PURPLE
# BLUE
# BROWN
# GREEN
# RED
# BLACK

# All block details found here: https://hub.spigotmc.org/javadocs/bukkit/org/bukkit/Material.html
# Block state information found here: https://minecraft.gamepedia.com/Block_states


WHITE_GLAZED_TERRACOTTA = Block2("WHITE_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    WHITE_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='white'
)

ORANGE_GLAZED_TERRACOTTA = Block2("ORANGE_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    ORANGE_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='orange'
)

MAGENTA_GLAZED_TERRACOTTA = Block2("MAGENTA_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    MAGENTA_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='magenta'
)

LIGHT_BLUE_GLAZED_TERRACOTTA = Block2("LIGHT_BLUE_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    LIGHT_BLUE_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='light_blue'
)

YELLOW_GLAZED_TERRACOTTA = Block2("YELLOW_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    YELLOW_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='yellow'
)

LIME_GLAZED_TERRACOTTA = Block2("LIME_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    LIME_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='lime'
)

PINK_GLAZED_TERRACOTTA = Block2("PINK_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    PINK_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='pink'
)

GRAY_GLAZED_TERRACOTTA = Block2("GRAY_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    GRAY_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='gray'
)

LIGHT_GRAY_GLAZED_TERRACOTTA = Block2("LIGHT_GRAY_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    LIGHT_GRAY_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='light_gray'
)

CYAN_GLAZED_TERRACOTTA = Block2("CYAN_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    CYAN_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='cyan'
)

PURPLE_GLAZED_TERRACOTTA = Block2("PURPLE_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    PURPLE_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='purple'
)

BLUE_GLAZED_TERRACOTTA = Block2("BLUE_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    BLUE_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='blue'
)

BROWN_GLAZED_TERRACOTTA = Block2("BROWN_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    BROWN_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='brown'
)

GREEN_GLAZED_TERRACOTTA = Block2("GREEN_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    GREEN_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='green'
)

RED_GLAZED_TERRACOTTA = Block2("RED_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    RED_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='red'
)

BLACK_GLAZED_TERRACOTTA = Block2("BLACK_GLAZED_TERRACOTTA") \
    .add_validator('facing', 'north', bdv_facing_compass)

repo.add(
    BLACK_GLAZED_TERRACOTTA,
    category='natural',
    sub_category='solid',
    colour='black'
)

# https://minecraft.fandom.com/wiki/Anvil
# https://minecraft.gamepedia.com/Anvil
ANVIL = Block2("ANVIL") \
    .add_validator('facing','north', bdv_facing_compass)

repo.add(
    ANVIL,
    category='utility',
    sub_category='solid',
    colour='black',
    block_id=145,
    block_data=0
)



# https://minecraft.fandom.com/wiki/Cauldron
# https://minecraft.gamepedia.com/Cauldron
CAULDRON = Block2("CAULDRON") \
    .add_validator('level', '0', bdv_zero_to_three)

repo.add(
    CAULDRON,
    category='utility',
    sub_category='solid',
    colour='black',
    block_id=118,
    block_data=0
)

# https://minecraft.gamepedia.com/Chain
# https://minecraft.fandom.com/wiki/Chain

CHAIN = Block2("CHAIN") \
    .add_validator('axis', 'y', bdv_axis) \
    .add_validator('waterlogged', 'false', bdv_waterlogged)

repo.add(
    CHAIN,
    category='utility',
    sub_category='partial',
    colour='gray'
)

# https://minecraft.fandom.com/wiki/Chest
# https://minecraft.gamepedia.com/Chest
CHEST = Block2("CHEST") \
    .add_validator('facing', "north", bdv_facing_compass) \
    .add_validator('type', 'single', bdv_chest_type) \
    .add_validator('waterlogged', 'false', bdv_waterlogged)

repo.add(
    CHEST,
    category='solid',
    sub_category='partial',
    colour='brown',
    interactive=True
)


# AIR                 = Block(0)
# STONE               = Block(1)
# GRASS               = Block(2)
# DIRT                = Block(3)
# COBBLESTONE         = Block(4)
# WOOD_PLANKS         = Block(5)
# SAPLING             = Block(6)
# BEDROCK             = Block(7)
# WATER_FLOWING       = Block(8)
# WATER               = WATER_FLOWING
# WATER_STATIONARY    = Block(9)
# LAVA_FLOWING        = Block(10)
# LAVA                = LAVA_FLOWING
# LAVA_STATIONARY     = Block(11)
# SAND                = Block(12)
# GRAVEL              = Block(13)
# GOLD_ORE            = Block(14)
# IRON_ORE            = Block(15)
# COAL_ORE            = Block(16)
# WOOD                = Block(17)
# LEAVES              = Block(18)
# GLASS               = Block(20)
# LAPIS_LAZULI_ORE    = Block(21)
# LAPIS_LAZULI_BLOCK  = Block(22)
# SANDSTONE           = Block(24)
# BED                 = Block(26)
# COBWEB              = Block(30)
# GRASS_TALL          = Block(31)
# WOOL                = Block(35)
# FLOWER_YELLOW       = Block(37)
# FLOWER_CYAN         = Block(38)
# MUSHROOM_BROWN      = Block(39)
# MUSHROOM_RED        = Block(40)
# GOLD_BLOCK          = Block(41)
# IRON_BLOCK          = Block(42)
# STONE_SLAB_DOUBLE   = Block(43)
# STONE_SLAB          = Block(44)
# BRICK_BLOCK         = Block(45)
# TNT                 = Block(46)
# BOOKSHELF           = Block(47)
# MOSS_STONE          = Block(48)
# OBSIDIAN            = Block(49)
# TORCH               = Block(50)
# FIRE                = Block(51)
# STAIRS_WOOD         = Block(53)
# CHEST               = Block(54)
# DIAMOND_ORE         = Block(56)
# DIAMOND_BLOCK       = Block(57)
# CRAFTING_TABLE      = Block(58)
# FARMLAND            = Block(60)
# FURNACE_INACTIVE    = Block(61)
# FURNACE_ACTIVE      = Block(62)
# DOOR_WOOD           = Block(64)
# LADDER              = Block(65)
# STAIRS_COBBLESTONE  = Block(67)
# DOOR_IRON           = Block(71)
# REDSTONE_ORE        = Block(73)
# SNOW                = Block(78)
# ICE                 = Block(79)
# SNOW_BLOCK          = Block(80)
# CACTUS              = Block(81)
# CLAY                = Block(82)
# SUGAR_CANE          = Block(83)
# FENCE               = Block(85)
# GLOWSTONE_BLOCK     = Block(89)
# BEDROCK_INVISIBLE   = Block(95)
# STONE_BRICK         = Block(98)
# GLASS_PANE          = Block(102)
# MELON               = Block(103)
# FENCE_GATE          = Block(107)
# GLOWING_OBSIDIAN    = Block(246)
# NETHER_REACTOR_CORE = Block(247)
#
# CONCRETE            = Block(251)
# CONCRETE_POWDER     = Block(252)
