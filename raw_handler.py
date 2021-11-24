import os
import copy
import shutil
import regex as re

object_types = {"BODY_DETAIL_PLAN": ["BODY_DETAIL_PLAN"],
                "BODY": ["BODY",
                         "BODYGLOSS"],
                "BUILDING": ["BUILDING_WORKSHOP"],
                "CREATURE": ["CREATURE"],
                # Note that CREATURE_VARIATION is missing
                "DESCRIPTOR_COLOR": ["COLOR"],
                "DESCRIPTOR_PATTERN": ["COLOR_PATTERN"],
                "DESCRIPTOR_SHAPE": ["SHAPE"],
                "ENTITY": ["ENTITY"],
                "INORGANIC": ["INORGANIC"],
                "INTERACTION": ["INTERACTION"],
                "ITEM": ["ITEM_AMMO",
                         "ITEM_ARMOR",
                         "ITEM_FOOD",
                         "ITEM_GLOVES",
                         "ITEM_HELM",
                         "ITEM_INSTRUMENT",
                         "ITEM_PANTS",
                         "ITEM_SHIELD",
                         "ITEM_SIEGEAMMO",
                         "ITEM_SHOES",
                         "ITEM_TOOL",
                         "ITEM_TOY",
                         "ITEM_TRAPCOMP",
                         "ITEM_WEAPON"],
                "LANGUAGE": ["TRANSLATION",
                             "SYMBOL",
                             "WORD"],
                "MATERIAL_TEMPLATE": ["MATERIAL_TEMPLATE"],
                "PLANT": ["PLANT"],
                "REACTION": ["REACTION"],
                "TISSUE_TEMPLATE": ["TISSUE_TEMPLATE"],
                # EDIT and OBJECT_TEMPLATE objects are not in vanilla,
                # they can be mixed in with the right kind of normal object,
                # or be placed in their own files
                "EDIT": ["EDIT"],
                "OBJECT_TEMPLATE": ["OBJECT_TEMPLATE"]
                }

object_type_file_names = {"BODY_DETAIL_PLAN": "b_detail_plan",
                          "BODY": "body",
                          "BUILDING": "building",
                          "CREATURE": "creature",
                          "DESCRIPTOR_COLOR": "descriptor_color",
                          "DESCRIPTOR_PATTERN": "descriptor_pattern",
                          "DESCRIPTOR_SHAPE": "descriptor_shape",
                          "ENTITY": "entity",
                          "INORGANIC": "inorganic",
                          "INTERACTION": "interaction",
                          "ITEM": "item",
                          "LANGUAGE": "language",
                          "MATERIAL_TEMPLATE": "material_template",
                          "PLANT": "plant",
                          "REACTION": "reaction",
                          "TISSUE_TEMPLATE": "tissue_template"}

# see https://dwarffortresswiki.org/index.php/DF2014:Raw_file#Parsing
# o_template has been added to the top, so they are always loaded first
# c_variation is included here for the sake of the SyntaxUpdater
header_load_order = ["o_template",
                     "language",
                     "descriptor_shape",
                     "descriptor_color",
                     "descriptor_pattern",
                     "material_template",
                     "inorganic",
                     "plant",
                     "tissue_template",
                     "item",
                     "building",
                     "b_detail_plan",
                     "body",
                     "c_variation",
                     "creature",
                     "entity",
                     "reaction",
                     "interaction",
                     "edit"]

special_tokens = ["GO_TO_END", "GO_TO_START", "GO_TO_TAG", "COPY_TAGS_FROM", "REMOVE_OBJECT",
                  "USE_OBJECT_TEMPLATE"]

object_template_tokens = ["OT_ADD_TAG", "OT_REMOVE_TAG", "OT_CONVERT_TAG",
                          "OTCT_TARGET", "OTCT_REPLACEMENT",
                          "OT_ADD_CTAG", "OT_REMOVE_CTAG", "OT_CONVERT_CTAG"]

# for the SyntaxUpdater
creature_variation_tokens = ["CV_ADD_TAG", "CV_NEW_TAG", "CV_REMOVE_TAG", "CV_CONVERT_TAG",
                             "CVCT_MASTER", "CVCT_TARGET", "CVCT_REPLACEMENT",
                             "CV_ADD_CTAG", "CV_NEW_CTAG", "CV_REMOVE_CTAG", "CV_CONVERT_CTAG"]

convertible_body_detail_plan_tokens = ["ADD_MATERIAL", "ADD_TISSUE", "BP_RELSIZE"]

syntax_updated_disclaimer1 = "\n" \
                             "====================================================================================\n" \
                             "The syntax of this file has been automatically updated/changed to be compatible with\n" \
                             "the modloader mockup. This means it is no longer compatible with vanilla DF, though\n" \
                             "the compiled raws output by the modloader are.\n"

bdp_leftover_disclaimer1 = "\n" \
                           "====================================================================================\n" \
                           "The syntax of this file has been automatically updated/changed to be compatible with\n" \
                           "the modloader mockup. In this case, some BODY_DETAIL_PLAN objects have been converted\n" \
                           "to OBJECT_TEMPLATE objects, and moved to a separate file. The exception is objects\n" \
                           "using BP_LAYERS, BP_POSITION and/or BP_RELATION, as those are not convertible to\n" \
                           "corresponding CREATURE tokens to use in the OBJECT_TEMPLATEs. The file that has been\n" \
                           "split off is "

bdp_templates_disclaimer1 = "\n" \
                            "====================================================================================\n" \
                            "This file has been automatically created for a mod to be compatible with the modloader\n" \
                            "mockup. In this case, BODY_DETAIL_PLAN objects have been converted to OBJECT_TEMPLATE\n" \
                            "objects. The original body detail plan, in which comments for these objects may still\n" \
                            "reside, is "

file_disclaimer2 = "The syntax updater is not strictly needed for the modloader to work, should\n" \
                   "this (or any other) new syntax be introduced - rather, it is a tool to facilitate\n" \
                   "playing around with the modloader, before learning new syntax. //voliol 2021-11-24\n" \
                   "====================================================================================\n"


# ====== classes  ===========================================================================================

