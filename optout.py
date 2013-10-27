import webapp2
import jinja2
import os
import urllib2
import xml.etree.ElementTree as ET
import models
import pickle
from google.appengine.ext import ndb
from google.appengine.api import mail
from client import captcha
import secrets

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)+'/templates'),
    extensions=['jinja2.ext.autoescape'])
    
class Letter(webapp2.RequestHandler):
	def post(self):
		"""Generates a letter in RTF format customised with the users details"""
		details={}
		details['name']=self.request.get('name')
		details['address1']=self.request.get('addr1')
		details['address2']=self.request.get('addr2')
		details['address3']=self.request.get('addr3')
		details['address4']=self.request.get('addr4')
		details['dob']=self.request.get('dob')
		details['practice']=models.practice.get_by_id(self.request.get('practice'))
		template_values=details
		template = JINJA_ENVIRONMENT.get_template('letter.rtf')
		self.response.headers.add('Content-Type', 'text/rtf; charset=utf8')
		self.response.headers.add('Content-Disposition','attachment; filename=GPLetter.rtf')
		self.response.write(template.render(template_values))
		
class semail(webapp2.RequestHandler):
	def post(self):
		"""Generates the email to be sent to the practice"""
		mail_record=models.request_email()
		address=[]
		mail_record.name=self.request.get('name')
		address.append(self.request.get('addr1'))
		address.append(self.request.get('addr2'))
		address.append(self.request.get('addr3'))
		address.append(self.request.get('addr4'))
		mail_record.setaddr(address)
		mail_record.dob=self.request.get('dob')
		copysender=self.request.get('sendcopy')
		if (copysender=="on"):
			mail_record.sendercopy=True
		mail_record.useremail=self.request.get('fromemail')
		try:
			mail_record.setpractice(self.request.get('practice'))
		except:
			raise webapp2.exc.HTTPNotFound('Practice could not be identified')
		validation=captcha.submit(self.request.get('recaptcha_challenge_field'),self.request.get('recaptcha_response_field'),secrets.recaptcha_private,os.environ['REMOTE_ADDR'])
		if validation.is_valid :
			mailtemplate=JINJA_ENVIRONMENT.get_template('email.txt')
			mail_record.sendemail(mailtemplate,self.request.get('useremail'))
			suppliedaddress=self.request.get('useremail') #the email address supplied by the user
			if len(suppliedaddress)>3:
				email=models.emailAddress.get_by_id(suppliedaddress,parent=mail_record.practice)
				if email==None :
					newemail=models.emailAddress(id=suppliedaddress,parent=mail_record.practice,count=1)
					newemail.put()
				else:
					email.increment()
					email.put()
			template=JINJA_ENVIRONMENT.get_template('sendsuccessful.html')
			self.response.write(template.render({'email':mail_record.mailbody.replace("\n","<br />"),'name':self.request.get('name')}))
		else :
			template= JINJA_ENVIRONMENT.get_template('senderror.html')
			self.response.write(template.render({'error':validation.error_code}))
		mail_record.put()


class PracticeList(webapp2.RequestHandler):
	def get(self):
		"""Look up postcode and generate list of practices. Also saves the list of practices to the datastore"""
		header={'user-agent':'care.data optout requestor. Urllib2 in python'} # A user agent seems to be compulsory for NHS Choices
		try:
			request=urllib2.Request("http://v1.syndication.nhschoices.nhs.uk/organisations/gppractices/postcode/%s.xml?apikey=%s&range=10" % (urllib2.quote(self.request.get("postcode")),secrets.apikey),headers=header)
			tree=ET.fromstring(urllib2.urlopen(request).read())
		except urllib2.HTTPError, X :
			if X.code==400:
				template=JINJA_ENVIRONMENT.get_template('nopostcode.html')
			else :
				template=JINJA_ENVIRONMENT.get_template('choiceserror.html')
			self.response.write(template.render({'error':X}))
		else:
			namespace="{http://syndication.nhschoices.nhs.uk/services}" #XML namespace - saves a lot of typing
			practices=[]
			for surgery in tree.iter(namespace+'organisationSummary'):
				name=surgery.find(namespace+'name').text
				ods=surgery.find(namespace+'odsCode').text
				address=[]
				for addrline in surgery.find(namespace+'address').iter(namespace+'addressLine'):
					address.append(addrline.text)
				postcode=surgery.find(namespace+'address').find(namespace+'postcode').text
				location=surgery.find(namespace+'geographicCoordinates')
				longitude=float(location.find(namespace+'longitude').text)
				latitude=float(location.find(namespace+'latitude').text)
				try:
					email=surgery.find(namespace+'contact').find(namespace+'email').text
				except:
					email=None
				#saving the practices in a local cache. Saves on NHS Choices lookups
				practices.append(models.practice.get_or_insert(ods,name=name,address=pickle.dumps(address),postcode=postcode,choicesemail=email,location=ndb.GeoPt(latitude,longitude)))
			logo=tree.find('{http://www.w3.org/2005/Atom}logo').text
			tracker=tree.find(namespace+'tracking').text
			template = JINJA_ENVIRONMENT.get_template('practicelist.html')
			self.response.write(template.render({'practicelist':practices,'logo':logo,'tracking':tracker}))

	

application= webapp2.WSGIApplication([('/find', PracticeList),('/letter',Letter),('/email',semail)],debug=True)
