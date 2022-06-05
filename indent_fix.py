with open('player_predictor.py', 'r') as f:
  with open('player_predictor_fixed.py', 'w') as k:
    for line in f.readlines():
      leadingspace = len(line) - len(line.lstrip())
      k.write((' ' * leadingspace) + line)