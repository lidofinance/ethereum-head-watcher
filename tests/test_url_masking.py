"""
Provider keys live inside endpoint URLs, and endpoint URLs reach the log through exception text rather than through
anything that looks like a credential. These are the shapes our providers use.
"""

from src.providers.http_provider import mask_url, mask_urls_in


def test_query_string_key_is_dropped():
    masked = mask_url('https://provider.org/ogrpc?network=ethereum&key=SECRETKEYVALUE')

    assert masked == 'https://provider.org'
    assert 'SECRETKEYVALUE' not in masked


def test_path_segment_key_is_dropped():
    masked = mask_url('https://provider.com/v2/SECRETKEYVALUE')

    assert masked == 'https://provider.com'


def test_host_survives_because_it_says_which_provider_failed():
    assert mask_url('http://kapi-server:3000/v1/keys') == 'http://kapi-server:3000'


def test_non_url_text_is_returned_unchanged():
    assert mask_url('not a url') == 'not a url'


def test_url_inside_exception_text_is_masked():
    # What requests actually produces on a failed call, key included.
    text = (
        "HTTPSConnectionPool(host='provider.org', port=443): Max retries exceeded with url: "
        "https://provider.org/ogrpc?network=ethereum&key=SECRETKEYVALUE (Caused by ReadTimeout)"
    )

    masked = mask_urls_in(text)

    assert 'SECRETKEYVALUE' not in masked
    assert 'Max retries exceeded' in masked
    assert 'ReadTimeout' in masked


def test_several_urls_in_one_message_are_all_masked():
    text = 'tried https://a.example/v2/KEYONEVALUE then https://b.example/eth-beacon-chain/KEYTWOVALUE'

    masked = mask_urls_in(text)

    assert 'KEYONEVALUE' not in masked
    assert 'KEYTWOVALUE' not in masked


def test_text_without_urls_is_untouched():
    # Hashes and block numbers are what makes an error readable; masking is not a blanket redaction.
    text = 'Block 0xabc123 not found at slot 12345'

    assert mask_urls_in(text) == text
