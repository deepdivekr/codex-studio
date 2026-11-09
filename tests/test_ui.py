import json, re, shutil, subprocess, unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]

class Labels(HTMLParser):
    def __init__(self):
        super().__init__(); self.labels=[]; self.buttons_in_labels=[]
    def handle_starttag(self,tag,attrs):
        if tag=='label': self.labels.append(dict(attrs))
        if tag=='button' and self.labels: self.buttons_in_labels.append(dict(attrs).get('id'))
    def handle_endtag(self,tag):
        if tag=='label' and self.labels:self.labels.pop()

class UI(unittest.TestCase):
    def test_buttons_do_not_share_implicit_slider_labels(self):
        parser=Labels();parser.feed((ROOT/'skills/codex-studio/assets/index.html').read_text(encoding='utf-8'))
        self.assertEqual(parser.buttons_in_labels,[])

    @unittest.skipUnless(shutil.which('node'),'Node required for browser helper check')
    def test_unsaved_comment_guards_switch_and_unload(self):
        source=(ROOT/'skills/codex-studio/assets/app.js').read_text(encoding='utf-8')
        start=source.index('function hasUnsavedWork()');end=source.index('async function openArtifact',start)
        script=source[start:end]+"""
let dirty=false,saving=false,switching=false,note='unsent comment',asked=0;
const $=()=>({value:note});const confirm=()=>{asked++;return false;};
if(allowSwitch()!==false||asked!==1)throw Error('unsent comment discarded');
note='';if(allowSwitch()!==true)throw Error('clean switch blocked');
dirty=true;if(allowSwitch()!==false)throw Error('dirty review discarded');
saving=true;if(allowSwitch()!==false)throw Error('save race');
"""
        subprocess.run(['node','-e',script],check=True,capture_output=True)
        self.assertRegex(source,r"beforeunload[^\n]+hasUnsavedWork\(\)")
