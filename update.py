#!/usr/bin/env python3
"""Berk's Book NBA v2. No paid dependencies; only current-season games.

Data: ESPN's undocumented public scoreboard + game-summary endpoints and
The Odds API's free 'totals' market. Unexpected response shapes fail closed:
no projection, never a fabricated estimate.
"""
from __future__ import annotations
import datetime as dt
import json
import logging
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SITE_DATA = ROOT / 'site' / 'data'
START = dt.date(2026, 10, 20)
TZ = ZoneInfo('America/New_York')
MIN_GAMES = 10          # Minimum for official WATCH/paper signals
PREVIEW_MIN_GAMES = 1   # Minimum for experimental projections
WATCH_EDGE = 5.5
HEADERS = {'User-Agent': 'BerkBookNBA/0.1 (personal stats dashboard)', 'Accept':'application/json'}
TEAMS = {
 'ATL':'Atlanta Hawks','BOS':'Boston Celtics','BKN':'Brooklyn Nets','CHA':'Charlotte Hornets',
 'CHI':'Chicago Bulls','CLE':'Cleveland Cavaliers','DAL':'Dallas Mavericks',
 'DEN':'Denver Nuggets','DET':'Detroit Pistons','GS':'Golden State Warriors',
 'GSW':'Golden State Warriors','HOU':'Houston Rockets','IND':'Indiana Pacers',
 'LAC':'Los Angeles Clippers','LAL':'Los Angeles Lakers','MEM':'Memphis Grizzlies',
 'MIA':'Miami Heat','MIL':'Milwaukee Bucks','MIN':'Minnesota Timberwolves',
 'NO':'New Orleans Pelicans','NOP':'New Orleans Pelicans','NY':'New York Knicks',
 'NYK':'New York Knicks','OKC':'Oklahoma City Thunder','ORL':'Orlando Magic',
 'PHI':'Philadelphia 76ers','PHX':'Phoenix Suns','POR':'Portland Trail Blazers',
 'SA':'San Antonio Spurs','SAS':'San Antonio Spurs','SAC':'Sacramento Kings',
 'TOR':'Toronto Raptors','UTAH':'Utah Jazz','UTA':'Utah Jazz','WAS':'Washington Wizards',
 'WSH':'Washington Wizards'
}

def now_utc(): return dt.datetime.now(dt.timezone.utc)

def read_json(path, default):
    try: return json.loads(path.read_text())
    except (OSError, ValueError): return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n')

def request_json(url, *, timeout=18):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.load(response)
        return data, dict(response.headers)

def parse_value(x):
    try: return float(str(x).replace(',','').strip())
    except (TypeError, ValueError): return None

def find_stat(stats, names, fallback_label=None):
    for item in stats:
        if not isinstance(item, dict): continue
        name = str(item.get('name','')).lower().replace('_','').replace('-','')
        label = str(item.get('label','')).lower()
        if name in names or (fallback_label and label in fallback_label):
            return item.get('displayValue', item.get('value'))
    return None

def extract_box(team_stats):
    """Recognizes standard ESPN boxscore team-stat rows; returns None otherwise."""
    if not isinstance(team_stats, list): return None
    fg = find_stat(team_stats, {'fieldgoalsmadefieldgoalsattempted'}, {'fg'})
    ft = find_stat(team_stats, {'freethrowsmadefreethrowsattempted'}, {'ft'})
    fga = find_stat(team_stats, {'fieldgoalsattempted'})
    fta = find_stat(team_stats, {'freethrowsattempted'})
    if isinstance(fg,str) and '-' in fg: fga = fg.split('-')[-1]
    if isinstance(ft,str) and '-' in ft: fta = ft.split('-')[-1]
    orb = find_stat(team_stats, {'offensiverebounds'}, {'or','oreb'})
    tov = find_stat(team_stats, {'turnovers','totalturnovers'}, {'to','tov'})
    vals = [parse_value(i) for i in [fga,fta,orb,tov]]
    if any(x is None for x in vals): return None
    fga, fta, orb, tov = vals
    poss = fga - orb + tov + .44 * fta
    return {'fga':fga,'fta':fta,'orb':orb,'tov':tov,'poss':round(poss,3)} if 60 < poss < 150 else None

