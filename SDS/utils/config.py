#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import cStringIO
import pprint
import os.path
import re
import copy

import SDS.utils.env as env

config = None


def as_project_path(path):
    return os.path.join(env.root(), path)


class Config(object):
    """
    Config handles configuration data necessary for all the components
    in the SDS. It implements a dictionary so that any component could
    store arbitrary structured data.

    When the configuration file is loaded, several automatic transformations
    are applied.
        1) '{cfg_abs_path}' as a substring of atomic attributes is replaced by
            an absolute path of the configuration files.  This can be used to
            make the configuration file independent of the location of programs
            using the configuration file.
    """

    def __init__(self, file_name=None, project_root=False, config={}):
        self.config = config

        if project_root:
            file_name = os.path.join(env.root(), file_name)

        if file_name:
            self.load(file_name)

    def get(self, i, default=None):
        return self.config.get(i, default)

    def __delitem__(self, i):
        del self.config[i]

    def __len__(self):
        return len(self.config)

    def __getitem__(self, i):
        return self.config[i]

    def __setitem__(self, key, val):
        self.config[key] = val

    def __iter__(self):
        for i in self.config:
            yield i

    def __str__(self):
        """ Converts the the config into a pretty print string.

        It removes all lines which include word:
            - password

        to prevent password logging.
        """
        sio = cStringIO.StringIO()
        pprint.pprint(self.config, sio, indent=2, width=120)
        cfg = sio.getvalue()

        cfg = re.sub(r".*password.*", "# this line was removed since it included a password", cfg)

        return cfg

    def contains(self, *path):
        """Check if configuration contains given keys (= path in config tree)."""
        curr = self.config
        for path_part in path:
            if path_part in curr:
                curr = curr[path_part]
            else:
                return False

        return True

    def load(self, file_name):
        """FIXME: Executing external files is not ideal! It should be changed in the future!
        """
        # pylint: disable-msg=E0602

        global config
        config = None

        execfile(file_name, globals())
        assert config is not None
        self.config = config

        cfg_abs_dirname = os.path.dirname(os.path.abspath(file_name))
        print cfg_abs_dirname, self.config
        self.config_replace('{cfg_abs_path}', cfg_abs_dirname)

        self.load_includes()



    def load_includes(self):
        if not self.contains("General", "include"):
            return
        for include in self["General"]["include"]:
            self.merge(include)


    def merge(self, other):
        """Merges self's config with other's config and saves it as a new
        self's config.

        Keyword arguments:
            - other: a Config object whose configuration dictionary to merge
                     into self's one
        """
        # pylint: disable-msg=E0602
        if type(other) is str:
            other = Config(other)
        self.update(other.config)

    def update(self, new_config, config_dict=None):
        """Updates the nested configuration dictionary by another, potentially
        also nested dictionary.

        Keyword arguments:
            - new_config: the new dictionary to update with
            - config_dict: the config dictionary to be updated

        """
        if config_dict is None:
            config_dict = self.config
        for key, val in new_config.iteritems():
            if isinstance(val, collections.Mapping):
                subdict = self.update(val, config_dict.get(key, {}))
                config_dict[key] = subdict
            else:
                config_dict[key] = new_config[key]
        return config_dict

    def config_replace(self, p, s, d=None):
        """\
        Replace a pattern p with string s in the whole config
        (recursively) or in a part of the config given in d.

        """

        print 'replacing', p, s
        if d is None:
            d = self.config
        for k, v in d.iteritems():
            if isinstance(v, collections.Mapping):
                self.config_replace(p, s, v)
            elif isinstance(v, str):
                d[k] = d[k].replace(p, s)
        return

    def unfold_lists(self, pattern, unfold_id_key=None, part=[]):
        """\
        Unfold lists under keys matching the given pattern
        into several config objects, each containing one item.
        If pattern is None, all lists are expanded.

        Stores a string representation of the individual unfolded values
        under the unfold_id_key if this parameter is set.

        Only expands a part of the whole config hash (given by list of
        keys forming a path to this part) if the path parameter is set.
        """
        # find the part of the config we're dealing with
        dict_to_unfold = self.config
        for key in part:
            dict_to_unfold = dict_to_unfold[key]
        # go through it and search for lists to unfold
        for k, v in dict_to_unfold.iteritems():
            # unfold lists
            if type(v) is list and (pattern is None or re.search(pattern, k)):
                unfolded = []
                for item in v:
                    # create a copy and replace with the unfolded item
                    ci = Config(config=copy.deepcopy(self.config))
                    target_dict = ci
                    for key in part:
                        target_dict = target_dict[key]
                    target_dict[k] = item
                    # store the value of the unfolded items under the given key
                    if unfold_id_key is not None:
                        str_rep = str(item)
                        ci[unfold_id_key] = ci[unfold_id_key] + '_' + str_rep \
                                            if unfold_id_key in ci else str_rep
                    # unfold other variables
                    unfolded.extend(ci.unfold_lists(pattern, unfold_id_key))
                return unfolded
            # recurse deeper into dictionaries
            elif type(v) is dict:
                return self.unfold_lists(pattern, unfold_id_key, part + [k])
        return [self]
