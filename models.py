from google.appengine.ext import ndb
import pickle
import jinja2
import os
import datetime
from google.appengine.api import mail


class practice(ndb.Model):
	name=ndb.StringProperty()
	address=ndb.PickleProperty()
	choicesemail=ndb.StringProperty()
	verifiedemail=ndb.StringProperty()
	useremails=ndb.PickleProperty
	location=ndb.GeoPtProperty()
	postcode=ndb.StringProperty()
	

	
	def addressline(self):
		address=pickle.loads(self.address)
		address.append(self.postcode)
		for line in address:
			yield line
		
	
	def addrstring(self):
		address=pickle.loads(self.address)
		string=', '
		return string.join(address)

	def bestemail(self):
		if self.verifiedemail!=None:
			return self.verifiedemail
		elif self.choicesemail!=None:
			return self.choicesemail
		else:
			return None
		
		
	def setaddr(self,addrlist):
		self.address=pickle.dumps(addrlist)

class request_email(ndb.Model):
	name=ndb.StringProperty()
	address=ndb.PickleProperty()
	useremail=ndb.StringProperty()
	senttoemail=ndb.StringProperty()
	practice=ndb.KeyProperty(kind="practice")
	created=ndb.DateTimeProperty(auto_now_add=True)
	sent=ndb.DateTimeProperty()
	dob=ndb.StringProperty() #there is no particular reason that we will need the DOB as a computable field. Save parsing
	sendercopy=ndb.BooleanProperty(default=False)
	mailbody=""
	
	def setaddr(self,addrlist):
		self.address=pickle.dumps(addrlist)
		
	def sendemail(self,template,customemail=None):
		recipient=self.practice.get()
		mailtext=template.render({'user':self,'practice':recipient})
		message=mail.EmailMessage(sender="PID Optout <info@optout.appspotmail.com",subject="Patient Identifiable Data Optout")
		message.body=mailtext
		self.mailbody=mailtext #store for other use
		if customemail==None:
			message.to="%s <%s>" % (recipient.name,recipient.bestemail())
			self.senttoemail=recipient.bestemail()
		else :
			message.to="%s <%s>" % (recipient.name,customemail)
			self.senttoemail=customemail
		message.headers={'On-Behalf-Of':self.useremail}
		message.cc=self.useremail
		#self.send()
		self.sent=datetime.datetime.now()
		
	def setpractice(self,practiceid):
		practice=ndb.Key('practice',practiceid) #Capital K needed there or difficult bug to trace
		if practice!=None :
			self.practice=practice
		else :
			raise "Practice Not Found"
		
	def addressline(self):
		address=pickle.loads(self.address)
		for line in address:
			yield line
				
class emailAddress(ndb.Model):
	count=ndb.IntegerProperty()
	
	def increment() :
		count=count+1
