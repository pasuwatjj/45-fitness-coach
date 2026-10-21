"""Local operator utility. Not exposed on HTTP; never run from user input."""
import argparse
import json
import os
from pathlib import Path
from leaderboard import LeaderboardStore
import shop
import membership

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['orders','receipts','fulfill','cancel','retry-mail','approve-vip','view-slip'])
    parser.add_argument('id',nargs='?')
    parser.add_argument('--transaction')
    parser.add_argument('--confirm-amount',type=int)
    parser.add_argument('--confirm-account')
    args=parser.parse_args()
    store=LeaderboardStore(os.environ.get('FITNESS_DATA_PATH',str(Path(__file__).parent/'data'/'fitness.db')))
    if args.action=='approve-vip':
        membership.approve_manual(store,args.id,args.transaction,args.confirm_amount,args.confirm_account)
        print('VIP approved after bank-transfer confirmation.');return
    if args.action=='view-slip':
        with store.lock,store.connect() as db:
            membership.schema(db)
            row=db.execute('SELECT image FROM vip_receipts WHERE id=?',(args.id,)).fetchone()
        if not row:parser.error('Receipt not found')
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg',delete=False) as out:
            out.write(row['image']);path=out.name
        print('Private receipt copy: '+path+' (delete after review)')
        if os.name=='nt':os.startfile(path)
        return
    if args.action in ('fulfill','cancel'):
        if not args.id:parser.error('Order ID required')
        shop.resolve(store,args.id,'fulfilled' if args.action=='fulfill' else 'cancelled')
        print('Saved.');return
    with store.lock,store.connect() as db:
        shop.schema(db)
        if args.action=='retry-mail':
            if not args.id:parser.error('Receipt ID required')
            db.execute("UPDATE vip_receipts SET mail_status='queued',mail_attempts=0,mail_after=0 WHERE id=? AND status!='checking'",(args.id,))
            print('Queued for retry. Keep Start-Configured.ps1 running.');return
        query=('SELECT * FROM shop_orders ORDER BY created DESC LIMIT 100' if args.action=='orders' else
               'SELECT id,email,status,result,mail_status,created FROM vip_receipts ORDER BY created DESC LIMIT 100')
        print(json.dumps([dict(r) for r in db.execute(query)],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
