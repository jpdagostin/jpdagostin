#!/usr/bin/env python3
"""Gera o painel de estatísticas do perfil (assets/painel-light.svg e assets/painel-dark.svg).

Uso na Action:  GITHUB_TOKEN=... python .github/scripts/painel.py --user jpdagostin
Uso local:      python .github/scripts/painel.py --data dados.json

Só usa a biblioteca padrão. Dados vêm da API GraphQL do GitHub (calendário de
contribuições e repositórios públicos). EXCLUDE remove repositórios das linguagens.
"""
import argparse, base64, datetime as dt, json, math, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

EXCLUDE = set(filter(None, os.environ.get("EXCLUDE_REPOS", "").split(",")))

MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
      restrictedContributionsCount
    }
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false){
      totalCount
      nodes{ name languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
    }
  }
}"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    u = json.load(urllib.request.urlopen(req))["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    for r in u["repositories"]["nodes"]:
        if r["name"] in EXCLUDE:
            continue
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return {"total": cal["totalContributions"], "days": days, "repos": u["repositories"]["totalCount"], "langs": langs}


def stats(data):
    days = sorted(data["days"])
    counts = [c for _, c in days]
    active = sum(1 for c in counts if c > 0)
    best_i = max(range(len(counts)), key=lambda i: counts[i]) if counts else 0
    streak = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        streak = max(streak, cur)
    return days, active, counts[best_i] if counts else 0, days[best_i][0] if days else "", streak


def font(name):
    return (ASSETS / "fonts" / f"{name}.woff2.b64").read_text().strip()


def fmt(n):
    return f"{n:,}".replace(",", ".")


