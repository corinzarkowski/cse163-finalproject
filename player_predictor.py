import os
import requests
import re
import pandas as pd
import argparse
import string
import json
import ssl
from difflib import SequenceMatcher

URL_CSV = 'https://gist.githubusercontent.com/corinzarkowski/4d1e66a9253b552ee95d62dbf74b3185/raw/579c5421fae54680435ca33e104c254c74638af1/cbb_nba_data.csv'
URL_JSON = 'https://gist.githubusercontent.com/corinzarkowski/f6bee01b354419c4095e55173d52873b/raw/8541672e08f7f1f00dd8ef4440b7742f87357c33/cbb_names_urls.json'


def process_args():
  parser = argparse.ArgumentParser(description='Take college basketball players and return career predictions')
  parser.add_argument('players', metavar='P', type=str, nargs='+',
                      help='Player(s) to predict. input in \'player1\' \'player2\' \'player3\' format')
  parser.add_argument('--reload-manual', dest='do_refresh_man', action='store_const',
                      const=True, default=False,
                      help='Option to refresh player data from https://www.sports-reference.com/cbb/, https://www.basketball-reference.com/. (slower, but updates data from source)')
  parser.add_argument('--reload-gist', dest='do_refresh_gist', action='store_const',
                      const=True, default=False,
                      help='Option to refresh player data from pre-existing gist pages. (quicker, but may be outdated) -- default')


  args = parser.parse_args()

  return args.do_refresh_man, args.do_refresh_gist, args.players


def data_loaded():
  return os.path.exists(os.path.join(os.getcwd(), 'data', 'player_data.csv')) and os.path.exists(os.path.join(os.getcwd(), 'data', 'college_players.json'))


def fetch_nba_player_URLs():
  print('fetching nba player urls...')

  letters = list(string.ascii_lowercase)
  players = {}

  for letter in letters:
    URL = 'https://www.basketball-reference.com/players/' + letter + '/'
    data = requests.get(URL, stream=True)
    
    for line in data.iter_lines():
      match = re.findall('data-stat="player" ><a href="/players/' + letter + '/([^>]*)">([^<]*)<', str(line))
      
      if(match):
        players[match[0][1]] = match[0][0]
  
  return players


def fetch_cbb_player_URLs():
  print('fetching cbb player urls...')

  letters = list(string.ascii_lowercase)
  players_cbb = {}

  for letter in letters:
    URL = 'https://www.sports-reference.com/cbb/players/' + letter + '-index.html'
    data = requests.get(URL, stream=True)
    for line in data.iter_lines():
      match = re.findall('p><a href="/cbb/players([^"]*)">([^<]*)', str(line))
      if match:
        players_cbb[match[0][1]] = match[0][0]

  return players_cbb


def fetch_nba_career_data(players):
  print('retrieving nba career data...')
  player_data_by_year = {}

  for year in range(1950, 2022):
    if (year - 1950) % 5 == 0:
      print(str(int((year - 1950) / 72 * 100)) + '%')

    URL = 'https://www.basketball-reference.com/leagues/NBA_' + str(year) + '_totals.html'
    data = requests.get(URL, stream=True)
    for line in data.iter_lines():
      match = re.findall('data-stat="player" csk="[^"]*" ><a href="/players/[^>]*>([^<]*)</a></td>', str(line))
      match2 = re.findall('class="italic_text partial_table"', str(line))
      
      if match and not match2 and match[0] in players.keys():
        if match[0] not in player_data_by_year.keys():
          player_data_by_year[match[0]] = {}
        
        player_data_by_year[match[0]][year] = {}

        match_points = re.findall('data-stat="pts" >([\d]*)</td>', str(line))
        if match_points:
          player_data_by_year[match[0]][year]['points'] = match_points[0]

        match_rebounds = re.findall('data-stat="trb" >([\d]*)</td>', str(line))
        if match_rebounds:
          player_data_by_year[match[0]][year]['rebounds'] = match_rebounds[0]

        match_steals = re.findall('data-stat="stl" >([\d]*)</td>', str(line))
        if match_steals:
          player_data_by_year[match[0]][year]['steals'] = match_steals[0]

        match_assists = re.findall('data-stat="ast" >([\d]*)</td>', str(line))
        if match_assists:
          player_data_by_year[match[0]][year]['assists'] = match_assists[0]

        match_blocks = re.findall('data-stat="blk" >([\d]*)</td>', str(line))
        if match_blocks:
          player_data_by_year[match[0]][year]['blocks'] = match_blocks[0]
  
  return player_data_by_year


