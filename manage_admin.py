"""Run locally as the site owner; never expose as an HTTP endpoint."""
import argparse,os
from pathlib import Path
from leaderboard import LeaderboardStore
from community import grant_admin
p=argparse.ArgumentParser();p.add_argument('--email',required=True);args=p.parse_args()
store=LeaderboardStore(os.environ.get('FITNESS_DATA_PATH',str(Path(__file__).parent/'data'/'fitness.db')))
try:grant_admin(store,args.email)
except ValueError as e:p.exit(1,str(e)+'\n')
print('Administrator enabled for '+args.email+'. Refresh the website.')