class RawObject:

    def __init__(self, object_id, tokens=None,
                 source_file_name=None, source_mod_name_and_version=None,
                 is_removed=False):
        self.object_id = object_id
        if tokens is None:
            self.tokens = []
        else:
            self.tokens = tokens
        self.source_file_name = source_file_name
        self.source_mod_name_and_version = source_mod_name_and_version
        self.is_removed = is_removed

    def has_token(self, ask_token):
        # takes either a string; checks for a token of that name
        if type(ask_token) == str:
            for token in self.tokens:
                if token[0] == ask_token:
                    return True
            return False
        # or a list (of strings); checks for a token of that name and those leading values.
        # e.g. ask_token=["BODY", "QUADRUPED_NECK"] returns True for the vanilla toad raws, as those include
        #      "[BODY:QUADRUPED_NECK:2_EYES:...:RIBCAGE]"
        elif type(ask_token) == list:
            for token in self.tokens:
                if token[:len(ask_token)] == ask_token:
                    return True
            return False
        else:
            raise TypeError("Unexpected type for ask_token, ", type(ask_token), ". Expected str or list.")

    def get_token_values(self, token_name, max_amount="inf"):
        token_values = []
        for token in self.tokens:
            if token[0] == token_name:
                token_values.append(token[1:])
            if len(token_values) == max_amount:
                return token_values
        return token_values

    def get_last_token_value(self, token_name, error_message):
        try:
            self.get_token_values(token_name)[-1]
        except IndexError:
            # should perhaps be Raise-d instead?
            print(error_message)
            return False
        else:
            return self.get_token_values(token_name)[-1]

    def remove_token(self, ask_token):
        # returns how many tokens were is_removed, useful for moving an "insertion_index"
        len_before = len(self.tokens)
        self.tokens = [token for token in self.tokens
                       if token[:len(ask_token)] != ask_token]
        return len_before - len(self.tokens)

    def convert_token(self, master, target, replacement):
        # master should be a list, target and replacement strings
        for i in range(len(self.tokens)):
            if self.tokens[i][:len(master)] == master:
                arg_string = ":".join(self.tokens[i][1:])
                if target in arg_string:
                    self.tokens[i] = [self.tokens[i][0]] + [arg for arg in
                                                            arg_string.replace(target, replacement).split(":")
                                                            if arg != ""]

    def tokens_with_arguments_inserted(self, arguments, arg_prefix="!ARG"):
        # returns a list of tokens with arguments inserted
        new_tokens = copy.copy(self.tokens)

        # "|" can be used in arguments as a stand-in for ":"
        for i in range(len(arguments)):
            arguments[i] = arguments[i].replace("|", ":")

        # inserts the exclamation args, in reverse order so that "!ARG1" doesn't take priority over e.g. "!ARG10"
        for i in range(len(arguments)-1, -1, -1):
            arg = arguments[i]
            for j in range(len(new_tokens)):
                new_tokens[j] = [token_arg.replace(arg_prefix+str(i+1), arg)
                                 for token_arg in new_tokens[j]]

        return new_tokens


class Mod:

    def __init__(self, name, version, creator, df_version,
                 description_string, dependencies_string,
                 path):
        self.name = name
        self.version = version
        self.creator = creator
        self.df_version = df_version
        # descriptions default to "No description"
        if description_string == "":
            self.description_string = "No description"
        else:
            self.description_string = description_string
        # dependencies default to "No known dependencies"
        if dependencies_string == "":
            self.dependencies_string = "No known dependencies"
        else:
            self.dependencies_string = dependencies_string
        self.path = path
        if os.path.isdir(path + "/objects"):
            self.file_names = [filename for filename in os.listdir(path + "/objects") if filename.endswith(".txt")]
        else:
            print(name, version, "in", path, "is missing an /objects folder. Loaded as empty mod.")
            self.file_names = []


def init_raw_dict_of_dicts():
    return {object_type: {}
            for object_type in
            # this just flattens the list of object_types.values()
            [val for sublist in object_types.values() for val in sublist]}


def init_raw_dict_of_lists():
    return {object_type: []
            for object_type in
            # this just flattens the list of object_types.values()
            [val for sublist in object_types.values() for val in sublist]}


