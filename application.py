import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])
    
class MainPage(webapp2.RequestHandler):
	def get(self):
		template_values=(address1:"3 Badgers Close",address2:"Wanborough",address3:"Swindon",name:"Gavin Jamie")
		template = JINJA_ENVIRONMENT.get_template('letter.rtf')
        self.response.write(template.render(template_values))

application= webapp2.WSGIApplication([('/', MainPage),],debug=True)
