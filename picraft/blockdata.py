from random import choice

def wrap_in_quote(value):
    return f"'{value}'"

class BlockDataValueValidator(object):
    def __init__(self, name, types=None):
        """
        Holds a number of individual block data type validators and chains the validation
        :param name: str the name of this validator
        :param types: list a list of instances of class:'BlockDataValueType' or None
        """
        self._name = name
        self.all_types = []
        if types:
            for type in types:
                self.add_type(type)

    def all_valid_values(self):
        for type in self.all_types:
            for valid_value in type.valid_values:
                yield valid_value

    def formatted_valid_values(self):
        return ", ".join([wrap_in_quote(x) for x in self.all_valid_values()])

    def valid_value(self, value):
        current_valid_values = list(self.all_valid_values())
        return value in current_valid_values

    def cycle_value(self, current_value):
        current_valid_values = list(self.all_valid_values())
        index = current_valid_values.index(current_value)
        index += 1
        if index > (len(current_valid_values) - 1):
            index = 0
        return current_valid_values[index]

    def random_value(self):
        current_valid_values = list(self.all_valid_values())
        return choice(current_valid_values)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def document(self, name, default=""):
        r = ""
        for type in self.all_types:
            r += f"{type.document(name, default)}\n"
        return r

    def add_type(self, block_data_type):
        assert isinstance(block_data_type, BlockDataValueType)
        self.all_types.append(block_data_type)
        return self

    def validate(self, value, use_and=False):
        """
        Loop through all of the validators and decide if the value is valid. If use_and is set to true then all
        validtors must say that the value is valid.
        :param value: The value to validate
        :param use_and: if True
        :return: bool
        """
        r = False
        for type in self.all_types:
            is_valid = type.validate(value)
            if use_and and is_valid is False:
                return False
            r = r or is_valid
        return f


class BlockDataValueType(object):
    """
    This validates and casts the block data value

    string_boolean = BlockDataValueType("string_boolean")
    """

    def __init__(self, additional_valid_values=None, default=""):
        if additional_valid_values:
            if not isinstance(additional_valid_values, list):
                additional_valid_values = [additional_valid_values]
        self._valid_values = [] if additional_valid_values is None else additional_valid_values
        self.add_valid_values()

    def document(self, name, default=""):
        r = f"{wrap_in_quote(name)}"
        r+= f" has a default value of {wrap_in_quote(default)}." if default else f" has no default value."
        r+= f" Valid values are: {', '.join([wrap_in_quote(x) for x in self.valid_values])}."
        return r

    @property
    def valid_values(self):
        return self._valid_values

    def add_valid_values(self):
        pass

    def normalise_value(self, value):
        return value

    def validate(self, value):
        return self.normalise_value(value) in self.valid_values

    def cast(self, value):
        return value


class BlockDataValueStringBoolean(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['true', 'false']

    def normalise_value(self, value):
        return value.lower()

    def cast(self, value):
        return self.normalise_value(value) == 'true'


class BlockDataValueFacing(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['north', 'south', 'east', 'west']


class BlockDataValueUpDown(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['up', 'down']


class BlockDataValueLeftRight(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['left','right']

class BlockDataValueAxis(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['x','y','z']

class BlockDataValueZeroToThree(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['0','1','2','3']

class BlockDataValueWoodTypes1(BlockDataValueType):

    def add_valid_values(self):
        self._valid_values += ['oak','spruce','birch','jungle','acacia','dark_oak']

bdv_facing_compass = BlockDataValueValidator(
    'facing_compass',
    [
        BlockDataValueFacing()
    ]
)

bdv_chest_type = BlockDataValueValidator(
    'chest_type',
    [
        BlockDataValueLeftRight(additional_valid_values=['single'])
    ]
)

bdv_waterlogged = BlockDataValueValidator(
    'waterlogged',
    [
        BlockDataValueStringBoolean()
    ]
)

bdv_axis = BlockDataValueValidator(
    'axis',
    [
        BlockDataValueAxis()
    ]
)

bdv_zero_to_three = BlockDataValueValidator(
    'level',
    [
        BlockDataValueZeroToThree()
    ]
)

bdv_wood_types_1 = BlockDataValueValidator(
    'type',
    [
        BlockDataValueWoodTypes1()
    ]
)