class Compiler:

    def __init__(self):
        # normally it's nicer to be able to refer to objects using ID, so a dictionary of dictionaries is preferred
        self.normal_objects = init_raw_dict_of_dicts()
        # however, there is also a list version containing the same objects,
        # so they can be outputted/written in a nice order (i.e. purely for the aesthetics of the output files)
        self.normal_objects_lists = init_raw_dict_of_lists()

        # object templates only have a dict-of-dicts, because they are not outputted to files
        self.object_templates = init_raw_dict_of_dicts()

        # where the objects are put in the step before writing, sort of
        # thanks to COPY_TAGS_FROM "compiled" objects must be accessible, and so having a dict-of-dicts is useful
        self.compiled_objects = init_raw_dict_of_dicts()
        self.compiled_objects_lists = init_raw_dict_of_lists()
        # object templates also have a "compiled" version thanks to both COPY_TAGS_FROM, and USE_OBJECT_TEMPLATE
        self.compiled_object_templates = init_raw_dict_of_dicts()

        # an anti recursion loop measure
        self.currently_compiling_ids = []

    def compile_mods(self, mods, output_path):

        # goes through each mod, see Compiler.read_mod_raws() for most of the raw handling
        for i in range(len(mods)):
            print("reading mod " + str(i + 1) + "/" + str(len(mods)), mods[i].name)
            self.read_mod_raws_and_apply_edit_objects(mods[i])

        self.apply_special_tokens_to_create_compiled_objects()

        self.write_compiled_objects(output_path)

    def read_mod_raws_and_apply_edit_objects(self, mod):

        # sorts the files according to the first line in the file (not file name!)
        sorted_file_names = sort_file_names(mod)

        # goes through each file of the mod, in the sorted order
        for i in range(len(sorted_file_names)):
            # opens the file and splits it into tokens
            print("\treading file " + str(i + 1) + "/" + str(len(sorted_file_names)), sorted_file_names[i])
            file_name = sorted_file_names[i]
            raw_file = open(mod.path + "/objects/" + file_name, "r", encoding="latin1")
            raw_file_tokens = split_file_into_tokens(raw_file)
            raw_file.close()

            # initially it doesn't know what object types to expect
            # and it has to know, because e.g. "COLOR" is both an object type and a common token elsewhere.
            # "EDIT" and "OBJECT_TEMPLATE" is a sort of honorary object type, which can be put anywhere because it
            # tells you what object ype the edit is for, and "EDIT" is never used as a common token.
            pos_object_types = ["EDIT", "OBJECT_TEMPLATE"]

            # reading_mode is either "NONE", "NEW" or "EDIT"
            reading_mode = "NONE"
            current_objects = []
            current_object_type = False

            # for special token converts
            convert_master = None
            convert_target = None

            # goes through all tokens
            for j in range(len(raw_file_tokens)):
                token = raw_file_tokens[j]
                # the "OBJECT" token tells it what object types to expect
                if token[0] == "OBJECT":
                    pos_object_types = object_types[token[1]]

                # if it's already reading an object, and it's not changing
                elif token[0] not in pos_object_types + ["EDIT", "OBJECT_TEMPLATE"]:

                    # non-EDIT objects are just read through and stored in this step
                    if reading_mode in "NEW":
                        current_objects[0].tokens.append(token)

                    elif reading_mode in "OT":
                        if token[0] in object_template_tokens:
                            current_objects[0].tokens.append(token)
                        else:
                            # normal tokens are read as OT_ADD_TAGs
                            current_objects[0].tokens.append(["OT_ADD_TAG"] + token)

                    # EDIT-objects are applied here
                    elif reading_mode == "EDIT":
                        # each EDIT-level token does something special

                        # PLUS_SELECT selects a new set of objects using the same kind of criteria as EDIT, and adds them.
                        # e.g. [EDIT:CREATURE:SEL_BY_CLASS:MAMMAL][PLUS_SELECT:SEL_BY_CLASS:POISONOUS] would select all
                        # creatures that are either mammals *or* poisonous, as opposed to
                        # [EDIT:CREATURE:SEL_BY_CLASS:MAMMAL:SEL_BY_CLASS:POISONOUS] which only selects creatures that are
                        # both mammals *and* poisonous - the platypus and its variants (in vanilla).
                        if token[0] == "PLUS_SELECT":
                            current_objects += select_objects_by_criteria(self.normal_objects_lists[current_object_type],
                                                                          token[1:])
                        # UNSELECT also uses the same same kind of criteria as EDIT, but instead unselects those objects.
                        # e.g [EDIT:CREATURE:SEL_BY_CLASS:MAMMAL][UNSELECT:SEL_BY_ID:PIG] selects all mammals but the pig
                        elif token[0] == "UNSELECT":
                            current_objects = [raw_object for raw_object in current_objects
                                               if raw_object not in
                                               select_objects_by_criteria(self.normal_objects_lists[current_object_type],
                                                                          token[1:])]

                        elif token[0] == "ADD_SPEC_TAG":
                            if token[1] in special_tokens:
                                for co in current_objects:
                                    co.tokens.append(token[1:])
                            else:
                                print("Unknown special token ", token[1], " is not compatible with ADD_SPEC_TAG.")

                        elif token[0] == "REMOVE_SPEC_TAG":
                            if token[1] in special_tokens:
                                for co in current_objects:
                                    co.remove_token(token[1:])
                            else:
                                print("Unknown special token ", token[1], " is not compatible with REMOVE_SPEC_TAG.")

                        elif token[0] == "CONVERT_SPEC_TAG":
                            if token[1] in special_tokens:
                                convert_master = token[1:]
                            else:
                                print("Unknown special token ", token[1], " is not compatible with CONVERT_SPEC_TAG.")

                        # inside a CONVERT_SPEC_TAG block
                        elif convert_master is not None:

                            if token[0] == "CST_TARGET":
                                convert_target = ":".join(token[1:])

                            elif token[0] == "CST_REPLACEMENT":
                                if convert_target is not None:
                                    convert_replacement = ":".join(token[1:])
                                    for co in current_objects:
                                        co.convert_token(convert_master, convert_target, convert_replacement)

                            else:
                                convert_master = None

                        # copies over special tokens and ov tokens
                        elif token[0] in special_tokens or token[0] in object_template_tokens:
                            for co in current_objects:
                                co.tokens.append(token)

                        # copies over normal tokens as OT_ADD_TAGs
                        else:
                            for co in current_objects:
                                co.tokens.append(["OT_ADD_TAG"] + token)

                # if it finds a new object or it is the last line in the file
                if token[0] in pos_object_types + ["EDIT", "OBJECT_TEMPLATE"] or j == len(raw_file_tokens) - 1:
                    # finishes the current object before starting to read the next one
                    if reading_mode == "NEW":
                        # you can only define one new object at a time, thus current_objects just has one element
                        # when reading_mode == "NEW".
                        co = current_objects[0]
                        self.normal_objects_lists[current_object_type].append(co)
                        self.normal_objects[current_object_type][co.object_id] = co

                    elif reading_mode == "OT":
                        co = current_objects[0]
                        self.object_templates[current_object_type][co.object_id] = co
                        # print(co.object_id, len(self.object_templates[current_object_type]))

                    # start of a new object, the vanilla way
                    if token[0] in pos_object_types and pos_object_types != ["OBJECT_TEMPLATE"]:
                        # always the same, regardless of kind of raw entry ("NEW", "EDIT" or whatever)
                        current_object_type = token[0]
                        current_objects = [RawObject(token[1], source_file_name=file_name,
                                                     source_mod_name_and_version=mod.name + " " + mod.version)]
                        reading_mode = "NEW"

                    # start of an EDIT object
                    elif token[0] == "EDIT":
                        if token[1] in pos_object_types or pos_object_types == ["EDIT"]:
                            current_object_type = token[1]
                            current_objects = select_objects_by_criteria(self.normal_objects_lists[current_object_type],
                                                                         token[2:])
                            reading_mode = "EDIT"

                            # print(":".join(token))
                            # print("[" + ", ".join(co.object_id for co in current_objects) + "]")
                        else:
                            print("Invalid file for " + ":".join(token) + "; " + file_name)

                    # start of an object template object
                    elif token[0] == "OBJECT_TEMPLATE":
                        if token[1] in pos_object_types or pos_object_types == ["OBJECT_TEMPLATE"]:
                            current_object_type = token[1]
                            current_objects = [RawObject(token[2])]
                            reading_mode = "OT"
                        else:
                            print("Invalid file for " + ":".join(token) + "; " + file_name)

    def apply_special_tokens_to_create_compiled_objects(self):
        print("applying object templates etc.")
        for object_type in self.normal_objects_lists:

            # first object templates
            for object_template in self.object_templates[object_type].values():
                # it's possible for an object to be compiled "out of order" due to COPY_TAGS_FROM,
                # this check makes sure such objects aren't counted twice
                if object_template.object_id not in self.compiled_objects[object_type]:
                    self.compile_object_template_using_special_tokens(object_type, object_template.object_id)

            # second normal objects, using normal_objects_lists for the sake of ordered output
            for normal_object in self.normal_objects_lists[object_type]:
                if normal_object.object_id not in self.compiled_objects[object_type]:
                    self.compile_normal_object_using_special_tokens(object_type, normal_object.object_id)

    def compile_object_template_using_special_tokens(self, object_type, object_id):
        # this is quite similar to self.compile_normal_object_using_special_tokens,
        # but not similar enough to have them be the same function

        # adds the object's id to self.currently_compiling_ids, for recursion reasons
        self.currently_compiling_ids.append(object_id)
        # print("ot", self.currently_compiling_ids)

        # co for "current object"
        co = self.object_templates[object_type][object_id]

        output_object = RawObject(co.object_id, source_file_name=co.source_file_name,
                                  source_mod_name_and_version=co.source_mod_name_and_version)
        insertion_index = 0

        for token in co.tokens:

            if token[0] == "GO_TO_END":
                insertion_index = len(output_object.tokens)

            elif token[0] == "GO_TO_START":
                insertion_index = 0

            # This is how GO_TO_TAG works in vanilla, strangely.
            # It goes to just before the target tag, and it looks for a string starting that way instead of full tokens.
            elif token[0] == "GO_TO_TAG":
                goto_tag_string = ":".join(token[1:])
                for i in range(len(output_object.tokens)):
                    if ":".join(output_object.tokens[i]).startswith(goto_tag_string):
                        insertion_index = i
                        break

            elif token[0] == "COPY_TAGS_FROM":
                if self.can_get_raw_object(object_type, token[1], False):
                    # object templates can only copy from (the same sub-type of) object templates
                    # this is how you nest templates
                    if token[1] not in self.compiled_objects[object_type]:
                        # this goes recursive, and so checks for a recursive loop, and raises an error if there is one
                        if token[1] not in self.currently_compiling_ids:
                            self.compile_object_template_using_special_tokens(object_type, token[1])
                        else:
                            raise RecursionError("COPY_TAGS_FROM loop with " + object_type + " objects "
                                                 ", ".join(self.currently_compiling_ids) + ".")
                    # note that it inserts arguments here
                    copy_tokens = self.compiled_objects[object_type][token[1]].tokens_with_arguments_inserted(token[2:])
                    output_object.tokens = output_object.tokens[:insertion_index] + \
                                           copy_tokens + \
                                           output_object.tokens[insertion_index:]
                    insertion_index += len(copy_tokens)

            # non-special tokens
            else:
                output_object.tokens.insert(insertion_index, token)
                insertion_index += 1

        self.compiled_object_templates[object_type][object_id] = output_object
        # removes the object's id when it is done
        self.currently_compiling_ids.remove(object_id)

    def compile_normal_object_using_special_tokens(self, object_type, object_id):
        # this is quite similar to self.compile_object_template_using_special_tokens,
        # but not similar enough to have them be the same function

        # adds the object's id to self.currently_compiling_ids, for recursion reasons
        self.currently_compiling_ids.append(object_id)
        # print(self.currently_compiling_ids)

        # co for "current object"
        co = self.normal_objects[object_type][object_id]

        output_object = RawObject(co.object_id, source_file_name=co.source_file_name,
                                  source_mod_name_and_version=co.source_mod_name_and_version)
        insertion_index = 0
        # for object template converts
        convert_master = None
        convert_target = None

        for token in co.tokens:

            # inside a OT_CONVERT block
            if convert_master is not None:

                if token[0] == "OTCT_TARGET":
                    convert_target = ":".join(token[1:])

                elif token[0] == "OTCT_REPLACEMENT":
                    if convert_target is not None:
                        convert_replacement = ":".join(token[1:])
                        output_object.convert_token(convert_master, convert_target, convert_replacement)

                else:
                    convert_master = None

            if token[0] == "GO_TO_END":
                insertion_index = len(output_object.tokens)

            elif token[0] == "GO_TO_START":
                insertion_index = 0

            # This is how GO_TO_TAG works in vanilla, strangely.
            # It goes to just before the target tag, and it looks for a string starting that way instead of full tokens.
            elif token[0] == "GO_TO_TAG":
                goto_tag_string = ":".join(token[1:])
                for i in range(len(output_object.tokens)):
                    if ":".join(output_object.tokens[i]).startswith(goto_tag_string):
                        insertion_index = i
                        break

            elif token[0] == "COPY_TAGS_FROM":
                if self.can_get_raw_object(object_type, token[1], False):
                    # normal objects can only copy from (the same type of) normal objects;
                    if token[1] not in self.compiled_objects[object_type]:
                        # this goes recursive, and so checks for a recursive loop, and raises an error if there is one
                        if token[1] not in self.currently_compiling_ids:
                            self.compile_normal_object_using_special_tokens(object_type, token[1])
                        else:
                            raise RecursionError("COPY_TAGS_FROM loop with " + object_type + " objects "
                                                 ", ".join(self.currently_compiling_ids) + ".")
                    copy_tokens = self.compiled_objects[object_type][token[1]].tokens
                    output_object.tokens = output_object.tokens[:insertion_index] + \
                                           copy_tokens + \
                                           output_object.tokens[insertion_index:]
                    insertion_index += len(copy_tokens)

            elif token[0] == "REMOVE_OBJECT":
                output_object.is_removed = True

            elif token[0] == "USE_OBJECT_TEMPLATE":
                # print("used object template!!!", output_object.object_id, token[1])
                insertion_index = self.use_object_template(output_object, insertion_index,
                                                           object_type, token[1], token[2:])

            elif token[0] == "OT_ADD_TAG":
                output_object.tokens.insert(insertion_index, token[1:])
                insertion_index += 1

            elif token[0] == "OT_REMOVE_TAG":
                insertion_index -= output_object.remove_token(token[1:])

            elif token[0] == "OT_CONVERT_TAG":
                convert_master = token[1:]

            # non-special tokens
            elif convert_master is None:
                output_object.tokens.insert(insertion_index, token)
                insertion_index += 1

        self.compiled_objects[object_type][object_id] = output_object
        self.compiled_objects_lists[object_type].append(output_object)
        # removes the object's id when it is done
        self.currently_compiling_ids.remove(object_id)

    def use_object_template(self, target_object, insertion_index, object_type, ot_id, arguments):
        # Object templates are a generalized form of vanilla creature variations, body detail plans, etc.,
        # intended to replace the latter. The syntax is similar to that for vanilla creature variations,
        # but with some wrinkles straightened out.
        # see: https://dwarffortresswiki.org/index.php/DF2014:Creature_variation_token

        def ctag_correct():
            try:
                int(ot_token[1])
            except ValueError:
                print("Incorrect usage of " + ot_token[0] + "; " + ot_token[1] + " is not an integer. "
                      + ":".join(ot_token))
                return False
            else:
                return True

        # can't use an object template which doesn't exist
        if ot_id not in self.compiled_object_templates[object_type]:
            return insertion_index

        # gets the object template tokens
        ot_tokens = self.compiled_object_templates[object_type][ot_id].tokens_with_arguments_inserted(arguments)
        # for object template converts
        convert_master = None
        convert_target = None

        # and iterates through all its tokens
        for i in range(len(ot_tokens)):
            ot_token = ot_tokens[i]
            #print(ot_token)

            if ot_token[0] == "OT_ADD_TAG":
                #print(target_object.object_id, ot_id, ot_token)
                target_object.tokens.insert(insertion_index, ot_token[1:])
                insertion_index += 1

            elif ot_token[0] == "OT_REMOVE_TAG":
                #print(target_object.object_id, ot_id, ot_token)
                insertion_index -= target_object.remove_token(ot_token[1:])

            elif ot_token[0] == "OT_CONVERT_TAG":
                convert_master = ot_token[1:]

            # These three "_CTAG" tokens are like the corresponding "_TAG" tokens above, but with the condition that
            # a numbered argument must be equal to a set value.
            # E.g. "[OT_ADD_CTAG:2:TREE:SPRING]" will only add SPRING if the second argument is "TREE".

            elif ot_token[0] == "OT_ADD_CTAG":
                if ctag_correct():
                    target_object.tokens.insert(insertion_index, ot_token[1:])
                    insertion_index += 1

            elif ot_token[0] == "OT_REMOVE_CTAG":
                if ctag_correct():
                    insertion_index -= target_object.remove_token(ot_token[1:])

            elif ot_token[0] == "OT_CONVERT_CTAG":
                if ctag_correct():
                    convert_master = ot_token[1:]

            # inside a OT_CONVERT block
            elif convert_master is not None:

                if ot_token[0] == "OTCT_TARGET":
                    convert_target = ":".join(ot_token[1:])

                elif ot_token[0] == "OTCT_REPLACEMENT":
                    if convert_target is not None:
                        convert_replacement = ":".join(ot_token[1:])
                        target_object.convert_token(convert_master, convert_target, convert_replacement)

                else:
                    convert_master = None

        # and finally makes sure the insertion index is updated
        return insertion_index

    def write_compiled_objects(self, output_path):
        print("writing to output files")
        # writes the compiled objects into one "_compiled.txt" for each super object type
        for super_object_type in object_types:
            # Edits and creature variations are not outputted;
            # as they are custom object types not recognized by DF, and do nothing outside of compilation.
            if super_object_type not in ["EDIT", "OBJECT_TEMPLATE"]:
                # opens the file for writing
                compiled_file = open(output_path + "/" + object_type_file_names[super_object_type] + "_compiled.txt",
                                     "w", encoding="latin1")
                compiled_file.write(object_type_file_names[super_object_type] + "_compiled" + "\n\n"
                                                                                              "[OBJECT:" + super_object_type + "]" + "\n")

                objects_in_file_count = 0

                for object_type in object_types[super_object_type]:
                    # writes each raw object of that object type *in order*
                    for raw_object in self.compiled_objects_lists[object_type]:
                        # objects is_removed by REMOVE_OBJECT are skipped
                        if not raw_object.is_removed:
                            objects_in_file_count += 1
                            # a blank line between each object
                            compiled_file.write("\n")
                            # the file and mod it came from, for convenience's sake
                            compiled_file.write(raw_object.source_mod_name_and_version + ", "
                                                + raw_object.source_file_name + "\n")
                            # the object "header"
                            compiled_file.write("[" + object_type + ":" + raw_object.object_id + "]\n")
                            # and then all its tokens
                            for token in raw_object.tokens:
                                compiled_file.write("\t[" + ":".join(token) + "]\n")

                # deletes the file if there were no objects written to it
                if objects_in_file_count == 0:
                    compiled_file.close()
                    os.remove(output_path + "/" + object_type_file_names[super_object_type] + "_compiled.txt")
                # otherwise writes down the count at the end
                else:
                    compiled_file.write("\n" + str(objects_in_file_count) + " raw objects in this compiled file.")
                    compiled_file.close()

    def can_get_raw_object(self, object_type, object_id, is_object_template):
        if not is_object_template:
            if object_id not in self.normal_objects[object_type].keys():
                print("Undefined object requested; " + object_type + ":" + object_id)
                return False
        else:
            if object_id not in self.object_templates[object_type].keys():
                print("Undefined object requested; OBJECT_TEMPLATE:" + object_type + ":" + object_id)
                return False
        return True