def short_name(competitor):
    team=competitor.get('team',{})
    abbr=str(team.get('abbreviation','')).upper()
    return TEAMS.get(abbr, team.get('displayName') or team.get('name') or '')

def normalize(name):
    import re
    return re.sub(r'[^a-z0-9]', '', str(name).lower().replace('la clippers','los angeles clippers'))

def event_to_game(event):
    comps=event.get('competitions',[])
    if not comps: return None
    competitors=comps[0].get('competitors',[])
    home=next((c for c in competitors if c.get('homeAway')=='home'),None)
    away=next((c for c in competitors if c.get('homeAway')=='away'),None)
    if not home or not away: return None
    status=event.get('status',{})
    completed=bool(status.get('type',{}).get('completed'))
    return {
      'id':str(event.get('id')),'date':event.get('date'),
      'home':short_name(home),'away':short_name(away),
      'status':'final' if completed else 'scheduled',
      'home_score':parse_value(home.get('score')) if completed else None,
      'away_score':parse_value(away.get('score')) if completed else None,
      'period':status.get('period',0),
      'home_team_id':str(home.get('id') or home.get('team',{}).get('id')),
      'away_team_id':str(away.get('id') or away.get('team',{}).get('id')),
    }

def attach_boxes(game):
    url='https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event='+urllib.parse.quote(game['id'])
    summary,_=request_json(url)
    boxes=summary.get('boxscore',{}).get('teams',[])
    for side in ('home','away'):
        target=normalize(game[side])
        matched=next((b for b in boxes if normalize(b.get('team',{}).get('displayName')) == target),None)
        if not matched:
            matched=next((b for b in boxes if str(b.get('team',{}).get('id'))==game[f'{side}_team_id']),None)
        if matched:
            parsed=extract_box(matched.get('statistics',[]))
            if parsed: game[side+'_box']=parsed
    return game

def pull_scores(archive, now_date):
    if now_date < START: return {}, []
    # Bootstrap from start of current season; afterwards re-check recent 3 days.
    start = START if not archive else max(START,now_date-dt.timedelta(days=3))
    todays=[]
    day=start
    while day <= now_date+dt.timedelta(days=1):
        url=f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day:%Y%m%d}&limit=100'
        try:
            body,_=request_json(url)
            events=body.get('events',[])
            if day in (now_date,now_date+dt.timedelta(days=1)):
                todays += [g for e in events if (g:=event_to_game(e))]
            for event in events:
                g=event_to_game(event)
                if not g or g['status']!='final' or g['home_score'] is None or g['away_score'] is None: continue
                old=archive.get(g['id']) or {}
                # Keep previously fetched boxscores if ESPN later returns no details.
                g.update({k:old[k] for k in ('home_box','away_box') if k in old})
                if 'home_box' not in g or 'away_box' not in g:
                    try: g=attach_boxes(g)
                    except Exception as ex: logging.warning('boxscore %s: %s',g['id'],ex)
                archive[g['id']] = g
        except Exception as ex:
            logging.warning('scoreboard %s: %s',day,ex)
        day += dt.timedelta(days=1)
        time.sleep(.07)
    return archive, todays

