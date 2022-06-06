"""
Corey Zarkowski, Bryan Phan, Lawrence Lorbiecki -- CSE 163
TEMPLATE COMMENT
"""

import os
import requests
import pandas as pd
import argparse
import json
import ssl
from difflib import SequenceMatcher
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
from manual_utils import fetch_cbb_player_URLs, fetch_college_data,\
                         fetch_college_player_data,\
                         fetch_nba_player_URLs, format_career_data,\
                         fetch_nba_career_data

URL_CSV = 'https://gist.githubusercontent.com/corinzarkowski/4d1e66a9253b552ee95d62dbf74b3185/raw/579c5421fae54680435ca33e104c254c74638af1/cbb_nba_data.csv'
URL_JSON = 'https://gist.githubusercontent.com/corinzarkowski/f6bee01b354419c4095e55173d52873b/raw/8541672e08f7f1f00dd8ef4440b7742f87357c33/cbb_names_urls.json'


def process_args():
    """
    TEMPLATE COMMENT
    """
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
    parser.add_argument('--test-models', dest='is_test',
                        action='store_const',
                        const=True, default=False,
                        help='Option to test models with depth \
                             and tree counts for random forest')

    args = parser.parse_args()

    return args.do_refresh_man, args.do_refresh_gist, \
           args.players, args.is_test


def data_loaded():
    """
    TEMPLATE COMMENT
    """
    return os.path.exists(os.path.join(os.getcwd(),
                          'data', 'player_data.csv'))\
           and os.path.exists(os.path.join(os.getcwd(), 'data',
                                           'college_players.json'))


def init_data_manual():
    """
    TEMPLATE COMMENT
    """
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
    """
    TEMPLATE COMMENT
    """
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
    """
    TEMPLATE COMMENT
    """
    most_similar = ''
    high_similarity = 0
    for other in player_list:
        if player[0].lower() == other[0].lower():
            similarity = SequenceMatcher(None, player, other).ratio()
            if similarity > high_similarity:
                most_similar = other
                high_similarity = similarity

    return most_similar


def train_model_careerstats(data, estimators, depth):
    """
    TEMPLATE COMMENT
    """
    data = data[['Points', 'Assists', 'Rebounds', 'FGP',
                 'best_year', 'nba_career_length']].dropna()

    features = data[['Points', 'Assists', 'Rebounds', 'FGP']].astype(float)
    labels = data[['best_year', 'nba_career_length']].astype(float)

    reg = RandomForestRegressor(n_estimators=estimators, max_depth=depth)
    reg.fit(features, labels)
    return reg


def train_model_allstar(data, estimators, depth):
    """
    TEMPLATE COMMENT
    """
    data = data[['Points', 'Assists', 'Rebounds', 'FGP', 'allstar']].dropna()

    features = data[['Points', 'Assists', 'Rebounds', 'FGP']].astype(float)
    label = data['allstar'].astype(bool)

    clf = RandomForestClassifier(n_estimators=estimators, max_depth=depth)
    clf.fit(features, label)
    return clf


def test_models(data):
    """
    TEMPLATE COMMENT
    """
    print('testing models...')
    data = data[['Points', 'Assists', 'Rebounds', 'FGP',
                 'best_year', 'nba_career_length', 'allstar']].dropna()

    train = data.sample(frac = 0.75)
    test = data.drop(train.index)

    best_reg = None
    best_clf = None
    best_mse = 0
    best_ascore = 0

    for est in range(100, 500, 100):
        for depth in range(10, 50, 10):
            reg = train_model_careerstats(train, est, depth)
            clf = train_model_allstar(train, est, depth)
            pred_r = reg.predict(test[['Points', 'Assists',
                                       'Rebounds', 'FGP']])
            pred_c = clf.predict(test[['Points', 'Assists',
                                       'Rebounds', 'FGP']])

            cur_mse = mean_squared_error(test[['best_year',
                                               'nba_career_length']],
                                         pred_r)
            cur_ascore = accuracy_score(test[['allstar']], pred_c)

            if cur_mse > best_mse:
                print('regressor values updated to est:' + str(est) +
                      ', depth: ' + str(depth))
                best_reg = reg
                best_mse = cur_mse
            if cur_ascore > best_ascore:
                print('classifier params updated to est:' + str(est) +
                      ', depth: ' + str(depth))
                best_clf = clf
                best_ascore = cur_ascore

    return best_reg, best_clf


def main():
    """
    TEMPLATE COMMENT
    """
    refresh_manual, refresh_gist, players, is_test = process_args()

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

    if not is_test:
        classifier_career = train_model_careerstats(players_df, 100, None)
        classifier_allstar = train_model_allstar(players_df, 100, None)
    else:
        classifier_career, classifier_allstar = test_models(players_df)

    for input_player in input_player_data:
        input_player_careerstats = classifier_career.predict([[input_player['Points'],
                                                               input_player['Assists'],
                                                               input_player['Rebounds'],
                                                               input_player['FGP']]])
        input_player_allstar = classifier_allstar.predict([[input_player['Points'],
                                                            input_player['Assists'],
                                                            input_player['Rebounds'],
                                                            input_player['FGP']]])
        print(input_player)
        print('projected career length: ' +
              str(int(input_player_careerstats[0][1])) +
              ' years')
        print('projected prime: year ' +
              str(int(input_player_careerstats[0][0])))
        print('will become all-star: ' + str(input_player_allstar[0]))


if __name__ == '__main__':
    main()
