import os

object_types = {"BODY_DETAIL_PLAN": ["BODY_DETAIL_PLAN"],
                "BODY": ["BODY",
                         "BODYGLOSS"],
                "BUILDING": ["BUILDING_WORKSHOP"],
                "CREATURE_VARIATION": ["CREATURE_VARIATION"],
                "CREATURE": ["CREATURE"],
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
                # for the modloader, does not exist in vanilla
                "OBJECT_VARIATION": ["OBJECT_VARIATION"]}

object_type_file_names = {"BODY_DETAIL_PLAN": "b_detail_plan",
                          "BODY": "body",
                          "BUILDING": "building",
                          "CREATURE_VARIATION": "c_variation",
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
# o_variation has been added to the top, so they are always loaded first
header_load_order = ["o_variation",
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
                     "interaction"]


# ====== classes  ===========================================================================================

class RawObject:

    def __init__(self, object_id, tokens=None, source_file_name=None, source_mod_name_and_version=None):
        self.object_id = object_id
        if tokens is None:
            self.tokens = []
        self.source_file_name = source_file_name
        self.source_mod_name_and_version = source_mod_name_and_version

    def has_token(self, token_name):
        for token in self.tokens:
            if token[0] == token_name:
                return True
        return False

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
        self.file_names = [filename for filename in os.listdir(path + "/objects") if filename.endswith(".txt")]


class Compiler:

    def __init__(self):
        # the objects are ordered
        self.top_level_objects = {object_type: []
                                  for object_type in
                                  # this just flattens the list of object_types.values()
                                  [val for sublist in object_types.values() for val in sublist]}

        # but it's still nice to be able to refer to them using ID
        self.top_level_objects_dicts = {object_type: {}
                                        for object_type in
                                        # this just flattens the list of object_types.values()
                                        [val for sublist in object_types.values() for val in sublist]}

    def compile_mods(self, mods, output_path):

        # goes through each mod, see Compiler.read_mod_raws() for most of the raw handling
        for i in range(len(mods)):
            print("reading mod " + str(i + 1) + "/" + str(len(mods)), mods[i].name)
            self.read_mod_raws(mods[i])

        # writes the compiled objects into one "_compiled.txt" for each super object type
        for super_object_type in object_types:
            # Object variations and creature variations are not outputted;
            # the former is a custom object type not recognized by DF, and does nothing outside of compilation,
            # the latter are also already compiled by this tool, and have no further use.
            if super_object_type not in ["OBJECT_VARIATION", "CREATURE_VARIATION"]:
                # opens the file for writing
                compiled_file = open(output_path + "/" + object_type_file_names[super_object_type] + "_compiled.txt",
                                     "w", encoding="latin1")
                compiled_file.write(object_type_file_names[super_object_type] + "_compiled" + "\n\n"
                                    "[OBJECT:" + super_object_type + "]" + "\n")

                objects_in_file_count = 0

                for object_type in object_types[super_object_type]:
                    # writes each raw object of that object type *in order*
                    for raw_object in self.top_level_objects[object_type]:
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

    def read_mod_raws(self, mod):

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

        # completes the sorting
        sorted_file_names = []
        for header in header_load_order:
            sorted_file_names += file_names_by_header[header]

        # goes through each file of the mod, in the sorted order
        for i in range(len(sorted_file_names)):
            # opens the file and splits it into tokens
            print("\treading file " + str(i + 1) + "/" + str(len(sorted_file_names)), sorted_file_names[i])
            file_name = sorted_file_names[i]
            raw_file = open(mod.path + "/objects/" + file_name, "r", encoding="latin1")
            raw_file_tokens = split_file_into_tokens(raw_file)

            # initially it doesn't know what object types to expect
            # and it has to know, because e.g. "COLOR" is both an object type and a common token elsewhere.
            pos_object_types = []

            # reading_mode is either "NONE", "NEW" or "EDIT"
            reading_mode = "NONE"
            current_objects = []
            current_object_type = False
            # for object variations
            ov_insertion_indexes = []
            pending_ov_token_lists = []

            # goes through all tokens
            for j in range(len(raw_file_tokens)):
                token = raw_file_tokens[j]
                # the "OBJECT" token tells it what object types to expect
                if token[0] == "OBJECT":
                    pos_object_types = object_types[token[1]]

                # if it's already reading an object, and it's not changing, append the current token to that object's
                # list of tokens
                elif reading_mode != "NONE" and token[0] not in pos_object_types:
                    for k in range(len(current_objects)):
                        co = current_objects[k]

                        # Nesting object variations is just silly (and difficult code-wise)
                        if current_object_type == "OBJECT_VARIATION":
                            co.tokens.append(token)

                        # object(/creature) variation handling, as well as other "special" tokens like GO_TO_START
                        else:
                            if token[0] == "APPLY_OBJECT_VARIATION":
                                if self.can_get_top_level_object("OBJECT_VARIATION", token[1]):
                                    object_variation = self.top_level_objects_dicts["OBJECT_VARIATION"][token[1]]
                                    co.tokens, ov_insertion_indexes[k] = \
                                        apply_object_variation(co.tokens, ov_insertion_indexes[k],
                                                               object_variation.tokens, token[2:])
                            # "Creature variation tokens" are mostly treated as 100% interchangable for their
                            # object variation counterparts. This here is the only exception, as
                            # "APPLY_CREATURE_VARIATION" reads a "CREATURE_VARIATION" object, while
                            # "APPLY_OBJECT_VARIATION" reads an "OBJECT_VARIATION" object.
                            elif token[0] == "APPLY_CREATURE_VARIATION":
                                if self.can_get_top_level_object("CREATURE_VARIATION", token[1]):
                                    object_variation = self.top_level_objects_dicts["CREATURE_VARIATION"][token[1]]
                                    co.tokens, ov_insertion_indexes[k] = \
                                        apply_object_variation(co.tokens, ov_insertion_indexes[k],
                                                               object_variation.tokens, token[2:])

                            elif token[0] in ["APPLY_CURRENT_OBJECT_VARIATION", "APPLY_CURRENT_CREATURE_VARIATION"]:
                                co.tokens, ov_insertion_indexes[k] = \
                                    apply_object_variation(co.tokens, ov_insertion_indexes[k],
                                                           pending_ov_token_lists[k], [])

                            elif token[0] == "COPY_TAGS_FROM":
                                if self.can_get_top_level_object(current_object_type, token[1]):
                                    source_object = self.top_level_objects_dicts[current_object_type][token[1]]
                                    for copy_token in source_object.tokens:
                                        co.tokens.insert(ov_insertion_indexes[k], copy_token)
                                        ov_insertion_indexes[k] += 1

                            # not applied until the next "APPLY_CURRENT_OBJECT/CREATURE_VARIATION"
                            # The latter set are what creature variation objects are made of,
                            # so they are not treated as special tokens if that's what's being read.
                            elif token[0] in ["OV_ADD_TAG", "OV_NEW_TAG", "OV_REMOVE_TAG",
                                              "OV_CONVERT_TAG",
                                              "OVCT_MASTER", "OVCT_TARGET", "OVCT_REPLACEMENT"] or \
                                (token[0] in ["CV_ADD_TAG", "CV_NEW_TAG", "CV_REMOVE_TAG",
                                              "CV_CONVERT_TAG",
                                              "CVCT_MASTER", "CVCT_TARGET", "CVCT_REPLACEMENT"] and
                                 current_object_type != "CREATURE_VARIATION"):
                                pending_ov_token_lists[k].append(token)

                            elif token[0] == "GO_TO_END":
                                ov_insertion_indexes[k] = len(co.tokens)

                            elif token[0] == "GO_TO_START":
                                ov_insertion_indexes[k] = 0

                            elif token[0] == "GO_TO_TAG":
                                goto_tag = token[1:]
                                goto_finished = False
                                i = 0
                                while not goto_finished and i < len(co.tokens):
                                    if co.tokens[i] == goto_tag:
                                        ov_insertion_indexes[k] = i
                                        goto_finished = True
                                    i += 1

                            # if it weren't a special token, just inserts it into the list of tokens
                            else:
                                co.tokens.insert(ov_insertion_indexes[k], token)
                                ov_insertion_indexes[k] += 1

                # if it finds a new object or it is the last line in the file
                if token[0] in pos_object_types or j == len(raw_file_tokens) - 1:
                    # finishes the current object before starting to read the next one
                    if reading_mode == "NEW":
                        for co in current_objects:
                            self.top_level_objects[current_object_type].append(co)
                            self.top_level_objects_dicts[current_object_type][co.object_id] = co

                    if token[0] in pos_object_types:
                        # always the same, regardless of kind of raw entry ("NEW", "EDIT" or whatever)
                        current_object_type = token[0]

                        # start of a new object, the vanilla way
                        if len(token) == 2:
                            current_objects = [RawObject(token[1], source_file_name=file_name,
                                                         source_mod_name_and_version=mod.name + " " + mod.version)]
                            reading_mode = "NEW"

                        else:
                            # selects out the "current objects" before knowing what to do with them
                            # if you're not plus-selecting, resets the current objects before
                            if token[1] != "PLUS_SELECT":
                                current_objects = []
                            # selects all objects of that object type (which have hitherto been defined)
                            if token[2] == "ALL":
                                current_objects = [raw_object for raw_object in
                                                   self.top_level_objects[current_object_type]]
                            # selects a single object
                            elif token[2] == "BY_ID":
                                if self.can_get_top_level_object(current_object_type, token[3]):
                                    current_objects += [self.top_level_objects_dicts[current_object_type][token[3]]]
                            # selects multiple objects
                            # ...by object class
                            elif token[2] == "BY_CLASS":
                                current_objects += [raw_object for raw_object in
                                                    self.top_level_objects[current_object_type]
                                                    if (["OBJECT_CLASS", token[3]] in raw_object.tokens or
                                                        ["CREATURE_CLASS", token[3]] in raw_object.tokens)]
                            # ...by token
                            elif token[2] == "BY_TOKEN":
                                current_objects += [raw_object for raw_object in
                                                    self.top_level_objects[current_object_type]
                                                    if raw_object.has_token(token[3])]
                            # ...by precise token (i.e. token with all the values the same as well)
                            elif token[2] == "BY_TOKEN_PRECISE":
                                current_objects += [raw_object for raw_object in
                                                    self.top_level_objects[current_object_type]
                                                    if token[3:] in raw_object.tokens]

                            # if it wasn't able to find any applicable objects
                            if len(current_objects) == 0:
                                reading_mode = "NONE"

                            elif token[1] == "EDIT":
                                reading_mode = "EDIT"

                            elif token[1] == "REMOVE":
                                # removes the objects immediately
                                for co in current_objects:
                                    self.top_level_objects[current_object_type].remove(co)
                                    del self.top_level_objects_dicts[current_object_type][co.object_id]
                                reading_mode = "NONE"

                        # resets the object variation related stuff
                        ov_insertion_indexes = [len(co.tokens) for co in current_objects]
                        pending_ov_token_lists = [[]] * len(current_objects)

    def can_get_top_level_object(self, object_type, object_id):
        if object_id not in self.top_level_objects_dicts[object_type].keys():
            print("Undefined object requested; " + object_type + ":" + object_id)
            return False
        return True


class ObjectVariationConvert:

    def __init__(self, master, target, replacement):
        self.master = master
        self.target = target
        if replacement is None:
            replacement = ""
        self.replacement = replacement


# ====== misc. functions ========================================================================================

def split_file_into_tokens(file):
    # does what it sounds like, splits a text file into tokens, discarding comments along the way
    token_list = []

    file_string = "".join(list(line for line in file))
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


def apply_object_variation(new_tokens, insertion_index, ov_tokens, exclamation_args):
    # print(new_tokens, insertion_index)

    # Object variations work like creature variation tokens do in "vanilla" raws
    # see: https://dwarffortresswiki.org/index.php/DF2014:Creature_variation_token
    # The difference is that all tokens start with "OV" (for object variation)
    # instead of with "CV" (for creature variation).
    # It should be noted that this function handles creature variations as well, despite the name.
    # The cv tokens are treated here as synonyms to the corresponding ov token.

    # "Exclamation args" are the ones like !ARG1, !ARG2 etc.
    for i in range(len(exclamation_args)):
        exclamation_args[i] = exclamation_args[i].replace("|", ":")
    # sets up a dictionary for later insertions/replacements
    exclamation_arg_dict = {"!ARG" + str(i + 1): exclamation_args[i] for i in range(len(exclamation_args))}

    # "pending" list of tokens to remove
    pending_ov_remove_tokens = []
    # stuff for the ov converts
    pending_ov_converts = []
    inside_ov_convert = False
    ov_convert_master = None
    ov_convert_target = None
    ov_convert_replacement = None
    # "pending" list of tokens to add
    pending_ov_add_tokens = []

    for i in range(len(ov_tokens)):
        ov_token = ov_tokens[i]
        # print(ov_token)
        # inserts the exclamation args
        for exclamation_arg in exclamation_arg_dict:
            ov_token = [ov_token_arg.replace(exclamation_arg, exclamation_arg_dict[exclamation_arg])
                        for ov_token_arg in ov_token]

        # regarding the ov_converts
        if inside_ov_convert:

            if ov_token[0] in ["OVCT_MASTER",
                               "CVCT_MASTER"]:
                ov_convert_master = ov_token[1]

            elif ov_token[0] in ["OVCT_TARGET",
                                 "CVCT_TARGET"]:
                ov_convert_target = ":".join(ov_token[1:])

            elif ov_token[0] in ["OVCT_REPLACEMENT",
                                 "CVCT_REPLACEMENT"]:
                ov_convert_replacement = ":".join(ov_token[1:])

            if i == len(ov_tokens) - 1 or ov_token[0] not in ["OVCT_MASTER", "OVCT_TARGET", "OVCT_REPLACEMENT",
                                                              "CVCT_MASTER", "CVCT_TARGET", "CVCT_REPLACEMENT"]:
                # they are appended normally here, but applied in "reverse order" later,
                # as cv converts are in the actual game
                pending_ov_converts.append(ObjectVariationConvert(ov_convert_master,
                                                                  ov_convert_target,
                                                                  ov_convert_replacement))
                ov_convert_master = None
                ov_convert_target = None
                ov_convert_replacement = None
                inside_ov_convert = False

        if ov_token[0] in ["OV_ADD_TAG", "OV_NEW_TAG",
                           "CV_ADD_TAG", "CV_NEW_TAG"]:
            # appends the token to pending_ov_add_tokens (but not "OV_ADD_TAG"/"OV_NEW_TAG")
            pending_ov_add_tokens.append(ov_token[1:])

        elif ov_token[0] in ["OV_REMOVE_TAG",
                             "CV_REMOVE_TAG"]:
            # appends the token to pending_ov_remove_tokens (but not "OV_REMOVE_TAG")
            pending_ov_remove_tokens.append(ov_token[1:])

        elif ov_token[0] in ["OV_CONVERT_TAG",
                             "CV_CONVERT_TAG"]:
            inside_ov_convert = True

        # These three "_CTAG" tokens are like the corresponding "_TAG" tokens above, but with the condition that
        # a numbered argument must be equal to a set value.
        # E.g. "[OV_ADD_CTAG:2:TREE:SPRING]" will only add SPRING if the second argument is "TREE".

        elif ov_token[0] in ["OV_ADD_CTAG", "OV_NEW_CTAG",
                             "CV_ADD_CTAG", "CV_NEW_CTAG"]:
            try:
                int(ov_token[1])
            except ValueError:
                print("Incorrect usage of " + ov_token[0] + "; " + ov_token[1] + " is not an integer. " +
                      ":".join(ov_token))
            else:
                if exclamation_args[int(ov_token[1])-1] == ov_token[2]:
                    pending_ov_add_tokens.append(ov_token[3:])

        elif ov_token[0] in ["OV_REMOVE_CTAG",
                             "CV_REMOVE_CTAG"]:
            try:
                int(ov_token[1])
            except ValueError:
                print("Incorrect usage of " + ov_token[0] + "; " + ov_token[1] + " is not an integer. "
                      + ":".join(ov_token))
            else:
                if exclamation_args[int(ov_token[1]) - 1] == ov_token[2]:
                    pending_ov_remove_tokens.append(ov_token[3:])

        elif ov_token[0] in ["OV_CONVERT_CTAG",
                             "CV_CONVERT_CTAG"]:
            try:
                int(ov_token[1])
            except ValueError:
                print("Incorrect usage of " + ov_token[0] + "; " + ov_token[1] + " is not an integer. "
                      + ":".join(ov_token))
            else:
                if exclamation_args[int(ov_token[1]) - 1] == ov_token[2]:
                    # debug text:
                    # print(exclamation_args[int(ov_token[1]) - 1] + "==" + ov_token[2] +
                    #       "\t[" + ", ".join(exclamation_args) + "]")
                    inside_ov_convert = True

    # first, removal of marked tokens (in reverse order, from the "bottom")
    for ov_remove_token in reversed(pending_ov_remove_tokens):
        len_before = len(new_tokens)

        new_tokens = [new_token for new_token in new_tokens
                      if new_token[0:len(ov_remove_token)] != ov_remove_token]

        # adjusts insertion_index, makes sure it doesn't go negative
        insertion_index -= len(new_tokens) - len_before
        if insertion_index < 0:
            insertion_index = 0

    # second, applies ov_converts (in reverse order, from the "bottom")
    for ov_convert in reversed(pending_ov_converts):
        for i in range(len(new_tokens)):
            if new_tokens[i][0] == ov_convert.master:
                # joins the args temporarily, so a series of args can be targeted for replacement
                args = ":".join(new_tokens[i][1:])
                if ov_convert.target in args:
                    args = args.replace(ov_convert.target, ov_convert.replacement)
                    new_tokens[i] = [new_tokens[i][0]] + [arg for arg in args.split(":") if arg != ""]
                # debug text:
                # print(ov_convert.target + " => " + ov_convert.replacement)

    # third, adding marked tokens (in non-reversed order, from the "top")
    for ov_add_token in pending_ov_add_tokens:
        # exclamation args containing a "|"/":" are split into before being added
        true_add_token = []
        for arg in ov_add_token:
            true_add_token += arg.split(":")
        new_tokens.insert(insertion_index, true_add_token)
        insertion_index += 1

    # and finally makes sure these two are updated
    return new_tokens, insertion_index
