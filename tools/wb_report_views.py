#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_report_views.py —— 资产报告视图层（工作台.html 同源组件拼装）。

数据管道（gen_asset_report.py）产出 data；本文件用 wb_components 的
top/sect/grid/card/badge/links 组件拼出四联报告：
    master-report.html    总览（数据卡 + 四图 + 分报告跳转 + 分阶段建议）
    character-report.html 人物（角色总览图 + 分级人物卡 + 群体 + 三阶段叙事 + 完整清单）
    scene-report.html     场景（场景总览图 + 区域空景提示词 + 场景卡）
    prop-report.html      道具（类别分布 + 类别清单 + TOP 排行 + 完整清单）
"""
from __future__ import annotations

import json

import wb_components as wb


def eps_text(nums) -> str:
    nums = sorted(set(nums))
    parts, start, prev = [], None, None
    out = []
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
    for a, b in out:
        parts.append(f"{a:02d}" if a == b else f"{a:02d}-{b:02d}")
    return "第" + "、".join(parts) + "集"


def _ep_pills(eps) -> str:
    return '<div class="pills">' + "".join(
        f'<span class="badge onetime">EP{e:02d}</span>' for e in eps) + "</div>"


def _prompt_html(name: str, texts) -> str:
    """提示词填充槽：库里有条目给可展开原文；没有给占位，报告重跑时自动填充。"""
    texts = texts or {}
    if name in texts:
        return (f'<details class="slot"><summary>提示词（@{wb.esc(name)}）</summary>'
                f'<pre>{wb.esc(texts[name])}</pre></details>')
    return (f'<div class="slot slot-none">提示词槽位预留 · @'
            f'{wb.esc(name)} 建库后重跑报告自动填入</div>')


def _chart_box(caption: str, cid: str, height: int = 300) -> str:
    return (f'<figure style="margin:0"><figcaption style="font-size:12.5px;color:var(--muted);'
            f'margin-bottom:6px">{wb.esc(caption)}</figcaption>'
            f'<div class="chart" id="{wb.esc(cid)}" style="height:{height}px"></div></figure>')


def _js_tokens() -> str:
    return ("var s=getComputedStyle(document.documentElement);"
            "var A=s.getPropertyValue('--acc').trim(),A2=s.getPropertyValue('--acc2').trim(),"
            "M=s.getPropertyValue('--muted').trim(),R=s.getPropertyValue('--line').trim(),INK=s.getPropertyValue('--ink').trim();")


def js_pie(div: str, data) -> str:
    vals = [[k, v] for k, v in data if v > 0]
    assert vals, f"pie 数据为空: {div}"
    body = (f"var el=document.getElementById('{div}');var c=echarts.init(el,null,{{renderer:'svg'}});"
            f"c.setOption({{tooltip:{{trigger:'item',formatter:'{{b}}: {{c}} ({{d}}%)',appendToBody:true}},"
            f"series:[{{type:'pie',radius:['45%','78%'],data:{json.dumps([{'name': k, 'value': v} for k, v in vals], ensure_ascii=False)},"
            f"label:{{formatter:'{{b}}\\n{{d}}%',color:M,fontSize:11}},itemStyle:{{borderRadius:4}},"
            f"color:[A,A2,'#d4a574','#c4956a','#8b7355'],animation:false}}]}});"
            f"window.addEventListener('resize',function(){{c.resize()}});")
    return _js_fn(f"bp_{div.replace('-', '_')}", body)


def js_bar(div: str, data, color: str, label_name: str) -> str:
    assert data, f"bar 数据为空: {div}"
    names = [k for k, _ in data]
    vals = [v for _, v in data]
    body = (f"var el=document.getElementById('{div}');var c=echarts.init(el,null,{{renderer:'svg'}});"
            f"c.setOption({{tooltip:{{trigger:'axis',axisPointer:{{type:'shadow'}},appendToBody:true}},"
            f"grid:{{left:'3%',right:'8%',bottom:'12%',containLabel:true}},"
            f"xAxis:{{type:'value',name:'{label_name}',nameTextStyle:{{color:M,fontSize:11}},axisLabel:{{color:M}},splitLine:{{lineStyle:{{color:R}}}}}},"
            f"yAxis:{{type:'category',data:{json.dumps(names, ensure_ascii=False)},axisLabel:{{color:INK,fontSize:11}},axisLine:{{show:false}},axisTick:{{show:false}}}},"
            f"series:[{{type:'bar',data:{json.dumps(vals, ensure_ascii=False)},itemStyle:{{color:{color},borderRadius:[0,4,4,0]}},label:{{show:true,position:'right',color:M,fontSize:11}},animation:false}}]}});"
            f"window.addEventListener('resize',function(){{c.resize()}});")
    return _js_fn(f"bb_{div.replace('-', '_')}", body)


def js_scatter_tl(div: str, names, data, max_ep: int) -> str:
    assert names and data, f"时间线数据为空: {div}"
    body = (f"var el=document.getElementById('{div}');var c=echarts.init(el,null,{{renderer:'svg'}});"
            f"c.setOption({{tooltip:{{formatter:function(p){{return p.name+' 第'+p.value[0]+'集';}},appendToBody:true}},"
            f"grid:{{left:'3%',right:'3%',bottom:'3%',containLabel:true}},"
            f"xAxis:{{type:'value',name:'集数',min:0,max:{max_ep + 1},nameTextStyle:{{color:M,fontSize:10}},axisLabel:{{color:M}},splitLine:{{lineStyle:{{color:R}}}}}},"
            f"yAxis:{{type:'category',data:{json.dumps(names, ensure_ascii=False)},axisLabel:{{color:INK,fontSize:10}},axisLine:{{show:false}},axisTick:{{show:false}}}},"
            f"series:[{{type:'scatter',symbolSize:9,data:{json.dumps(data, ensure_ascii=False)},itemStyle:{{color:A}},animation:false}}]}});"
            f"window.addEventListener('resize',function(){{c.resize()}});")
    return _js_fn(f"bs_{div.replace('-', '_')}", body)


def _js_fn(fn_name: str, body: str) -> str:
    return f"function {fn_name}(){{{body}}}{fn_name}();\n"


LEVEL_ORDER = ["core", "important", "minor", "onetime"]
LEVEL_LABEL = {"core": "核心角色", "important": "重要配角", "minor": "次要配角", "onetime": "一次性角色"}
LEVEL_HINT = {"core": "出场≥15集，贯穿全剧主线", "important": "出场5-14集", "minor": "出场2-4集", "onetime": "仅1集"}


def _pages(which: str) -> list:
    return [
        ("master-report.html", "总", "总览", which == "master"),
        ("character-report.html", "人", "人物", which == "character"),
        ("scene-report.html", "景", "场景", which == "scene"),
        ("prop-report.html", "物", "道具", which == "prop"),
    ]


def _collect_levels(data):
    chars = data["chars"]
    levels = {}
    for lv in LEVEL_ORDER:
        lst = [c for c in chars.values() if _char_level(c) == lv]
        levels[lv] = sorted(lst, key=lambda c: (-len(c["eps"]), -c["mentions"]))
    groups = sorted((c for c in chars.values() if c["group"]), key=lambda c: (-len(c["eps"]), c["display"]))
    return levels, groups


def _char_level(rec) -> str:
    if rec.get("group"):
        return "group"
    n = len(rec["eps"])
    if n >= 15:
        return "core"
    if n >= 5:
        return "important"
    if n >= 2:
        return "minor"
    return "onetime"


def _tbl(headers, rows) -> str:
    th = "".join("<th>" + wb.esc(h) + "</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = ""
        for c in row:
            raw = c if isinstance(c, str) and c.startswith("<") else wb.esc(c)
            tds += "<td>" + raw + "</td>"
        trs += "<tr>" + tds + "</tr>"
    return '<div style="overflow:auto"><table class="tbl"><thead><tr>' + th + '</tr></thead><tbody>' + trs + "</tbody></table></div>"


def _charts_card(charts_html: str, title: str, tag: str) -> str:
    grid = '<div class="grid" style="grid-template-columns:1fr 1fr">' + charts_html + "</div>"
    return wb.card({"ic": "📊", "t": title, "tag": tag, "m": "", "body": grid, "search": title})


def _member(rec, bio: str, badge_kind: str, prompt_html: str = "") -> str:
    meta = f'出场<b>{len(rec["eps"])}</b>集（第{"、".join(str(e).zfill(2) for e in rec["eps"])[:80]}集）· 提及<b>{rec["mentions"]}</b>次'
    body = (f'<p class="m">{meta}</p><p class="bio">{wb.esc(bio)}</p>'
            + _ep_pills(rec["eps"]) + prompt_html)
    return wb.card({"ic": "👤" if badge_kind != "prop" else "物", "t": rec["display"],
                    "tag": LEVEL_LABEL.get(badge_kind, badge_kind), "m": "", "body": body,
                    "search": rec["display"] + " " + bio})


def build_master(data) -> str:
    d = data
    levels, groups = _collect_levels(d)
    stats = [(d["ep_count"], "总集数"), (len(d["named"]), "命名角色"),
             (len(d["scenes"]), "场景地点"), (len(d["props"]), "道具种类")]
    dist = [(LEVEL_LABEL[lv], len(levels[lv])) for lv in LEVEL_ORDER if len(levels[lv])]
    if groups:
        dist.append(("群体角色", len(groups)))
    top = sorted(((c["display"], len(c["eps"])) for c in d["chars"].values() if not c["group"]), key=lambda x: -x[1])[:10]
    region_counts = [(r[0], sum(1 for s in r[1] if s in d["scenes"])) for r in d["regions"]]
    covered = {s for _, lst, _ in d["regions"] for s in lst}
    if sorted(s for s in d["scenes"] if s not in covered):
        region_counts.append(("单场·其他", len([s for s in d["scenes"] if s not in covered])))
    cat = {}
    for p in d["props"]:
        cat[p["cat"]] = cat.get(p["cat"], 0) + 1
    charts = (js_pie("c-ch", dist) + js_bar("c-ep", top, "A", "出场集数")
              + js_bar("c-sc", region_counts, "A2", "场景数")
              + (js_pie("c-pr", list(cat.items())) if cat else ""))
    ch = (_chart_box("人物类型分布", "c-ch") + _chart_box("角色出场集数 TOP 10", "c-ep")
          + _chart_box("场景区域分布", "c-sc") + (_chart_box("道具类别分布", "c-pr") if cat else ""))
    links = (wb.link("character-report.html", "人物报告", "big") + wb.link("scene-report.html", "场景报告", "big")
             + wb.link("prop-report.html", "道具报告", "big")
             + wb.link("character-prompts.md", "人物提示词") + wb.link("scene-prompts.md", "场景提示词")
             + wb.link("prop-prompts.md", "道具提示词"))
    phases = _tbl(("阶段", "主题", "核心场景", "核心人物", "核心道具"),
                  [(f"<b>{wb.esc(a)}</b>", wb.esc(b), wb.esc(c), wb.esc(ch), wb.esc(pr)) for a, b, c, ch, pr in d["phases"]])
    h = wb.sect("📈 三大资产概览") + _charts_card(ch, "三大资产概览", "四图")
    h += wb.sect("🔗 分报告跳转") + wb.grid_open()
    h += wb.card({"ic": "人", "t": "人物分析报告", "m": "小传/出场统计/叙事结构", "links": links, "search": "人物 报告 跳转"})
    h += wb.card({"ic": "景", "t": "场景分析报告", "m": "区域分组 · 无人空景提示词", "links": links, "search": "场景 报告 跳转"})
    h += wb.card({"ic": "物", "t": "道具分析报告", "m": f"{len(d['props'])} 道具 · {len(cat)} 类 · TOP 排行", "links": links, "search": "道具 报告 跳转"})
    h += wb.grid_close()
    h += wb.sect("🎨 提示词资产槽位") + wb.card(
        {"ic": "🎨", "t": "提示词资产槽位",
         "m": f"人物 {len(d.get('prompt_texts', {}).get('chars', {}))} 条 · 场景 "
              f"{len(d.get('prompt_texts', {}).get('scenes', {}))} 条 · 道具 "
              f"{len(d.get('prompt_texts', {}).get('props', {}))} 条",
         "body": ('<div class="narr"><p>每张角色/场景/道具卡都预留了提示词槽位：'
                  '提示词库（assets/{character,scene,prop}-prompts.md）建好后重跑本报告，'
                  '槽位自动填充为可展开的完整提示词原文。</p></div>'),
         "search": "提示词 资产 槽位"})
    if d["phases"]:
        h += wb.sect("🗂 分阶段制作建议") + wb.card({"ic": "🗂", "t": "分阶段制作建议", "m": "从剧本分布推导的排期参考", "body": phases, "search": "分阶段 制作 建议"})
    return wb.wb_page(drama=d["drama"], title="📑 资产总览报告", icon="📊", pages=_pages("master"),
                      stats=[], cards_html=h, charts_js=_js_tokens() + charts,
                      search_ph="搜索 指标 / 阶段 / 报告…")


def build_character(data) -> str:
    d = data
    levels, groups = _collect_levels(d)
    named_total = len(d["named"])
    rank_src = levels["core"] + levels["important"] + levels["minor"]
    if not rank_src:
        rank_src = levels["onetime"]
    named_list = [(c["display"], len(c["eps"])) for c in rank_src][:15]
    mention_list = [(c["display"], c["mentions"]) for c in rank_src][:15]
    charts = (js_bar("c-ep", named_list, "A", "出场集数")
              + js_bar("c-mt", mention_list, "A2", "提及次数")
              + js_pie("c-type", [(LEVEL_LABEL[lv], len(levels[lv])) for lv in LEVEL_ORDER if len(levels[lv])]))
    tl_src = levels["core"] + levels["important"]
    if not tl_src:
        tl_src = (levels["minor"] + levels["onetime"])[:12]
    tl_names = [c["display"] for c in tl_src]
    tl_data = []
    for i, c in enumerate(tl_src):
        tl_data.extend([ep, len(tl_src) - i] for ep in c["eps"])
    if tl_src:
        charts += js_scatter_tl("c-tl", tl_names, tl_data, d["ep_count"])
        ch = (_chart_box("角色出场集数 TOP 15（命名）", "c-ep")
              + _chart_box("角色提及次数 TOP 15（命名）", "c-mt")
              + _chart_box("角色类型分布", "c-type") + _chart_box("核心+重要出场时间线", "c-tl"))
    else:
        ch = (_chart_box("角色出场集数 TOP 15（命名）", "c-ep")
              + _chart_box("角色提及次数 TOP 15（命名）", "c-mt")
              + _chart_box("角色类型分布", "c-type"))
    h = wb.sect("📊 角色总览") + _charts_card(ch, "角色总览", "四图")
    rail_stats = [(named_total, "命名角色"), (len(levels["core"]), "核心"), (len(levels["important"]), "重要"),
                  (len(levels["minor"]), "次要"), (len(levels["onetime"]), "一次性")]
    for lv in LEVEL_ORDER:
        if not levels[lv]:
            continue
        h += wb.sect(f"✦ {LEVEL_LABEL[lv]}（{len(levels[lv])}）")
        h += wb.grid_open()
        for c in levels[lv]:
            bio = d["bios"].get(c["display"]) or "出场频次偏低，作为场景性/功能型配角使用。"
            h += _member(c, bio, lv, _prompt_html(
                c["display"], d.get("prompt_texts", {}).get("chars", {})))
        h += wb.grid_close()
    if groups:
        h += wb.sect(f"✦ 群体角色（{len(groups)}）")
        rows = [(wb.esc(c["display"]), "群像/泛指", "第" + "、".join(str(e).zfill(2) for e in c["eps"]) + "集", str(c["mentions"])) for c in groups]
        h += wb.card({"ic": "👥", "t": f"群体角色（{len(groups)}）", "m": "无具体姓名的群演，不建独立资产",
                      "body": _tbl(("群体", "类型", "出场集数", "提及"), rows), "search": "群体角色 群像"})
    if d["narrative"]:
        narr = "".join(f'<div class="narr"><h3>{wb.esc(hh)}</h3><p>{wb.esc(pp)}</p></div>' for hh, pp in d["narrative"])
        h += wb.sect("📖 三阶段叙事结构") + wb.card({"ic": "📖", "t": "三阶段叙事结构", "m": "主线结构摘要", "body": narr, "search": "叙事 结构"})
    idx = 0
    all_rows = []
    for lv in LEVEL_ORDER:
        for c in levels[lv]:
            idx += 1
            all_rows.append((str(idx), wb.esc(c["display"]), LEVEL_LABEL[lv],
                             "第" + "、".join(str(e).zfill(2) for e in c["eps"]) + "集", str(c["mentions"])))
    h += wb.sect("📋 完整清单") + wb.card({"ic": "📋", "t": f"完整清单（{len(all_rows)}）", "m": "全角色一览",
                                           "body": _tbl(("#", "姓名", "类型", "出场集数", "提及次数"), all_rows),
                                           "search": "完整清单"})
    return wb.wb_page(drama=d["drama"], title="👤 人物分析报告", icon="👤", pages=_pages("character"),
                      stats=[], cards_html=h, charts_js=_js_tokens() + charts,
                      search_ph="搜索 姓名 / 集数 / 小传…")


def build_scene(data) -> str:
    d = data
    scenes = d["scenes"]
    regions = [(r[0], r[1], r[2]) for r in d["regions"]]
    covered = {s for _, lst, _ in regions for s in lst}
    leftover = sorted(s for s in scenes if s not in covered)
    if leftover:
        regions.append(("单场·其他", leftover, "散点单场。"))
    top = sorted(scenes.items(), key=lambda kv: -kv[1]["rows"])[:15]
    charts = (js_bar("c-top", [(k, v["rows"]) for k, v in top], "A", "场次数")
              + js_bar("c-area", [(r[0], sum(1 for s in r[1] if s in scenes)) for r in regions], "A2", "场景数"))
    ch = _chart_box("高频场景 TOP 15（场次数）", "c-top") + _chart_box("区域场景分布", "c-area")
    stats = [(len(scenes), "正式场景"), (len(d["regions"]), "区域"), (d["scene_rows"], "总场次数")]
    h = wb.sect("📊 场景总览") + _charts_card(ch, "场景总览", "双图")
    scene_prompts = d.get("prompt_texts", {}).get("scenes", {})
    for i, (rname, members, prompt) in enumerate(regions, 1):
        present = [s for s in members if s in scenes]
        if not present:
            continue
        h += wb.sect(f"▸ {rname}（{len(present)}个场景）")
        if prompt:
            h += wb.card({"ic": "🎨", "t": f"{rname} · 无人空景提示词", "m": "空景 · 不含人物",
                          "body": f'<div class="narr"><p>{wb.esc(prompt)}</p></div>',
                          "search": rname + " 无人空景"})
        h += wb.grid_open()
        for s in sorted(present, key=lambda x: (-scenes[x]["rows"], x)):
            rec = scenes[s]
            i_o = "/".join(sorted(rec["inout"])) or "—"
            tod = "、".join(sorted(rec["times"])) or "—"
            detail = (f'{i_o} · <b>{rec["rows"]}</b>场 · <b>{len(rec["eps"])}</b>集 · 时间 {tod}')
            body = f'<p class="m">{detail}</p>' + _ep_pills(rec["eps"]) + _prompt_html(s, scene_prompts)
            h += wb.card({"ic": "🏠", "t": s, "tag": rname, "m": "", "body": body,
                          "search": s + " " + rname})
        h += wb.grid_close()
    return wb.wb_page(drama=d["drama"], title="🏠 场景分析报告", icon="🏠", pages=_pages("scene"),
                      stats=[], cards_html=h, charts_js=_js_tokens() + charts,
                      search_ph="搜索 场景 / 区域 / 集数…")


def build_prop(data) -> str:
    d = data
    props = d["props"]
    if not props:
        h = wb.card({"ic": "🔧", "t": "道具数据缺失", "m": "待建库",
                     "body": '<div class="narr"><p>未找到标准道具清单表：请先在 assets/prop-prompts.md 建立「一、道具清单表」'
                             '（| @引用名 | 名称 | 首次出场集 | … |）后重跑 python tools/gen_asset_report.py。</p></div>'
                             '<div class="slot slot-none">提示词槽位已预留 · prop-prompts.md 建库后重跑报告自动填入</div>',
                     "search": "道具缺失"})
        return wb.wb_page(drama=d["drama"], title="🔧 道具分析报告", icon="🔧",
                          pages=_pages("prop"), stats=[(0, "道具")], cards_html=h,
                          charts_js="", search_ph="…")
    prop_prompts = d.get("prompt_texts", {}).get("props", {})
    cat_kinds, cat_mentions = {}, {}
    for p in props:
        cat_kinds.setdefault(p["cat"], []).append(p)
        cat_mentions[p["cat"]] = cat_mentions.get(p["cat"], 0) + p["count"]
    charts = (js_pie("c-cat", [(k, len(v)) for k, v in cat_kinds.items()])
              + js_pie("c-mt", [(k, v) for k, v in cat_mentions.items() if v > 0]))
    ch = _chart_box("道具类别分布（种类数）", "c-cat") + _chart_box("类别总提及次数", "c-mt")
    stats = [(len(props), "道具种类"), (len(cat_kinds), "类别"), (sum(cat_mentions.values()), "总提及")]
    h = wb.sect("📊 道具总览") + _charts_card(ch, "道具总览", "双图")
    rail = []
    for cat, lst in sorted(cat_kinds.items(), key=lambda kv: -len(kv[1])):
        rows = []
        for p in sorted(lst, key=lambda x: (-x["count"], x["name"])):
            occur = eps_text(p["eps"]) if p["eps"] else (f"库登记首现 第{p['first']:02d}集" if p.get("first") else "—")
            rows.append((wb.esc(p["name"]) + f'（{wb.esc(p["ref"])}）', wb.esc(occur), str(p["count"])))
        h += wb.sect(f"▸ {cat}（{len(lst)}种）")
        slots = "".join(
            (f'<details class="slot"><summary>道具提示词（@{wb.esc(p["ref"].lstrip("@"))}）</summary>'
             f'<pre>{wb.esc(prop_prompts[p["ref"].lstrip("@")])}</pre></details>'
             if p["ref"].lstrip("@") in prop_prompts else
             f'<div class="slot slot-none">提示词槽位预留 · @{wb.esc(p["ref"].lstrip("@"))} '
             f'prop-prompts.md 建库后重跑报告自动填入</div>')
            for p in sorted(lst, key=lambda x: (-x["count"], x["name"])))
        h += wb.card({"ic": "🔧", "t": f"{cat}（{len(lst)}种）", "m": "类别清单",
                      "body": _tbl(("道具名", "出现集数", "提及"), rows) + slots,
                      "search": cat + " ".join(p["name"] for p in lst)})
        rail.append((cat, len(lst)))
    ranked = sorted(props, key=lambda p: -p["count"])
    rank_rows = [("#" + str(i), wb.esc(p["name"]) + f'（{wb.esc(p["ref"])}）',
                  f'{p["count"]}次 · {len(p["eps"])}集 · {wb.esc(eps_text(p["eps"]))}')
                 for i, p in enumerate([p for p in ranked[:20] if p["count"] > 0], 1)]
    h += wb.sect("🏆 道具排行 TOP 20") + wb.card({"ic": "🏆", "t": "道具排行 TOP 20", "m": "按提及降序",
                                                  "body": _tbl(("#", "道具名", "统计"), rank_rows), "search": "排行"})
    all_rows = []
    for i, p in enumerate(ranked, 1):
        occur = eps_text(p["eps"]) if p["eps"] else (f"库登记首现 第{p['first']:02d}集" if p.get("first") else "—")
        all_rows.append((str(i), wb.esc(p["name"]) + f'（{wb.esc(p["ref"])}）', wb.esc(p["cat"]), wb.esc(occur), str(p["count"])))
    h += wb.sect("📋 完整清单") + wb.card({"ic": "📋", "t": f"完整清单（{len(all_rows)}）", "m": "全道具一览",
                                           "body": _tbl(("#", "道具名", "类别", "出现集数", "提及次数"), all_rows),
                                           "search": "完整清单"})
    return wb.wb_page(drama=d["drama"], title="🔧 道具分析报告", icon="🔧", pages=_pages("prop"),
                      stats=[], cards_html=h, charts_js=_js_tokens() + charts,
                      search_ph="搜索 道具 / 类别 / 集数…")


def render_pages(data) -> dict:
    return {
        "master-report.html": build_master(data),
        "character-report.html": build_character(data),
        "scene-report.html": build_scene(data),
        "prop-report.html": build_prop(data),
    }
