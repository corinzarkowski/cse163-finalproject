import sys
import requests
import re
import pandas as pd
import argparse

def process_args():
  # TODO: add checks to make sure args are valid

  parser = argparse.ArgumentParser(description='Take college basketball players and return career predictions')
  parser.add_argument('players', metavar='P', type=str, nargs='+',
                      help='player(s) to predict')
  parser.add_argument('--refresh-data', dest='do_refresh', action='store_const',
                      const=True, default=False,
                      help='Option to refresh player data from https://www.sports-reference.com/cbb/, https://www.basketball-reference.com/')

  args = parser.parse_args()

  return args.do_refresh, args.players


# check validity of college player
# if not valid throw error

# train random forest on data files
# return predictions for player

def main():
  refresh, players = process_args()

  print(refresh)
  print(players)


if __name__ == '__main__':
  main()