def calculate_team_stats(archive):
    records={}
    for game in archive.values():
        # Overtime games: totals are not comparable with 48-minute pace.
        if game.get('period',4) > 4: continue
        if 'home_box' not in game or 'away_box' not in game: continue
        if game.get('home_score') is None or game.get('away_score') is None: continue
        for side in ('home','away'):
            other='away' if side=='home' else 'home'
            name=game[side]; box=game[side+'_box']; opponent=game[other+'_box']
            r=records.setdefault(name,{'name':name,'games':0,'pts':0,'opp_pts':0,'poss':0,'opp_poss':0})
            r['games']+=1; r['pts']+=game[side+'_score'];r['opp_pts']+=game[other+'_score']
            r['poss']+=box['poss']; r['opp_poss']+=opponent['poss']
    league_pts=sum(v['pts'] for v in records.values())
    league_poss=sum(v['poss'] for v in records.values())
    league_eff=100*league_pts/league_poss if league_poss else None
    out={}
    for name,r in records.items():
        out[name]={'team':name,'games':r['games'],
          'pace':round(r['poss']/r['games'],2),
          'ortg':round(100*r['pts']/r['poss'],2),
          'drtg':round(100*r['opp_pts']/r['opp_poss'],2),
          'ready':r['games']>=MIN_GAMES}
    return out, league_eff

def get_odds(api_key):
    if not api_key: return [],None
    args=urllib.parse.urlencode({'apiKey':api_key,'regions':'us','markets':'totals','oddsFormat':'american'})
    url='https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?'+args
    body,headers=request_json(url)
    return body,headers.get('x-requests-remaining')

def find_odds(game, odds):
    for e in odds:
        if normalize(e.get('home_team')) != normalize(game['home']) or normalize(e.get('away_team')) != normalize(game['away']): continue
        offers=[]
        for book in e.get('bookmakers',[]):
            for market in book.get('markets',[]):
                if market.get('key')!='totals':continue
                over=next((o for o in market.get('outcomes',[]) if o.get('name')=='Over'),None)
                under=next((o for o in market.get('outcomes',[]) if o.get('name')=='Under'),None)
                if not over or not under:continue
                if parse_value(over.get('point'))!=parse_value(under.get('point')):continue
                offers.append({'book':book.get('title','Bookmaker'),
                  'line':parse_value(over['point']),
                  'over_price':parse_value(over.get('price')),
                  'under_price':parse_value(under.get('price'))})
        offers=[o for o in offers if o['line'] is not None]
        if not offers: return None
        line=statistics.median(o['line'] for o in offers)
        best=min(offers,key=lambda o:abs(o['line']-line))
        return {'line':line,'book':best['book'], 'over_price':best['over_price'],
                'under_price':best['under_price'], 'offers':len(offers)}
    return None

def excel_v1_projection(game, teams, odds_info=None):
    """Replicate NBA Totals v1.xlsx Daily!K:P using current-season inputs.

    Excel: pace=(away_pace+home_pace)/2;
      away_points=pace*AVERAGE(away_ORtg,home_DRtg)/100;
      home_points=pace*AVERAGE(home_ORtg,away_DRtg)/100.
    The original sheet evaluates >=5.5 on its UNROUNDED edge.
    """
    home = teams.get(game['home']); away = teams.get(game['away'])
    if not home or not away or home['games'] < PREVIEW_MIN_GAMES or away['games'] < PREVIEW_MIN_GAMES:
        return None
    pace = (home['pace'] + away['pace']) / 2
    away_pts = pace * ((away['ortg'] + home['drtg']) / 2) / 100
    home_pts = pace * ((home['ortg'] + away['drtg']) / 2) / 100
    raw_total = away_pts + home_pts
    if not (170 <= raw_total <= 290):
        return None   # Early-season extremes: do not fabricate a plausible total.
    raw_edge = raw_total - odds_info['line'] if odds_info else None
    side = ('OVER' if raw_edge >= WATCH_EDGE else 'UNDER' if raw_edge <= -WATCH_EDGE else None) if raw_edge is not None else None
    preview = home['games'] < MIN_GAMES or away['games'] < MIN_GAMES
    return {'total':round(raw_total,1),'edge':round(raw_edge,2) if raw_edge is not None else None,
            'pace':round(pace,2),'away_points':round(away_pts,2),'home_points':round(home_pts,2),
            'watch':side if not preview else None,'preview_direction':side if preview else None,
            'preview':preview,'model_version':'Excel v1 exact formula, 2026–27 estimated inputs'}

