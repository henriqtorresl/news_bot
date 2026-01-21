import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd

from app.config.environments import env
from app.config.logs import logger
from app.database.relevant_news import get_news_to_sent, update_news_status_and_sent_at
from app.database.recipients import get_recipient_emails


def send_newsletter_email():
    news = None
    try:
        sender_email = 'Newsletter de PPPs e Concessões'
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = env.MAIL_USER
        smtp_password = env.MAIL_PASSWORD

        if not smtp_user or not smtp_password:
            raise Exception("Variáveis de ambiente MAIL_USER e MAIL_PASSWORD não encontradas.")

        news = get_news_to_sent()
        if not news:
            logger.info("Nenhuma notícia disponível para disparo de e-mail (lista vazia ou None).")
            return

        recipient_emails = get_recipient_emails()
        if not recipient_emails:
            logger.info("Nenhum destinatário encontrado para envio de e-mail (lista vazia ou None).")
            return

        html = "<h2>Resumo das Notícias</h2>"
        temas = {}
        for n in news:
            tema = n.get('topic', 'Sem tema')
            if tema not in temas:
                temas[tema] = []
            temas[tema].append(n)
        for tema, grupo in temas.items():
            headline = grupo[0].get('headline', f"Tema {tema}")
            resumo = grupo[0].get('ai_summary', '')
            html += f'<h3>{headline}</h3>'
            html += f'<p><b>Resumo:</b> {resumo}</p>'
            html += '<ul>'
            for n in grupo:
                dt = n.get('published_at', '')
                if dt:
                    try:
                        dt = pd.to_datetime(dt).strftime('%d/%m/%Y')
                    except Exception:
                        pass
                fonte = n.get('source', '')
                html += (
                    f'<li style="font-size: 14px; font-weight: normal; color: #555;">'
                    f'<a href="{n.get('original_url','')}" style="color: #1a73e8; text-decoration: none; font-size: 14px;">{n.get('original_title','')}</a> '
                    f'(Fonte: <span style="font-size: 12px; color: #777;">{fonte} - {dt}</span>)'
                    f'</li>'
                )
            html += '</ul><br>'
        msg = MIMEMultipart("alternative")
        msg['Subject'] = f'Resumo das Notícias - {datetime.today().strftime("%d/%m/%Y")}'
        msg['From'] = sender_email
        msg['To'] = ','.join(recipient_emails)
        part = MIMEText(html, "html")
        msg.attach(part)
        logger.info("Conectando ao servidor SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        logger.info("E-mail enviado com sucesso!")
        if news:
            news_ids = [n['id'] for n in news]
            update_news_status_and_sent_at(news_ids, 'sent')
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        if news:
            news_ids = [n['id'] for n in news]
            update_news_status_and_sent_at(news_ids, 'error')
