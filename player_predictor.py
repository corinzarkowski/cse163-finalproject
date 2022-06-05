import os
import requests
import pandas as pd
import argparse
import json
import ssl
from difflib import SequenceMatcher
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from manual_utils import fetch_cbb_player_URLs, fetch_college_data,\
                         fetch_college_player_data,\
                         fetch_nba_player_URLs, format_career_data,\
                         fetch_nba_career_data

URL_CSV = 'https://gist.githubusercontent.com/corinzarkowski/4d1e66a9253b552ee95d62dbf74b3185/raw/579c5421fae54680435ca33e104c254c74638af1/cbb_nba_data.csv'
URL_JSON = 'https://gist.githubusercontent.com/corinzarkowski/f6bee01b354419c4095e55173d52873b/raw/8541672e08f7f1f00dd8ef4440b7742f87357c33/cbb_names_urls.json'


def process_args():
    parser = argparse.ArgumentParser(description='Take college basketball \
                                                 players and return career \
                                                 predictions')
    parser.add_argument('players', metavar='P', type=str, nargs='+',
                        help='Player(s) to predict. input \
                             in \'player1\' \'player2\' \
                             \'player3\' format')
    parser.add_argument('--reload-manual', dest='do_refresh_man',
                        action='store_const',
                        const=True, default=False,
                        help='Option to refresh player data \
                             from https://www.sports-referen\
                             ce.com/cbb/, https://www.basket\
                             ball-reference.com/. (slower, \
                             but updates data from source)')
    parser.add_argument('--reload-gist', dest='do_refresh_gist',
                        action='store_const',
                        const=True, default=False,
                        help='Option to refresh player data \
                             from pre-existing gist pages (default)')

    args = parser.parse_args()

    return args.do_refresh_man, args.do_refresh_gist, args.players


def data_loaded():
    return os.path.exists(os.path.join(os.getcwd(),
                          'data', 'player_data.csv'))\
           and os.path.exists(os.path.join(os.getcwd(), 'data',
                                           'college_players.json'))


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

    with open(os.path.join(os.getcwd(), 'data', 'college_players.json'), 'w') \
         as outfile:
        json.dump(player_urls_cbb, outfile)


def init_data_gist():
    print('initializing data...')

    ssl._create_default_https_context = ssl._create_unverified_context

    if not os.path.exists(os.path.join(os.getcwd(), 'data')):
        os.mkdir(os.path.join(os.getcwd(), 'data'))

    player_df = pd.read_csv(URL_CSV)
    cbb_json = requests.get(URL_JSON).json()

    player_df.to_csv(os.path.join(os.getcwd(), 'data', 'player_data.csv'))
    with open(os.path.join(os.getcwd(), 'data', 'college_players.json'), 'w') \
         as outfile:
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


def train_model_careerstats(data):
    data = data[['Points', 'Assists', 'Rebounds', 'FGP',
                 'best_year', 'nba_career_length']]
    data = data.dropna()

    features = data[['Points', 'Assists', 'Rebounds', 'FGP']].astype(float)
    labels = data[['best_year', 'nba_career_length']].astype(float)

    clf = RandomForestClassifier(max_depth=10, random_state=0)
    clf.fit(features, labels)

    return clf


def train_model_allstar(data):
    data = data[['Points', 'Assists', 'Rebounds', 'allstar']]
    data = data.dropna()

    features = data[['Points', 'Assists', 'Rebounds']].astype(float)
    label = data['allstar'].astype(bool)

    clf = DecisionTreeClassifier(max_depth=10, random_state=0)
    clf.fit(features, label)

    return clf


def main():
    refresh_manual, refresh_gist, players = process_args()

    if refresh_manual:
        init_data_manual()

    if refresh_gist or not data_loaded():
        init_data_gist()

    players_df = pd.read_csv(os.path.join(os.getcwd(),
                                          'data',
                                          'player_data.csv'))
    cbb_players = json.load(open(os.path.join(os.getcwd(),
                                              'data',
                                              'college_players.json'), 'r'))

    players_valid = []
    for player in players:
        if player in cbb_players.keys():
            players_valid.append(player)
        else:
            potential_player = find_similar_player(player,
                                                   list(cbb_players.keys()))
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

    classifier_career = train_model_careerstats(players_df)
    classifier_allstar = train_model_allstar(players_df)

    for input_player in input_player_data:
        input_player_careerstats = classifier_career.predict([[input_player['Points'],
                                                               input_player['Assists'],
                                                               input_player['Rebounds'],
                                                               input_player['FGP']]])
        input_player_allstar = classifier_allstar.predict([[input_player['Points'],
                                                            input_player['Assists'],
                                                            input_player['Rebounds']]])
        print(input_player)
        print('projected career length: ' + str(input_player_careerstats[0][1]))
        print('projected best year: ' + str(input_player_careerstats[0][0]))
        print('projected all star: ' + str(input_player_allstar[0]))


if __name__ == '__main__':
    main()
