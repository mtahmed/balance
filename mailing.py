#!/usr/bin/python

import smtplib

class Mailer:
   '''Mailer for notifications'''

   def __init__(self, user, host):
      self.sender = user + '@' + host
      self.host = host


   def sendNotification(self, toAddr, subject, body):
      '''
      Given a recipient list, message subject and body,
      send an e-mail with those parameters
      '''

      if not self.host:
         return

      receivers = []
      for receiver in toAddr.split(';'):
         receivers.append("<" + receiver + "@" + host + ">")

      message = "From: No Reply Balance <no-reply@balance.com>\n" \
                "To: " + ';'.join(receivers) + "\n" \
                "Subject: " + subject + "\n" + \
                 body

      try:
         smtpObj = smtplib.SMTP(self.host, 25, 'localhost')
         smtpObj.sendmail(self.sender, receivers, message)
      except smtplib.SMTPException:
         print "error: email notification failed"
         sys.exit(0)
