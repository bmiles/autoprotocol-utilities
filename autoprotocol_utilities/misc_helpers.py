from autoprotocol import UserError
from collections import namedtuple
import datetime
import sys

if sys.version_info[0] >= 3:
    string_type = str
else:
    string_type = basestring


def user_errors_group(error_msgs):
    """Takes a list error messages and neatly displays as a single UserError

    Parameters
    ----------
    error_msgs : list
        List of strings that are the error messages

    """
    assert isinstance(error_msgs, list), ("Error messages must be in the form"
                                          " of a list to properly format the "
                                          "grouped message.")
    if len(error_msgs) != 0:
        raise UserError(
            "%s error(s) found in this protocol: " % len(error_msgs) +
            " ".join(["<Error " +
                      str(i + 1) + "> " +
                      str(m) for i, m in enumerate(error_msgs)]))


def printdatetime():
    """
    Generate a datetime string

    Returns
    -------
    printdate : str

    """
    printdate = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    return printdate


def printdate():
    """
    Generate a date string

    Returns
    -------
    printdate : str

    """
    printdate = datetime.datetime.now().strftime('%Y-%m-%d')
    return printdate


def make_list(my_str, integer=False):
    """
    Sometimes you need a list of a type that is not supported.

    Parameters
    ----------
    my_str : string
        String with individual elements separated by comma
    interger : bool
        If true list of integers instead of list of strings
        is returned.

    Returns
    -------
    my_str : list
        List of strings or integers

    """
    assert isinstance(my_str, string_type), "Input needs to be of type string"
    if integer:
        my_str = [int(x.strip()) for x in my_str.split(",")]
    else:
        my_str = [x.strip() for x in my_str.split(",")]
    return my_str


def flatten_list(l):
    """
    Flatten a list recursively without for loops or additional modules

    Parameters
    ---------
    l : list
        List to flatten

    Returns
    -------
    list : list
        Flat list

    """
    if l == []:
        return l
    if isinstance(l[0], list):
        return flatten_list(l[0]) + flatten_list(l[1:])
    return l[:1] + flatten_list(l[1:])


def det_new_group(i, base=0):
    """Determine if new_group should be added to pipetting operation.

    Helper to determine if new_group should be added. Returns true when
    i matches the base, which defaults to 0.

    Parameters
    ----------
    i : int
        The iteration you are on
    base : int, optional
        The value at which you want to trigger

    Returns
    -------
    new_group : bool

    """
    assert isinstance(i, int), "Needs an integer."
    assert isinstance(base, int), "Base has to be an integer"
    if i == base:
        new_group = True
    else:
        new_group = False
    return new_group


def char_limit(label, length=22, trunc=False, clip=False):
    """Enforces a string limit on the label provided

    Parameters
    ----------
    label : str
        String to test
    length : int, optional
        Maximum label length for this string. Default: 22
    trunc : bool, optional
        Truncate the label if it is too long. Default off.
    clip : bool, optional
        Clip the label (remove from beginning of the string) if it is too long
        Default off. If both trunc and clip are True, trunc will take effect
        and not clip.

    Returns
    -------
    Response : namedtuple
        `label` (str) and `error_message` (string) that is empty on success
        `label` is the unmodified, truncated to clipped label as indicated

    """
    assert isinstance(label, string_type), "Label has to be of type string"

    r = namedtuple('Response', 'label error_message')
    if trunc and len(label) > length:
        label = label[0: length]
    if clip and len(label) > length:
        label = label[len(label) - length: len(label)]

    error_message = None
    if len(label) > length:
        error_message = ("The specified label, '%s', has too many characters."
                         " Please enter a label of %s or fewer "
                         "characters.") % (label, length)

    return r(label=label, error_message=error_message)


def recursive_search(params, class_name=None, method=None, args={}):
    """
    Iterates through all items of a passed in dict, tuple, or list
    and returns all, optional subset or calls a method on a subset

    Parameters
    ----------
    params : list, tuple or dict
        Structure to parse
    class_name : Class name, optional
        Optionally return only instances of a class.
    method : function, optional
        A function that will be applied to all instances found of a class, must include class name.
    args : parameters, optional
        Parameters to pass to a method, if desired.

    Returns
    -------
    found_fields : list
        Will return a list of all items, or the found items of a specified class, or the
        response (if not None) from a method called on found items.

    Example
    -------

            .. code-block:: python

            recursive_search(params, Well, volume_check, args={"usage_volume": 1500})

    """

    all_fields = []

    def find_all_fields(params):
        if isinstance(params, dict):
            for key, value in params.iteritems():
                all_fields.append(key)
                find_all_fields(value)
        elif isinstance(params, list) or isinstance(params, tuple):
            for item in params:
                find_all_fields(item)
        else:
            all_fields.append(params)

    find_all_fields(params)

    if class_name:
        found_instances = []
        for field in all_fields:
            if isinstance(field, class_name):
                found_instances.append(field)
        if method:
            method_msgs = []
            if hasattr(method, '__call__'):
                for found in found_instances:
                    response = method(found, **args)
                    if response is not None:
                        method_msgs.append(response)
            return method_msgs
        else:
            return found_instances
    else:
        return all_fields