import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("m", "tools/import_bilingual_storyboard.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
paras = m.read_docx(Path("scripts/消费十倍返利！打脸装穷豪门妻子/消费十倍返利！打脸装穷豪门妻子 1-40.docx"))
front, eps = m.split_episodes([p for p in paras if p])
for ep in eps:
    cn_dlg = cn_bracket = cn_skip = ind_nested = untag_dlg = 0
    for raw in ep["lines"]:
        tm = m.TAG_RE.match(raw)
        if tm:
            body = raw[tm.end():].strip()
            langs = set(re.findall(r"印|中", tm.group(0)))
            nested = m.NESTED_CN_RE.search(body)
            if nested:
                cn_part = body[nested.end():].strip()
                if m.is_chinese_dialogue(cn_part):
                    ind_nested += 1
            elif "印" in langs:
                ind_nested += 0
            elif body.startswith("【") and body.endswith("】"):
                cn_bracket += 1
            elif m.dialogue_text(body) is not None and m.is_chinese_text(m.dialogue_text(body)):
                cn_dlg += 1
            else:
                cn_skip += 1
        else:
            text = m.dialogue_text(raw)
            if text is not None and m.is_chinese_text(text):
                untag_dlg += 1
    out_lines, out_dlg = m.build_ep_text(ep)
    exp = cn_dlg + ind_nested + untag_dlg
    if exp != out_dlg:
        print(f"ep{ep['num']:02d}: cn_dlg={cn_dlg} ind_nested={ind_nested} untag_dlg={untag_dlg} "
              f"bracket={cn_bracket} skip={cn_skip} -> exp={exp} out={out_dlg}")
