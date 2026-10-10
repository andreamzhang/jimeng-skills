#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_asset_report.py —— 经典资产分析报告（暖金主题，黑道千金规范版）。

严格按 `.agents/skills/jimeng-asset-report/SKILL.md` 的 [HTML 规范] 产出：
  scripts/<剧名>/assets/master-report.html      总表（数据卡+四图+跳转卡+分阶段建议）
  scripts/<剧名>/assets/character-report.html   人物（类型分级+人物卡+三阶段叙事+完整清单）
  scripts/<剧名>/assets/scene-report.html       场景（区域分组+无人空景提示词+场景卡）
  scripts/<剧名>/assets/prop-report.html        道具（类别分组+排行+完整清单）
  scripts/<剧名>/assets/_shared/js/echarts.min.js（本地复制，无 CDN）

数据解析口径与 `gen_character_inventory.py` / `gen_scene_inventory.py` 一致：
人物 = 人物行 + 对话冒号行双通道并集；场景 = 场号行（N-M 时间 内外 地点）；
道具 = 关键词逐集扫描。编辑层内容（小传/区域分组/分阶段建议）写在
DRAMA_NOTES，未配置的剧自动降级为纯机械数据版。

用法:
    python tools/gen_asset_report.py "<剧名>"
退出码: 0 = 成功, 1 = 失败
"""
import json
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from gen_character_inventory import scan as scan_characters  # noqa: E402
from gen_scene_inventory import norm_scene, SCENE_RE  # noqa: E402

ECHARTS_SRC = ROOT / ".agents/skills/jimeng-asset-report/assets/_shared/js/echarts.min.js"

# ─────────────────────────── CSS（与黑道千金报告逐类一致） ───────────────────────────
# 视图层组件化：视图层源码见 shell 内 view 层段（对标仓库根 工作台.html 视觉语言）
def compress_ranges(nums):
    """[1,2,3,5] -> [(1,3),(5,5)]"""
    nums = sorted(set(nums))
    out, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append((start, prev))
            start = prev = n
    if start is not None:
        out.append((start, prev))
    return out


def eps_text(nums):
    parts = []
    for a, b in compress_ranges(nums):
        parts.append(f"{a:02d}" if a == b else f"{a:02d}-{b:02d}")
    return "第" + "、".join(parts) + "集"

# ─────────────────────────── 编辑层配置（入宗门当卧底不料撞脸魔教少主） ───────────────────────────
DRAMA_NOTE = "入宗门当卧底不料撞脸魔教少主"

GROUP_DISPLAY = {"魔教黑衣人·5": "魔教黑衣众", "魔教黑衣人×5": "魔教黑衣众"}

GROUP_SET_NAMED = {
    "众弟子", "村民", "众村民", "正道弟子", "众长老", "众魔军", "全体",
    "众将士", "大量魔军精锐", "所有幸存者", "投降魔兵", "残余魔军",
    "百万魔军", "魔军", "魔教众将领", "魔教黑衣人·5", "魔教黑衣人×5",
}

BIOS = {
    "阿福": "男，18岁，青石村砍柴少年，受魔教胁迫伪装少主潜入青云宗做后山杂役。寡言克制、本分耐打，凭一双砍柴老茧撑过山门初查；与魔焱同一张脸是全剧最大的定时炸弹。ep39 魔气觉醒、ep43 起正面大战，从「替全村卖命」一路走到 ep60 终局亲手翻盘。",
    "魔焱": "男，18岁，魔教教主长子、真少主，与阿福同脸（骨相五官逐字一致，仅气质发型装束反转）。傲慢暴戾、居高临下，目光自上而下压人；腰悬玄铁魔纹令牌，ep52 战场祭出本命魔焰长刀，是不加掩饰的最终反派。",
    "小熙": "女，17岁，青石村少女，阿福青梅竹马；父母死于魔教火海后独自撑家。朴实坚韧、认死理，笑起来眼睛先到，受创走「硬扛」的钝痛；ep51 拔出防身短刃上战场，是山村线最硬的执念。",
    "清月": "女，24岁，青云宗师姐「周静娴」，实为魔教潜伏二十年的卧底「青鸾」。目光静而利、算得极清，温柔只在唇线松开的一瞬；持黑蝶传讯符单线接头，ep38 身份线撞破，是贯穿正邪两面最深的一枚暗钉。",
    "孙磊": "男，21岁，青云宗弟子。谨慎持重，先看人再开口、遇事先留退路；ep08 起与赵乾结伴同修，是同窗线里「稳」的那半个。",
    "赵乾": "男，22岁，青云宗弟子。直率气盛，话直人更直、先动手再讲道理；ep08 起与孙磊同修，是同窗线里「冲」的那半个。",
    "掌门": "男，56岁，青云宗掌门。清正威仪，开口前先压住场面；ep10 起正式主持山门与教务，是正道线的定盘星。",
    "魔教教主": "男，45岁，魔教之主，阿福与魔焱的生父。静止时的威压最重，不发怒亦压场；ep26 亲入总坛主持大局，旧物半福玉佩压着幼子旧案，终局亲自下场。",
    "弟子甲": "男，20岁，青云宗守山弟子。多疑急躁，眼神先找破绽、先怀疑再听解释——ep01 山门初查第一个亮剑的人，此后始终盯着柴房里那名「可疑杂役」。",
    "村长": "男，58岁，青石村村长，全剧唯一知道阿福卧底身份的人。愧疚煎熬、说话前先叹气的老实相，骨子里却是硬扛到底的实在人；ep03 亲手授出魔教密信筒。",
    "弟子乙": "男，20岁，青云宗守山弟子。咋呼爱起哄，嗓门先到人后到，是山门包围圈里喊得最响的那一个。",
    "玄尘长老": "男，52岁，青云宗执法长老。峻刻、不讲情面、看人先看骨，ep10 起把后山杂役盯得最细的那双眼睛。",
}

REGIONS = [
    ("青云宗门面区域", ["青云宗山门", "青云宗山门外", "青云宗大殿", "青云宗戒律堂"],
     "仙门门面组：九千九百九十九级白玉石阶牌楼山门与进山大道开阔坡地，重檐大殿与旗阵殿外，戒律堂回廊偏房。青灰石白基调，仙门威压，远山云海。"),
    ("青云宗后山·杂役生活区", ["青云宗杂役院", "青云宗柴房", "青云宗柴房禁闭室", "青云宗玄岩禁闭室", "青云宗练功房", "青云宗藏书阁", "青云宗清月居所"],
     "后山生活组：水井柴房前院的杂役院、窄木床草席的柴房、铁皮包木门的柴房禁闭室与玄岩镇压石室、练功静室与藏书楼、山腰独门小屋。木构烟火气，从局促到肃杀渐次压暗。"),
    ("青云宗后山·山野区", ["青云宗后山", "青云宗后山竹林", "青云宗后山劈柴场"],
     "后山山野组：溪涧石潭林间的后山本体、竹列拱廊落叶铺地的毛竹林、劈柴木桩带柴垛斧头的土场。晨雾夜露、淡淡灵光。"),
    ("青石村区域", ["青石村", "青石村村口", "青石村村长土屋"],
     "山村组：村道农舍篱笆菜畦溪流的青石村本体、老槐树草垛石井的村口、油灯布帘窄炕的村长土屋。土墙灰瓦、市井烟火与山野夜色。"),
    ("魔教区域", ["魔教总坛大殿", "魔教总坛内殿暗室", "魔教祭坛", "魔教分坛大殿"],
     "魔教组：山腹黑石巨殿与黑玉王座、王座屏壁后的内殿暗室与禁地铜镜、血池黑幡祭坛、石质高椅的黑石分坛。黑石魔纹、暗红点缀，阴冷压迫。"),
    ("战场区域", ["魔军阵营", "青云宗外战场", "青云宗主战场", "远方幽深荒谷"],
     "决战组：荒原魔军黑旗方阵与浮空高台、护山大阵金光阵幕的山门外战场、焦土主战场诸视角、百里外黑岩荒谷伏笔场。从列阵压迫到焦土黎明。"),
    ("深山崎岖线", ["深山石屋", "深山幽谷密林", "乱石山道石牢"],
     "深山组：残破猎人石屋、参天古木巨岩谷地的幽谷密林、陡坡乱石山道尽头的巨石咬合石牢。荒莽湿滑、夜色浓重。"),
    ("幻境", ["血色幻境"],
     "幻境组：赤红天地、悬浮碎岩、血色雾面与出口光缝，教主布下的心境杀阵。"),
]

PROPS = [
    ("魔教密信信筒", "@魔教密信筒", "魔教密令", r"信筒"),
    ("玄铁魔纹令牌", "@魔教令牌", "魔教密令", r"令牌"),
    ("黑蝶暗纹传讯符", "@黑蝶传讯符", "魔教密令", r"传讯符"),
    ("魔教卧底联络符", "@魔教联络符", "魔教密令", r"联络符"),
    ("半「福」碎玉佩", "@半福玉佩", "核心信物", r"玉佩"),
    ("魔教禁地古铜镜", "@古旧铜镜", "核心信物", r"铜镜"),
    ("魔教少主画像", "@魔教少主画像", "画告公示", r"画像"),
    ("青石村砍柴斧", "@砍柴斧", "武器", r"斧"),
    ("魔焱魔焰长刀", "@魔焰长刀", "武器", r"长刀|魔焰刀"),
    ("小熙防身短刃", "@小熙短刃", "武器", r"短刃"),
    ("青云宗制式佩剑", "@青云宗佩剑", "武器", r"佩剑"),
    ("阿福磨亮的破铜镜片", "@破铜片", "随身用物", r"铜片"),
    ("清月冻疮药膏瓷盒", "@清月药膏", "随身用物", r"药膏"),
    ("小熙素帕", "@小熙帕子", "随身用物", r"帕子"),
    ("魔教使者魔纹黑轿", "@魔纹黑轿", "座驾", r"黑轿"),
]

PHASES = [
    ("第01-09集", "卧底开局", "青云宗山门、青云宗后山（劈柴场/小径）、青云宗杂役院、青石村、青石村村口、青石村村长土屋",
     "阿福、村长、弟子甲/乙/丙、众弟子、魔教使者", "青云宗佩剑、魔教令牌、魔教密信筒、砍柴斧"),
    ("第10-19集", "潜伏柴房·多重试探", "青云宗大殿、青云宗戒律堂、青云宗后山（竹林/山坳）、青云宗清月居所、青云宗柴房、青云宗杂役院、魔教分坛大殿、青云宗山门外",
     "掌门、清月、玄尘长老、小熙、弟子甲、魔教黑衣众", "黑蝶传讯符、魔教联络符、小熙帕子、清月药膏、破铜片"),
    ("第20-33集", "身份显影·画像风波", "青云宗山门外、青石村村口、青石村、青云宗主战场（伏笔远景）、魔教总坛大殿",
     "小熙、村民甲/乙/丙、掌门、正道弟子（群像）、魔教教主", "魔教少主画像、魔教令牌"),
    ("第34-51集", "旧案与觉醒", "青云宗后山、深山石屋、深山幽谷密林、乱石山道石牢、魔教总坛内殿暗室、魔教祭坛、青云宗柴房禁闭室、玄岩禁闭室",
     "阿福、魔焱、魔教教主、清月、小熙", "半福玉佩、古旧铜镜、小熙短刃、破铜片"),
    ("第52-60集", "总决战·终局", "魔军阵营、青云宗外战场、青云宗主战场、远方幽深荒谷",
     "阿福、魔焱、魔教教主、清月、魔军（群像）", "魔焰长刀、小熙短刃、青云宗佩剑"),
]

NARRATIVE = [
    ("阶段一：卧底开局（第1-9集）",
     "魔教灭村要挟，砍柴少年阿福扮成「魔教少主」脸踏入青云宗山门，山门初查的剑阵把全村性命压在他一个人肩上。村长以密信筒单线接头，柴房杂役的屈辱从劈柴场、小径、杂役院一路延伸；与魔焱同脸的真相只作为一个远景悬念（ep05 后山杂役房起）埋在观众视角里。核心冲突：阿福 vs 山门戒律，村长的愧疚是唯一出口。"),
    ("阶段二：潜伏与身份显影（第10-33集）",
     "掌门与玄尘长老把杂役线纳入法眼，黑蝶传讯符、联络符、密信筒的三角传递让柴房变成全剧最危险的通信节点；清月以师姐身份护人又接头，善意与算计同体。魔教少主画像印发至村口（ep33），村民骚动把「同脸」阴谋推上台前，画像风波成为正邪双方的第一次公开摊牌。核心冲突：接头链 vs 盘查网，小熙的村线信任是软肋也是防线。"),
    ("阶段三：觉醒与终局（第34-60集）",
     "半福玉佩与铜镜揭开旧案，魔教教主亲入总坛，阿福在魔气缠绕里觉醒（ep39）、乱石山道石牢坠入绝境（ep47），终在 ep52 魔焰长刀压场的战场上正面翻盘，护山大阵金光与焦土主战场交替承载 ep43-59 大战；ep60 村口黄昏收束，砍柴老茧握住的是活下来的全村。核心冲突：同脸双生子 vs 生父子局，身份最终由亲缘与信义共同裁定。"),
]


# ─────────────────────────── 数据加载 ───────────────────────────
def ep_num(stem: str):
    m = re.match(r"ep(\d+)$", stem)
    return int(m.group(1)) if m else None


def load_chars(script_dir: Path, alias: dict):
    rec = scan_characters(script_dir, alias)
    out = {}
    for name, d in rec.items():
        display = GROUP_DISPLAY.get(name, name)
        mentions = sum(d["variants"].values())
        out[name] = {
            "display": display,
            "eps": [ep_num(e) or 0 for e in d["eps"]],
            "dialogue_eps": [ep_num(e) or 0 for e in d["dialogue_eps"]],
            "lines": d["lines"],
            "mentions": mentions,
            "group": name in GROUP_SET_NAMED,
        }
    return out


def load_scene_merge(assets: Path):
    """scene-prompts.md 别名归并表 -> (机械地点->正式场景, 正式场景->定位说明)。"""
    mapping, desc = {}, {}
    if not (assets / "scene-prompts.md").is_file():
        return mapping, desc
    text = (assets / "scene-prompts.md").read_text(encoding="utf-8")
    in_merge, in_loc = False, False
    for line in text.splitlines():
        s = line.strip()
        if "别名归并表" in s:
            in_merge = True
            in_loc = False
            continue
        if s.startswith("## ") and in_merge:
            in_merge = False
        if "定位" in s and s.startswith("> |") is False and "正式场景" in s:
            in_loc = True
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or s.startswith("|--") or set(cells[0]) <= set("-— "):
            continue
        if in_merge and not cells[0].startswith("@"):
            m = re.search(r"@([\u4e00-\u9fffA-Za-z0-9·（）()]+)", cells[1] if len(cells) > 1 else "")
            if m:
                target = m.group(1).replace("（", "").replace("）", "")
                if target != "引用名":
                    # 清点行可能带加粗/补录注记：**血色幻境（清点表未收录，补录）**
                    key = re.sub(r"[*\s]", "", cells[0])
                    key = re.sub(r"[（(][^）)]*[）)]$", "", key)
                    mapping[key] = target
        elif cells[0].startswith("@"):
            desc_name = cells[0].lstrip("@")
            desc[desc_name] = cells[1] if len(cells) > 1 else ""
    return mapping, desc


def load_scenes(script_dir: Path, mapping: dict, is_note: bool = False):
    """逐集场景行 -> {正式场景: {"eps": set, "rows": int, "inout": set, "times": set}}。
    未在归并表中的机械地点按关键词兜底映射，仍不中的进「单场·其他」。"""
    scenes = {}
    fallback_rules = [] if is_note is False else [
        (r"石牢", "乱石山道石牢"), (r"深山", "深山幽谷密林"), (r"石屋", "深山石屋"),
        (r"主战场|战场", "青云宗主战场"), (r"魔军", "魔军阵营"), (r"祭坛", "魔教祭坛"),
        (r"总坛|暗室", "魔教总坛内殿暗室"), (r"分坛", "魔教分坛大殿"),
        (r"禁闭", "青云宗玄岩禁闭室"), (r"柴房", "青云宗柴房"), (r"杂役|洗衣|厨房", "青云宗杂役院"),
        (r"戒律堂", "青云宗戒律堂"), (r"大殿|殿后", "青云宗大殿"), (r"藏书", "青云宗藏书阁"),
        (r"练功", "青云宗练功房"), (r"竹林", "青云宗后山竹林"), (r"劈柴|磨坊", "青云宗后山劈柴场"),
        (r"村口|村门|槐树", "青石村村口"), (r"土屋", "青石村村长土屋"), (r"青石村|村", "青石村"),
        (r"山门", "青云宗山门"), (r"幽谷|荒谷|荒野", "深山幽谷密林"), (r"后山|山道|林地", "青云宗后山"),
        (r"居所", "青云宗清月居所"),
    ]
    before, after = set(mapping.keys()), {v for v in mapping.values()}
    rows_total = 0
    for p in sorted(script_dir.glob("ep*.txt")):
        ep = ep_num(p.stem)
        if ep is None:
            continue
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            m = SCENE_RE.match(line)
            if not m:
                continue
            place, tod, inout, _ = norm_scene(m.group(2))
            rows_total += 1
            target = mapping.get(place)
            if target is None:
                for pat, tgt in fallback_rules:
                    if re.search(pat, place):
                        target = tgt
                        break
            if target is None:
                target = place
            rec = scenes.setdefault(target, {"eps": set(), "rows": 0, "inout": set(), "times": set()})
            rec["eps"].add(ep)
            rec["rows"] += 1
            if inout:
                rec["inout"].add(inout)
            if tod:
                rec["times"].add(tod)
    return scenes, rows_total


def load_props(script_dir: Path):
    first_map = {}
    lib_path = script_dir.parent / "assets" / "prop-prompts.md"
    lib_defs = []
    if lib_path.is_file():
        for line in lib_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("| @") and " | " in s:
                cells = [c.strip() for c in s.strip("|").split("|")]
                if len(cells) >= 3 and re.fullmatch(r"ep\d+", cells[2]):
                    first_map[cells[0]] = int(cells[2][2:])
                    lib_defs.append((re.sub(r"（.*$", "", cells[1]).strip() or cells[1], cells[0]))
    out = []
    for name, ref, cat, pat in PROPS:
        eps, cnt = [], 0
        for p in sorted(script_dir.glob("ep*.txt")):
            ep = ep_num(p.stem)
            if ep is None:
                continue
            n = len(re.findall(pat, p.read_text(encoding="utf-8", errors="replace")))
            if n:
                eps.append(ep)
                cnt += n
        out.append({"name": name, "ref": ref, "cat": cat, "eps": eps, "count": cnt})
        out[-1]["first"] = first_map.get(ref)
    return out


def load_props_from_library(assets: Path):
    """无 PROPS 配置的剧：直接使用 assets/prop-prompts.md 道具清单表（机械口径，标注为库登记）。"""
    out = []
    path = assets / "prop-prompts.md"
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not (s.startswith("| @") and " | " in s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"ep\d+", cells[2]):
            continue
        ref, name, first = cells[0], cells[1], int(cells[2][2:])
        out.append({"name": name, "ref": ref, "cat": "资产库清单（首现）",
                    "eps": [first], "count": 1, "first": first})
    return out


def load_prompt_bios(assets: Path):
    """character-prompts.md 条目 -> 自动小传兜底（[性别]行 + [气质]行）。"""
    bios = {}
    path = assets / "character-prompts.md"
    if not path.is_file():
        return bios
    txt = path.read_text(encoding="utf-8")
    for e in re.split(r"^## @", txt, flags=re.M)[1:]:
        name = re.split(r"[（(]", e, maxsplit=1)[0].strip()
        gm = re.search(r"^\[性别\][：:]?\s*(.+)$", e, re.M)
        qm = re.search(r"^\[气质\][：:]?\s*(.+)$", e, re.M)
        if not gm:
            continue
        ident = gm.group(1).strip()
        persona = ""
        if qm:
            tail = qm.group(1).split("——")[-1].strip()
            persona = re.split(r"[：;；]", tail)[0].strip() or tail[:24]
        bios[name] = f"{ident}" + (f"；性格底色：{persona}。" if persona else "。")
    return bios


def load_prompt_sections(assets: Path, filename: str, heading_pat: str):
    """提示词库条目全文：{条目名(不带@): 条目原始 markdown}。"""
    path = assets / filename
    if not path.is_file():
        return {}
    out = {}
    for body in re.split(heading_pat, path.read_text(encoding="utf-8"), flags=re.M)[1:]:
        name = re.split(r"[（( \n]", body, maxsplit=1)[0].strip()
        if name:
            out[name] = body
    return out


def load_prompt_texts(assets: Path):
    """三类提示词库统一读取（人物/场景条目块 + 道具条目块）。"""
    return {
        "chars": load_prompt_sections(assets, "character-prompts.md", r"^## @"),
        "scenes": load_prompt_sections(assets, "scene-prompts.md", r"^## @"),
        "props": load_prompt_sections(assets, "prop-prompts.md", r"^### \d+\.\s*@"),
    }


def char_level(rec):
    if rec["group"]:
        return "group"
    n = len(rec["eps"])
    if n >= 15:
        return "core"
    if n >= 5:
        return "important"
    if n >= 2:
        return "minor"
    return "onetime"


LEVEL_ORDER = ["core", "important", "minor", "onetime"]
LEVEL_LABEL = {"core": "核心角色", "important": "重要配角", "minor": "次要配角", "onetime": "一次性角色"}
LEVEL_TITLES = {"core": "✦ 核心角色", "important": "✦ 重要配角", "minor": "✦ 次要配角", "onetime": "✦ 一次性角色"}
LEVEL_HINT = {
    "core": "出场≥15集，贯穿全剧主线",
    "important": "出场5-14集，有独立剧情线或冲突功能",
    "minor": "出场2-4集",
    "onetime": "仅1集出场，功能性/场景性角色",
}


def render_pages(data):
    import wb_report_views
    return wb_report_views.render_pages(data)


def main() -> int:
    if len(sys.argv) != 2:
        print('用法: gen_asset_report.py "<剧名>"', file=sys.stderr)
        return 1
    drama = sys.argv[1].strip()
    base = ROOT / "scripts" / drama
    script_dir = base / "script"
    assets = base / "assets"
    if not script_dir.is_dir():
        print(f"✗ 找不到 {script_dir}", file=sys.stderr)
        return 1
    alias = {}
    alias_path = assets / "_character-aliases.json"
    if alias_path.is_file():
        alias = json.loads(alias_path.read_text(encoding="utf-8"))
    ep_files = sorted(p for p in script_dir.glob("ep*.txt") if ep_num(p.stem))
    if not ep_files:
        print("✗ 未找到 epNN.txt", file=sys.stderr)
        return 1
    is_note = drama == DRAMA_NOTE
    mapping, desc = load_scene_merge(assets)
    scenes, rows_total = load_scenes(script_dir, mapping, is_note)
    chars = load_chars(script_dir, alias)
    group_named = GROUP_SET_NAMED if is_note else set()
    for n, c in chars.items():
        c["group"] = n in group_named or n.endswith("（群像）")
    named = {n: c for n, c in chars.items() if not c["group"]}
    data = {
        "drama": drama,
        "ep_count": len(ep_files),
        "chars": chars,
        "named": named,
        "bios": {} if is_note is False else {k: v for k, v in BIOS.items()},
        "scenes": {s: {**rec} for s, rec in scenes.items()},
        "mapping": mapping,
        "scene_rows": rows_total,
        "props": load_props(script_dir) if is_note else load_props_from_library(assets),
        "regions": [(s, [s], "") for s in sorted(scenes)] if not mapping and not is_note else REGIONS,
        "phases": PHASES if is_note else [],
        "narrative": NARRATIVE if is_note else [],
        "prompt_texts": load_prompt_texts(assets),
    }
    bios_auto = load_prompt_bios(assets)
    for key, val in bios_auto.items():
        data["bios"].setdefault(key, val)
    outs = render_pages(data)
    shared = assets / "_shared" / "js"
    shared.mkdir(parents=True, exist_ok=True)
    dest = shared / "echarts.min.js"
    if not dest.is_file():
        if not ECHARTS_SRC.is_file():
            print(f"✗ 缺少 echarts 源 {ECHARTS_SRC}", file=sys.stderr)
            return 1
        shutil.copyfile(ECHARTS_SRC, dest)
    import wb_report_views
    outs = wb_report_views.render_pages(data)
    for fname, html in outs.items():
        # 基本校验：每个 echarts.init 都有对应容器
        inits = len(re.findall(r"echarts\.init\(", html))
        divs = len(re.findall(r'id="c-[a-z0-9-]+"', html))
        assert inits == divs, f"{fname}: 图容器 {divs} != init {inits}"
        (assets / fname).write_text(html, encoding="utf-8")
        print(f"  ✓ {assets / fname}  ({len(html) // 1024} KB, {inits} 图)")
    print(f"✓ {drama} 经典资产报告 4 份已生成（黑道千金规范 / 暖金主题 / 本地 echarts）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


