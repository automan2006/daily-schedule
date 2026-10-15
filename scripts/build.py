"""Validate and build the GitHub distribution; Python standard library only."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build():
    manifest = read_json(ROOT / 'plugin.json')
    legacy = read_json(ROOT / '.codex-plugin/plugin.json')
    assert manifest['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
    assert manifest['name'] == legacy['name'] == 'daily-planner'
    assert manifest['version'] == legacy['version']
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    interface = manifest['extensions']['com.openai']['interface']
    assert interface == legacy['interface']
    assert interface['displayName'] == 'Daily Schedule'
    assert len(interface['shortDescription']) <= 30
    assert manifest['extensions']['com.openai']['apps'] == './.app.json'
    apps = read_json(ROOT / '.app.json')['apps']
    assert set(apps) == {'google-calendar', 'todoist'}
    for app in apps.values():
        assert re.fullmatch(r'(?:connector_|asdk_app_|templated_apps_)[A-Za-z0-9][A-Za-z0-9_-]*', app['id'])
        assert app['required'] is True
    skill_dir = ROOT / 'skills/daily-planner'
    skill = (skill_dir / 'SKILL.md').read_text(encoding='utf-8')
    frontmatter = json.loads(skill.split('---', 2)[1])  # JSON is a YAML 1.2 subset.
    assert frontmatter['name'] == skill_dir.name and frontmatter['description'].strip()
    agent = read_json(skill_dir / 'agents/openai.yaml')
    assert agent['interface']['display_name'] == 'Daily Schedule'
    assert agent['policy']['allow_implicit_invocation'] is True
    assert '$daily-planner' in agent['interface']['default_prompt']
    files = [ROOT / 'plugin.json', ROOT / '.app.json', ROOT / '.codex-plugin/plugin.json', ROOT / 'LICENSE']
    files += sorted(p for directory in ('skills', 'assets') for p in (ROOT / directory).rglob('*') if p.is_file())
    assert len(files) == 10
    for path in files:
        assert not path.is_symlink()
        text = path.read_text(encoding='utf-8')
        assert not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|ya29\.[A-Za-z0-9_-]{20,}', text), path
        assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text), path
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' not in link and not link.startswith('#'):
                    target = (path.parent / link.split('#')[0]).resolve()
                    assert target.is_relative_to(ROOT) and target.is_file(), target
    for field in ('logo', 'composerIcon'):
        icon = (ROOT / interface[field]).resolve()
        assert icon.is_relative_to(ROOT) and icon.is_file()
        svg = ET.parse(icon).getroot()
        assert svg.tag.endswith('svg')
        assert int(svg.attrib['width']) == int(svg.attrib['height']) >= 48
    output = ROOT / 'dist' / ('daily-schedule-' + manifest['version'] + '.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as package:
        for path in files:
            package.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == {p.relative_to(ROOT).as_posix() for p in files}
        for path in files:
            assert package.read(path.relative_to(ROOT).as_posix()) == path.read_bytes()
    print(json.dumps({'validated': True, 'files': len(files), 'archive': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    build()