class SyntaxUpdater:

    def __init__(self):
        # for the raw file currently being updated
        self.file_path = None
        self.lines = None
        self.tokens = None
        self.file_name = None

        self.bdp_leftovers_ids = []
        self.bdp_templates_ids = []

    def update_mods_syntax(self, mods, backup_path):

        overwrite_backups_decided = False
        overwrite_backups = False
        for i in range(len(mods)):
            mod = mods[i]
            if os.path.isdir(backup_path + "\\" + mod.name + " " + mod.version):
                if not overwrite_backups_decided:
                    if input("Found an existing backup for one of the mods. Do you want to overwrite existing "
                             "backups?(Y/N) ").lower() == "y":
                        overwrite_backups = True
                    else:
                        overwrite_backups = False
                    overwrite_backups_decided = True
                if overwrite_backups:
                    print("Making backup of mod " + str(i + 1) + "/" + str(len(mods)) + ": " +
                          mod.name + " " + mod.version)
                    shutil.rmtree(backup_path + "\\" + mod.name + " " + mod.version)
                    shutil.copytree(mod.path, backup_path + "\\" + mod.name + " " + mod.version)
            else:
                print("Making backup of mod " + str(i + 1) + "/" + str(len(mods)) + ": " + mod.name + " " + mod.version)
                shutil.copytree(mod.path, backup_path + "\\" + mod.name + " " + mod.version)

            sorted_file_names = sort_file_names(mod)

            # goes through each file of the mod, in the sorted order
            for j in range(len(sorted_file_names)):
                # opens the file and splits it into tokens
                self.file_name = sorted_file_names[j]
                print("\treading file " + str(j + 1) + "/" + str(len(sorted_file_names)), self.file_name)
                self.file_path = mod.path + "/objects/" + self.file_name
                raw_file = open(self.file_path, "r", encoding="latin1")
                self.lines = raw_file.readlines()
                self.tokens = split_lines_into_tokens(self.lines)
                print(len(self.lines))
                raw_file.close()

                if self.lines[0].startswith("b_detail_plan"):
                    self.update_body_detail_plan()

                elif self.lines[0].startswith("c_variation"):
                    print("Handling", self.file_path)
                    self.update_creature_variation()

                elif self.lines[0].startswith("creature"):
                    #print("Handling", self.file_path)
                    self.update_creature()

                raw_file.close()

    def update_body_detail_plan(self):
        # When it comes to body detail plans, sadly they can't be 100% converted to object templates;
        # this is because unlike all other bdp tokens, corresponding creature tokens don't exist for
        # BP_POSITION and BP_RELATION.

        # First, creates a new object template file and fills it

        # gets the relevant objects
        ot_objects = split_tokens_into_raw_objects_simple(self.tokens, "BODY_DETAIL_PLAN",
                                                          allowed_tokens=convertible_body_detail_plan_tokens,
                                                          skip_empty_objects=True)
        # saves their ids in self.bdp_templates_ids
        self.bdp_templates_ids = [ot_object.object_id for ot_object in ot_objects]
        # and writes the ot file
        ot_file = open(self.file_path.replace("b_detail_plan_", "o_template_bdp_"), "w", encoding="latin1")
        ot_file.write(self.lines[0].replace("b_detail_plan_", "o_template_bdp_"))
        ot_file.write(bdp_templates_disclaimer1 + self.file_name +
                      "\n" + file_disclaimer2)
        ot_file.write("[OBJECT:OBJECT_TEMPLATE]")
        for ot_object in ot_objects:
            # a blank line between each object
            ot_file.write("\n")
            # the object "header"
            ot_file.write("[OBJECT_TEMPLATE:CREATURE:" + ot_object.object_id + "]\n")
            # and then all its tokens
            for token in ot_object.tokens:
                # ADD_MATERIAL => USE_MATERIAL_TEMPLATE
                if token[0] == "ADD_MATERIAL":
                    token[0] = "USE_MATERIAL_TEMPLATE"
                # ADD_TISSUE => USE_TISSUE_TEMPLATE
                elif token[0] == "ADD_TISSUE":
                    token[0] = "USE_TISSUE_TEMPLATE"
                # BP_RELSIZE => RELSIZE
                elif token[0] == "BP_RELSIZE":
                    token[0] = "RELSIZE"
                # ARG => !ARG
                for i in range(len(token)):
                    token[i] = token[i].replace("ARG", "!ARG")
                ot_file.write("\t[" + ":".join(token) + "]\n")
        ot_file.flush()
        ot_file.close()

        # Second, the original bdp file is altered

        # inserts disclaimer
        self.lines.insert(1, bdp_leftover_disclaimer1 + self.file_name.replace("b_detail_plan_", "o_template_bdp_") +
                          "\n" + file_disclaimer2)
        # removes convertible tokens
        for token in convertible_body_detail_plan_tokens:
            self.remove_token(token)
        # if an object has no tokens after that, "comments it out" by removing its left bracket
        self.tokens = split_lines_into_tokens(self.lines)
        bdp_objects = split_tokens_into_raw_objects_simple(self.tokens, "BODY_DETAIL_PLAN",
                                                           skip_empty_objects=False)
        for bdp_object in bdp_objects:
            if len(bdp_object.tokens) == 0:
                pattern = re.compile("\[BODY_DETAIL_PLAN:" + bdp_object.object_id + "\]")
                print("[BODY_DETAIL_PLAN:" + bdp_object.object_id + "]")
                self.lines = [pattern.sub("BODY_DETAIL_PLAN:" + bdp_object.object_id + "] -moved-", line)
                              for line in self.lines]
            else:
                self.bdp_leftovers_ids.append(bdp_object.object_id)
        # and writes the edited file
        raw_file = open(self.file_path, "w", encoding="latin1")
        for line in self.lines:
            raw_file.write(line)
        raw_file.flush()
        raw_file.close()

    def update_creature_variation(self):
        # "c_variation_" => "o_template_cv_" (the first line)
        self.lines[0] = self.lines[0].replace("c_variation_", "o_template_cv_")

        # inserts disclaimer
        self.lines.insert(1, syntax_updated_disclaimer1 + file_disclaimer2)

        # gets a string of ot tokens from the cv tokens of each object
        ot_token_line_chunks = self.get_ot_tokens_line_chunks("CREATURE_VARIATION")
        # finds the indexes to insert at
        cv_indexes = []
        for i in range(len(self.lines)):
            for j in range(self.lines[i].count("[CREATURE_VARIATION:")):
                cv_indexes.append(i+1)
        print(ot_token_line_chunks, cv_indexes)
        print(len(ot_token_line_chunks), len(cv_indexes))
        # inserts the lines starting at the bottom
        for i in range(len(ot_token_line_chunks)):
            self.lines = self.lines[:cv_indexes[-i]] + \
                         ["\t" + line + "\n" for line in ot_token_line_chunks[-i]] + self.lines[cv_indexes[-i]:]

        # removes the cv tokens
        for token_name in creature_variation_tokens:
            self.remove_token(token_name)

        for i in range(len(self.lines)):
            # OBJECT:CREATURE_VARIATION => OBJECT:OBJECT_TEMPLATE
            self.lines[i] = self.lines[i].replace("[OBJECT:CREATURE_VARIATION", "[OBJECT:OBJECT_TEMPLATE")
            # CREATURE_VARIATION:id => OBJECT_TEMPLATE:CREATURE:id
            self.lines[i] = self.lines[i].replace("[CREATURE_VARIATION:", "[OBJECT_TEMPLATE:CREATURE:")

        # "changes name" of the file by removing it and writing to a new one
        os.remove(self.file_path)
        self.file_path = self.file_path.replace("c_variation_", "o_template_cv_")
        # and writes the edited file
        raw_file = open(self.file_path, "w", encoding="latin1")
        for line in self.lines:
            raw_file.write(line)
        raw_file.flush()
        raw_file.close()

    def update_creature(self):
        # inserts disclaimer
        self.lines.insert(1, syntax_updated_disclaimer1 + file_disclaimer2)

        # APPLY_CREATURE_VARIATION => USE_OBJECT_TEMPLATE
        for i in range(len(self.lines)):
            self.lines[i] = self.lines[i].replace("[APPLY_CREATURE_VARIATION:", "[USE_OBJECT_TEMPLATE:")

        # BODY_DETAIL_PLAN => USE_OBJECT_TEMPLATE, when relevant
        self.convert_body_detail_plan_tokens()

        ot_token_line_chunks = self.get_ot_tokens_line_chunks("CREATURE")

        # "accv" for "APPLY_CURRENT_CREATURE_VARIATION"
        accv_indexes_and_indentation = []
        for i in range(len(self.lines)):
            for j in range(self.lines[i].count("[APPLY_CURRENT_CREATURE_VARIATION]")):
                indentation = count_tabs(self.lines[i])
                accv_indexes_and_indentation.append((i, indentation))
        print(ot_token_line_chunks, accv_indexes_and_indentation)
        print(len(ot_token_line_chunks), len(accv_indexes_and_indentation))
        # inserts the lines starting at the bottom
        for i in range(len(ot_token_line_chunks)):
            index = accv_indexes_and_indentation[-i][0]
            indentation = accv_indexes_and_indentation[-i][1]
            self.lines = self.lines[:index] + \
                         ["\t"*indentation + line + "\n" for line in ot_token_line_chunks[-i]] + self.lines[index:]

        # removes APPLY_CURRENT_CREATURE_VARIATION
        self.remove_token("APPLY_CURRENT_CREATURE_VARIATION")
        # removes all creature_variation_tokens
        for token_name in creature_variation_tokens:
            self.remove_token(token_name)

        # and writes the edited file
        raw_file = open(self.file_path, "w", encoding="latin1")
        for line in self.lines:
            raw_file.write(line)
        raw_file.flush()
        raw_file.close()

    def get_ot_tokens_line_chunks(self, object_type):
        # gets the lines of object template tokens to replace creature variation tokens
        # They need to be re-ordered because object templates are handled differently (more direct) than
        # vanilla creature variations, so this is a bit of a hassle.

        # The "line chunks" it returns represents one place where creature tokens would be applied, so either instances
        # of APPLY_CURRENT_CREATURE_VARIATION or singular CREATURE_VARIATION objects.
        ot_token_line_chunks = []

        # some intermediary lists and bools for states
        pending_add_tokens = []
        pending_remove_tokens = []
        pending_convert_tokens = []
        current_convert = []
        current_convert_conditional = ""
        inside_cv_convert = False
        has_closure = True
        for i in range(len(self.tokens)):
            token = self.tokens[i]

            if inside_cv_convert:

                # CVCT_MASTER is baked into OT_CONVERT_TAG (or OT_CONVERT_CTAG) as part of the syntax updating
                if token[0] == "CVCT_MASTER":
                    if current_convert_conditional == "":
                        current_convert = ["[OT_CONVERT_TAG:" + ":".join(token[1:]) + "]"]
                    else:
                        current_convert = ["[OT_CONVERT_CTAG:" + current_convert_conditional + \
                                                  ":".join(token[1:]) + "]"]
                    has_closure = False

                # CVCT_TARGET => OTCT_TARGET
                elif token[0] == "CVCT_TARGET":
                    current_convert.append("\t[OTCT_TARGET:" + ":".join(token[1:]) + "]")
                    has_closure = False

                # CVCT_REPLACEMENT => OTCT_REPLACEMENT
                elif token[0] == "CVCT_REPLACEMENT":
                    current_convert.append("\t\t[OTCT_REPLACEMENT:" + ":".join(token[1:]) + "]")
                    has_closure = False

                else:
                    # they are appended to pending_convert_tokens reversed
                    # (meaning each OT_CONVERT_TAG in pending_convert_tokens comes after the corresponding TARGET
                    # and REPLACEMENT), because pending_convert_tokens is reversed again later
                    pending_convert_tokens += reversed(current_convert)
                    inside_cv_convert = False

            # CV_ADD_TAG, CV_NEW_TAG => OT_ADD_TAG
            if token[0] in ["CV_ADD_TAG", "CV_NEW_TAG"]:
                pending_add_tokens.append("[" + ":".join(["OT_ADD_TAG"] + token[1:]) + "]")
                has_closure = False

            # CV_REMOVE_TAG => OT_REMOVE_TAG
            elif token[0] == "CV_REMOVE_TAG":
                pending_remove_tokens.append("[" + ":".join(["OT_REMOVE_TAG"] + token[1:]) + "]")
                has_closure = False

            # just tells the program it is now inside a cv convert, and resets some strings
            elif token[0] == "CV_CONVERT_TAG":
                current_convert_conditional = ""
                inside_cv_convert = True
                has_closure = False

            # CV_ADD_CTAG, CV_NEW_CTAG => OT_ADD_CTAG
            elif token[0] in ["CV_ADD_CTAG", "CV_NEW_CTAG"]:
                pending_add_tokens.append("[" + ":".join(["OT_ADD_CTAG"] + token[1:]) + "]")
                has_closure = False

            # CV_REMOVE_CTAG => OT_REMOVE_CTAG
            elif token[0] == "CV_REMOVE_CTAG":
                pending_remove_tokens.append("[" + ":".join(["OT_REMOVE_CTAG"] + token[1:]) + "]")
                has_closure = False

            # the same as CV_CONVERT_TAG, but stores the conditional given
            elif token[0] == "CV_CONVERT_CTAG":
                current_convert_conditional = ":".join(token[1:])
                inside_cv_convert = True
                has_closure = False

            if (object_type == "CREATURE" and token[0] == "APPLY_CURRENT_CREATURE_VARIATION") or \
                 (object_type == "CREATURE_VARIATION" and
                  (token[0] == "CREATURE_VARIATION" or i == len(self.tokens) - 1)):
                # constructs the new "line chunk", pending_remove_tokens and pending_convert_tokens
                # are reversed, corresponding to cv removes and converts being read bottom-up
                ot_token_line_chunks.append(list(reversed(pending_remove_tokens)) +
                                            list(reversed(pending_convert_tokens)) +
                                            pending_add_tokens)
                pending_add_tokens = []
                pending_remove_tokens = []
                pending_convert_tokens = []
                current_convert = []
                has_closure = True
                print(i, len(self.tokens) - 1, token[0] == "CREATURE_VARIATION")

            # a check to make sure there is an APPLY_CURRENT_CREATURE_VARIATION to close it off,
            # so the next creature doesn't get the tokens
            elif token[0] == "CREATURE" and not has_closure:
                print("Invalid usage of creature variation tokens in " + self.file_path + "; "
                      "missing instance of APPLY_CURRENT_CREATURE_VARIATION.")
                return []

        # removes redundant OT_CONVERT_TAG and OT_CONVERT_CTAG
        for line_chunk in ot_token_line_chunks:
            redundant_convert_indexes = []
            current_convert_string = ""
            for i in range(len(line_chunk)):
                if line_chunk[i].startswith("[OT_CONVERT_"):
                    if line_chunk[i] == current_convert_string:
                        redundant_convert_indexes.append(i)
                    else:
                        current_convert_string = line_chunk[i]
            for index in reversed(redundant_convert_indexes):
                del line_chunk[index]

        return ot_token_line_chunks

    def remove_token(self, ask_token):
        # this is regex to recognize any of the creature variation tokens (and removing them)
        # the "normal" way of recognizing the tokens by splitting them into lists doesn't work here,
        # because it strips away all comments etc.
        if type(ask_token) == str:
            # pattern 1, token alone on line
            p1 = re.compile("^\s*\[" + ask_token +":?[^\]]*\]\s*$")
            # pattern 2, token not alone on line
            p2 = re.compile("\[" + ask_token + ":?[^\]]*\]")
        elif type(ask_token) == list:
            p1 = re.compile("^\s*\[" + ":".join(ask_token) + ":?[^\]]*\]\s*$")
            p2 = re.compile("\[" + ":".join(ask_token) + ":?[^\]]*\]")
        else:
            raise TypeError("Unexpected type for ask_token, ", type(ask_token), ". Expected str or list.")
        for i in range(len(self.lines)):
            # replaces the appropriate pattern
            if p1.match(self.lines[i]):
                self.lines[i] = p1.sub("", self.lines[i])
            else:
                self.lines[i] = p2.sub("", self.lines[i])

    def convert_body_detail_plan_tokens(self):
        # Either convert (each) BODY_DETAIL_PLAN into USE_OBJECT_TEMPLATE, leave it unchanged, or split it into both,
        # depending on self.bdp_leftovers_ids and self.bdp_templates_ids (whether the bdp were changed/split before)
        pattern = re.compile("\[BODY_DETAIL_PLAN:[^\]]*[\]:]")
        for i in range(len(self.lines)):
            bdp_strings = pattern.findall(self.lines[i])
            for bdp_string in bdp_strings:
                bdp_token = bdp_string[1:-1].split(":")
                replacement_string = ""
                if bdp_token[1] in self.bdp_leftovers_ids:
                    replacement_string += bdp_string
                if bdp_token[1] in self.bdp_templates_ids:
                    replacement_string += "[" + ":".join(["USE_OBJECT_TEMPLATE"] + bdp_token[1:]) + "]"
                self.lines[i] = self.lines[i].replace(bdp_string, replacement_string)


