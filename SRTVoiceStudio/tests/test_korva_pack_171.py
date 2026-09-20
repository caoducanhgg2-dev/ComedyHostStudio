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


def test_korva_onnx_uses_file_sha256_not_xet_hash():
    by_path={path:sha for path,_,sha in FILES}
    expected={
        'onnx/duration_predictor.onnx':'c59dd540d003e781f55efc3f39807ad9939164a34dbc74eb05f39ab41b4632d7',
        'onnx/text_encoder.onnx':'4522eea5c39f68c101f27fc14758cc65311a4abfc64500ddf32e6d582de5daab',
        'onnx/vector_estimator.onnx':'f7a5abb7feca5e657977781953cd30997869eb54363bdcc729e848b4c7ca2702',
        'onnx/vocoder.onnx':'7d305c4cc06e9cd2ac47834d90e9b97b69df316cbda75682dd0f4c17d289324f',
    }
    previous_xet_hashes={
        '26d385840e93bda0395013b719464894d86fb5fb705099de38a759529d27a882',
        'e130d8960cd4c0008ef021a62bfceebb30bec3106d660df1e9d3a0f589853507',
        'f78d2893feaca9ee7eb54e892d7c65deb4793e5b5e68f6a47a5c594d4696970a',
        '91795b4dd3ad3b05e5095332aeaf3999f889fd8496e016682da60092c5ed9295',
    }
    assert {path:by_path[path] for path in expected}==expected
    assert not (set(by_path.values()) & previous_xet_hashes)
