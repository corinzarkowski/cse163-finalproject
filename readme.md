# College Basketball Player Predictor

usage: player_predictor.py [-h] [--reload-manual] [--reload-gist] P [P ...]

---
positional arguments:

  P                Player(s) to predict. input in 'player1' 'player2' 'player3' format

---
optional arguments:

  -h, --help       show this help message and exit

  --reload-manual  Option to refresh player data from https://www.sports-
                   reference.com/cbb/, https://www.basketball-reference.com/. (slower, but
                   updates data from source)

  --reload-gist    Option to refresh player data from pre-existing gist pages. (quicker,
                   but may be outdated) -- default
