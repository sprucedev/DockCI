import io
import json
import subprocess

import docker
import pytest

from dockci.util import (add_to_url_path,
                         client_kwargs_from_config,
                         parse_ref,
                         )


class TestClientKwargsFromConfig(object):
    """ Tests for ``dockci.util.client_kwargs_from_config`` """
    @pytest.mark.parametrize('host_str,expected,expected_tls_dict', (
        ('https://localhost', {'base_url': 'https://localhost'}, {}),
        (
            'https://localhost assert_hostname=no',
            {'base_url': 'https://localhost'},
            {
                'assert_fingerprint': None,
                'assert_hostname': False,
                'ssl_version': 5,
            },
        ),
        (
            'https://localhost ssl_version=TLSv1',
            {'base_url': 'https://localhost'},
            {
                'assert_fingerprint': None,
                'assert_hostname': None,
                'ssl_version': 3,
            },
        ),
        (
            'https://localhost verify=no',
            {'base_url': 'https://localhost'},
            {
                'assert_fingerprint': None,
                'assert_hostname': None,
                'ssl_version': 5,
                'verify': False,
            },
        ),
        (
            'https://localhost assert_hostname=no ssl_version=TLSv1',
            {'base_url': 'https://localhost'},
            {
                'assert_fingerprint': None,
                'assert_hostname': False,
                'ssl_version': 3,
            },
        ),
    ))
    def test_parse_host_str(self,
                            host_str,
                            expected,
                            expected_tls_dict,
                            ):
        """ Test basic ``host_str`` parsing; no surprises """
        out = client_kwargs_from_config(host_str)
        out_tls = out.pop('tls', {})

        try:
            out_tls = out_tls.__dict__
        except AttributeError:
            pass

        assert out == expected
        assert out_tls == expected_tls_dict

    def test_parse_host_str_certs(self, tmpdir):
        """ Test setting all certificates """
        tmpdir.join('cert.pem').ensure()
        tmpdir.join('key.pem').ensure()
        tmpdir.join('ca.pem').ensure()

        out = client_kwargs_from_config(
            'http://l cert_path=%s' % tmpdir.strpath
        )

        assert out['tls'].cert == (
            tmpdir.join('cert.pem').strpath,
            tmpdir.join('key.pem').strpath,
        )
        assert out['tls'].verify == tmpdir.join('ca.pem').strpath

    @pytest.mark.parametrize('host_str_fs', (
        'http://l verify=no cert_path={cert_path}',
        'http://l cert_path={cert_path} verify=no',
    ))
    def test_no_verify_no_ca(self, host_str_fs, tmpdir):
        """ Test that ``verify=no`` overrides ``cert_path`` """
        tmpdir.join('cert.pem').ensure()
        tmpdir.join('key.pem').ensure()
        tmpdir.join('ca.pem').ensure()

        out = client_kwargs_from_config(
            host_str_fs.format(cert_path=tmpdir.strpath),
        )

        assert out['tls'].cert == (
            tmpdir.join('cert.pem').strpath,
            tmpdir.join('key.pem').strpath,
        )
        assert out['tls'].verify == False

    def test_certs_error(self, tmpdir):
        """ Test raising ``TLSParameterError`` when certs don't exist """
        with pytest.raises(docker.errors.TLSParameterError):
            client_kwargs_from_config(
                'http://l cert_path=%s' % tmpdir.strpath
            )

    def test_no_ca_no_error(self, tmpdir):
        """
        Ensure that when client cert/key exists, but the CA doesn't, cert
        params are set without verify
        """
        tmpdir.join('cert.pem').ensure()
        tmpdir.join('key.pem').ensure()

        out = client_kwargs_from_config(
            'http://l cert_path=%s' % tmpdir.strpath
        )

        assert out['tls'].cert == (
            tmpdir.join('cert.pem').strpath,
            tmpdir.join('key.pem').strpath,
        )
        assert out['tls'].verify == None


class TestParseRef(object):
    """ Test the ``parse_ref`` function """
    @pytest.mark.parametrize('ref,exp_type,exp_name', [
        ('refs/heads/testbranch', 'branch', 'testbranch'),
        ('remotes/origin/remotebranch', 'branch', 'remotebranch'),
        ('refs/tags/testtag', 'tag', 'testtag'),
        ('some_k1nd-0f_BR@NCH', 'branch', 'some_k1nd-0f_BR@NCH'),
        ('refs/unknown/thing', None, 'refs/unknown/thing'),
        ('things/heads/thing', None, 'things/heads/thing'),
        ('things/tags/thing', None, 'things/tags/thing'),
    ])
    def test_all(self, ref, exp_type, exp_name):
        """ Ensure that outputs are expected for given inputs """
        actual_type, actual_name = parse_ref(ref)
        assert actual_type == exp_type
        assert actual_name == exp_name


class TestAddToUrlPath(object):
    """ Tests the ``add_to_url_path`` utility """
    @pytest.mark.parametrize('in_url,in_path,exp_url', [
        ('http://example.com', '/a/thing', 'http://example.com/a/thing'),
        ('http://example.com/a', 'thing', 'http://example.com/a/thing'),
        ('http://example.com/', '/a/thing', 'http://example.com/a/thing'),
        ('http://example.com/a/', '/thing', 'http://example.com/a/thing'),
        ('http://example.com//', '/a//thing', 'http://example.com/a/thing'),
        ('http://example.com////', '/a///thing', 'http://example.com/a/thing'),
    ])
    def test_basic(self, in_url, in_path, exp_url):
        """ Test that some basic combinations produce expected outputs """
        assert add_to_url_path(in_url, in_path) == exp_url
