#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_components.py —— 「工作台.html」同源视觉底座（资产报告组件化共用层）。

对标仓库根 工作台.html（即梦分镜师深色版）：
  · 同 Token：--bg:#141414 / --panel:#1c1c1c / --panel2:#242424 / --panel3:#2e2e2e / --acc:#e5484d
  · 同骨架：.body-bg 网点底 → .frame 大圆角面板 → .top（logo 圆徽 + titlebox + center-pill + right-grp）
  · 同组件：.sect / .grid / .card(.hero) / .btn(.big) / .badge / .links / .none
  · 同交互：搜索即过滤（含 .none 占位）、hero 上浮 hover、hash 路由跳报告、viewer 内嵌
报告场景语义映射（不改视觉）：
  · sect==分区；card==角色/场景/道具/图表块；tag30 槽==每卡 tag；badge==等级药丸
  · center-pill==分页（总览/人物/场景/道具）；stat==本页关键统计
  · echarts 颜色严格从 Token 取
API： wb_page / card / link / badge / sect / grid_open / grid_close
"""
from __future__ import annotations


def esc(s: str) -> str:
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(opts, wide: bool = False) -> str:
    cls = "card" + (" hero" if opts.get("hero") else "") + (" wide" if wide else "")
    ic = f'<span class="ic">{esc(opts["ic"])}</span>' if opts.get("ic") else ""
    tag = f'<span class="tag">{esc(opts["tag"])}</span>' if opts.get("tag") else ""
    id_attr = f' id="{esc(opts["id"])}"' if opts.get("id") else ""
    search = f' data-search="{esc((opts.get("search") or "").lower())}"' if opts.get("search") is not None else ""
    bio = f'<p class="bio">{esc(opts["bio"])}</p>' if opts.get("bio") else ""
    m_html = f'<div class="m">{opts["m"]}</div>' if opts.get("m") else ""
    links = opts.get("links", "")
    return (f'<div{ id_attr} class="{cls}"{search}>'
            f'<div class="hd">{ic}<span class="t">{esc(opts.get("t", ""))}</span>{tag}</div>'
            + m_html + bio + (opts.get("body") or "")
            + (f'<div class="links">{links}</div>' if links else "") + "</div>")


def link(href: str, label: str, cls: str = "", blank: bool = False) -> str:
    if not href:
        return '<span class="none">' + esc(label) + " 未产出</span>"
    target = ' target="_blank"' if blank else ""
    return f'<a class="btn{" " + cls if cls else ""}" href="{esc(href)}"{target}>{esc(label)}</a>'


def badge(kind: str, text: str = "") -> str:
    return f'<span class="badge {esc(kind)}">{esc(text or kind)}</span>'


def stat(v, k: str) -> str:
    return f'<span class="stat"><b>{esc(v)}</b>{esc(k)}</span>'


def sect(title: str) -> str:
    return f'<div class="sect"><h2>{esc(title)}</h2><div class="rule"></div></div>'


def grid_open() -> str:
    return '<div class="grid">'


def grid_close() -> str:
    return "</div>"


CSS_TOKENS = """:root{--bg:#141414;--panel:#1c1c1c;--panel2:#242424;--panel3:#2e2e2e;--ink:#f2f2f2;--muted:#9a9a9a;--dim:#6f6f6f;
  --line:rgba(255,255,255,.08);--acc:#e5484d;--acc2:#ff7376;--acc-soft:rgba(229,72,77,.16);
  --ok:#4fc48a;--ok-soft:rgba(79,196,138,.14);--warn:#e0a04a;--warn-soft:rgba(224,160,74,.14)}
"""

CSS = CSS_TOKENS + """*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.7 system-ui,-apple-system,"PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif}
.body-bg{min-height:100vh;padding:18px 18px 30px;background-image:radial-gradient(rgba(255,255,255,.045) 1px,transparent 1px);background-size:22px 22px}
.frame{max-width:1340px;margin:0 auto;background:var(--panel);border:1px solid var(--line);border-radius:26px;padding:20px 28px 46px;box-shadow:0 24px 70px rgba(0,0,0,.45)}
.top{display:flex;align-items:flex-start;gap:16px;margin-bottom:12px;flex-wrap:wrap}
.top-btn{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:52px;text-decoration:none}
.top-btn>span:last-child{font-size:11px;color:var(--muted)}
.rbtn{width:42px;height:42px;border-radius:50%;background:var(--panel2);border:1px solid var(--line);display:grid;place-items:center;color:var(--ink);font-size:17px;text-decoration:none;cursor:pointer;transition:background .12s;font:inherit}
.rbtn:hover{background:var(--panel3)}
.titlebox{padding-top:3px}
.titlebox h1{margin:0;font-size:20px;font-weight:700;letter-spacing:-.01em;line-height:1.35}
.titlebox h1 .dim{color:var(--dim);font-weight:400}
.titlebox .sub{margin:2px 0 0;color:var(--muted);font-size:12px}
.tag{display:inline-block;margin-left:6px;font-size:10px;color:var(--acc2);border:1px solid var(--line);border-radius:6px;padding:0 5px;vertical-align:2px;font-weight:400}
.center-pill{display:flex;gap:2px;background:var(--panel2);border:1px solid var(--line);border-radius:15px;padding:4px;margin:0 auto;align-self:center}
.center-pill a{display:flex;flex-direction:column;align-items:center;gap:3px;color:var(--muted);text-decoration:none;font-size:11px;padding:5px 16px;border-radius:11px;min-width:64px}
.center-pill a .g{font-size:15px;color:var(--ink)}
.center-pill a.on{background:var(--panel3);color:var(--ink)}
.center-pill .stat{display:flex;flex-direction:column;align-items:center;color:var(--muted);font-size:11px;padding:5px 16px;min-width:64px}
.center-pill .stat b{color:var(--ink);font-size:14px}
.right-grp{display:flex;gap:14px;margin-left:auto;align-items:flex-start}
#search{padding:8px 12px;width:200px;border:1px solid var(--line);border-radius:12px;font:inherit;font-size:13px;background:var(--panel2);color:var(--ink);margin-top:2px}
#search::placeholder{color:var(--dim)}
.badge{font-size:11px;padding:2px 9px;border-radius:10px;display:inline-block}
.badge.core{background:var(--acc-soft);color:var(--acc2)}
.badge.important{background:rgba(255,115,118,.1);color:var(--acc2);opacity:.85}
.badge.minor{background:var(--panel3);color:var(--muted)}
.badge.onetime{background:transparent;color:var(--dim)}
.badge.ok{background:var(--ok-soft);color:var(--ok)}
.badge.doing{background:var(--warn-soft);color:var(--warn)}
.sect{margin:24px 0 12px;display:flex;align-items:center;gap:10px}
.sect h2{margin:0;font-size:13px;color:var(--muted);letter-spacing:.08em}
.sect .rule{flex:1;border-top:1px solid var(--line)}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(270px,1fr))}
.card{background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:14px 16px}
.card.hero{border-color:rgba(255,255,255,.14);cursor:pointer;transition:transform .12s,border-color .12s,box-shadow .12s}
.card.hero:hover{transform:translateY(-2px);border-color:var(--acc);box-shadow:0 14px 34px -14px rgba(229,72,77,.35)}
.card .hd{display:flex;align-items:center;gap:9px;margin-bottom:6px;flex-wrap:wrap}
.ic{flex:none;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;background:var(--panel3);color:var(--ink);border:1px solid var(--line)}
.card.hero .ic{background:var(--acc-soft);color:var(--acc2);border-color:transparent}
.card .t{font-weight:700;font-size:14.5px;word-break:break-all}
.card .m{color:var(--muted);font-size:12px;margin:2px 0 8px}
.card .m b{color:var(--ink);font-weight:600}
.card .bio{color:var(--muted);font-size:12.5px;line-height:1.8;margin:0 0 8px}
.card .wide{grid-column:1 / -1}
.links{display:flex;flex-wrap:wrap;gap:6px}
.btn{font-size:12px;text-decoration:none;color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:3px 10px;background:var(--panel3);display:inline-block;cursor:pointer;font:inherit}
.btn:hover{border-color:var(--acc2)}
.btn.big{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:700;padding:4px 13px}
.btn.big:hover{background:var(--acc2)}
.links a{font-size:12px;text-decoration:none;color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:3px 10px;background:var(--panel3)}
.links a:hover{border-color:var(--acc2)}
.links a.big{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:700;padding:4px 13px}
.links a.big:hover{background:var(--acc2)}
.links .none{font-size:12px;color:var(--dim);border:1px dashed var(--line);border-radius:9px;padding:3px 10px}
.chart{width:100%;height:300px}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.narr{border-left:3px solid var(--acc);margin:8px 0;padding:4px 14px;color:var(--muted)}
.narr h3{color:var(--ink);font-size:13.5px;margin:0 0 2px}
.narr p{margin:0;font-size:12.5px;line-height:1.85}
.tbl{width:100%;border-collapse:collapse;margin:10px 0;font-size:12.5px}
.tbl th,.tbl td{border:1px solid var(--line);padding:5px 11px;text-align:left;vertical-align:top}
.tbl th{background:var(--panel2)}
.empty{text-align:center;color:var(--dim);padding:50px 0}
#msg{font-size:12px;color:var(--dim);margin:0 0 6px}
.slot{margin-top:8px;border:1px dashed var(--line);border-radius:12px;padding:6px 10px;background:rgba(255,255,255,.03)}
.slot summary{cursor:pointer;color:var(--acc2);font-size:11.5px;outline:none}
.slot summary::marker{color:var(--acc2)}
.slot pre{margin:8px 0 0;white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;
  font:11.5px/1.75 ui-monospace,Consolas,"Liberation Mono",monospace;color:var(--muted)}
