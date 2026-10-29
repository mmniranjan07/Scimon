"""Run from an extracted pack to validate images, names, IDs and evolution links."""
import hashlib,json
from pathlib import Path
from PIL import Image

def validate(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    m=json.loads((root/'sprite_manifest.json').read_text());rows=m['species']
    names=json.loads((root/'species_name_patch.json').read_text())
    aliases=json.loads((root/'legacy_filename_map.json').read_text())
    lines=json.loads((root/'evolution_lines.json').read_text())
    ids={r['species_id']:r for r in rows}
    assert len(rows)==len(ids)==327
    assert len({r['display_name'].lower() for r in rows})==327
    assert len(lines)==len({r['family_id'] for r in rows})==109
    assert len(aliases)==654 and len(set(aliases.values()))==654
    assert set(names)==set(ids)
    found=set()
    for r in rows:
        assert not any(w in r['display_name'].lower().split() for w in ('baby','middle','final'))
        for view in ('front','back'):
            entry=r['views'][view];p=root/entry['file'];found.add(p.resolve())
            assert p.stem==r['display_name']
            assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
            assert aliases[r['species_id']+'-'+view+'.png']==entry['file']
            with Image.open(p) as im:
                im.load();assert im.mode=='RGBA' and im.size==(entry['width'],entry['height'])
                a=im.getchannel('A');bbox=a.getbbox();assert bbox and a.getextrema()[0]==0
                assert bbox[0]>=8 and bbox[1]>=8 and bbox[2]<=im.width-8 and bbox[3]<=im.height-8
        if r['evolves_to']:
            target=ids[r['evolves_to']]
            assert target['evolves_from']==r['species_id']
            assert target['stage_ordinal']==r['stage_ordinal']+1
    actual={p.resolve() for p in (root/'sprites').rglob('*.png')}
    assert actual==found and len(actual)==654
    for f in lines:
        assert len(f['forms'])==3
        assert [ids[x['species_id']]['stage_ordinal'] for x in f['forms']]==[1,2,3]
    return {'families':109,'named_forms':327,'front_pngs':327,'back_pngs':327,'individual_pngs':654,
            'image_decoding':'passed','transparency_and_padding':'passed','names_and_evolution_links':'passed','checksums':'passed'}

if __name__=='__main__':print(json.dumps(validate(),indent=2))