# ====== misc. functions ========================================================================================

def split_file_into_tokens(file):
    # splits the contents of a file into tokens
    # note that calling this reads all the lines, meaning the next file.readlines()/.readline() will return nothing
    return split_lines_into_tokens(list(line for line in file))


def split_lines_into_tokens(lines):
    # does what it sounds like, splits lines (a list of strings, such as from file.readlines()) into tokens,
    # discarding comments along the way
    token_list = []

    file_string = "".join(lines)
    reading_mode = "comments"
    token = ""
    args = ""
    # just goes through each of the characters in the file, switching "reading_mode" when necessary.
    for c in file_string:
        if reading_mode == "comments":
            if c == "[":
                reading_mode = "token"
        elif reading_mode == "token":
            if c == ":":
                reading_mode = "args"
            elif c == "]":
                token_list.append([token])
                token = ""
                reading_mode = "comments"
            else:
                token += c
        elif reading_mode == "args":
            if c == "]":
                token_list.append([token] + args.split(":"))
                token = ""
                args = ""
                reading_mode = "comments"
            else:
                args += c

    return token_list


def split_tokens_into_raw_objects_simple(tokens, object_type, allowed_tokens=None, skip_empty_objects=False):
    # Very simple way to get RawObjects from a list of tokens. They must have a set object type,
    # and EDITs and object templates are not supported.
    raw_objects = []

    co = None
    reading_mode = "NONE"
    for i in range(len(tokens)):
        token = tokens[i]
        # adds tokens to the current object
        if token[0] != object_type and reading_mode == "NEW":
            if allowed_tokens is None:
                co.tokens.append(token)
            else:
                if token[0] in allowed_tokens:
                    co.tokens.append(token)
        # when a new object or the end of the file is encountered
        if token[0] == object_type or i == len(tokens) - 1:
            # finishes the current object before starting to read the next one
            if reading_mode == "NEW":
                if not (skip_empty_objects and len(co.tokens) == 0):
                    raw_objects.append(co)
            co = RawObject(token[1])
            reading_mode = "NEW"

    return raw_objects