def project(game, teams, league_eff, odds_info):
    hs=teams.get(game['home']); a=teams.get(game['away'])
    if not hs or not a or hs['games'] < PREVIEW_MIN_GAMES or a['games'] < PREVIEW_MIN_GAMES:
        return None
    original=excel_v1_projection(game,teams,odds_info)
    preview = hs['games'] < MIN_GAMES or a['games'] < MIN_GAMES
    # v2 uses current-season league-mean shrinkage. The Excel v1 calculation above does not.
    if league_eff is None:
        return {'total':None,'edge':None,'watch':None,'preview':preview,
                'preview_direction':None,'home_games':hs['games'],'away_games':a['games'],
                'original':original,'model_version':'v0.3 adjusted model (awaiting league baseline)'}
    hwt=hs['games']/(hs['games']+8)
    awt=a['games']/(a['games']+8)
    h_off=league_eff+(hs['ortg']-league_eff)*hwt
    h_def=league_eff+(hs['drtg']-league_eff)*hwt
    a_off=league_eff+(a['ortg']-league_eff)*awt
    a_def=league_eff+(a['drtg']-league_eff)*awt
    pace=(hs['pace']+a['pace'])/2
    raw_total=pace*(h_off+a_def-league_eff+a_off+h_def-league_eff)/100
    if not (170 <= raw_total <= 290):
        projected=None; edge=None; direction=None
    else:
        projected=round(raw_total,1)
        edge=round(projected-odds_info['line'],1) if odds_info else None
        direction='OVER' if edge is not None and edge >= WATCH_EDGE else 'UNDER' if edge is not None and edge <= -WATCH_EDGE else None
    return {'total':projected,'pace':round(pace,1),'edge':edge,
            'watch':direction if not preview else None,
            'preview':preview,'preview_direction':direction if preview else None,
            'home_games':hs['games'],'away_games':a['games'],'original':original,
            'model_version':'v0.3 adjusted model (2026–27 baseline, unvalidated)'}

def american_units(price):
    if price is None or price==0: return None
    return round(price/100 if price>0 else 100/abs(price),4)

def grade_paper(picks,archive):
    for row in picks.values():
        g=archive.get(row['event_id'])
        if not g or g.get('home_score') is None or g.get('away_score') is None: continue
        if row.get('result') not in (None,'pending'): continue
        total=g['home_score']+g['away_score'];row['actual']=total
        if total==row['line']: row['result']='push';row['units']=0
        elif (total>row['line'])==(row['side']=='OVER'):
            row['result']='win'; row['units']=american_units(row['price'])
        else: row['result']='loss';row['units']=-1
    return picks

