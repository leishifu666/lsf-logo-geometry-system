"""Build portable distribution archives; never include caches or local configuration."""
from pathlib import Path
import zipfile, hashlib
root=Path(__file__).resolve().parents[1]
out=root/'dist';out.mkdir(exist_ok=True)
name='lsf-logo-geometry-system';skill=root/'skills'/name
archives=[]
for archive,base,prefix in [(out/f'{name}-v1.5.0.zip',skill,name),(out/'logo-examples-v1.5.0.zip',root/'gallery','gallery')]:
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']:
                z.write(p,Path(prefix)/p.relative_to(base))
        z.write(root/'LICENSE','LICENSE')
        z.write(root/'NOTICE.md','NOTICE.md')
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    archives.append(f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}')
(out/'SHA256SUMS.txt').write_text('\n'.join(archives)+'\n',encoding='utf-8')
print('\n'.join(archives))
