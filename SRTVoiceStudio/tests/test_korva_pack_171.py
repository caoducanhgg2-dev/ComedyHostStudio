from studio.korva_pack import FILES, REVISION, packs
from studio.voice_catalog import korva_catalog

def test_korva_manifest_is_fully_pinned_and_matches_ten_voices():
    assert len(korva_catalog())==10
    assert len(FILES)==16
    assert len(REVISION)==40
    assert all(size>0 and len(sha)==64 for _,size,sha in FILES)
    assert len({path for path,_,_ in FILES})==len(FILES)

def test_korva_pack_urls_are_revision_pinned_https_and_apache():
    ps=packs()
    assert len(ps)==len(FILES)
    for pack in ps:
        assert pack.url.startswith('https://huggingface.co/dogenthq/KorvaTTS/resolve/'+REVISION+'/')
        assert pack.license=='Apache-2.0'
        assert pack.size>0 and len(pack.sha256)==64

def test_korva_total_download_is_under_410_mb():
    total=sum(size for _,size,_ in FILES)
    assert 395_000_000 < total < 410_000_000