.slot-none{font-size:11.5px;color:var(--dim)}
.viewer-body pre{white-space:pre-wrap;word-break:break-word;font:13.5px/1.8 system-ui,sans-serif}
@media(max-width:768px){.center-pill{margin:0}.right-grp{margin-left:0}}
"""


JS_RUNTIME = r"""
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function openViewer(href){
  var v=document.getElementById("viewer");
  document.getElementById("viewerTitle").textContent=decodeURIComponent(href.split("/").pop());
  document.getElementById("viewerRaw").setAttribute("href",href);
  var body=document.getElementById("viewerBody");body.textContent="加载中…";v.hidden=false;
  fetch(href,{cache:"no-store"}).then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.text();})
  .then(function(t){body.innerHTML='<pre>'+esc(t)+"</pre>";body.scrollTop=0;})
  .catch(function(){v.hidden=true;window.open(href,"_blank");});
}
function closeViewer(){document.getElementById("viewer").hidden=true;}
function bindViewer(){
  var v=document.getElementById("viewer");
  v.addEventListener("click",function(e){if(e.target===v)closeViewer();});
  document.getElementById("viewerClose").addEventListener("click",closeViewer);
  document.addEventListener("keydown",function(e){if(e.key==="Escape"&&!v.hidden)closeViewer();});
  document.addEventListener("click",function(e){
    var a=e.target.closest("a");
    if(!a||v.contains(a))return;
    var href=a.getAttribute("href")||"";
    if(/\.md(\?|#|$)|\.txt(\?|#|$)/.test(href)){e.preventDefault();openViewer(href);}
  });
}
function bindSearch(){
  var qEl=document.getElementById("search");
  document.addEventListener("keydown",function(e){
    if(e.key==="/"&&document.activeElement!==qEl){e.preventDefault();qEl.focus();}
    if(e.key==="Escape"&&document.activeElement===qEl)qEl.blur();
  });
  qEl.addEventListener("input",runSearch);runSearch();
}
function runSearch(){
  var q=(document.getElementById("search").value||"").toLowerCase();
  var n=0,total=0;
  document.querySelectorAll(".card").forEach(function(c){
    total++;
    var hit=!q||(c.dataset.search||"").indexOf(q)!==-1;
    c.style.display=hit?"":"none";
    if(hit)n++;
  });
  var empty=document.getElementById("emptyState");
  if(empty)empty.style.display=(q&&!n)?"":"none";
}
"""


def topbar_html(drama: str, title: str, icon: str, pages, stats, search_ph: str) -> str:
    """pages=[(href, glyph, label, active)]，href 可为文件名或 #锚点；stats=[(数值, 标签)]。"""
    pill = "".join(
        f'<a href="{esc(h)}"{" class=\"on\"" if active else ""}><span class="g">{esc(g)}</span>{esc(l)}</a>'
        for h, g, l, active in pages)
    stat_html = "".join(stat(v, k) for v, k in stats)
    return f'''<div class="top">
  <a class="top-btn" href="javascript:history.back()" title="返回"><span class="rbtn">{esc(icon)}</span><span>返回</span></a>
  <div class="titlebox"><h1>{esc(title)}<span class="tag">{esc(drama)}</span></h1>
    <p class="sub">资产分析报告 · 与 工作台.html 同源视觉</p></div>
  <div class="center-pill">{pill}{stat_html}</div>
  <div class="right-grp">
    <input id="search" type="search" autocomplete="off" placeholder="{esc(search_ph)}" aria-label="搜索报告">
    <a class="top-btn" href="#" onclick="location.reload();return false;"><span class="rbtn">&#8635;</span><span>刷新</span></a>
  </div>
</div>
<p id="msg"></p>'''


def wb_page(drama: str, title: str, icon: str, pages, stats, cards_html: str,
            charts_js: str = "", echarts: bool = True, search_ph: str = "搜索…") -> str:
    """整页拼装（单文件 HTML，工作台.html 同源视觉）。

    pages=[(hash, glyph, label, active)]  stats=[(数值, 标签)]
    cards_html 由调用方用 card/sect/grid_* 组件拼出。
    """
    ech = '<script src="./_shared/js/echarts.min.js"></script>' if echarts else ""
    return f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · {esc(drama)} · 资产报告</title>
<style>{CSS}</style></head>
<body><div class="body-bg"><div class="frame" id="main">
{topbar_html(drama, title, icon, pages, stats, search_ph)}
{cards_html}
<div class="empty" id="emptyState" style="display:none">没有匹配的条目</div>
</div></div>
<div class="viewer" id="viewer" hidden><div class="viewer-panel">
  <div class="viewer-bar"><span class="vt" id="viewerTitle"></span>
    <a id="viewerRaw" href="#" target="_blank">原始文件</a>
    <button class="vclose" id="viewerClose" title="关闭">&#215;</button></div>
  <div class="viewer-body" id="viewerBody"></div>
</div></div>
{ech}
<script>
{charts_js}
{JS_RUNTIME}
bindViewer();bindSearch();
</script>
</body></html>'''
