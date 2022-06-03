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
  # TODO: add checks to make sure args are valid

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
  
  print('successfully retrieved nba player urls')
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

  print('successfully retrieved cbb player urls')
  return players_cbb


def fetch_nba_career_data(players):
  print('retrieving nba career data...')
  player_data_by_year = {}

  for year in range(1950, 2022):
    print('current year: ' + str(year))
    URL = 'https://www.basketball-reference.com/leagues/NBA_' + str(year) + '_totals.html'
    data = requests.get(URL, stream=True)
    for line in data.iter_lines():
      match = re.findall('data-stat="player" csk="[^"]*" ><a href="/players/[^>]*>([^<]*)</a></td>', str(line))
      match2 = re.findall('class="italic_text partial_table"', str(line))
      
      if match and not match2 and match[0] in players.keys():
        if match[0] not in player_data_by_year.keys():
          player_data_by_year[match[0]] = {}
        
        player_data_by_year[match[0]][year] = {}

        matchPoints = re.findall('data-stat="pts" >([\d]*)</td>', str(line))
        if matchPoints:
          player_data_by_year[match[0]][year]['points'] = matchPoints[0]

        matchRebounds = re.findall('data-stat="trb" >([\d]*)</td>', str(line))
        if matchRebounds:
          player_data_by_year[match[0]][year]['rebounds'] = matchRebounds[0]

        matchSteals = re.findall('data-stat="stl" >([\d]*)</td>', str(line))
        if matchSteals:
          player_data_by_year[match[0]][year]['steals'] = matchSteals[0]

        matchAssists = re.findall('data-stat="ast" >([\d]*)</td>', str(line))
        if matchAssists:
          player_data_by_year[match[0]][year]['assists'] = matchAssists[0]

        matchBlocks = re.findall('data-stat="blk" >([\d]*)</td>', str(line))
        if matchBlocks:
          player_data_by_year[match[0]][year]['blocks'] = matchBlocks[0]
  
  print('successfully retrieved nba career data')
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

  print('successfully formatted career data')
  return player_data_noyear


def fetch_college_data(players_cbb, player_data_noyear):
  print('fetching college data for nba players...')
  print('this may take awhile')

  count = 0

  for player in player_data_noyear.keys():
    count += 1
    if count % 100 == 0:
      print(str(int(count / len(player_data_noyear.keys()) * 100)) + '%')
        
    if player not in players_cbb.keys():
      continue
    
    URL = 'https://www.sports-reference.com/cbb/players' + players_cbb[player]
    data = requests.get(URL, stream=True)
    
    gamesLine = False
    pointsLine = False
    reboundsLine = False
    assistsLine = False
    FGPLine = False
    TFGPLine = False
    FTPLine = False
    EFGPLine = False
    WSLine = False
    
    for line in data.iter_lines():
      if gamesLine:
        match = re.findall('<p>([\d]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['Games'] = match[0]
        gamesLine = False
      if pointsLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['Points'] = match[0]
        pointsLine = False
      if reboundsLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['Rebounds'] = match[0]
        reboundsLine = False
      if assistsLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['Assists'] = match[0]
        assistsLine = False
      if FGPLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['FGP'] = match[0]
        FGPLine = False
      if TFGPLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['TFGP'] = match[0]
        TFGPLine = False
      if FTPLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['FTP'] = match[0]
        FTPLine = False
      if EFGPLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['EFGP'] = match[0]
        EFGPLine = False
      if WSLine:
        match = re.findall('<p>([\d.]*)</p></div>', str(line))
        if match:  
          player_data_noyear[player]['WS'] = match[0]
        WSLine = False
      
      
      matchGames = re.findall('data-tip="Games"><strong>G</strong>', str(line))
      matchPoints = re.findall('data-tip="Points"><strong>PTS</strong>', str(line))
      matchRebounds = re.findall('data-tip="Total Rebounds"><strong>TRB</strong>', str(line))
      matchAssists = re.findall('data-tip="Assists"><strong>AST</strong>', str(line))
      matchFGP = re.findall('data-tip="Field Goal Percentage"><strong>FG%</strong>', str(line))
      matchTFGP = re.findall('data-tip="3-Point Field Goal Percentage"><strong>FG3%</strong>', str(line))
      matchFTP = re.findall('data-tip="Free Throw Percentage"><strong>FT%</strong>', str(line))
      matchEFGP = re.findall('data-tip="Effective Field Goal Percentage; this statistic adjusts for the fact that a 3-point field goal is worth one more point than a 2-point field goal."><strong>eFG%</strong>', str(line))
      matchWS = re.findall('data-tip="Win Shares; an estimate of the number of wins contributed by a player due to his offense and defense."><strong>WS</strong>', str(line))
      
      if matchGames:
        gamesLine = True
      if matchPoints:
        pointsLine = True
      if matchRebounds:
        reboundsLine = True
      if matchAssists:
        assistsLine = True
      if matchFGP:
        FGPLine = True
      if matchTFGP:
        TFGPLine = True
      if matchFTP:
        FTPLine = True
      if matchEFGP:
        EFGPLine = True
      if matchWS:
        WSLine = True

  print('successfully retrieved all college data')
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


# TODO: optimize or remove
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

  for player in players:
    if player not in cbb_players.keys():
      potential_player = find_similar_player(player, list(cbb_players.keys()))
      print(player + ' is not recognized as a valid college player. Did you mean ' + potential_player + '?')


if __name__ == '__main__':
  main()