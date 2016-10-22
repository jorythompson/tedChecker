import smtplib
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import ConfigParser


class EmailConnection:
    TITLE = "Email Connection"
    USERNAME = "username"
    PASSWORD = "password"
    FROM = "from"

    def __init__(self, config=None, username=None, password=None, from_user=None):
        if config is None:
            self.username = username
            self.password = password
            self.from_user = from_user
        else:
            self.username = config.get(EmailConnection.TITLE, EmailConnection.USERNAME)
            self.password = config.get(EmailConnection.TITLE, EmailConnection.PASSWORD)
            self.from_user = config.get(EmailConnection.TITLE, EmailConnection.FROM)


class EmailSender:
    def __init__(self, email_connection):
        self.email_connection = email_connection

    def send(self, to_email, subject, message):
        msg = MIMEMultipart()
        msg['From'] = self.email_connection.from_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(str(message), "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.email_connection.username, self.email_connection.password)
            server.sendmail(self.email_connection.username, to_email, msg.as_string())
            server.quit()
            print "Successfully sent mail to " + to_email
        except smtplib.SMTPAuthenticationError as e:
            print "Failed to send mail to " + to_email


if __name__ == "__main__":
    mail = EmailSender(EmailConnection(username="jorythompson@gmail.com", password="ftxsirhfclvmxkgp"))
    mail.send("jorythompson@gmail.com", "this is a test from emailSender", "Here is the message using parameters passed in")
    config = ConfigParser.ConfigParser()
    config.read("laptop-home.ini")
    mail = EmailSender(EmailConnection(config))
    mail.send("jorythompson@gmail.com", "this is a test from emailSender", "Here is the message using the configuration file")