def build(data, theme, today):
    days, active, best, best_date, streak = stats(data)
    last90 = sum(c for _, c in days[-90:])
    W, H = 1200, 500
    ink = "#1F2328" if theme == "light" else "#E6EDF3"
    mute = "#59636E" if theme == "light" else "#9198A1"
    hair = "#D1D9E0" if theme == "light" else "#3D444D"
    paper, pink, pmute, red, rim = "#F4EFE3", "#22201C", "#8A8272", "#B42318", "#D9D1BF"

    x0, x1 = 40, 1160
    ty0, ty1 = 92, 252          # fita
    base, top = ty1 - 34, ty0 + 18
    n = len(days)
    step = (x1 - x0 - 40) / max(n - 1, 1)
    peak = max([c for _, c in days] + [1])

    def xp(i): return x0 + 20 + i * step
    def yp(c): return base - (math.sqrt(c) / math.sqrt(peak)) * (base - top)

    # traço em degraus, como a agulha do tacógrafo
    d = [f"M{xp(0):.1f},{yp(days[0][1]):.1f}"] if days else []
    for i in range(1, n):
        d.append(f"H{xp(i):.1f}V{yp(days[i][1]):.1f}")
    d.append(f"H{x1-20:.1f}")
    trace = "".join(d)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">']
    o.append(f'<title id="t">Registro do GitHub nos últimos 12 meses: {data["total"]} contribuições em {active} dias ativos.</title>')
    o.append(f"""<style>
@font-face{{font-family:A8;src:url(data:font/woff2;base64,{font('archivo-800')}) format('woff2')}}
@font-face{{font-family:A5;src:url(data:font/woff2;base64,{font('archivo-500')}) format('woff2')}}
@font-face{{font-family:M5;src:url(data:font/woff2;base64,{font('plexmono-500')}) format('woff2')}}
.h{{font:500 26px A5,sans-serif;letter-spacing:-0.01em;fill:{ink}}}
.u{{font:500 12px M5,monospace;letter-spacing:0.08em;fill:{mute}}}
.big{{font:800 52px A8,sans-serif;letter-spacing:-0.03em;fill:{ink};font-variant-numeric:tabular-nums}}
.lab{{font:500 12px M5,monospace;letter-spacing:0.08em;fill:{mute}}}
.sm{{font:500 11px M5,monospace;letter-spacing:0.06em;fill:{pmute}}}
.lg{{font:500 13px M5,monospace;letter-spacing:0.04em;fill:{ink}}}
.lgp{{font:500 13px M5,monospace;fill:{mute}}}
.ghost{{fill:none;stroke:{red};stroke-opacity:.18;stroke-width:1.6;stroke-linejoin:round}}
.ink{{fill:none;stroke:{red};stroke-width:1.8;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:draw 3.4s cubic-bezier(.16,1,.3,1) .2s forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
@media (prefers-reduced-motion:reduce){{.ink{{animation:none;stroke-dashoffset:0}}}}
</style>""")
    sh = "0.10" if theme == "light" else "0.45"
    o.append(f'<defs><filter id="sh" x="-5%" y="-30%" width="110%" height="160%"><feDropShadow dx="0" dy="5" stdDeviation="8" flood-color="#000" flood-opacity="{sh}"/></filter></defs>')

    o.append(f'<text class="h" x="{x0}" y="52">Registro dos últimos 12 meses</text>')
    d_today = dt.date.fromisoformat(today)
    o.append(f'<text class="u" x="{x1}" y="52" text-anchor="end">ATUALIZADO {d_today.day:02d} {MESES[d_today.month-1]} {d_today.year}</text>')

    # fita de papel
    o.append(f'<rect x="{x0}" y="{ty0}" width="{x1-x0}" height="{ty1-ty0}" rx="4" fill="{paper}" filter="url(#sh)"/>')
    o.append(f'<rect x="{x0+0.5}" y="{ty0+0.5}" width="{x1-x0-1}" height="{ty1-ty0-1}" rx="4" fill="none" stroke="{rim}"/>')
    for k in range(4):
        yy = base - (base - top) * k / 3
        o.append(f'<line x1="{x0+20}" y1="{yy:.1f}" x2="{x1-20}" y2="{yy:.1f}" stroke="{pmute}" stroke-opacity="{0.5 if k==0 else 0.18}" stroke-width="{1 if k==0 else 0.7}"/>')
    for i, (date, _) in enumerate(days):
        dd = dt.date.fromisoformat(date)
        if dd.weekday() == 0:
            o.append(f'<line x1="{xp(i):.1f}" y1="{base}" x2="{xp(i):.1f}" y2="{base+5}" stroke="{pink}" stroke-opacity=".35" stroke-width=".7"/>')
        if dd.day == 1:
            o.append(f'<line x1="{xp(i):.1f}" y1="{top-6}" x2="{xp(i):.1f}" y2="{base+9}" stroke="{pink}" stroke-opacity=".45" stroke-width=".8" stroke-dasharray="2 3"/>')
            o.append(f'<text class="sm" x="{xp(i)+5:.1f}" y="{base+22}">{MESES[dd.month-1]}</text>')
    o.append(f'<path class="ghost" d="{trace}"/>')
    o.append(f'<path class="ink" pathLength="1" d="{trace}"/>')

    # leituras
    reads = [
        (fmt(data["total"]), "CONTRIBUIÇÕES"),
        (str(active), "DIAS ATIVOS"),
        (str(best), "MELHOR DIA"),
        (fmt(last90), "ÚLTIMOS 90 DIAS"),
        (str(data["repos"]), "REPOSITÓRIOS"),
    ]
    colw = (x1 - x0) / len(reads)
    for i, (v, lab) in enumerate(reads):
        x = x0 + i * colw
        if i:
            o.append(f'<line x1="{x-16:.1f}" y1="292" x2="{x-16:.1f}" y2="350" stroke="{hair}"/>')
        o.append(f'<text class="big" x="{x:.1f}" y="334">{v}</text>')
        o.append(f'<text class="lab" x="{x:.1f}" y="360">{lab}</text>')

    # linguagens
    langs = sorted(data["langs"].items(), key=lambda kv: -kv[1])
    tot = sum(v for _, v in langs) or 1
    top5 = langs[:5]
    other = tot - sum(v for _, v in top5)
    if other > 0:
        top5.append(("Outras", other))
    tones = [red, ink, "#C9733A", mute, "#7A8B6F", hair] if theme == "light" else [red, ink, "#D98A4E", mute, "#8FA383", hair]
    bx, by, bw = x0, 428, x1 - x0
    o.append(f'<text class="lab" x="{bx}" y="{by-12}">LINGUAGENS EM REPOSITÓRIOS PÚBLICOS</text>')
    cx = bx
    for k, (name, v) in enumerate(top5):
        w = bw * v / tot
        o.append(f'<rect x="{cx:.1f}" y="{by}" width="{max(w-2,1):.1f}" height="10" rx="1.5" fill="{tones[k % len(tones)]}"/>')
        cx += w
    lx = bx
    for k, (name, v) in enumerate(top5):
        pct = f"{100*v/tot:.0f}%"
        o.append(f'<rect x="{lx}" y="{by+30}" width="10" height="10" rx="1.5" fill="{tones[k % len(tones)]}"/>')
        o.append(f'<text class="lg" x="{lx+16}" y="{by+40}">{name}</text>')
        wname = 8.2 * len(name)
        o.append(f'<text class="lgp" x="{lx+22+wname:.0f}" y="{by+40}">{pct}</text>')
        lx += 22 + wname + 8.2 * len(pct) + 34
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "jpdagostin"))
    ap.add_argument("--data")
    a = ap.parse_args()
    if a.data:
        data = json.loads(Path(a.data).read_text())
    else:
        data = fetch(a.user, os.environ["GITHUB_TOKEN"])
    today = dt.date.today().isoformat()
    for theme in ("light", "dark"):
        (ASSETS / f"painel-{theme}.svg").write_text(build(data, theme, today), encoding="utf-8")
    print("painel gerado:", data["total"], "contribuições")


if __name__ == "__main__":
    main()