def format_career_data(player_data_by_year):
  print('formatting career data...')

  player_data_noyear = {}

  for player_name in player_data_by_year.keys():
    best_year = -1
    cur_year = 1
    stat_total = 0
    cur_stat_total = 0
    
    for year in player_data_by_year[player_name]:
      stats = [player_data_by_year[player_name][year][stat] for stat in player_data_by_year[player_name][year]]

      if '' not in stats:
        cur_stat_total = int(player_data_by_year[player_name][year]['points']) * \
                        int(player_data_by_year[player_name][year]['rebounds']) * \
                        int(player_data_by_year[player_name][year]['steals']) * \
                        int(player_data_by_year[player_name][year]['assists']) * \
                        int(player_data_by_year[player_name][year]['blocks'])
        if cur_stat_total > stat_total:
          stat_total = cur_stat_total
          best_year = cur_year
        cur_year += 1

    if best_year != -1:
      player_data_noyear[player_name] = {}
      player_data_noyear[player_name]['best_year'] = best_year
      player_data_noyear[player_name]['career_length'] = cur_year - 1

  return player_data_noyear


def fetch_college_player_data(player_url):
  URL = 'https://www.sports-reference.com/cbb/players' + player_url
  data = requests.get(URL, stream=True)
  cur_player = {}
  
  games_line = False
  points_line = False
  rebounds_line = False
  assists_line = False
  fgp_line = False
  tfgp_line = False
  ftp_line = False
  efgp_line = False
  ws_line = False
  
  for line in data.iter_lines():
    if games_line:
      match = re.findall('<p>([\d]*)</p></div>', str(line))
      if match:  
        cur_player['Games'] = match[0]
      games_line = False
    if points_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['Points'] = match[0]
      points_line = False
    if rebounds_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['Rebounds'] = match[0]
      rebounds_line = False
    if assists_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['Assists'] = match[0]
      assists_line = False
    if fgp_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['FGP'] = match[0]
      fgp_line = False
    if tfgp_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['TFGP'] = match[0]
      tfgp_line = False
    if ftp_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['FTP'] = match[0]
      ftp_line = False
    if efgp_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['EFGP'] = match[0]
      efgp_line = False
    if ws_line:
      match = re.findall('<p>([\d.]*)</p></div>', str(line))
      if match:  
        cur_player['WS'] = match[0]
      ws_line = False
    
    
    match_games = re.findall('data-tip="Games"><strong>G</strong>', str(line))
    match_points = re.findall('data-tip="Points"><strong>PTS</strong>', str(line))
    match_rebounds = re.findall('data-tip="Total Rebounds"><strong>TRB</strong>', str(line))
    match_assists = re.findall('data-tip="Assists"><strong>AST</strong>', str(line))
    match_fgp = re.findall('data-tip="Field Goal Percentage"><strong>FG%</strong>', str(line))
    match_tfgp = re.findall('data-tip="3-Point Field Goal Percentage"><strong>FG3%</strong>', str(line))
    match_ftp = re.findall('data-tip="Free Throw Percentage"><strong>FT%</strong>', str(line))
    match_efgp = re.findall('data-tip="Effective Field Goal Percentage; this statistic adjusts for the fact that a 3-point field goal is worth one more point than a 2-point field goal."><strong>eFG%</strong>', str(line))
    match_ws = re.findall('data-tip="Win Shares; an estimate of the number of wins contributed by a player due to his offense and defense."><strong>WS</strong>', str(line))
    
    if match_games:
        games_line = True
    if match_points:
        points_line = True
    if match_rebounds:
        rebounds_line = True
    if match_assists:
        assists_line = True
    if match_fgp:
        fgp_line = True
    if match_tfgp:
        tfgp_line = True
    if match_ftp:
        ftp_line = True
    if match_efgp:
        efgp_line = True
    if match_ws:
        ws_line = True

  return cur_player


