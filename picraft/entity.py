from .vector import vector_range, Vector

class EntityBase(object):
    ENTITY_NAME_LOOKUP = {
        1: "DROPPED_ITEM",
        2: "EXPERIENCE_ORB",
        3: "AREA_EFFECT_CLOUD",
        4: "ELDER_GUARDIAN",
        5: "WITHER_SKELETON",
        6: "STRAY",
        7: "EGG",
        8: "LEASH_HITCH",
        9: "PAINTING",
        10: "ARROW",
        11: "SNOWBALL",
        12: "FIREBALL",
        13: "SMALL_FIREBALL",
        14: "ENDER_PEARL",
        15: "ENDER_SIGNAL",
        17: "THROWN_EXP_BOTTLE",
        18: "ITEM_FRAME",
        19: "WITHER_SKULL",
        20: "PRIMED_TNT",
        23: "HUSK",
        24: "SPECTRAL_ARROW",
        25: "SHULKER_BULLET",
        26: "DRAGON_FIREBALL",
        27: "ZOMBIE_VILLAGER",
        28: "SKELETON_HORSE",
        29: "ZOMBIE_HORSE",
        30: "ARMOR_STAND",
        31: "DONKEY",
        32: "MULE",
        33: "EVOKER_FANGS",
        34: "EVOKER",
        35: "VEX",
        36: "VINDICATOR",
        37: "ILLUSIONER",
        40: "MINECART_COMMAND",
        41: "BOAT",
        42: "MINECART",
        43: "MINECART_CHEST",
        44: "MINECART_FURNACE",
        45: "MINECART_TNT",
        46: "MINECART_HOPPER",
        47: "MINECART_MOB_SPAWNER",
        50: "CREEPER",
        51: "SKELETON",
        52: "SPIDER",
        53: "GIANT",
        54: "ZOMBIE",
        55: "SLIME",
        56: "GHAST",
        57: "PIG_ZOMBIE",
        58: "ENDERMAN",
        59: "CAVE_SPIDER",
        60: "SILVERFISH",
        61: "BLAZE",
        62: "MAGMA_CUBE",
        63: "ENDER_DRAGON",
        64: "WITHER",
        65: "BAT",
        66: "WITCH",
        67: "ENDERMITE",
        68: "GUARDIAN",
        69: "SHULKER",
        90: "PIG",
        91: "SHEEP",
        92: "COW",
        93: "CHICKEN",
        94: "SQUID",
        95: "WOLF",
        96: "MUSHROOM_COW",
        97: "SNOWMAN",
        98: "OCELOT",
        99: "IRON_GOLEM",
        100: "HORSE",
        101: "RABBIT",
        102: "POLAR_BEAR",
        103: "LLAMA",
        104: "LLAMA_SPIT",
        105: "PARROT",
        120: "VILLAGER",
        200: "ENDER_CRYSTAL"
    }

    ENTITY_TYPE_ID_LOOKUP = {
        v: k for k, v in ENTITY_NAME_LOOKUP.items()
    }

    def __init__(self, name):
        self._name = name.upper()
        self._type_id = self.get_type_id(name)
        self._entity_id = None
        self._connection = None

    def get_type_id(self, name):
        return self.ENTITY_TYPE_ID_LOOKUP.get(name.upper(),-1)

    def __repr__(self):
        try:
            return '<Entity "%s" id=%d type_id=%d>' % (self._name, self.entity_id, self._type_id)
        except KeyError:
            return '<Entity "%s">' % (self._name)

    @property
    def type_id(self):
        return self._type_id

    @property
    def name(self):
        return self._name

    @property
    def entity_id(self):
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value):
        self._entity_id = value

    @property
    def connection(self):
        return self._connection

    @connection.setter
    def connection(self, value):
        self._connection = value

    def make_instance(self, connection, id):
        # Called to turn the generic Entity into a specific instance in the game
        self._connection = connection
        self._entity_id = id

    def check_is_instance(self):
        if self._connection is None or self._entity_id is None:
            raise ValueError('Entity is a shell and has not been attached to an instance within the game.')

    def _method_call(self, method_name, return_value, *args):
        self.check_is_instance()
        all_args = ",".join([str(x) for x in args])
        signature = method_name + "," + all_args if all_args else method_name
        cmd = 'entity.invokeMethod(%d,%s)' % (
            self._entity_id,
            signature
        )
        print(f"  About to call: {method_name} with a signature of: {signature}: cmd = {cmd}")
        try:
            if return_value:
                r = self._connection.transact(cmd)
            else:
                r = None
                self._connection.send(cmd)
        except CommandError:
            print('CommandErrom processing: %s' % (cmd))
            r = None
        return r

    def invoke_method(self, method_name, *args):
        self._method_call(method_name, False, *args)

    def invoke_method_return(self, method_name, *args):
        return self._method_call(method_name, True, *args)


