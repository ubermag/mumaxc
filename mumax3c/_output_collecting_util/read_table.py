import re

import pandas as pd
import ubermagtable


def table_from_file(filename, /, x=None, rename=True):
    """Convert a mumax3 ``.txt`` scalar data file into a ``ubermagtable.Table``.

    Parameters
    ----------
    filename : str

        mumax3 ``.txt`` file.

    x : str, optional

        Independent variable name. Defaults to ``None``.

    rename : bool, optional

        If ``rename=True``, the column names are renamed with their shorter
        versions. Defaults to ``True``.

    Returns
    -------
    ubermagtable.Table

        Table object.

    TODO: update example
    Examples
    --------
    1. Defining ``ubermagtable.Table`` by reading an OOMMF ``.odt`` file.

    >>> import os
    >>> import ubermagtable as ut
    ...
    >>> odtfile = os.path.join(os.path.dirname(__file__),
    ...                        'tests', 'test_sample',
    ...                        'oommf-hysteresis1.odt')
    >>> table = ut.Table.fromfile(odtfile, x='B_hysteresis')

    2. Defining ``ubermagtable.Table`` by reading a mumax3 ``.txt`` file.

    >>> odtfile = os.path.join(os.path.dirname(__file__),
    ...                        'tests', 'test_sample', 'mumax3-file1.txt')
    >>> table = ut.Table.fromfile(odtfile, x='t')

    """
    quantities = _read_header(filename, rename=rename)
    data = pd.read_csv(
        filename,
        sep=r"\s+",
        comment="#",
        header=None,
        names=list(quantities.keys()),
    )
    return ubermagtable.Table(data=data, units=quantities, x=x)


def _read_header(filename, rename=True):
    """Extract quantities for individual columns from a table file.

    This method extracts both column names and units and returns a dictionary,
    where keys are column names and values are the units.

    Parameters
    ----------
    filename : str

        OOMMF ``.odt`` or mumax3 ``.txt`` file.

    rename : bool

        If ``rename=True``, the column names are renamed with their shorter
        versions. Defaults to ``True``.

    Returns
    -------
    dict

        Dictionary of column names and units.
    """

    with open(filename) as f:
        header_line_1 = f.readline()

    header_line_1 = header_line_1[len("# ") :].rstrip().split("\t")
    # COLUMN NAMES
    cols = [elem.split()[0] for elem in header_line_1]
    # UNITS
    units = [re.sub(r"[()]", "", elem.split()[1]) for elem in header_line_1]

    if rename:
        cols = [_rename_column(col, _MUMAX3_DICT) for col in cols]

    return dict(zip(cols, units))


def _rename_column(name, cols_dict):
    """Rename columns to get shorter names without spaces.

    Renaming is based on _MUMAX3_DICT.
    """
    return cols_dict.get(name, name)


# The mumax3 columns are renamed according to this dictionary.
_MUMAX3_DICT = {
    "t": "t",
    "mx": "mx",
    "my": "my",
    "mz": "mz",
    "E_total": "E",
    "E_exch": "E_totalexchange",
    "E_demag": "E_demag",
    "E_Zeeman": "E_zeeman",
    "E_anis": "E_totalanisotropy",
    "dt": "dt",
    "maxTorque": "maxtorque",
}
