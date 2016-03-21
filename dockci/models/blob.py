""" Persistent blob storage based on content hash """

import hashlib
import json

from collections import OrderedDict

import py.path  # pylint:disable=import-error

from dockci.util import path_contained


CHUNK_SIZE = 4000


def _copy_data(from_path, to_path, sources):
    """
    Copy data in ``sources`` from a path, to a path preserving directory
    structure

    Examples:

    >>> test_path = getfixture('tmpdir')
    >>> from_path = test_path.join('from')
    >>> to_path = test_path.join('to')
    >>> from_path.ensure_dir()
    local(...)
    >>> to_path.ensure_dir()
    local(...)

    >>> from_file = from_path.join('dockci_doctest_a')
    >>> to_file = to_path.join('dockci_doctest_a')
    >>> from_file.write_binary(b'')

    >>> from_file.chmod(0o755)
    >>> _copy_data(from_path, to_path, [from_file])
    >>> oct(to_file.stat().mode)[-3:]
    '755'
    """
    for from_path_i in sources:
        rel_path_str = from_path_i.relto(from_path)
        to_path_i = to_path.join(rel_path_str)

        to_path_i.dirpath().ensure_dir()
        from_path_i.copy(to_path_i, mode=True)


class FilesystemBlob(object):
    """ On-disk blob data storage used to access data by hash """

    def __init__(self,
                 store_dir,
                 root_path,
                 etag,
                 split_levels=3,
                 split_size=2,
                 ):
        if not isinstance(store_dir, py.path.local):
            store_dir = py.path.local(store_dir)

        self.data_paths = []

        self.store_dir = store_dir
        self.root_path = root_path
        self.etag = etag
        self.split_levels = split_levels
        self.split_size = split_size

    @classmethod
    def from_files(cls,
                   store_dir,
                   root_path,
                   file_paths,
                   meta=None,
                   **kwargs):
        """
        Create a ``FilesystemBlob`` object from file paths, using their hash as
        an etag

        Examples:

        >>> test_path = getfixture('tmpdir')

        >>> first_path_1 = test_path.join('dockci_doctest_a')
        >>> with first_path_1.open('w') as handle:
        ...     handle.write('content')
        7

        >>> second_path_1 = test_path.join('dockci_doctest_b')
        >>> with second_path_1.open('w') as handle:
        ...     handle.write('more content')
        12

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [first_path_1, second_path_1],
        ... ).etag
        'e45315d583e1b7f0a87d890771257d3e4c4b39b8'

        >>> first_path_2 = first_path_1.dirpath().join('dockci_doctest_c')
        >>> first_path_1.move(first_path_2)

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [first_path_2, second_path_1],
        ... ).etag
        'e45315d583e1b7f0a87d890771257d3e4c4b39b8'

        >>> dir_path = test_path.join('dockci_doctest_dir')
        >>> dir_path.ensure_dir()
        local('.../dockci_doctest_dir')

        >>> first_path_3 = dir_path.join('dockci_doctest_a')
        >>> first_path_2.move(first_path_3)
        >>> second_path_3 = dir_path.join('dockci_doctest_b')
        >>> second_path_1.move(second_path_3)

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [first_path_3, second_path_3],
        ... ).etag
        'e45315d583e1b7f0a87d890771257d3e4c4b39b8'

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [second_path_3, first_path_3],
        ... ).etag
        'e45315d583e1b7f0a87d890771257d3e4c4b39b8'

        >>> with first_path_3.open('w') as handle:
        ...     handle.write('different content')
        17

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [second_path_3, first_path_3],
        ... ).etag
        'ac4ee46879f69d4563f7c3237d35df8d87517fb4'

        >>> with second_path_3.open('w') as handle:
        ...     handle.write('more different content')
        22

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [second_path_3, first_path_3],
        ... ).etag
        '8914666e0bfa9fc23d2fb0058db2aafec335caf0'

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [second_path_3, first_path_3],
        ...     meta={'version': '3', 'other': ('things', 'here')}
        ... ).etag
        '204612e03ad9679f1ba0c5857a6059f086c45298'

        >>> FilesystemBlob.from_files(
        ...     None, None,
        ...     [second_path_3, first_path_3],
        ...     meta={'version': '4', 'other': ('things', 'here')}
        ... ).etag
        '880ebbe5e2277acbe15750062277a2538795f186'
        """
        if isinstance(meta, dict):
            meta = OrderedDict([
                (key, meta[key]) for key in sorted(meta.keys())
            ])

        digests = []
        for file_path in file_paths:
            with file_path.open('rb') as handle:
                file_hash = hashlib.sha1(json.dumps(meta).encode())

                chunk = None
                while chunk is None or len(chunk) == CHUNK_SIZE:
                    chunk = handle.read(CHUNK_SIZE)
                    file_hash.update(chunk)

                digests.append(file_hash.digest())

        all_hash = hashlib.sha1()
        for digest in sorted(digests):
            all_hash.update(digest)

        return cls(store_dir, root_path, all_hash.hexdigest(), **kwargs)

    @property
    def _etag_split_iter(self):
        """
        Range object for the split

        Examples:

        >>> list(FilesystemBlob(None, None, None, 3, 2)._etag_split_iter)
        [0, 2, 4]

        >>> list(FilesystemBlob(None, None, None, 4, 2)._etag_split_iter)
        [0, 2, 4, 6]

        >>> list(FilesystemBlob(None, None, None, 3, 3)._etag_split_iter)
        [0, 3, 6]
        """
        return range(0, self.split_levels * self.split_size, self.split_size)

    @property
    def path(self):
        """
        ``py.path.local`` path to the blob

        Examples:

        >>> FilesystemBlob(
        ...     py.path.local('/test'),
        ...     None,
        ...     'abcdefghijkl',
        ... ).path.strpath
        '/test/ab/cd/ef/abcdefghijkl'

        >>> FilesystemBlob(
        ...     py.path.local('/test'),
        ...     None,
        ...     'abcdefghijkl',
        ...     split_levels=4,
        ... ).path.strpath
        '/test/ab/cd/ef/gh/abcdefghijkl'

        >>> FilesystemBlob(
        ...     py.path.local('/test'),
        ...     None,
        ...     'abcdefghijkl',
        ...     split_size=3,
        ... ).path.strpath
        '/test/abc/def/ghi/abcdefghijkl'

        >>> FilesystemBlob(
        ...     py.path.local('/other'),
        ...     None,
        ...     'abcdefghijkl',
        ... ).path.strpath
        '/other/ab/cd/ef/abcdefghijkl'
        """
        return self.store_dir.join(*[
            self.etag[idx:idx + self.split_size]
            for idx in self._etag_split_iter
        ] + [self.etag])

    @property
    def exists(self):
        """ Check if the blob exists already """
        return self.path.exists()

    def add_data(self, rel_path_str):
        """ Add data to store in the blob """
        full_path = self.root_path.join(rel_path_str)
        assert path_contained(self.root_path, full_path), (
            "Data not inside container")
        self.data_paths.append(full_path)

    def extract(self):
        """ Extract data from the blob to the ``root_path`` """
        blob_path = self.path
        _copy_data(blob_path, self.root_path, blob_path.listdir())

    def write(self):
        """ Write data to the blob """
        blob_path = self.path
        blob_path.ensure_dir()
        _copy_data(self.root_path, blob_path, self.data_paths)
