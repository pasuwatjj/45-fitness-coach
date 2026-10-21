"""Preflight provider quota and SMTP authentication; sends no email/payment."""
import os
import smtplib
import ssl
import sys
import requests

def main():
    try:
        branch=os.environ.get('FITNESS_SLIPOK_BRANCH','')
        if branch:
            result=requests.get('https://api.slipok.com/api/line/apikey/'+branch+'/quota',
                headers={'x-authorization':os.environ['FITNESS_SLIPOK_KEY']},timeout=(8,15),allow_redirects=False)
            body=result.json()
            if result.status_code!=200 or body.get('success') is not True or int(body['data']['quota'])<=0:
                raise ValueError('SlipOK credentials or quota unavailable')
        context=ssl.create_default_context();port=int(os.environ['FITNESS_SMTP_PORT'])
        connection=(smtplib.SMTP_SSL(os.environ['FITNESS_SMTP_HOST'],port,context=context,timeout=12) if port==465
                    else smtplib.SMTP(os.environ['FITNESS_SMTP_HOST'],port,timeout=12))
        with connection as smtp:
            if port!=465:smtp.starttls(context=context)
            smtp.login(os.environ['FITNESS_SMTP_USER'],os.environ['FITNESS_SMTP_PASSWORD'])
    except Exception:
        print('Preflight failed: check SlipOK quota/key and SMTP login/TLS. Manual review remains available.')
        return 1
    print(('SlipOK quota and SMTP login passed.' if branch else 'SMTP login passed. Manual receipt review selected.')+' No email or payment was sent.')
    return 0

if __name__=='__main__':sys.exit(main())