def run():
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    today=now_utc().astimezone(TZ).date()
    archive=read_json(DATA/'archive.json',{})
    picks=read_json(DATA/'paper_bets.json',{})
    odds_snapshots=read_json(DATA/'odds_snapshots.json',[])
    archive, schedule=pull_scores(archive,today)
    stats,league_eff=calculate_team_stats(archive)
    odds=[]; remaining=None
    try: odds, remaining = get_odds(os.environ.get('ODDS_API_KEY',''))
    except Exception as ex: logging.warning('odds unavailable: %s',ex)
    rows=[]; seen=set(); stamp=now_utc().isoformat()
    for g in sorted(schedule,key=lambda g:g.get('date') or ''):
        if g['id'] in seen:continue
        seen.add(g['id'])
        info=find_odds(g,odds)
        try: pregame=dt.datetime.fromisoformat(g['date'].replace('Z','+00:00'))>now_utc() and g['status']!='final'
        except (TypeError,ValueError,AttributeError): pregame=False
        calc=project(g,stats,league_eff,info) if pregame else None
        # Preserve pregame market data from day one, even before projections unlock.
        # This does NOT backfill historical odds or imply a wager was made.
        if pregame and info:
            odds_snapshots.append({'event_id':g['id'],'captured_at':stamp,
                'commence_time':g['date'],'home':g['home'],'away':g['away'],
                'line':info['line'],'book':info['book'],
                'over_price':info['over_price'],'under_price':info['under_price'],
                'offers':info['offers']})
        rec={k:g[k] for k in ('id','date','home','away','status','home_score','away_score')}
        rec['market']=info
        rec['prediction']=calc
        rows.append(rec)
        # Only lock picks after BOTH teams have >= 10 qualifying games.
        # V1 and V2 receive independent, immutable pregame entries.
        if pregame and calc and not calc['preview'] and info:
            for model_name, model_calc in (('v1',calc.get('original')),('v2',calc)):
                if not model_calc or not model_calc.get('watch'): continue
                pick_key=g['id']+'|'+model_name
                if pick_key in picks or (model_name=='v2' and g['id'] in picks): continue
                side=model_calc['watch']
                price=info['over_price' if side=='OVER' else 'under_price']
                if price is None: continue
                picks[pick_key]={'event_id':g['id'],'date':g['date'],'home':g['home'],'away':g['away'],
                  'model':model_name,'side':side,'line':info['line'],'price':price,
                  'book':info['book'],'projection':model_calc['total'],'edge':model_calc['edge'],
                  'timestamp':stamp,'result':'pending','units':None,'paper_only':True}
    picks=grade_paper(picks,archive)
    def perf(model_name):
        relevant=[p for p in picks.values() if p.get('model','v2')==model_name]
        settled=[p for p in relevant if p.get('result') in ('win','loss','push')]
        wins=sum(p['result']=='win' for p in settled)
        losses=sum(p['result']=='loss' for p in settled)
        return {'wins':wins,'losses':losses,'pushes':len(settled)-wins-losses,
                'units':round(sum(p.get('units') or 0 for p in settled),2),
                'pending':sum(p.get('result')=='pending' for p in relevant)}
    v1_perf=perf('v1'); v2_perf=perf('v2')
    dashboard={
      'generated_at':stamp,'season':'2026–27','source_status':{
        'games_archived':len(archive),'teams_with_stats':len(stats),
        'teams_ready':sum(s['ready'] for s in stats.values()),
        'odds_configured':bool(os.environ.get('ODDS_API_KEY')),
        'odds_events_available':len(odds),'odds_credits_remaining':remaining,
        'odds_snapshots_saved':len(odds_snapshots),
        'injuries_integrated':False},
      'settings':{'min_games':MIN_GAMES,'preview_min_games':PREVIEW_MIN_GAMES,'watch_edge':WATCH_EDGE,'start_date':str(START)},
      'performance':v2_perf,'performance_by_model':{'v1':v1_perf,'v2':v2_perf},
      'games':rows,'teams':sorted(stats.values(),key=lambda r:r['team']),
      'paper_bets':sorted(picks.values(),key=lambda p:p.get('date',''),reverse=True)[:150],
      'notes':['V1 exactly reproduces the original Excel arithmetic using 2026–27 derived pace/ratings; inputs are approximate, not the old workbook values.',
               'Historical Excel workbook reports 40–28, +8.1128u but does not prove predictions were frozen at tipoff.',
               'PREVIEW projections appear after each team has at least one valid current-season game and are excluded from paper tracking.',
               'Official WATCH signals require 10 qualifying games per team.',
               'Both projections use 2026–27 stats only and are not validated.',
               'Injury and rotation adjustments are not integrated yet.',
               'ESPN data is unofficial; missing boxscores intentionally prevent predictions.',
               'Watch signals are research/paper-tracking labels, not verified betting advantages.']
    }
    save_json(DATA/'archive.json',archive)
    save_json(DATA/'paper_bets.json',picks)
    save_json(DATA/'odds_snapshots.json',odds_snapshots)
    save_json(SITE_DATA/'dashboard.json',dashboard)
    print(f"Games={len(archive)} teams={len(stats)} ready={dashboard['source_status']['teams_ready']} scheduled={len(rows)} paper={len(picks)}")

if __name__=='__main__':run()