class Ageable(object):
    def get_age(self):
        return self.invoke_method_return("getAge")

    def is_adult(self):
        return self.invoke_method_return("isAdult")

    def set_adult(self):
        self.invoke_method("setAdult")

    def set_age(self, value):
        self.invoke_method("setAge",str(value))

    def set_baby(self):
        self.invoke_method("setBaby")

class Damageable(object):
    def damage(self, value):
        self.invoke_method("damage|void:double", value)

    def get_health(self):
        return self.invoke_method_return("getHealth|Double:void")

    def set_health(self, value):
        self.invoke_method("setHealth|void:double", value)

    def get_absorption_amount(self):
        return self.invoke_method_return('getAbsorptionAmount|Double:void')

    def set_absorption_amount(self, value):
        self.invoke_method("setAbsorptionAmount|void:double", value)



class Entity(EntityBase):

    def set_block(self, connection, vector):
        self.check_is_instance()
        cmd = 'world.spawnEntity(%d,%d,%d,%s)' % (
            vector.x,
            vector.y,
            vector.z,
            # self._type_id
            self._name
        )
        print(f"set_block: About to create entity with this command: {cmd}")
        r = connection.transact(
            cmd
        )
        self._entity_id = int(r)
        self._connection = connection
        return self

    def set_blocks(self, connection, vector_from, vector_to):
        self.check_is_instance()
        for v in vector_range(vector_from, vector_to):
            self.set_block(connection, v)


class Entities(object):
    def __init__(self, connection):
        # @
        self._connection = connection
        self._entities = {} # Keyed on entity_id
        self.refresh()

    def refresh(self):
        self._get_entities()

    def __repr__(self):
        return '<Entities>'

    def parse_entities(self, r):
        array_of_entities = []
        for x in r.split("|"):
            if not x:
                continue
            elements = x.split(",")
            id = int(elements[0])
            name = elements[1].upper()
            location = Vector(
                int(float(elements[2])),
                int(float(elements[3])),
                int(float(elements[4]))
            )
            # Set to -1 if we don't recognise the entity
            entity_type_id = Entity.ENTITY_TYPE_ID_LOOKUP.get(name, -1)
            entity = Entity(
                name
            )
            entity.connection = self._connection
            entity.entity_id = id
            array_of_entities.append(
                {
                    "id": id,
                    "entity": entity,
                    "location": location
                }
            )
        return array_of_entities

    def _get_entities(self):
        r = self._connection.transact(
            'world.getEntities(%s)' % ("all")
        )
        for entity_detail in self.parse_entities(r):
            self._entities[entity_detail["id"]] = entity_detail["entity"]

    def get_entities(self):
         return [x for x in self._entities.values()]

    def spawn(self, entity, vector):
        cmd = 'world.spawnEntity(%d,%d,%d,%s)' % (
            vector.x,
            vector.y,
            vector.z,
            # self._type_id
            entity.name
        )
        print(f"About to create entity with this command: {cmd}")
        r = self._connection.transact(
            cmd
        )
        entity_id = int(r)
        entity.make_instance(self._connection, entity_id)
        self._entities[entity_id] = entity
        return entity