def sort_file_names(mod):
    # before the files are read, they are sorted in accordance to the first line,
    # here called the "header"
    # https://dwarffortresswiki.org/index.php/DF2014:Raw_file#Parsing
    file_names_by_header = {header: [] for header in header_load_order}

    for file_name in mod.file_names:
        with open(mod.path + "/objects/" + file_name, "r", encoding="latin1") as f:
            first_line = f.readline()
        file_header = False
        # if there is no proper header, the file is simply ignored
        for header in header_load_order:
            if first_line.startswith(header):
                file_header = header
        if file_header is not False:
            file_names_by_header[file_header].append(file_name)

    # completes the sorting, and returns the list
    sorted_file_names = []
    for header in header_load_order:
        sorted_file_names += file_names_by_header[header]
    return sorted_file_names


def count_tabs(string):
    n = 0
    for c in string:
        if c == "\t":
            n += 1
        else:
            return n
    return n


def select_objects_by_criteria(objects, criteria):
    if len(criteria) == 0:
        print("Error found at unknown location in your raws: selection criteria missing.")

    if criteria[0] == "ALL":
        return objects

    for i in range(len(criteria)):
        # selects a single object
        if criteria[i] == "SEL_BY_ID":
            objects = [raw_object for raw_object in objects
                       if raw_object.object_id == criteria[i + 1]]
        # selects multiple objects
        # ...by object class
        elif criteria[i] == "SEL_BY_CLASS":
            objects = [raw_object for raw_object in objects
                       if (["OBJECT_CLASS", criteria[i + 1]] in raw_object.tokens or
                           ["CREATURE_CLASS", criteria[i + 1]] in raw_object.tokens)]
        # ...by token (and any amount of leading values)
        elif criteria[i] == "SEL_BY_TAG":
            # all the "criteria" between SEL_BY_TAG and the next "SEL_BY" are assumed to be a token
            # and its leading values. For this to be possible, there's an inner loop
            token_values = []
            for j in range(i + 1, len(criteria)):
                if criteria[j] in ["SEL_BY_ID", "SEL_BY_CLASS", "SEL_BY_TAG", "SEL_BY_TAG_PRECISE"]:
                    break
                else:
                    token_values.append(criteria[j])
            objects = [raw_object for raw_object in objects
                       if raw_object.has_token(token_values)]
        # ...by precise token (i.e. like "by token", but instead of leading values, the values specified are the
        #                      *only* values;
        #                      SELECT_BY_TAG_PRECISE:BODY:QUADRUPED_NECK won't select the vanilla toad raws,
        #                      as the toad's BODY token continues after QUADRUPED_NECK.)
        elif criteria[i] == "SEL_BY_TAG_PRECISE":
            token_values = []
            for j in range(i + 1, len(criteria)):
                if criteria[j] in ["SEL_BY_ID", "SEL_BY_CLASS", "SEL_BY_TAG", "SEL_BY_TAG_PRECISE"]:
                    break
                else:
                    token_values.append(criteria[j])
            print(token_values)
            objects = [raw_object for raw_object in objects
                       if token_values in raw_object.tokens]

    # returns the objects that matched the criteria
    return objects
