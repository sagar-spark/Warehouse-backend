from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_email(request, user, reset_url):
    plaintext = "emails/email.txt"
    htmly     = "emails/email.html"
    host = request._current_scheme_host
    msg_plain = render_to_string(plaintext, {'user': user, "reset_url": reset_url})
    msg_html = render_to_string(htmly, {'user': user, "reset_url": reset_url, 'host':host})

    try:
        send_mail(
                    'Password Reset',
                     msg_plain,
                    'info@connectco.com',
                    [user.email],
                    html_message=msg_html,
                    fail_silently=False,
                )
        mail_sent = True
    except Exception:
        mail_sent = False

    return mail_sent        