class WolfTest(EntityBase, Ageable, Damageable):
    name = "WOLF"
    def __init__(self):
        super().__init__(self.name)


DROPPED_ITEM = Entity("DROPPED_ITEM")
EXPERIENCE_ORB = Entity("EXPERIENCE_ORB")
AREA_EFFECT_CLOUD = Entity("AREA_EFFECT_CLOUD")
ELDER_GUARDIAN = Entity("ELDER_GUARDIAN")
WITHER_SKELETON = Entity("WITHER_SKELETON")
STRAY = Entity("STRAY")
EGG = Entity("EGG")
LEASH_HITCH = Entity("LEASH_HITCH")
PAINTING = Entity("PAINTING")
ARROW = Entity("ARROW")
SNOWBALL = Entity("SNOWBALL")
FIREBALL = Entity("FIREBALL")
SMALL_FIREBALL = Entity("SMALL_FIREBALL")
ENDER_PEARL = Entity("ENDER_PEARL")
ENDER_SIGNAL = Entity("ENDER_SIGNAL")
THROWN_EXP_BOTTLE = Entity("THROWN_EXP_BOTTLE")
ITEM_FRAME = Entity("ITEM_FRAME")
WITHER_SKULL = Entity("WITHER_SKULL")
PRIMED_TNT = Entity("PRIMED_TNT")
HUSK = Entity("HUSK")
SPECTRAL_ARROW = Entity("SPECTRAL_ARROW")
SHULKER_BULLET = Entity("SHULKER_BULLET")
DRAGON_FIREBALL = Entity("DRAGON_FIREBALL")
ZOMBIE_VILLAGER = Entity("ZOMBIE_VILLAGER")
SKELETON_HORSE = Entity("SKELETON_HORSE")
ZOMBIE_HORSE = Entity("ZOMBIE_HORSE")
ARMOR_STAND = Entity("ARMOR_STAND")
DONKEY = Entity("DONKEY")
MULE = Entity("MULE")
EVOKER_FANGS = Entity("EVOKER_FANGS")
EVOKER = Entity("EVOKER")
VEX = Entity("VEX")
VINDICATOR = Entity("VINDICATOR")
ILLUSIONER = Entity("ILLUSIONER")
MINECART_COMMAND = Entity("MINECART_COMMAND")
BOAT = Entity("BOAT")
MINECART = Entity("MINECART")
MINECART_CHEST = Entity("MINECART_CHEST")
MINECART_FURNACE = Entity("MINECART_FURNACE")
MINECART_TNT = Entity("MINECART_TNT")
MINECART_HOPPER = Entity("MINECART_HOPPER")
MINECART_MOB_SPAWNER = Entity("MINECART_MOB_SPAWNER")
CREEPER = Entity("CREEPER")
SKELETON = Entity("SKELETON")
SPIDER = Entity("SPIDER")
GIANT = Entity("GIANT")
ZOMBIE = Entity("ZOMBIE")
SLIME = Entity("SLIME")
GHAST = Entity("GHAST")
PIG_ZOMBIE = Entity("PIG_ZOMBIE")
ENDERMAN = Entity("ENDERMAN")
CAVE_SPIDER = Entity("CAVE_SPIDER")
SILVERFISH = Entity("SILVERFISH")
BLAZE = Entity("BLAZE")
MAGMA_CUBE = Entity("MAGMA_CUBE")
ENDER_DRAGON = Entity("ENDER_DRAGON")
WITHER = Entity("WITHER")
BAT = Entity("BAT")
WITCH = Entity("WITCH")
ENDERMITE = Entity("ENDERMITE")
GUARDIAN = Entity("GUARDIAN")
SHULKER = Entity("SHULKER")
PIG = Entity("PIG")
SHEEP = Entity("SHEEP")
COW = Entity("COW")
CHICKEN = Entity("CHICKEN")
SQUID = Entity("SQUID")
WOLF = Entity("WOLF")
MUSHROOM_COW = Entity("MUSHROOM_COW")
SNOWMAN = Entity("SNOWMAN")
OCELOT = Entity("OCELOT")
IRON_GOLEM = Entity("IRON_GOLEM")
HORSE = Entity("HORSE")
RABBIT = Entity("RABBIT")
POLAR_BEAR = Entity("POLAR_BEAR")
LLAMA = Entity("LLAMA")
LLAMA_SPIT = Entity("LLAMA_SPIT")
PARROT = Entity("PARROT")
VILLAGER = Entity("VILLAGER")
ENDER_CRYSTAL = Entity("ENDER_CRYSTAL")

    # DROPPED_ITEM("item", Item.class, 1, false),
    # EXPERIENCE_ORB("experience_orb", ExperienceOrb.class, 2),
    # AREA_EFFECT_CLOUD("area_effect_cloud", AreaEffectCloud.class, 3),
    # ELDER_GUARDIAN("elder_guardian", ElderGuardian.class, 4),
    # WITHER_SKELETON("wither_skeleton", WitherSkeleton.class, 5),
    # STRAY("stray", Stray.class, 6),
    # EGG("egg", Egg.class, 7),
    # LEASH_HITCH("leash_knot", LeashHitch.class, 8),
    # PAINTING("painting", Painting.class, 9),
    # ARROW("arrow", Arrow.class, 10),
    # SNOWBALL("snowball", Snowball.class, 11),
    # FIREBALL("fireball", LargeFireball.class, 12),
    # SMALL_FIREBALL("small_fireball", SmallFireball.class, 13),
    # ENDER_PEARL("ender_pearl", EnderPearl.class, 14),
    # ENDER_SIGNAL("eye_of_ender", EnderSignal.class, 15),
    # SPLASH_POTION("potion", ThrownPotion.class, 16, false),
    # THROWN_EXP_BOTTLE("experience_bottle", ThrownExpBottle.class, 17),
    # ITEM_FRAME("item_frame", ItemFrame.class, 18),
    # WITHER_SKULL("wither_skull", WitherSkull.class, 19),
    # PRIMED_TNT("tnt", TNTPrimed.class, 20),
    # FALLING_BLOCK("falling_block", FallingBlock.class, 21, false),
    # FIREWORK("firework_rocket", Firework.class, 22, false),
    # HUSK("husk", Husk.class, 23),
    # SPECTRAL_ARROW("spectral_arrow", SpectralArrow.class, 24),
    # SHULKER_BULLET("shulker_bullet", ShulkerBullet.class, 25),
    # DRAGON_FIREBALL("dragon_fireball", DragonFireball.class, 26),
    # ZOMBIE_VILLAGER("zombie_villager", ZombieVillager.class, 27),
    # SKELETON_HORSE("skeleton_horse", SkeletonHorse.class, 28),
    # ZOMBIE_HORSE("zombie_horse", ZombieHorse.class, 29),
    # ARMOR_STAND("armor_stand", ArmorStand.class, 30),
    # DONKEY("donkey", Donkey.class, 31),
    # MULE("mule", Mule.class, 32),
    # EVOKER_FANGS("evoker_fangs", EvokerFangs.class, 33),
    # EVOKER("evoker", Evoker.class, 34),
    # VEX("vex", Vex.class, 35),
    # VINDICATOR("vindicator", Vindicator.class, 36),
    # ILLUSIONER("illusioner", Illusioner.class, 37),
    # MINECART_COMMAND("command_block_minecart", CommandMinecart.class, 40),
    # BOAT("boat", Boat.class, 41),
    # MINECART("minecart", RideableMinecart.class, 42),
    # MINECART_CHEST("chest_minecart", StorageMinecart.class, 43),
    # MINECART_FURNACE("furnace_minecart", PoweredMinecart.class, 44),
    # MINECART_TNT("tnt_minecart", ExplosiveMinecart.class, 45),
    # MINECART_HOPPER("hopper_minecart", HopperMinecart.class, 46),
    # MINECART_MOB_SPAWNER("spawner_minecart", SpawnerMinecart.class, 47),
    # CREEPER("creeper", Creeper.class, 50),
    # SKELETON("skeleton", Skeleton.class, 51),
    # SPIDER("spider", Spider.class, 52),
    # GIANT("giant", Giant.class, 53),
    # ZOMBIE("zombie", Zombie.class, 54),
    # SLIME("slime", Slime.class, 55),
    # GHAST("ghast", Ghast.class, 56),
    # ZOMBIFIED_PIGLIN("zombified_piglin", PigZombie.class, 57),
    # ENDERMAN("enderman", Enderman.class, 58),
    # CAVE_SPIDER("cave_spider", CaveSpider.class, 59),
    # SILVERFISH("silverfish", Silverfish.class, 60),
    # BLAZE("blaze", Blaze.class, 61),
    # MAGMA_CUBE("magma_cube", MagmaCube.class, 62),
    # ENDER_DRAGON("ender_dragon", EnderDragon.class, 63),
    # WITHER("wither", Wither.class, 64),
    # BAT("bat", Bat.class, 65),
    # WITCH("witch", Witch.class, 66),
    # ENDERMITE("endermite", Endermite.class, 67),
    # GUARDIAN("guardian", Guardian.class, 68),
    # SHULKER("shulker", Shulker.class, 69),
    # PIG("pig", Pig.class, 90),
    # SHEEP("sheep", Sheep.class, 91),
    # COW("cow", Cow.class, 92),
    # CHICKEN("chicken", Chicken.class, 93),
    # SQUID("squid", Squid.class, 94),
    # WOLF("wolf", Wolf.class, 95),
    # MUSHROOM_COW("mooshroom", MushroomCow.class, 96),
    # SNOWMAN("snow_golem", Snowman.class, 97),
    # OCELOT("ocelot", Ocelot.class, 98),
    # IRON_GOLEM("iron_golem", IronGolem.class, 99),
    # HORSE("horse", Horse.class, 100),
    # RABBIT("rabbit", Rabbit.class, 101),
    # POLAR_BEAR("polar_bear", PolarBear.class, 102),
    # LLAMA("llama", Llama.class, 103),
    # LLAMA_SPIT("llama_spit", LlamaSpit.class, 104),
    # PARROT("parrot", Parrot.class, 105),
    # VILLAGER("villager", Villager.class, 120),
    # ENDER_CRYSTAL("end_crystal", EnderCrystal.class, 200),
    # TURTLE("turtle", Turtle.class, -1),
    # PHANTOM("phantom", Phantom.class, -1),
    # TRIDENT("trident", Trident.class, -1),
    # COD("cod", Cod.class, -1),
    # SALMON("salmon", Salmon.class, -1),
    # PUFFERFISH("pufferfish", PufferFish.class, -1),
    # TROPICAL_FISH("tropical_fish", TropicalFish.class, -1),
    # DROWNED("drowned", Drowned.class, -1),
    # DOLPHIN("dolphin", Dolphin.class, -1),
    # CAT("cat", Cat.class, -1),
    # PANDA("panda", Panda.class, -1),
    # PILLAGER("pillager", Pillager.class, -1),
    # RAVAGER("ravager", Ravager.class, -1),
    # TRADER_LLAMA("trader_llama", TraderLlama.class, -1),
    # WANDERING_TRADER("wandering_trader", WanderingTrader.class, -1),
    # FOX("fox", Fox.class, -1),
    # BEE("bee", Bee.class, -1),
    # HOGLIN("hoglin", Hoglin.class, -1),
    # PIGLIN("piglin", Piglin.class, -1),
    # STRIDER("strider", Strider.class, -1),
    # ZOGLIN("zoglin", Zoglin.class, -1),
    # PIGLIN_BRUTE("piglin_brute", PiglinBrute.class, -1),
    # FISHING_HOOK("fishing_bobber", FishHook.class, -1, false),
    # LIGHTNING("lightning_bolt", LightningStrike.class, -1, false),
    # PLAYER("player", Player.class, -1, false),
    # UNKNOWN((String)null, (Class)null, -1, false);