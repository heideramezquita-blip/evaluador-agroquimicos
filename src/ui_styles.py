"""Static CSS for the Streamlit interface.

Kept separate from app.py so presentation styling does not obscure the
application flow. The stylesheet is static and does not affect evaluation
logic.
"""

APP_CSS = r"""<style>
:root{--accent:#e5322d;--ink:#161616;--muted:#667085;--line:#e7e7e7;--surface:#fff;--soft:#f7f7f8}
[data-testid="stAppViewContainer"]{background:#fff}
[data-testid="stHeader"]{background:rgba(255,255,255,.94);border-bottom:1px solid #eee}
.block-container{max-width:1040px;padding-top:2.1rem;padding-bottom:4.5rem}
.brand{display:flex;align-items:center;gap:.7rem;font-weight:800;font-size:1.05rem;color:var(--ink);margin-bottom:3.3rem}
.brand-mark{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:9px;background:var(--accent);color:#fff;font-size:17px}
.brand-badge{font-size:.72rem;font-weight:700;padding:.25rem .55rem;border-radius:999px;background:#f2f4f7;color:#475467}
.hero{text-align:center;max-width:820px;margin:0 auto 2rem}
.hero h1{font-size:2.55rem;letter-spacing:-.035em;line-height:1.1;margin:0 0 .75rem;color:var(--ink);font-weight:800}
.hero p{font-size:1.08rem;line-height:1.6;color:var(--muted);margin:0 auto;max-width:720px}
.upload-wrap{max-width:760px;margin:0 auto 1rem}
div[data-testid="stFileUploader"]{max-width:760px;margin:0 auto}
div[data-testid="stFileUploader"]>label{display:none}
div[data-testid="stFileUploader"] section{min-height:210px;border:2px dashed #d0d5dd!important;border-radius:16px!important;background:#fafafa!important;padding:2.2rem 1rem!important;transition:.18s ease}
div[data-testid="stFileUploader"] section:hover{border-color:var(--accent)!important;background:#fff8f7!important}
div[data-testid="stFileUploader"] section button{background:var(--accent)!important;color:#fff!important;border:0!important;border-radius:9px!important;font-weight:750!important;padding:.65rem 1.1rem!important}
div[data-testid="stFileUploader"] section button *,div[data-testid="stFileUploader"] section button p,div[data-testid="stFileUploader"] section button span,div[data-testid="stFileUploader"] section button svg{color:#fff!important;fill:#fff!important}
div[data-testid="stFileUploader"] section>div{width:100%!important;align-items:center!important;text-align:center!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]{align-items:center!important;text-align:center!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]>div{text-align:center!important}
div[data-testid="stFileUploader"] section button{margin-left:auto!important;margin-right:auto!important}
.helper{text-align:center;color:#667085;font-size:.9rem;font-weight:500;margin:.3rem 0 1.8rem}
.secondary{max-width:760px;margin:0 auto}
div[data-testid="stExpander"]{border:1px solid #d0d5dd;border-radius:12px;background:#fff} div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary *{color:#344054!important;font-weight:650!important;opacity:1!important} div[data-testid="stExpander"] svg{fill:#667085!important;color:#667085!important}
div.stButton{max-width:760px;margin:1.2rem auto 0}
div.stButton>button{min-height:3.2rem;border:0;border-radius:10px;font-size:1rem;font-weight:750;background:var(--accent)!important;color:#fff!important;box-shadow:0 4px 12px rgba(229,50,45,.18)}
div.stButton>button *,div.stButton>button p,div.stButton>button span,div.stButton>button svg{color:#fff!important;fill:#fff!important}
div.stButton>button:hover{background:#c92b27;color:#fff;border:0}
.divider{height:1px;background:#eee;margin:3rem 0 2rem}
.result-card{padding:1.35rem 1.45rem;border-radius:14px;margin:1rem 0 1.5rem;border:1px solid;border-left-width:7px}
.result-card h2{margin:0 0 .5rem;font-size:1.42rem}.result-card p{margin:0;line-height:1.58}.result-note{display:block;margin-top:.55rem;font-size:.9rem;color:#667085;font-weight:500}
.result-identity{display:block;margin-top:.75rem;padding-top:.65rem;border-top:1px solid rgba(71,84,103,.18);font-size:.92rem;line-height:1.5;font-weight:650}
.result-card.result-red{background:#fff2f1;border-color:#ef4444;color:#7f1d1d}
.result-card.result-red-review{background:#fff7f7;border-color:#f87171;color:#991b1b}
.result-card.result-pink{background:#fdf2f8;border-color:#ec4899;color:#9d174d}
.result-card.result-orange{background:#fff6ed;border-color:#f97316;color:#7c2d12}
.result-card.result-yellow{background:#fffbeb;border-color:#eab308;color:#713f12}
.result-card.result-purple{background:#faf5ff;border-color:#a855f7;color:#6b21a8}
.result-card.result-green{background:#f0fdf4;border-color:#22c55e;color:#166534}
.result-card.result-neutral{background:#f8fafc;border-color:#94a3b8;color:#334155}
.section-title{font-size:1.25rem;font-weight:800;color:var(--ink);margin:1.7rem 0 .8rem}
.match-box{border:1px solid #e4e7ec;border-radius:12px;padding:1rem 1.1rem;margin:.65rem 0;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.03)}
.match-title{font-size:1.05rem;font-weight:800;color:#101828;margin-bottom:.35rem}.match-meta{color:#475467;font-size:.92rem;line-height:1.6}.match-meta b{color:#344054;font-weight:750}.criterion-summary{margin:.7rem 0 0;padding:.7rem .8rem;border-radius:9px;background:#f8fafc;color:#344054;font-size:.9rem;line-height:1.5}.criterion-summary-title{font-weight:800;color:#101828;margin-bottom:.25rem}.criterion-summary ul{margin:.2rem 0 0;padding-left:1.1rem}.criterion-summary li+li{margin-top:.3rem}
[data-testid="stMetric"]{background:#fafafa;border:1px solid #eee;padding:.8rem;border-radius:10px}
/* Streamlit theme hardening: keep native widgets readable in light UI */
.stApp, .stApp p, .stApp label, .stApp span, .stApp div{color:#344054}
div[data-testid="stExpander"] details{background:#fff!important}
div[data-testid="stExpander"] details,div[data-testid="stExpander"] details>*{background:#fff!important;color:#344054!important}
div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary[aria-expanded="true"]{background:#f8fafc!important;color:#1f2937!important;border-radius:11px!important}
div[data-testid="stExpander"] summary:hover{background:#f2f4f7!important}
div[data-testid="stExpander"] summary p,div[data-testid="stExpander"] summary span,div[data-testid="stExpander"] summary svg{color:#1f2937!important;fill:#475467!important;font-weight:700!important}
div[data-testid="stExpander"] details>div,div[data-testid="stExpander"] details>div>div{background:#fff!important;color:#344054!important}
div[data-testid="stExpander"] details>div p,
div[data-testid="stExpander"] details>div label,
div[data-testid="stExpander"] details>div span,
div[data-testid="stExpander"] details>div strong,
div[data-testid="stExpander"] details>div div{color:#344054!important}
div[data-testid="stExpander"] details>div [data-testid="stMarkdownContainer"],
div[data-testid="stExpander"] details>div [data-testid="stMarkdownContainer"] *{color:#344054!important;background-color:transparent!important}
div[data-testid="stTextArea"] label p{color:#344054!important;font-weight:650!important}
div[data-testid="stTextArea"] textarea{background:#fff!important;color:#101828!important;border:1px solid #98a2b3!important}
div[data-testid="stTextArea"] textarea::placeholder{color:#667085!important;opacity:1!important}
div[data-testid="stCheckbox"] label p,div[data-testid="stCheckbox"] label span{color:#344054!important}
div[data-testid="stMetric"]{background:#f8fafc!important}
div[data-testid="stMetric"] label,div[data-testid="stMetric"] label p{color:#475467!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"],div[data-testid="stMetric"] [data-testid="stMetricValue"] *{color:#101828!important}
[data-testid="stDataFrame"]{color:#101828!important;border:1px solid #dfe3e8!important;border-radius:12px!important;overflow:hidden!important;background:#fff!important;box-shadow:0 1px 2px rgba(16,24,40,.04)}
[data-testid="stDataFrame"] *{font-size:.9rem!important}
[data-testid="stDataFrame"] [role="columnheader"]{background:#f2f4f7!important;color:#344054!important;font-weight:750!important;border-color:#d0d5dd!important}
[data-testid="stDataFrame"] [role="columnheader"] *{color:#344054!important;font-weight:750!important}
[data-testid="stDataFrame"] [role="gridcell"]{background:#fff!important;color:#101828!important;border-color:#eaecf0!important}
[data-testid="stDataFrame"] [role="gridcell"] *{color:#101828!important}
[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"]{background:#f9fafb!important}
[data-testid="stDataFrame"] canvas{filter:none!important}
h1,h2,h3,h4{color:#101828!important}

/* File uploader: light file chips + centered empty-state controls */
div[data-testid="stFileUploader"] section{display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important}
div[data-testid="stFileUploader"] section>div{display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important;gap:.7rem!important;width:100%!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"]{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;width:auto!important}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] *{text-align:center!important}
div[data-testid="stFileUploader"] section small{color:#667085!important;text-align:center!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]{background:#fff!important;border:1px solid #d0d5dd!important;border-radius:10px!important;color:#344054!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *{color:#344054!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button{background:#f2f4f7!important;border:1px solid #e4e7ec!important;color:#475467!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button *{color:#475467!important;fill:#475467!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button:hover{background:#fee4e2!important;border-color:#fda29b!important}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button:hover *{color:#b42318!important;fill:#b42318!important}

/* Uploaded-file document glyph: target Streamlit's icon container, not only the SVG */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div:first-child,
div[data-testid="stFileUploader"] ul>li>div:first-child{
background:#f2f4f7!important;
color:#475467!important;
border-radius:8px!important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div:first-child *,
div[data-testid="stFileUploader"] ul>li>div:first-child *{
color:#475467!important;
fill:#475467!important;
}

/* Uploaded-file row: Streamlit renders this outside the dropzone in some versions */
div[data-testid="stFileUploader"] ul,
div[data-testid="stFileUploader"] ul>li,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"]>div{
background:#fff!important;color:#344054!important;border-color:#d0d5dd!important}
div[data-testid="stFileUploader"] ul>li{border:1px solid #d0d5dd!important;border-radius:10px!important;box-shadow:0 1px 2px rgba(16,24,40,.04)!important}
div[data-testid="stFileUploader"] ul>li *,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *{color:#344054!important}

/* Uploaded document icon: Streamlit/BaseWeb may keep a dark theme background */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg,
div[data-testid="stFileUploader"] ul>li svg{
color:#475467!important;
fill:#475467!important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg:first-of-type,
div[data-testid="stFileUploader"] ul>li svg:first-of-type{
background:#f2f4f7!important;
border-radius:8px!important;
}
div[data-testid="stFileUploader"] ul>li button,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button{background:#f2f4f7!important;color:#475467!important;border:1px solid #e4e7ec!important}
div[data-testid="stFileUploader"] ul>li button *,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button *{color:#475467!important;fill:#475467!important}

.clean-table-wrap{width:100%;overflow-x:auto;border:1px solid #dfe3e8;border-radius:12px;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.04);margin:.35rem 0 1.25rem}
.clean-table{width:100%;border-collapse:collapse;background:#fff;color:#101828;font-size:.9rem}
.clean-table th{background:#f2f4f7;color:#344054;font-weight:750;text-align:left;padding:.72rem .75rem;border-bottom:1px solid #d0d5dd;white-space:nowrap}
.clean-table td{background:#fff;color:#101828;padding:.72rem .75rem;border-bottom:1px solid #eaecf0;vertical-align:top}
.clean-table tr:last-child td{border-bottom:0}.clean-table tbody tr:hover td{background:#f9fafb}
/* Print/PDF: expose collapsed Streamlit expander content. */
@media print{
  html,body,[data-testid="stAppViewContainer"],.stApp{background:#fff!important}
  *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}

  /* Native <details> elements are normally printed in their current
     collapsed state. Force Streamlit expander bodies to participate in
     print layout without changing their interactive state on screen. */
  div[data-testid="stExpander"] details,
  div[data-testid="stExpander"] details:not([open]){
    overflow:visible!important;
    height:auto!important;
    max-height:none!important;
  }
  div[data-testid="stExpander"] details>div,
  div[data-testid="stExpander"] details:not([open])>div,
  div[data-testid="stExpander"] details>summary~*{
    display:block!important;
    visibility:visible!important;
    overflow:visible!important;
    height:auto!important;
    max-height:none!important;
    opacity:1!important;
  }
  div[data-testid="stExpander"]{
    overflow:visible!important;
    break-inside:auto!important;
    page-break-inside:auto!important;
  }
  div[data-testid="stExpander"] summary{
    break-after:avoid-page!important;
    page-break-after:avoid!important;
  }

  /* Interactive controls are not part of the printable evaluation report. */
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stFileUploader"],
  div.stButton,
  footer{
    display:none!important;
  }

  .block-container{
    max-width:none!important;
    padding:0.35in 0.45in!important;
  }
  .brand{margin-bottom:1.4rem!important}
  .hero{margin-bottom:1.2rem!important}
  .clean-table-wrap{overflow:visible!important}
  .result-card,.match-box,.clean-table-wrap,[data-testid="stMetric"]{
    break-inside:avoid-page!important;
    page-break-inside:avoid!important;
  }
}

footer{visibility:hidden}
@media(max-width:700px){.block-container{padding-top:1.2rem}.brand{margin-bottom:2.2rem}.hero h1{font-size:2rem}.hero p{font-size:.98rem}}
</style>"""
