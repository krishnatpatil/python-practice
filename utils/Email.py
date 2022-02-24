#!/usr/bin/env python

"""Email.py

General purpose mail utility to send the emails

Usage:

    import sys
    import Utils.Email as Email

    sender = "kkpatil007@gmail.com"
    receiver = ["krishnatpatil@yahoo.co.in", "testmail@example.com"]
    subject = "Testing"
    body = "test mail"

    # create a mail instance
    mail = Email.Email(
        sender = sender,
        receiver = receiver,
        subject = subject,
        body = body,
    )

    # call method to send a mail
    try:
        mail.send()
    except RuntimeError as error:
        sys.stdout.write(str(error))
        return

    # send mail with attachment and CC
    attachment = ["test.log", "./data.csv", "/tmp/data.txt"]
    CC = ["krishnatpatil@yahoo.co.in"]

    mail.attachment = attachment
    mail.cc = CC
    
    try:
        mail.send()
    except RuntimeError as error:
        sys.stdout.write(str(error))
        return
"""
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Email(object):
    """
    Class to send the mail notifications using SMTP

    Usage:
        mail = Email(
            sender="kkpatil007@gmail.com",
            receiver=["krishnatpatil@yahoo.co.in"],
            cc=["testmail@example.com"],
            subject="Testing",
            body="Test mail",
            attachment=["data.csv"],
            )

        mail.send()
    """

    MAILSERVER = "smtp.gmail.com"

    def __init__(self, **args):
        """
        Constructor method to instantiate the class with required parameters

        Required Parameters:
          subject: string, subject of the mail
          body: string, body of the mail. Could be text or html format

        Optional Parameters:
          sender: string, FROM address. Default is "kkpatil007@gmail.com"
          receiver: list, TO addresses. Default is ["krishnatpatil@yahoo.co.in"]
          cc: list, CC addresses. Default is None
          attachment: list, List of file paths to attach. Default is None
        """
        self.sender = "kkpatil007@gmail.com"
        self.receiver = ["krishnatpatil@yahoo.co.in"]
        self.cc = None
        self.subject = None
        self.body = None
        self.attachment = None

        self._handleArgs(**args)

    def _handleArgs(self, **args):
        """
        Handles the constructor arguments. Meant for internal use.
        Gets called automatically at the time of object creation.
        """
        for attribute in (
            loopAttribute
            for loopAttribute in self.__dict__.keys()
            if loopAttribute in args
        ):
            setattr(self, attribute, args[attribute])

        requiredAttributes = ["subject", "body"]
        missingAttributes = [
            attribute
            for attribute in requiredAttributes
            if getattr(self, attribute) is None
        ]

        if missingAttributes:
            errorString = "Required attribute(s): '{}' not provided!".format(
                ",".join(missingAttributes)
            )
            raise AttributeError(errorString)

    def send(self):
        """
        Method to create SMTP connection and send the mail

        Usage:
            mail = Email(subject="Test", body="test mail")
            mail.send()
        """
        # Create a multipart message and set headers
        message = MIMEMultipart("alternative")
        message["From"] = self.sender
        message["To"] = ",".join(self.receiver)
        if self.cc:
            message["CC"] = ",".join(self.cc)
        message["Subject"] = self.subject

        # Turn mail body into plain/html MIMEText objects
        textBody = MIMEText(self.body, "plain")
        htmlBody = MIMEText(self.body, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(textBody)
        message.attach(htmlBody)

        # attach the files, if provided
        if self.attachment:
            for filename in self.attachment:
                try:
                    with open(filename, "rb") as f:
                        # Add file as application/octet-stream
                        # Email client can usually download this automatically as attachment
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())

                    # Encode file in ASCII characters to send by email
                    encoders.encode_base64(part)

                    # Add header as key/value pair to attachment part
                    part.add_header(
                        "Content-Disposition",
                        "attachment; filename= {}".format(filename),
                    )
                    # Add attachment to message
                    message.attach(part)
                except Exception as error:
                    errorString = "Could not attach {} due to {}".format(
                        filename, str(error)
                    )
                    raise RuntimeError(errorString)

        # Try to log in to server and send email
        try:
            server = smtplib.SMTP(self.MAILSERVER)
            server.sendmail(self.sender, self.receiver, message.as_string())
        except smtplib.SMTPException as error:
            raise RuntimeError(error)
        finally:
            if server:
                server.quit()

