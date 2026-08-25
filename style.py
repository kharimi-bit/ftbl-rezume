# -*- coding: utf-8 -*-
"""Стили сервиса. Один файл на всё: экран и печать.

Палитра — брендбук «Футбологики», раздел 02. Терракота #B4472F взята
как акцент событий и здесь работает акцентом действия: она единственная
тёплая на зелёном листе, поэтому глаз находит кнопку сразу.
"""

CSS = """
:root{
  --jade:#40916C; --ink:#1B4332; --mint:#74C69D; --soft:#D8F3DC;
  --muted:#6E8B7C; --line:#D8F3DC; --bg:#fff; --ground:#F4F8F5;
  --accent:#B4472F;
  --font:'Carlito',Calibri,'Segoe UI',system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--font);
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--jade)}
img{max-width:100%;display:block}

/* ─── лист резюме ─── */
.sheet{max-width:820px;margin:0 auto;background:var(--bg);
  box-shadow:0 1px 2px rgba(27,67,50,.06),0 18px 50px -24px rgba(27,67,50,.4)}
.sheet-in{padding:0}

.bar{background:var(--ink);color:#fff;font-weight:700;font-size:1.02rem;
  padding:11px 22px;letter-spacing:.01em}
.bar.sm{font-size:.94rem;padding:9px 22px}

.top{display:grid;grid-template-columns:190px minmax(0,1fr);gap:0;
  border:1px solid var(--line);border-top:0}
@media(max-width:620px){.top{grid-template-columns:1fr}}
.photo{background:var(--soft);min-height:230px;position:relative;overflow:hidden}
.photo img{width:100%;height:100%;object-fit:cover;position:absolute;inset:0}
.photo .none{position:absolute;inset:0;display:grid;place-items:center;
  color:var(--muted);font-size:.82rem;text-align:center;padding:16px}
.facts{border-left:1px solid var(--line)}
@media(max-width:620px){.facts{border-left:0;border-top:1px solid var(--line)}}
.fact{display:grid;grid-template-columns:210px minmax(0,1fr);
  border-bottom:1px solid var(--line)}
.fact:last-child{border-bottom:0}
@media(max-width:620px){.fact{grid-template-columns:1fr}}
.fact dt{padding:9px 16px;font-weight:700;background:#fff;font-size:.94rem}
.fact dd{margin:0;padding:9px 16px;border-left:1px solid var(--line);
  color:var(--ink);font-weight:700;font-size:.94rem}
@media(max-width:620px){.fact dd{border-left:0;padding-top:0;font-weight:400}}

.block{border:1px solid var(--line);border-top:0}
.row{padding:10px 22px;border-bottom:1px solid var(--line);font-size:.95rem}
.row:last-child{border-bottom:0}
.row b{font-weight:700}
.sub{padding:12px 22px;border-bottom:1px solid var(--line)}
.sub:last-child{border-bottom:0}
.sub h4{margin:0 0 8px;font-size:.86rem;color:var(--muted);font-weight:700;
  letter-spacing:.04em;text-transform:uppercase}
.sub ul{margin:0;padding-left:19px}
.sub li{margin-bottom:5px;font-size:.95rem}
.sub li:last-child{margin-bottom:0}

.ref{display:grid;grid-template-columns:170px minmax(0,1fr);
  border:1px solid var(--line);border-top:0}
@media(max-width:620px){.ref{grid-template-columns:1fr}}
.ref-ph{background:var(--soft);min-height:150px;position:relative;overflow:hidden}
.ref-ph img{width:100%;height:100%;object-fit:cover;position:absolute;inset:0}
.ref-tx{padding:16px 20px;font-size:.94rem;text-align:center;
  border-left:1px solid var(--line)}
@media(max-width:620px){.ref-tx{border-left:0}}
.ref-tx .who{margin-top:9px;font-weight:700}
.ref-tx .role{color:var(--muted);font-size:.88rem;font-weight:400}

.files{display:grid;gap:8px;padding:14px 22px}
.file{display:flex;align-items:center;gap:11px;padding:9px 13px;
  border:1px solid var(--line);border-radius:9px;background:#fff;
  text-decoration:none;color:var(--ink);font-size:.92rem}
.file:hover{border-color:var(--jade)}
.file .k{font-size:.76rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em;margin-left:auto;white-space:nowrap}

/* ─── шапка и карточки: нужны и анкете, и титульной ─── */
.hdr{background:var(--ink);color:#fff}
.hdr-in{max-width:1360px;margin:0 auto;padding:16px 22px;display:flex;
  align-items:center;gap:14px;flex-wrap:wrap}
.hdr .mk{display:flex;gap:5px;flex:none}
.hdr .mk i{width:8px;height:8px;border-radius:50%;background:var(--mint)}
.hdr .mk i:last-child{background:#fff}
.hdr b{font-size:1.04rem;letter-spacing:.02em}
.hdr .sp{margin-left:auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.hdr small{color:var(--mint);font-size:.85rem}
.card{background:#fff;border:2px solid var(--line);border-radius:16px;
  padding:22px 24px;margin-bottom:16px}
.card>h2{margin:0 0 4px;font-size:1.18rem}
.card>p.hint{margin:0 0 16px;color:var(--muted);font-size:.9rem}

/* ─── интерфейс вокруг листа ─── */
.wrap{max-width:1080px;margin:0 auto;padding:26px 20px 70px}
.tools{max-width:820px;margin:0 auto 18px;display:flex;flex-wrap:wrap;gap:10px;
  align-items:center}
.btn{display:inline-block;padding:11px 22px;border-radius:999px;border:0;
  font-family:inherit;font-size:.97rem;font-weight:700;cursor:pointer;
  text-decoration:none;transition:.16s}
.btn-main{background:var(--accent);color:#fff}
.btn-main:hover{background:#9d3c26}
.btn-ghost{background:#fff;color:var(--ink);border:2px solid var(--line)}
.btn-ghost:hover{border-color:var(--jade)}
.btn-jade{background:var(--jade);color:#fff}
.btn-jade:hover{background:#357a5b}
.note{max-width:820px;margin:0 auto 18px;font-size:.88rem;color:var(--muted)}

/* ─── печать: чистый A4 ─── */
@page{size:A4;margin:12mm}
@media print{
  body{background:#fff}
  .wrap{padding:0;max-width:none}
  .tools,.note,.noprint{display:none!important}
  .sheet{box-shadow:none;max-width:none;margin:0}
  .bar{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .photo,.ref-ph{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .block,.top,.ref{break-inside:avoid}
  .ref{break-inside:avoid}
  a{text-decoration:none}
}
"""
