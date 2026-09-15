# -*- coding: utf-8 -*-
"""qn 千牛网页版「聊天记录」日期范围抓取（双月日历，自动导航月份，只点本月格子）。
用法: python qn_scrape_range.py <YYYY-MM-DD起> <YYYY-MM-DD止> <slug> <port>"""
import sys, re
from pathlib import Path
from playwright.sync_api import sync_playwright

START=sys.argv[1]; END=sys.argv[2]
SLUG=sys.argv[3] if len(sys.argv)>3 else "dashi"
PORT=sys.argv[4] if len(sys.argv)>4 else "9222"
OUT=Path(r"C:\Users\Administrator\千牛产出\脱敏记录"); OUT.mkdir(parents=True,exist_ok=True)

PHONE=re.compile(r'1[3-9]\d{9}'); ORDER=re.compile(r'\d{11,}'); IDC=re.compile(r'\d{17}[\dXx]')
EMAIL=re.compile(r'[\w.\-]+@[\w.\-]+\.\w+'); TAXNO=re.compile(r'\b[0-9A-HJ-NP-Z]{15,20}\b')
COMPANY=re.compile(r'[一-龥A-Za-z0-9（）()]{2,}?(?:有限公司|股份公司|集团|科技公司|商贸|贸易公司|实业|厂|店|公司)')
ADDR=re.compile(r'[一-龥\dA-Za-z]{0,12}(?:省|市|区|县|镇|乡|村|路|街|巷|道|弄|号|室|栋|幢|座|单元|楼|小区|花园|绿洲|公寓|大厦|苑|庄|[一二三四五六七八九十\d]+期)[一-龥\dA-Za-z\-#]{0,18}')
CN={'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'十一':11,'十二':12}
_bmap={}; _L='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
def alias(n):
    if n not in _bmap: _bmap[n]='客户'+_L[len(_bmap)%26]+('' if len(_bmap)<26 else str(len(_bmap)//26))
    return _bmap[n]
def ds(t):
    if not t: return ''
    for nk,al in sorted(_bmap.items(),key=lambda x:-len(x[0])):
        if nk: t=t.replace(nk,al)
    t=EMAIL.sub('**邮箱**',t); t=COMPANY.sub('**单位**',t)
    t=PHONE.sub('1**手机**',t); t=IDC.sub('**证件**',t); t=TAXNO.sub('**税号**',t); t=ORDER.sub('**单号**',t)
    t=re.sub(r'\btb[a-z0-9_]{4,}\b','客户*',t,flags=re.I); t=ADDR.sub('**地址**',t)
    return re.sub(r'\s+',' ',t).strip()

def panel_month(page):
    for btn in page.query_selector_all('.next-calendar-btn'):
        t=(btn.inner_text() or '').strip()
        m=re.match(r'^([一二三四五六七八九十]{1,2})月$', t)
        if m and m.group(1) in CN: return CN[m.group(1)]
    return None
def pick_cur_month_day(page, day):
    for c in page.query_selector_all('.next-calendar-cell'):
        cls=c.get_attribute('class') or ''
        if 'prev-month' in cls or 'next-month' in cls or 'disabled' in cls: continue
        if (c.inner_text() or '').strip()==day:
            try: c.click(force=True,timeout=3000); return True
            except Exception: continue
    return False
def nav_and_pick(page, ym, day):
    m=int(ym[5:7])
    for _ in range(14):
        pm=panel_month(page)
        if pm is None: return False
        if pm==m: return pick_cur_month_day(page, day)
        btn=page.query_selector('.next-calendar-btn-prev-month' if m<pm else '.next-calendar-btn-next-month')
        if not btn: return False
        try: btn.click(force=True,timeout=2000)
        except Exception: return False
        page.wait_for_timeout(450)
    return False

with sync_playwright() as p:
    b=p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx=b.contexts[0]
    for pg in list(ctx.pages):
        if 'im-history-search' in pg.url:
            try: pg.close()
            except Exception: pass
    page=ctx.new_page()
    page.goto("https://market.m.taobao.com/app/qn/im-history-search/index.html#/", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(2500); page.bring_to_front()
    ins=page.query_selector_all('input')
    if len(ins)<4: print("ERR 无查询表单(该店千牛未登录?)"); raise SystemExit

    # 起始日期
    ins[2].click(force=True); page.wait_for_timeout(1200)
    ok1=nav_and_pick(page, START[:7], str(int(START[8:10])))
    page.wait_for_timeout(800)
    # 结束日期
    if not page.query_selector('.next-calendar'):
        ins[3].click(force=True); page.wait_for_timeout(1000)
    ok2=nav_and_pick(page, END[:7], str(int(END[8:10])))
    page.wait_for_timeout(600)
    for btn in page.query_selector_all('button'):
        if (btn.inner_text() or '').strip() in ('确定','确认'):
            try: btn.click(force=True,timeout=3000)
            except Exception: pass
            break
    page.wait_for_timeout(700)
    for btn in page.query_selector_all('button'):
        if (btn.inner_text() or '').strip()=='查询':
            try: btn.click(force=True,timeout=3000)
            except Exception: pass
            break
    page.wait_for_timeout(4500)
    vals=page.eval_on_selector_all('input','e=>e.map(x=>x.value)')
    print("日期框:", vals, "起始点击:", ok1, "结束点击:", ok2)
    if START not in str(vals) or END not in str(vals):
        print("WARN 日期未设到位")

    # 左侧结果滚动加载
    left=page.query_selector('.message-list-left')
    if left:
        for _ in range(40):
            n0=page.eval_on_selector_all('.message-list-left .results-list','e=>e.length')
            page.evaluate('(e)=>e.scrollTop=e.scrollTop+e.scrollHeight', left)
            page.wait_for_timeout(600)
            n1=page.eval_on_selector_all('.message-list-left .results-list','e=>e.length')
            if n1==n0: break
    n=page.eval_on_selector_all('.message-list-left .results-list','e=>e.length')
    print("结果会话数:", n)

    sessions=[]
    for i in range(n):
        items=page.query_selector_all('.message-list-left .results-list')
        if i>=len(items): break
        it=items[i]
        try: it.scroll_into_view_if_needed()
        except Exception: pass
        nick=(it.inner_text() or '').strip().split('\n')[0]
        al=alias(nick)
        try: it.click(force=True,timeout=4000)
        except Exception: continue
        page.wait_for_timeout(900)
        sc=page.query_selector('.message-list-right')
        collected={}
        if sc:
            for _ in range(14):
                for w in page.query_selector_all('.message-list-right [class*=chatWrap]'):
                    raw=(w.inner_text() or '').strip()
                    if not raw: continue
                    tm=re.search(r'\b(\d{2}:\d{2}:\d{2})\b',raw); tm=tm.group(1) if tm else ''
                    rstr=raw.rstrip()
                    if '服务助手' in raw: who='智能助手'
                    elif nick and rstr.endswith(nick): who='买家'
                    else: who='客服'
                    body=re.sub(r'\b\d{2}:\d{2}:\d{2}\b','',raw)
                    if nick: body=body.replace(nick,'')
                    body=re.sub(r'[一-龥A-Za-z0-9_]+\s*[:：]\s*[一-龥A-Za-z]{1,6}\s*$','',body)
                    body=ds(body)
                    if body and body!='**地址**': collected[(tm,who,body)]=1
                page.evaluate('(e)=>e.scrollTop=Math.max(0,e.scrollTop-350)', sc)
                page.wait_for_timeout(150)
        sessions.append((al,sorted(collected.keys(),key=lambda x:x[0])))
        print(f"  [{i+1}/{n}] {al}: {len(sessions[-1][1])}条")

    md=[f"# {SLUG} 客服聊天(脱敏) {START}~{END}","",f"会话数: {len(sessions)}  总消息: {sum(len(m) for _,m in sessions)}",""]
    for al,msgs in sessions:
        md.append(f"\n## {al}  ({len(msgs)}条)")
        for tm,who,body in msgs: md.append(f"- {tm} **{who}**: {body}")
    dest=OUT/f"qn_chats_{START}_{END}_{SLUG}.md"; dest.write_text("\n".join(md),encoding="utf-8")
    print("DONE 会话数:", len(sessions), "总消息:", sum(len(m) for _,m in sessions), "→", dest.name)
