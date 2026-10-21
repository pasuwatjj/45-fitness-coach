"""Single-process threaded production entry point; sessions stay in this process."""
import os,threading
from waitress import serve
from app import app,store,membership
threading.Thread(target=membership.run_mail_worker,args=(store,),daemon=True).start()
serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','5000')),threads=16,max_request_body_size=5*1024*1024)
