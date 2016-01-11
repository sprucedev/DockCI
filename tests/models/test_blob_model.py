import py.path
import pytest

from dockci.models.blob import FilesystemBlob


class TestFiresystemBlob(object):
    """ Test the ``FilesystemBlob`` class """
    def test_write(self, tmpdir):
        """ Test that ``FilesystemBlob.write`` copies all files """
        store_path = tmpdir.join('store').ensure_dir()
        root_path = tmpdir.join('root').ensure_dir()
        blob = FilesystemBlob(store_path, root_path, 'abcdefghi')

        root_path.join('file_a').write('content a')
        root_path.join('dir_a').ensure_dir().join('file_b').write('content b')

        blob.add_data('file_a')
        blob.add_data('dir_a/file_b')

        blob.write()

        assert blob.path.join('file_a').read() == 'content a'
        assert blob.path.join('dir_a', 'file_b').read() == 'content b'

    def test_extract(self, tmpdir):
        """ Test that ``FilesystemBlob.extract`` copies all files """
        store_path = tmpdir.join('store').ensure_dir()
        root_path = tmpdir.join('root').ensure_dir()
        blob = FilesystemBlob(store_path, root_path, 'abcdefghi')

        blob.path.ensure_dir()
        blob.path.join('file_a').write('content a')
        blob.path.join('dir_a').ensure_dir().join('file_b').write('content b')

        blob.extract()

        assert root_path.join('file_a').read() == 'content a'
        assert root_path.join('dir_a/file_b').read() == 'content b'

    def test_add_uncontained_path(self):
        blob = FilesystemBlob(py.path.local(), py.path.local(), 'abcdefghi')

        with pytest.raises(AssertionError):
            blob.add_data('..')