def fetch_college_data(players_cbb, player_data_noyear):
  print('fetching college data for nba players...')
  print('this may take a while')

  count = 0

  for player in player_data_noyear.keys():
    count += 1
    if count % 100 == 0:
      print(str(int(count / len(player_data_noyear.keys()) * 100)) + '%')
        
    if player not in players_cbb.keys():
      continue

    player_data_noyear[player] = fetch_college_player_data(players_cbb[player])

  return player_data_noyear


def init_data_manual():
  print('initializing data...')
  if not os.path.exists(os.path.join(os.getcwd(), 'data')):
    os.mkdir(os.path.join(os.getcwd(), 'data'))

  player_urls_nba = fetch_nba_player_URLs()
  player_urls_cbb = fetch_cbb_player_URLs()
  player_data_unformatted = fetch_nba_career_data(player_urls_nba)
  player_data = format_career_data(player_data_unformatted)
  player_data_final = fetch_college_data(player_urls_cbb, player_data)

  player_list = []
  for player in player_data_final.keys():
    player_list.append({
        'name': player,
        **player_data_final[player]
    })

  player_df = pd.DataFrame(player_list)
  player_df.to_csv(os.path.join(os.getcwd(), 'data', 'player_data.csv'))

  with open(os.path.join(os.getcwd(), 'data', 'college_players.json'), 'w') as outfile:
    json.dump(player_urls_cbb, outfile)


def init_data_gist():
  print('initializing data...')

  ssl._create_default_https_context = ssl._create_unverified_context

  if not os.path.exists(os.path.join(os.getcwd(), 'data')):
    os.mkdir(os.path.join(os.getcwd(), 'data'))

  player_df = pd.read_csv(URL_CSV)
  cbb_json = requests.get(URL_JSON).json()

  player_df.to_csv(os.path.join(os.getcwd(), 'data', 'player_data.csv'))
  with open(os.path.join(os.getcwd(), 'data', 'college_players.json'), 'w') as outfile:
    json.dump(cbb_json, outfile)


def find_similar_player(player, player_list):
  most_similar = ''
  high_similarity = 0
  for other in player_list:
    if player[0].lower() == other[0].lower():
      similarity = SequenceMatcher(None, player, other).ratio()
      if similarity > high_similarity:
        most_similar = other
        high_similarity = similarity

  return most_similar


def main():
  refresh_manual, refresh_gist, players = process_args()

  if refresh_manual:
    init_data_manual()

  if refresh_gist or not data_loaded():
    init_data_gist()

  players_df = pd.read_csv(os.path.join(os.getcwd(), 'data', 'player_data.csv'))
  cbb_players = json.load(open(os.path.join(os.getcwd(), 'data', 'college_players.json'), 'r'))

  players_valid = []
  for player in players:
    if player in cbb_players.keys():
      players_valid.append(player)
    else:
      potential_player = find_similar_player(player, list(cbb_players.keys()))
      r = input(player + ' is not recognized as a valid college player. Did you mean ' + potential_player + '? [y/n]\n>')
      if r == 'y':
        players_valid.append(potential_player)
  
  print('fetching data on input players...')
  input_player_data = []
  for player in players_valid:
    input_player_data.append({
      'name': player,
      **fetch_college_player_data(cbb_players[player])
    })

  input_player_df = pd.DataFrame(input_player_data)

  print(input_player_df)


if __name__ == '__main__':
  main()